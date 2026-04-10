"""
main.py — L.I.A. (Local Intelligent Assistant) — Main Loop
"""

import os
import json
import asyncio
import sys
import re
import base64
import hashlib
import subprocess
from pathlib import Path
import mouse
import keyboard

# ==========================================
# ENVIRONMENT SETUP
# ==========================================
os.environ["KMP_DUPLICATE_LIB_OK"]      = "TRUE"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"
os.environ["PYTHONUTF8"]                 = "1"

# ==========================================
# IMPORTS
# ==========================================
from mcp import stdio_client, ClientSession, StdioServerParameters

import config
import memory
import skills as skills_mod
from web_input_watcher import start_web_input_watcher
from mouth import speak as gerar_voz, start_voice_consumer, clear_queue, is_speaking
from i18n  import t

# MCP: pip install na primeira execução + ferramentas que abrem navegador podem levar minutos.
MCP_TOOL_TIMEOUT_SEC = 100

# ==========================================
# UTILITIES
# ==========================================
def _write_status(msg: str):
    """Write current processing status to DB for the dashboard to display."""
    try:
        config.run_sql(
            "INSERT OR REPLACE INTO system_state (key, text_value) VALUES (?, ?)",
            ("status_msg", msg)
        )
    except Exception:
        pass


def _format_tools(mcp_tools) -> list[dict]:
    return [{
        "type": "function",
        "function": {
            "name":        tool.name,
            "description": tool.description,
            "parameters":  tool.inputSchema
        }
    } for tool in mcp_tools.tools]


def _clean_response(text: str) -> str:
    """Strip system tags and fake tool-call JSON blocks from AI responses."""
    if not text:
        return "Done!"
    text = re.sub(r'<function=.*?>.*?</function>', '', text, flags=re.DOTALL)
    text = re.sub(r'\[DEBUG_METADATA\].*?\n\n',   '', text, flags=re.DOTALL)
    # Remove fake JSON tool-calls some models generate when they don't have real tools
    for pattern in [r'"tool_code"', r'"tool_use"', r'"visual_analysis"', r'"image_url"',
                    r'"tool"', r'"web_search"', r'"params"', r'"function"']:
        text = re.sub(rf'```(?:json)?\s*\{{[^`]*{pattern}[^`]*\}}\s*```', '', text, flags=re.DOTALL)
        text = re.sub(rf'^\s*\{{[^}}]*{pattern}[^}}]*\}}\s*$', '', text, flags=re.DOTALL | re.MULTILINE)
    return text.strip() or "Action completed."


def _unwrap_exception(e, level=0) -> str:
    prefix = "   " * level + "└ "
    if hasattr(e, "exceptions"):
        lines = [f"{prefix}ExceptionGroup ({len(e.exceptions)} sub-errors):"]
        for sub in e.exceptions:
            lines.append(_unwrap_exception(sub, level + 1))
        return "\n".join(lines)
    return f"{prefix}{type(e).__name__}: {e}"


# ==========================================
# INTENT CLASSIFIER
# ==========================================
async def classify_intent(message: str) -> str:
    """
    Use a small fast model to classify message intent.
    Returns: "vision" | "code" | "general"
    Roleplay/affection is ONLY activated manually via the dashboard toggle.
    """
    prompt = (
        "Classify the message below into ONE category. Reply ONLY the category word.\n\n"
        "- vision: user wants the AI to look at the screen or analyze an image\n"
        "- code: user wants help writing, fixing or understanding programming code\n"
        "- general: everything else\n\n"
        f"Message: {message}"
    )
    try:
        r = await asyncio.to_thread(
            config.client_groq.chat.completions.create,
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=5,
            temperature=0.0
        )
        cat = r.choices[0].message.content.strip().lower()
        return cat if cat in ("vision", "code", "general") else "general"
    except Exception:
        return "general"


# ==========================================
# MICROPHONE PREP
# ==========================================
async def prepare_mic():
    await clear_queue()
    config.mic_state = "listening"
    _write_status("🎤 Listening...")


# ==========================================
# SCREEN HASH (background vision)
# ==========================================
_last_screen_hash = ""

async def screen_changed() -> bool:
    global _last_screen_hash
    try:
        from mss import mss
        with mss() as sct:
            shot  = sct.grab(sct.monitors[1])
            data  = bytes(shot.rgb)[::4]
            h     = hashlib.md5(data).hexdigest()
        if h == _last_screen_hash:
            return False
        if _last_screen_hash and sum(a != b for a, b in zip(h, _last_screen_hash)) < 4:
            return False
        _last_screen_hash = h
        return True
    except Exception:
        return False


# ==========================================
# MEETING DETECTOR
# ==========================================
_MEETING_KEYWORDS = ["meet.google", "teams.microsoft", "zoom.us", "whereby", "webex"]

def detect_meeting() -> bool:
    try:
        import win32gui
        title = win32gui.GetWindowText(win32gui.GetForegroundWindow()).lower()
        if any(k in title for k in _MEETING_KEYWORDS + ["meeting", " call"]):
            return True
    except Exception:
        pass
    return False


# ==========================================
# IMAGE LOADER
# ==========================================
def _load_image_b64(url_path: str) -> dict | None:
    try:
        name    = url_path.split("/")[-1]
        path    = Path(config.BASE_DIR) / "uploads" / name
        data    = path.read_bytes()
        ext     = name.split(".")[-1].lower()
        mime    = {"jpg":"image/jpeg","jpeg":"image/jpeg","png":"image/png",
                   "gif":"image/gif","webp":"image/webp"}.get(ext, "image/png")
        b64     = base64.b64encode(data).decode()
        print(t("ai.image_loading", name=name, size=len(data)//1024))
        return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}
    except Exception as e:
        print(t("ai.image_error", name=url_path.split("/")[-1], e=e))
        return None


def _read_text_file(url_path: str, original_name: str) -> str:
    try:
        name = url_path.split("/")[-1]
        path = Path(config.BASE_DIR) / "uploads" / name
        content = path.read_text(encoding="utf-8", errors="ignore")[:4000]
        return f"\n\n[File content: '{original_name}']:\n{content}"
    except Exception:
        return ""


# ==========================================
# MAIN LOOP
# ==========================================
class _ReloadMCP(Exception):
    pass


async def assistant_loop():
    print(t("system.boot",    mode=config.CURRENT_MODE.upper()))
    print(t("system.hotkeys"))
    print("=" * 50)

    system_commands = {
        "[SYSTEM: CLEAR_CHAT]": lambda: config.clear_history(),
        "[SYSTEM: RELOAD]":     lambda: config.reload_all()
    }

    # Session is created lazily on first message, not at boot
    session_id  = None
    session_log = []

    while True:
        print(t("mcp.connecting"))
        # Garante que roda no mesmo Python da Maya e herda as variáveis (UTF-8, etc)
        params = StdioServerParameters(
            command=sys.executable, 
            args=["-u", "server_mcp.py"], 
            env=os.environ.copy()
        )

        try:
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as mcp:
                    await mcp.initialize()
                    raw_tools  = await mcp.list_tools()
                    tools_json = _format_tools(raw_tools)
                    print(t("mcp.connected", n=len(tools_json)))

                    reload_mcp = False
                    while not reload_mcp:
                        try:
                            session_id = await _process_turn(
                                mcp, tools_json, system_commands, session_log, session_id
                            )
                        except _ReloadMCP:
                            reload_mcp = True
                        except Exception as e:
                            print(t("turn.error_recovery", e=_unwrap_exception(e)))
                            _write_status("")
                            await gerar_voz("I ran into a small issue. Could you repeat that?")

        # Não usar BaseException: KeyboardInterrupt (Ctrl+C) herdaria disso e o loop
        # faria sleep(5)+reconnect em loop — parece “travamento” ao fechar.
        except Exception as e:
            print(t("mcp.error", e=_unwrap_exception(e)))
            _end_session(session_id, session_log)
            session_log = []
            session_id  = None   # will be re-created on next message
            print(t("mcp.reconnecting"))
            await asyncio.sleep(5)


async def _process_turn(mcp, tools_json, system_commands, session_log, session_id):
    """One complete turn: listen → process → respond. Returns current session_id."""

    # ── INPUT ─────────────────────────────────────────────────────────
    raw_input    = ""
    special_mode = None

    from ears import ouvir_microfone, ouvir_continuo_vad
    listen_method = config.config_data.get("audio", {}).get("metodo_escuta", "atalho")

    if listen_method == "silero":
        if mouse.is_pressed("x2"):
            await prepare_mic()
            raw_input    = ouvir_microfone("\n📸 [Manual Vision]...", "x2")
            special_mode = "vision"
        else:
            raw_input    = await asyncio.to_thread(ouvir_continuo_vad)
            special_mode = "chat"
    else:
        while True:
            if config.pending_web_input:
                raw_input    = config.pending_web_input
                config.pending_web_input = None
                special_mode = "chat"
                print(t("turn.web_received"))
                break
            if mouse.is_pressed("x"):
                await prepare_mic()
                raw_input    = ouvir_microfone(f"\n🎙️ [{config.CURRENT_MODE.upper()}] Speaking...", "x")
                special_mode = "chat"
                break
            elif mouse.is_pressed("x2"):
                await prepare_mic()
                raw_input    = ouvir_microfone("\n📸 [Manual Vision]...", "x2")
                special_mode = "vision"
                break
            await asyncio.sleep(0.05)

    if not raw_input and special_mode == "chat":
        return session_id

    # ── NORMALIZE INPUT ───────────────────────────────────────────────
    attachments  = []
    has_image    = False
    message_text = ""

    if isinstance(raw_input, dict):
        attachments  = raw_input.get("arquivos", [])
        message_text = raw_input.get("texto", "").strip()
        display_text = raw_input.get("conteudo_completo", message_text)
        has_image    = any(a.get("tipo") == "imagem" for a in attachments)
        user_message = message_text or display_text
        print(t("turn.attachment", n=len(attachments), text=message_text[:60]))
    else:
        user_message = str(raw_input)
        message_text = user_message
        display_text = user_message

    print(t("turn.you", text=user_message[:80]))

    # ── SYSTEM COMMANDS ───────────────────────────────────────────────
    msg_lower = user_message.lower()

    reload_phrases = ["update tools", "reload mcp", "restart server", "reload tools"]
    if any(p in msg_lower for p in reload_phrases):
        print(t("turn.reload_mcp"))
        await gerar_voz("Restarting my tools, one moment!")
        raise _ReloadMCP()

    chat_activate   = ["let's chat", "chat mode", "casual mode", "let's talk", "want to chat"]
    chat_deactivate = ["stop chatting", "normal mode", "focus mode", "back to normal"]
    if any(p in msg_lower for p in chat_activate):
        skills_mod.activate()
        await gerar_voz("Chat mode on! Let's talk.")
        return session_id
    if any(p in msg_lower for p in chat_deactivate):
        skills_mod.deactivate()
        await gerar_voz("Back to normal mode!")
        return session_id

    if special_mode == "vision":
        user_message += " (Please look at my screen now to understand the context.)"
        display_text  = user_message

    # ── CREATE SESSION ON FIRST MESSAGE ──────────────────────────────
    # Session is not created at boot — only when the user actually sends a message.
    if session_id is None:
        session_id = config.start_new_session()
        config.set_current_session(session_id)
        print(t("session.new", id=session_id))

    # ── SAVE TO HISTORY ───────────────────────────────────────────────
    config.add_to_history("user", display_text)
    session_log.append(f"User: {user_message[:100]}")

    config.update_roleplay_state()
    asyncio.ensure_future(asyncio.to_thread(config.compress_history_if_needed))

    # ── RAG ───────────────────────────────────────────────────────────
    memories = await asyncio.to_thread(memory.search_memories, user_message, 4, 0.42)
    memory_block = (
        "\n\n[🧠 RELEVANT MEMORIES]\n" + "\n".join(f"- {m}" for m in memories)
    ) if memories else ""

    # ── SKILL INJECTION ───────────────────────────────────────────────
    skill_injection = skills_mod.get_prompt_injection() if not has_image else ""

    # ── BUILD API MESSAGES ────────────────────────────────────────────
    summary   = config.get_status_summary()
    metadata = (
        f"[SYSTEM CONTEXT]\n{summary}{memory_block}{skill_injection}\n\n"
        "NATIVE TOOL USE: You must use the provided tool-calling capability for any actions. "
        "NEVER manually write tags like <function> or XML/JSON blocks in your text response. "
        "Only call a tool if the user EXPLICITLY asked for an action (open apps, search, music, commands). "
        "NEVER call tools for greetings, casual conversation, or affectionate messages. "
        "When in doubt, provide a standard text response without using tools."
    )
    history_base = list(config.history[:-1])   # exclude last (the user msg just added)

    if has_image:
        parts = [{"type": "text", "text": message_text or "Describe what you see in this image."}]
        for att in attachments:
            if att.get("tipo") == "imagem":
                block = _load_image_b64(att["url"])
                if block:
                    parts.append(block)
        # Vision: minimal system prompt (avoids fake tool-call JSON)
        api_messages = (
            [{"role": "system", "content": config.personality_context}]
            + [m for m in history_base if m["role"] != "system"][-8:]
            + [{"role": "user", "content": parts}]
        )
    else:
        extra_context = ""
        for att in attachments:
            if att.get("tipo") == "arquivo":
                extra_context += _read_text_file(att["url"], att.get("nome", ""))
        api_messages = (
            history_base
            + [{"role": "system", "content": metadata}]
            + [{"role": "user",   "content": f"{user_message}{extra_context}"}]
        )

    # ── MODEL ROUTING ─────────────────────────────────────────────────
    model_main    = config.config_data.get("modelo_principal", "deepseek/deepseek-chat")
    model_vision  = config.config_data.get("modelo_visao",     "google/gemini-2.0-flash-001")
    model_code    = config.config_data.get("modelo_codigo",    "anthropic/claude-3.5-sonnet")
    model_persona = config.config_data.get("modelo_roleplay",  "nousresearch/hermes-3-llama-3.1-405b")

    if config.ROLEPLAY_ACTIVE:
        intent      = "roleplay"
        final_model = model_persona
        print(t("ai.roleplay", model=final_model))
    elif has_image or special_mode == "vision":
        intent      = "vision"
        final_model = model_vision
        print(t("ai.vision", model=final_model))
    else:
        intent = await classify_intent(user_message)
        final_model = {"vision": model_vision,
                       "code":   model_code}.get(intent, model_main)
        print(t("ai.intent", intent=intent, model=final_model))

    # ── API CALL ──────────────────────────────────────────────────────
    response_text = ""

    if has_image:
        _write_status("🖼️ Analyzing image...")
        def _call_vision():
            if config.CURRENT_MODE == "openrouter" and config.client_openrouter:
                return config.client_openrouter.chat.completions.create(model  = config.config_data.get("modelo_visao",     "google/gemini-2.0-flash-001"), messages=api_messages, temperature=0.7)
            elif config.CURRENT_MODE == "groq" and config.client_groq:
                return config.client_groq.chat.completions.create(
                    model  = config.config_data.get("modelo_visao",     "meta-llama/llama-4-scout-17b-16e-instruct"), messages=api_messages, temperature=0.7)
            else:
                return config.client_openai.chat.completions.create(
                    model="gpt-4o-mini", messages=api_messages, temperature=0.7)
        
        r = await asyncio.to_thread(_call_vision)
        response_text = r.choices[0].message.content or ""

    else:
        _write_status("⚙️ Generating response...")

        # Roleplay mode: no tools — the persona model should respond freely
        use_tools = tools_json if not config.ROLEPLAY_ACTIVE else []

        def _call_chat():
            if config.CURRENT_MODE == "openrouter" and config.client_openrouter:
                return config.client_openrouter.chat.completions.create(
                    model=final_model, messages=api_messages,
                    temperature=0.6, tools=use_tools or None)
            elif config.CURRENT_MODE == "groq" and config.client_groq:
                return config.client_groq.chat.completions.create(
                    model=final_model, messages=api_messages,
                    temperature=0.6, tools=use_tools or None)
            else:
                return config.client_openai.chat.completions.create(
                    model="gpt-4o-mini", messages=api_messages,
                    tools=use_tools or None)

        r = await asyncio.to_thread(_call_chat)
        msg = r.choices[0].message
        response_text = msg.content or ""

       # --- Tool calls (MCP) ---
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            tool_names = [tc.function.name for tc in msg.tool_calls]
            print(t("mcp.tool_using", tools=", ".join(tool_names)))
            
            results = []
            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments)
                try:
                    res = await asyncio.wait_for(
                        mcp.call_tool(tc.function.name, arguments=args),
                        timeout=MCP_TOOL_TIMEOUT_SEC,
                    )
                    text_result = (res.content[0].text if res.content else "")
                except Exception as e:
                    text_result = f"Error executing {tc.function.name}: {str(e)}"
                
                results.append(text_result)
                print(t("mcp.tool_result", result=text_result[:80]))

                # --- Process results after the loop finishes ---
                combined_result = " ".join(results).strip()

                if combined_result.startswith("[DIRECT]"):
                # Fast track: return the plugin's response directly to the UI
                    response_text = combined_result.replace("[DIRECT]", "").strip()
                else:
                    # Agentic track: send the technical result back to the LLM for interpretation
                    _write_status("Processing tool data...")
                    ctx = [
                        {"role": "system", "content": config.personality_context},
                        {"role": "user", "content": (
                            f"Technical results from tools:\n\n{combined_result}\n\n"
                            "Respond NATURALLY to the user based on this data. "
                            "Talk directly TO the user using 'you'. "
                            "Maintain the assigned persona at all times."
                        )}
                    ]
                    try:
                        if config.CURRENT_MODE == "openrouter":
                            r2 = config.client_openrouter.chat.completions.create(
                                model=model_main, messages=ctx, temperature=0.7)
                        elif config.CURRENT_MODE == "groq":
                            r2 = config.client_groq.chat.completions.create(
                                model=model_main, messages=ctx, temperature=0.7)
                        else:
                            r2 = config.client_openai.chat.completions.create(
                                model=model_main, messages=ctx)
                        response_text = r2.choices[0].message.content or ""
                    
                    except Exception as e:
                        response_text = "Sorry, I had trouble processing the tool results."

    # ── FINALIZE ──────────────────────────────────────────────────────
    for tag, action in system_commands.items():
        if tag in (response_text or ""):
            action()
            break

    final_text = _clean_response(response_text)
    config.add_to_history("assistant", final_text)
    session_log.append(f"AI: {final_text[:100]}")

    _write_status("")
    config.mic_state = "idle"

    if final_text:
        await gerar_voz(final_text)

    asyncio.ensure_future(memory.extract_and_save_facts(user_message, final_text))
    return session_id


def _end_session(session_id, log: list):
    if session_id is None or not log:
        return
    try:
        first = next((m for m in log if m.startswith("User:")), "")
        title   = first.replace("User:", "").strip()[:50] or "Chat"
        summary = "\n".join(log[-10:])
        config.end_session(session_id, title, summary)
    except Exception:
        pass


# ==========================================
# BACKGROUND LOOPS
# ==========================================
async def loop_watchdog():
    while True:
        mins = config.WATCHDOG_INTERVAL or 10
        await asyncio.sleep(mins * 60)
        if (config.WATCHDOG_ENABLED
                and not config.FOCUS_MODE
                and not config.DND_MODE
                and config.mic_state == "idle"
                and not is_speaking()):
            print(t("system.watchdog"))
            config.pending_web_input = "Hey, what are you up to right now?"


async def loop_vision_bg():
    await asyncio.sleep(30)
    while True:
        await asyncio.sleep(60)
        if not config.VISION_BG_ENABLED:
            continue
        if config.FOCUS_MODE or config.DND_MODE or is_speaking():
            continue
        try:
            if await screen_changed():
                print(t("system.vision_bg"))
                import eyes
                desc = await eyes.analisar_tela_groq("Briefly describe what is on the screen.")
                if desc:
                    config.run_sql(
                        "INSERT OR REPLACE INTO system_state (key, text_value) VALUES (?, ?)",
                        ("vision_desc", desc)
                    )
        except Exception as e:
            print(t("system.vision_error", e=e))


async def loop_meeting_monitor():
    while True:
        await asyncio.sleep(120)
        try:
            in_meeting = await asyncio.to_thread(detect_meeting)
            if in_meeting != config.DND_MODE:
                config.DND_MODE = in_meeting
                print(t("system.meeting_on" if in_meeting else "system.meeting_off"))
        except Exception:
            pass


async def loop_weekly_maintenance():
    await asyncio.sleep(3600)
    while True:
        print(t("system.maintenance"))
        await asyncio.to_thread(memory.apply_decay, 30)
        await asyncio.sleep(7 * 24 * 3600)


# ==========================================
# SHUTDOWN
# ==========================================
def force_quit():
    """Encerra sem esperar threads do executor (VAD, STT em to_thread)."""
    try:
        keyboard.unhook_all()
    except Exception:
        pass
    print(t("system.shutdown"))
    os._exit(0)


def _install_interrupt_handlers() -> None:
    """
    Ctrl+C no Windows/Linux entrega SIGINT; o loop asyncio + to_thread() pode demorar
    minutos a encerrar se o microfone estiver bloqueado. Este handler sai na hora.
    """
    import signal

    def _fast_exit(_signum=None, _frame=None) -> None:
        force_quit()

    for sig in (getattr(signal, "SIGINT", None), getattr(signal, "SIGTERM", None)):
        if sig is None:
            continue
        try:
            signal.signal(sig, _fast_exit)
        except (ValueError, OSError):
            pass


async def start_system():
    config.initialize_db()
    memory.initialize_table()
    memory.warmup_embedding_model()
    skills_mod.sync_state()
    start_voice_consumer()

    await asyncio.gather(
        assistant_loop(),
        loop_watchdog(),
        loop_vision_bg(),
        loop_meeting_monitor(),
        loop_weekly_maintenance(),
    )


# ==========================================
# BOOT
# ==========================================
if __name__ == "__main__":
    _install_interrupt_handlers()
    start_web_input_watcher()

    def _toggle_focus():
        config.FOCUS_MODE = not config.FOCUS_MODE
        print(t("system.focus_on" if config.FOCUS_MODE else "system.focus_off"))

    keyboard.add_hotkey("ctrl+alt+m", lambda: subprocess.Popen(
        'start msedge --app="http://127.0.0.1:8000" || '
        'start chrome --app="http://127.0.0.1:8000"', shell=True))
    keyboard.add_hotkey("ctrl+alt+f", _toggle_focus)

    if os.name == "nt":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(start_system())
    except KeyboardInterrupt:
        force_quit()
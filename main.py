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

import core.config as config
import core.memory as memory
import core.skills as skills
import core.tool_retrieval as tool_retrieval
from core.web_input_watcher import start_web_input_watcher
from core.mouth import speak as gerar_voz, start_voice_consumer, clear_queue, is_speaking
from core.i18n import t
from core.tool_executor import execute_tool

# MCP: pip install na primeira execução + ferramentas que abrem navegador podem levar minutos.
MCP_TOOL_TIMEOUT_SEC = 100

active_system_context = ""

# ==========================================
# AUTO-RELOAD SYSTEM
# ==========================================
RELOAD_SIGNAL_FILE = os.path.join(config.BASE_DIR, "data", "reload_signal.flag")
CLEAR_SESSION_FILE = os.path.join(config.BASE_DIR, "data", "clear_session.flag")
def _extract_system_context(text: str) -> tuple[str, str]:
    """
    Extract [SYSTEM] content from tool responses.
    
    Returns:
        tuple: (cleaned_text, system_context)
        - cleaned_text: Text without [SYSTEM] tags
        - system_context: Content inside [SYSTEM] tags (or empty string)
    """
    if not text or '[SYSTEM]' not in text:
        return text, ""
    
    # Extract system context
    import re
    pattern = r'\[SYSTEM\](.*?)\[/SYSTEM\]'
    matches = re.findall(pattern, text, re.DOTALL)
    
    # Remove [SYSTEM] tags from text
    cleaned = re.sub(pattern, '', text, flags=re.DOTALL).strip()
    
    # Join all system contexts
    system_context = '\n'.join(matches).strip()
    
    return cleaned, system_context

def _get_file_type(att):
    return att.get("tipo") or att.get("type")

def _get_file_name(att):
    return att.get("nome") or att.get("name")

def check_reload_signal():
    """Verifica se há sinal para recarregar configurações"""
    if os.path.exists(RELOAD_SIGNAL_FILE):
        try:
            os.remove(RELOAD_SIGNAL_FILE)
            print("🔄 Recarregando configurações...")
            config.reload_all()
        except Exception as e:
            print(f"⚠️ Erro ao recarregar: {e}")

def _start_reload_monitor():
    """Monitora arquivo de reload em thread separada (igual ao web_input_watcher)"""
    import threading
    import time
    
    def _monitor_loop():
        while True:
            try:
                check_reload_signal()
                
                # Monitora clear session igual ao web_input_watcher
                if os.path.exists(CLEAR_SESSION_FILE):
                    os.remove(CLEAR_SESSION_FILE)
                    config.pending_clear_session = True
                    print("🧹 Sinal de limpar sessão detectado")
                
                time.sleep(0.5)  # Verifica a cada 500ms
            except Exception as e:
                print(f"⚠️ [Reload Monitor] Erro: {e}")
    
    thread = threading.Thread(target=_monitor_loop, daemon=True)
    thread.start()
    print("✅ [Reload Monitor] Iniciado")

# ==========================================
# UTILITIES
# ==========================================
def _write_status(msg: str):
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
    
    # ✅ NOVO: Extract and remove [SYSTEM] content FIRST
    text, _ = _extract_system_context(text)  # Remove [SYSTEM] but don't use it here
    
    text = re.sub(r'<function=.*?>.*?</function>', '', text, flags=re.DOTALL)
    text = re.sub(r'\[DEBUG_METADATA\].*?\n\n',   '', text, flags=re.DOTALL)
    
    # Remove fake JSON tool-calls
    for pattern in [r'"tool_code"', r'"tool_use"', r'"visual_analysis"', r'"image_url"',
                    r'"tool"', r'"web_search"', r'"params"', r'"function"']:
        text = re.sub(rf'```(?:json)?\s*\{{[^`]*{pattern}[^`]*\}}\s*```', '', text, flags=re.DOTALL)
        text = re.sub(rf'^\s*\{{[^}}]*{pattern}[^}}]*\}}\s*$', '', text, flags=re.DOTALL | re.MULTILINE)
    
    # Parse i18n tags BEFORE returning
    text = _parse_i18n_response(text)
    
    return text.strip() or "Action completed."


def _parse_i18n_response(text: str) -> str:
    """
    Parse multilingual tool responses.
    Format: [DIRECT][EN]English text[/EN][PT]Portuguese text[/PT]
    
    Extracts only the text for the current UI language.
    Falls back to original text if no tags found.
    """
    if not text:
        return text
    
    # Get current language from config
    from core.i18n import get_language
    current_lang = get_language() or 'pt'
    
    # Map language codes to tags
    lang_tag = 'EN' if current_lang == 'en' else 'PT'
    
    # Pattern to match [EN]...[/EN] or [PT]...[/PT]
    pattern = rf'\[{lang_tag}\](.*?)\[/{lang_tag}\]'
    matches = re.findall(pattern, text, re.DOTALL)
    
    if matches:
        # Join all matches and remove [DIRECT] tag
        extracted = ' '.join(matches).strip()
        return extracted.replace('[DIRECT]', '').strip()
    
    # No language tags found - return original (still remove [DIRECT])
    return text.replace('[DIRECT]', '').strip()


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
        # Respeita modo local
        if config.CURRENT_MODE.startswith("local") and hasattr(config, 'client_local') and config.client_local:
            local_model = config.config_data.get("modelo_ia_local", "local-model")
            r = await asyncio.to_thread(
                config.client_local.chat.completions.create,
                model=local_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=5,
                temperature=0.0
            )
        elif config.client_groq:
            r = await asyncio.to_thread(
                config.client_groq.chat.completions.create,
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=5,
                temperature=0.0
            )
        else:
            return "general"
        cat = r.choices[0].message.content.strip().lower()
        return cat if cat in ("vision", "code", "general") else "general"
    except Exception:
        return "general"
    
async def classify_action_vs_question(message: str) -> str:
    """
    Use a small fast model to classify if message is an action command or question.
    Returns: "action" | "question"
    """
    prompt = (
        "Classify the message below into ONE category. Reply ONLY the category word.\n\n"
        "- action: user wants to DO something (play music, open app, type text, create file, etc.)\n"
        "- question: user is ASKING about something (what is, which one, do you know, etc.)\n\n"
        f"Message: {message}\n\n"
        "Reply ONLY: action OR question"
    )
    try:
        # Respeita modo local
        if config.CURRENT_MODE.startswith("local") and hasattr(config, 'client_local') and config.client_local:
            local_model = config.config_data.get("modelo_ia_local", "local-model")
            r = await asyncio.to_thread(
                config.client_local.chat.completions.create,
                model=local_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=5,
                temperature=0.0
            )
        elif config.client_groq:
            r = await asyncio.to_thread(
                config.client_groq.chat.completions.create,
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=5,
                temperature=0.0
            )
        else:
            return "action"  # Fallback: assume action (mais seguro)
        
        cat = r.choices[0].message.content.strip().lower()
        return cat if cat in ("action", "question") else "action"
    except Exception:
        return "question"


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
        config.mic_state = "idle"  # Reseta status do microfone
        _write_status("")  # Limpa status do webui
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


def _convert_tools_to_mcp_format(tools_list: list) -> list:
    """
    Converte ferramentas do formato tool_retrieval para o formato MCP esperado.
    
    tool_retrieval retorna: {name, description, input_schema}
    MCP espera: {type: "function", function: {name, description, parameters}}
    """
    return [{
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool.get("input_schema", {})
        }
    } for tool in tools_list]


async def _process_turn(mcp, tools_json, system_commands, session_log, session_id):
    """One complete turn: listen → process → respond. Returns current session_id."""

    # ── INPUT ─────────────────────────────────────────────────────────
    raw_input    = ""
    special_mode = None
    global active_system_context

    from core.ears import listen_button, listen_continuous_vad
    listen_method = config.config_data.get("audio", {}).get("metodo_escuta", "atalho")

    if listen_method == "silero":
        if mouse.is_pressed("x2"):
            await prepare_mic()
            raw_input    = listen_button("\n📸 [Manual Vision]...", "x2")
            special_mode = "vision"
        else:
            result = await asyncio.to_thread(listen_continuous_vad)
            if isinstance(result, dict):
                # É input web
                raw_input = result
                special_mode = "chat"
            else:
                # É transcrição de áudio
                raw_input = result
                special_mode = "chat"
    else:
        while True:
            input_file = os.path.join(config.BASE_DIR, "data", "input_web.json")
            if os.path.exists(input_file):
                try:
                    with open(input_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    os.remove(input_file)  # Remove após ler com sucesso
                    
                    if data.get("comando") == "toggle_batepapo":
                        if data.get("ativo"):
                            skills.activate()
                        else:
                            skills.deactivate()
                        continue
                    
                    if data.get("conteudo_completo") or data.get("arquivos"):
                        config.pending_web_input = data
                        print(t("turn.web_received"))
                        break
                except Exception as e:
                    print(f"❌ Erro ao ler input_web.json: {e}")
                    os.remove(input_file)  # Remove arquivo corrompido

            if config.pending_web_input:
                raw_input = config.pending_web_input
                config.pending_web_input = None
                special_mode = "chat"
                print(t("turn.web_received"))
                break
            if mouse.is_pressed("x"):
                await prepare_mic()
                raw_input    = listen_button(f"\n🎙️ [{config.CURRENT_MODE.upper()}] Speaking...", "x")
                special_mode = "chat"
                break
            elif mouse.is_pressed("x2"):
                await prepare_mic()
                raw_input    = listen_button("\n📸 [Manual Vision]...", "x2")
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
        has_image = any(_get_file_type(a) == "imagem" for a in attachments)
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
        skills.activate()
        await gerar_voz("Chat mode on! Let's talk.")
        return session_id
    if any(p in msg_lower for p in chat_deactivate):
        skills.deactivate()
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

    # ── VERIFICA CLEAR SESSION ANTES DE ADICIONAR AO HISTÓRICO ────────
    # CRÍTICO: Verifica aqui para limpar ANTES de add_to_history
    if hasattr(config, 'pending_clear_session') and config.pending_clear_session:
        config.pending_clear_session = False
        print("🧹 Limpando sessão (antes de adicionar nova mensagem)...")
        session_log.clear()
        session_id = None
        
        # Espera banco limpar
        for _ in range(20):
            rows = config.run_sql("SELECT COUNT(*) FROM chat_history", fetch=True)
            if rows and rows[0][0] == 1:
                break
            await asyncio.sleep(0.05)
        
        config.history = [
            {"role": row[0], "content": row[1]} 
            for row in config.run_sql("SELECT role, content FROM chat_history ORDER BY id", fetch=True)
        ]
        print(f"   Histórico recarregado: {len(config.history)} mensagem(ns)")

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
    skill_injection = skills.get_prompt_injection() if not has_image else ""

    # ── BUILD API MESSAGES ────────────────────────────────────────────
    summary   = config.get_status_summary()
    metadata = (
    f"[SYSTEM CONTEXT]\n{summary}{memory_block}{skill_injection}\n\n"
    "⚠️ CRITICAL: NEVER write <function=...> or XML/JSON tags in your response!\n"
    "Use ONLY the native tool calling system. Writing function tags = INSTANT FAILURE.\n\n"
    "CRITICAL TOOL USAGE RULES:\n\n"
    "1. QUESTIONS vs COMMANDS:\n"
    "   Questions (what/which/do you know) → ANSWER ONLY, NO TOOLS\n"
    "   Commands (play/open/create) → USE TOOLS\n\n"
    "2. ONLY use action tools with EXPLICIT verbs:\n"
    "   play, open, show, create, send, delete, execute, start\n"
    "   toca, abre, mostra, cria, envia, deleta, executa, inicia\n\n"
    "3. NEVER for: questions, greetings, casual talk, statements, memory\n\n"
    "KEY EXAMPLES:\n"
    "✅ 'Play my favorite playlist' → use youtube_player\n"
    "❌ 'What is my favorite playlist?' → answer only (NO TOOL)\n"
    "❌ 'My favorite is X' → conversational response\n\n"
    "TOOL RULES:\n"
    "- If tool unavailable, ask user to rephrase with action verb\n\n"
    "[NOTE] Prefer specialized master tools over general ones."
)
    history_base = list(config.history[:-1])   # exclude last (the user msg just added)

    if has_image:
        parts = [{"type": "text", "text": message_text or "Describe what you see in this image."}]
        for att in attachments:
            if _get_file_type(att) == "imagem":
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
            if _get_file_type(att) == "arquivo":
                file_name = att.get("nome") or att.get("name", "")
                extra_context += _read_text_file(att["url"], file_name)
                
    # ── MODEL ROUTING ─────────────────────────────────────────────────
    current_provider = config.config_data.get("modo_ia", "groq")
    provider_models = config.config_data.get("modelos", {}).get(current_provider, {})

    # Modo local: usa o mesmo modelo para TUDO
    if config.CURRENT_MODE.startswith("local"):
        local_model = config.config_data.get("modelo_ia_local", "local-model")
        model_main = model_vision = model_code = model_persona = local_model
        print(f"🤖 Modo local: Usando '{local_model}' para todas as tarefas")
    else:
        model_main    = provider_models.get("modelo_principal", "llama-3.3-70b-versatile")
        model_vision  = provider_models.get("modelo_visao",     "llama-3.2-90b-vision-preview")
        model_code    = provider_models.get("modelo_codigo",    "llama-3.3-70b-versatile")
        model_persona = provider_models.get("modelo_roleplay",  "llama-3.3-70b-versatile")
    
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
        # Corrige o log para modo local
        display_model = config.config_data.get("modelo_ia_local") if config.CURRENT_MODE.startswith("local") else final_model
        print(t("ai.intent", intent=intent, model=display_model))

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
            elif config.CURRENT_MODE.startswith("local") and hasattr(config, 'client_local') and config.client_local:
                local_model = config.config_data.get("modelo_ia_local", "local-model")
                return config.client_local.chat.completions.create(model=local_model, messages=api_messages, temperature=0.7)
            else:
                return config.client_openai.chat.completions.create(
                    model="gpt-4o-mini", messages=api_messages, temperature=0.7)
        
        r = await asyncio.to_thread(_call_vision)
        response_text = r.choices[0].message.content or ""

    else:
        _write_status("⚙️ Generating response...")
        action_classification = await classify_action_vs_question(user_message)
        is_action_request = (action_classification == "action")
        
        # Usa RAG para buscar ferramentas relevantes (embeddings)
        relevant_tools_data = tool_retrieval.get_relevant_tools_for_ai(
            user_message, 
            top_k=5, 
            is_action_request=is_action_request
        )
        relevant_tools = _convert_tools_to_mcp_format(relevant_tools_data)
        use_tools = relevant_tools if not config.ROLEPLAY_ACTIVE else []
        
        # ✅ ADICIONAR: Processar anexos de arquivo
        extra_context = ""
        for att in attachments:
            if _get_file_type(att) == "arquivo":
                file_name = att.get("nome") or att.get("name", "")
                extra_context += _read_text_file(att["url"], file_name)
        
        system_context_msg = []
        if active_system_context:
            system_context_msg = [{"role": "system", "content": active_system_context}]
        
        few_shot_example = []
        if use_tools:  # Only add if tools are available
            few_shot_example = [
                {"role": "user", "content": "Activate the typing master"},
                {"role": "assistant", "content": "", "tool_calls": [
                    {
                        "id": "call_example",
                        "type": "function",
                        "function": {
                            "name": "activate_master",
                            "arguments": '{"master_name": "typing_control"}'
                        }
                    }
                ]},
                {"role": "tool", "tool_call_id": "call_example", "content": "Master activated successfully"}
            ]
        
        api_messages = (
            history_base
            + [{"role": "system", "content": metadata}]
            + system_context_msg
            + few_shot_example
            + [{"role": "user", "content": f"{user_message}{extra_context}"}]  # ← Agora extra_context existe!
        )

        def _call_chat():
            if config.CURRENT_MODE == "openrouter" and config.client_openrouter:
                return config.client_openrouter.chat.completions.create(
                    model=final_model, messages=api_messages,
                    temperature=0.6, tools=use_tools or None)
            elif config.CURRENT_MODE == "groq" and config.client_groq:
                return config.client_groq.chat.completions.create(
                    model=final_model, messages=api_messages,
                    temperature=0.6, tools=use_tools or None)
            elif config.CURRENT_MODE.startswith("local") and hasattr(config, 'client_local') and config.client_local:
                local_model = config.config_data.get("modelo_ia_local", "local-model")
                return config.client_local.chat.completions.create(model=local_model, messages=api_messages, temperature=0.6, tools=use_tools or None)
            else:
                return config.client_openai.chat.completions.create(
                    model="gpt-4o-mini", messages=api_messages,
                    tools=use_tools or None)

        # ✅ ADICIONAR TRY/EXCEPT AQUI:
        try:
            r = await asyncio.to_thread(_call_chat)
        except Exception as api_error:
            error_msg = str(api_error)
            
            # ✅ FALLBACK: Detect XML syntax and convert to tool calling
            if 'tool_use_failed' in error_msg and '<function=' in error_msg:
                print("⚠️ [FALLBACK] LLM used XML syntax - parsing and executing...")
                
                # Extract tool name and arguments from error
                match = re.search(r"<function=([^:>]+):?([^>]*)>", error_msg)
                
                if match:
                    tool_name = match.group(1).strip()
                    args_str = match.group(2).strip()
                    
                    # Parse arguments
                    try:
                        args = json.loads(args_str) if args_str and args_str != '{}' else {}
                    except:
                        args = {}
                    
                    print(f"✅ [FALLBACK] Parsed: {tool_name}({args})")
                    
                    # Execute tool via MCP
                    try:
                        res = await asyncio.wait_for(
                            mcp.call_tool(tool_name, arguments=args),
                            timeout=MCP_TOOL_TIMEOUT_SEC,
                        )
                        result_text = (res.content[0].text if res.content else "")
                        print(f"✅ [FALLBACK] Executed successfully!")
                        
                        # Return as if it was a normal response
                        response_text = result_text
                        await gerar_voz(response_text)
                        return session_id
                        
                    except Exception as tool_error:
                        print(f"❌ [FALLBACK] Execution failed: {tool_error}")
                        raise api_error
                else:
                    print("❌ [FALLBACK] Could not parse XML")
                    raise api_error
            else:
                # Not XML error - re-raise
                raise
        
        msg = r.choices[0].message
        response_text = msg.content or ""
        
       # --- Tool calls (MCP) ---
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            tool_names = [tc.function.name for tc in msg.tool_calls]
            print(t("mcp.tool_using", tools=", ".join(tool_names)))
            
            results = []
            system_contexts = []  # Store system contexts
            
            
            for tc in msg.tool_calls:
                tool_name = tc.function.name
                args = json.loads(tc.function.arguments)
                
                try:
                    res = await asyncio.wait_for(
                        mcp.call_tool(tool_name, arguments=args),
                        timeout=MCP_TOOL_TIMEOUT_SEC,
                    )
                    text_result = (res.content[0].text if res.content else "")
                except Exception as e:
                    text_result = f"Error executing {tc.function.name}: {str(e)}"
                
                results.append(text_result)
                
                # ✅ NOVO: Extrair contexto de sistema ANTES de processar
                cleaned_result, system_context = _extract_system_context(text_result)
                
                if system_context:
                    system_contexts.append(system_context)
                    print(f"🔍 [SYSTEM Context] {system_context[:100]}...")  # Debug
                
                results.append(cleaned_result)
                print(t("mcp.tool_result", result=cleaned_result[:80]))

            # --- Process results after the loop finishes ---
            combined_result = " ".join(results).strip()

            if combined_result.startswith("[DIRECT]"):
                # Fast track: return the plugin's response directly to the UI
                response_text = combined_result.replace("[DIRECT]", "").strip()
            else:
                # Agentic track: send the technical result back to the LLM for interpretation
                _write_status("Processing tool data...")
                
                # ✅ NOVO: Inject system context into the LLM prompt
                system_injection = ""
                if system_contexts:
                    system_injection = "\n\n[INTERNAL CONTEXT - Use this data to answer the user]:\n" + "\n".join(system_contexts)
                
                ctx = [
                    {"role": "system", "content": config.personality_context},
                    {"role": "user", "content": (
                        f"Technical results from tools:\n\n{combined_result}{system_injection}\n\n"
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
                    elif config.CURRENT_MODE.startswith("local") and hasattr(config, 'client_local') and config.client_local:
                        local_model = config.config_data.get("modelo_ia_local", "local-model")
                        r2 = config.client_local.chat.completions.create(model=local_model, messages=ctx, temperature=0.7)
                    else:
                        r2 = config.client_openai.chat.completions.create(
                            model=model_main, messages=ctx)
                    response_text = r2.choices[0].message.content or ""
                    
                except Exception as e:
                    response_text = "Sorry, I had trouble processing the tool results."

    # ── FINALIZE ──────────────────────────────────────────────────────
    # Detect and warn about old function syntax
    if response_text and '<function=' in response_text:
        print("⚠️ [SYSTEM] LLM attempted to use old <function> syntax - this will fail!")
        # Strip the invalid syntax
        response_text = re.sub(r'<function=.*?>.*?</function>', '', response_text, flags=re.DOTALL)
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
                import core.eyes as eyes
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
    
    # Desativa master ativo antes de sair
    try:
        config.run_sql("UPDATE active_master SET master_name = NULL WHERE id = 1")
        print("🔧 Master desativado")
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
    skills.sync_state()
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
    _start_reload_monitor()  # Monitora reloads continuamente

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
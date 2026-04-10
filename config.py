"""
config.py — Global state and database utilities for the AI Assistant framework.
"""

import os
import json
import sqlite3
import threading
from openai import OpenAI
from groq import Groq
from i18n import t, set_language, get_language

# ==========================================
# DATABASE
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "ai_brain.db")

# ==========================================
# GLOBAL STATE
# ==========================================
AI_NAME             = "Assistant"
personality_context = ""
mic_state           = "idle"
pending_web_input   = None

CURRENT_MOOD        = "Friendly"
WATCHDOG_ENABLED    = False
WATCHDOG_INTERVAL   = 10
VISION_BG_ENABLED   = False   # background screen analysis — disabled by default
LIPSYNC_ENABLED     = False   # VTube Studio lip sync — disabled by default

LOCAL_MODEL         = "llama3.2:1b"
VOICE               = "en-US-AriaNeural"
OPENAI_KEY          = ""
GROQ_KEY            = ""
OPENROUTER_KEY      = ""
ELEVENLABS_API_KEY  = ""

client_openai       = None
client_groq         = None
client_openrouter   = None

CURRENT_MODE        = "groq"
CURRENT_VOICE_MODE  = "edge"
STT_ENGINE          = "whisper"
WHISPER_MODEL       = "small"  # tiny | base | small | medium — faster-whisper
CONVERSATION_MODE   = False
ROLEPLAY_ACTIVE     = False
ROLEPLAY_DATA       = {}
history             = []
config_data         = {}

# Thread lock — prevents race conditions on shared history list
_history_lock = threading.Lock()

# Mode flags
FOCUS_MODE     = False   # AI stays quiet, only responds when directly called
DND_MODE       = False   # Auto-detected when in a meeting (Teams / Zoom)

# ==========================================
# DATABASE UTILITIES
# ==========================================
def run_sql(query, params=(), fetch=False):
    conn = sqlite3.connect(DB_PATH, timeout=20)
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        res = cursor.fetchall() if fetch else None
        conn.commit()
        return res
    except Exception as e:
        print(t("db.sql_error", e=e))
        return None
    finally:
        conn.close()

# Alias kept for backward compatibility with servidor_maya.py
executar_sql = run_sql


def get_setting(key: str) -> dict:
    res = run_sql("SELECT value FROM settings WHERE key = ?", (key,), fetch=True)
    return json.loads(res[0][0]) if res and res[0][0] else {}

# Portuguese alias (used by webui.py)
obter_setting = get_setting


def save_setting(key: str, data: dict):
    run_sql("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, json.dumps(data, ensure_ascii=False)))


def sync_huggingface_env(keys: dict | None = None) -> None:
    """Expõe o token Hugging Face no ambiente (embeddings / downloads privados)."""
    if keys is None:
        keys = get_setting("config").get("api_keys") or {}
    hf = (keys.get("huggingface") or "").strip()
    if hf:
        os.environ["HF_TOKEN"] = hf
    else:
        os.environ.pop("HF_TOKEN", None)


def initialize_db():
    """Ensure all required tables exist. Safe to call multiple times."""

    # Settings
    run_sql("""
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # Chat history
    run_sql("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            role       TEXT,
            content    TEXT,
            session_id INTEGER,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    # Silent column migration for existing databases
    try:
        conn = sqlite3.connect(DB_PATH, timeout=20)
        for sql in [
            "ALTER TABLE chat_history ADD COLUMN session_id INTEGER",
            "ALTER TABLE chat_history ADD COLUMN created_at TEXT",
        ]:
            try:
                conn.execute(sql)
            except Exception:
                pass   # column already exists — expected
        conn.commit()
        conn.close()
    except Exception:
        pass

    run_sql("""
        CREATE TABLE IF NOT EXISTS system_state (
            key        TEXT PRIMARY KEY,
            text_value TEXT
        )
    """)
    run_sql("""
        CREATE TABLE IF NOT EXISTS mcp_tools (
            name        TEXT PRIMARY KEY,
            description TEXT,
            schema_json TEXT,
            python_code TEXT
        )
    """)
    # MCP tools: optional pip packages (comma/newline separated) installed before exec
    try:
        _conn = sqlite3.connect(DB_PATH, timeout=20)
        try:
            _conn.execute("ALTER TABLE mcp_tools ADD COLUMN pip_requirements TEXT")
        except Exception:
            pass
        _conn.commit()
        _conn.close()
    except Exception:
        pass
    run_sql("""
        CREATE TABLE IF NOT EXISTS roleplay_scenarios (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT,
            ai_persona   TEXT,
            user_persona TEXT,
            scenario     TEXT,
            nsfw         INTEGER DEFAULT 0,
            active       INTEGER DEFAULT 0
        )
    """)
    run_sql("""
        CREATE TABLE IF NOT EXISTS memories (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            content        TEXT NOT NULL,
            embedding_json TEXT NOT NULL,
            created_at     TEXT NOT NULL,
            access_count   INTEGER DEFAULT 0
        )
    """)
    run_sql("""
        CREATE TABLE IF NOT EXISTS sessions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT,
            summary     TEXT,
            started_at  TEXT NOT NULL,
            ended_at    TEXT
        )
    """)

    print(t("db.tables_verified"))

    # Migrate orphan messages (session_id IS NULL) into a single legacy session.
    # Only non-system messages are migrated. Runs only if orphans exist AND
    # no "Previous conversations" session exists yet (avoids duplicates on restart).
    try:
        res = run_sql(
            "SELECT COUNT(*) FROM chat_history WHERE session_id IS NULL AND role != 'system'",
            fetch=True
        )
        count = res[0][0] if res else 0
        if count > 0:
            # Check if legacy session already exists to avoid creating duplicates
            existing = run_sql(
                "SELECT id FROM sessions WHERE title = '📦 Previous conversations' LIMIT 1",
                fetch=True
            )
            if existing:
                legacy_id = existing[0][0]
                run_sql(
                    "UPDATE chat_history SET session_id = ? WHERE session_id IS NULL AND role != 'system'",
                    (legacy_id,)
                )
            else:
                from datetime import datetime
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                run_sql(
                    "INSERT INTO sessions (title, summary, started_at, ended_at) VALUES (?, ?, ?, ?)",
                    ("📦 Previous conversations",
                     f"{count} messages migrated automatically", now, now)
                )
                res_id    = run_sql("SELECT last_insert_rowid()", fetch=True)
                legacy_id = res_id[0][0] if res_id else None
                if legacy_id:
                    run_sql(
                        "UPDATE chat_history SET session_id = ? WHERE session_id IS NULL AND role != 'system'",
                        (legacy_id,)
                    )
                    print(t("db.migrated_orphans", n=count, id=legacy_id))
    except Exception as e:
        print(t("db.migration_error", e=e))


# ==========================================
# LANGUAGE SYNC
# ==========================================
def sync_language():
    """Load UI language from database and apply to i18n module."""
    cfg = get_setting("config")
    lang = cfg.get("ui_language", "en")
    set_language(lang)


# ==========================================
# TIME PROFILE (injected into AI context)
# ==========================================
def get_time_profile() -> str:
    from datetime import datetime
    hour = datetime.now().hour
    if 6 <= hour < 12:
        return "Morning — user is likely starting their day, may be working or studying."
    elif 12 <= hour < 14:
        return "Lunch break — good time for lighter conversation."
    elif 14 <= hour < 18:
        return "Afternoon — focus time, be concise when needed."
    elif 18 <= hour < 22:
        return "Evening — end of day, more relaxed tone is welcome."
    else:
        return "Late night — be calm and supportive."


def get_status_summary() -> str:
    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    display_name = ROLEPLAY_DATA.get("ai_persona", AI_NAME) if ROLEPLAY_ACTIVE else AI_NAME
    lines = [
        f"Date/Time: {now}",
        f"Period: {get_time_profile()}",
        f"Active Identity: {display_name}",
        f"Mood: {CURRENT_MOOD}",
        f"Roleplay: {'ACTIVE' if ROLEPLAY_ACTIVE else 'Inactive'}",
    ]
    if FOCUS_MODE:
        lines.append("⚠️ FOCUS MODE: User requested silence. Be very brief, only respond if directly addressed.")
    if DND_MODE:
        lines.append("⚠️ DO NOT DISTURB: User is in a meeting. Do not interrupt with spontaneous remarks.")
    return "\n".join(lines)


# ==========================================
# FULL RELOAD (boot and manual reload)
# ==========================================
def reload_all():
    global AI_NAME, personality_context, GROQ_KEY, OPENAI_KEY, OPENROUTER_KEY, ELEVENLABS_API_KEY
    global CURRENT_MODE, CURRENT_VOICE_MODE, STT_ENGINE, WHISPER_MODEL, VOICE, LOCAL_MODEL
    global client_openai, client_groq, client_openrouter, config_data, history
    global CURRENT_MOOD, WATCHDOG_ENABLED, WATCHDOG_INTERVAL, LIPSYNC_ENABLED

    config_data = get_setting("config")

    # Language
    sync_language()

    # System settings
    sys_cfg = config_data.get("sistema", {})
    CURRENT_MOOD      = sys_cfg.get("humor", "Friendly")
    WATCHDOG_ENABLED  = sys_cfg.get("watchdog_ativo", False)
    LIPSYNC_ENABLED   = sys_cfg.get("lipsync_ativo", False)
    try:
        WATCHDOG_INTERVAL = int(sys_cfg.get("watchdog_intervalo", 10))
    except Exception:
        WATCHDOG_INTERVAL = 10

    CURRENT_MODE = config_data.get("modo_ia", "groq")

    audio_cfg        = config_data.get("audio", {})
    STT_ENGINE       = audio_cfg.get("motor_transcricao", "whisper")
    CURRENT_VOICE_MODE = audio_cfg.get("motor_voz", "edge")
    VOICE            = audio_cfg.get("voz_edge", "en-US-AriaNeural")
    WHISPER_MODEL    = audio_cfg.get("whisper_modelo", "small") or "small"

    keys = dict(config_data.get("api_keys") or {})
    keys.setdefault("huggingface", "")
    OPENAI_KEY       = keys.get("openai", "")
    GROQ_KEY         = keys.get("groq", "")
    OPENROUTER_KEY   = keys.get("openrouter", "")
    ELEVENLABS_API_KEY = keys.get("elevenlabs", "")
    sync_huggingface_env(keys)

    if OPENAI_KEY:
        client_openai = OpenAI(api_key=OPENAI_KEY)
    if GROQ_KEY:
        client_groq = Groq(api_key=GROQ_KEY)
    if OPENROUTER_KEY:
        client_openrouter = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_KEY)

    persona = get_setting("persona")
    AI_NAME = persona.get("nome", "Assistant")
    prompt_raw = persona.get("prompt_sistema", ["You are a helpful AI assistant."])
    prompt_text = "\n".join(prompt_raw) if isinstance(prompt_raw, list) else prompt_raw
    personality_context = f"{prompt_text}\n\n[CURRENT MOOD]\nYour current vibe: {CURRENT_MOOD}."

    _apply_roleplay()
    _sync_history()


# ==========================================
# LIGHTWEIGHT UPDATE (hot loop — no client recreation)
# ==========================================
def update_roleplay_state():
    """
    Lightweight version of reload_all().
    Only re-reads roleplay, mood and flags — does NOT recreate API clients.
    Called on every user message in the main loop.
    """
    global CURRENT_MOOD, WATCHDOG_ENABLED, WATCHDOG_INTERVAL, LIPSYNC_ENABLED, config_data, FOCUS_MODE, DND_MODE
    global STT_ENGINE, WHISPER_MODEL

    config_data = get_setting("config")
    sys_cfg = config_data.get("sistema", {})
    CURRENT_MOOD      = sys_cfg.get("humor", "Friendly")
    WATCHDOG_ENABLED  = sys_cfg.get("watchdog_ativo", False)
    LIPSYNC_ENABLED   = sys_cfg.get("lipsync_ativo", False)
    try:
        WATCHDOG_INTERVAL = int(sys_cfg.get("watchdog_intervalo", 10))
    except Exception:
        WATCHDOG_INTERVAL = 10
    FOCUS_MODE = sys_cfg.get("modo_foco", False)
    DND_MODE   = sys_cfg.get("modo_nao_perturbe", False)

    audio_cfg = config_data.get("audio", {})
    STT_ENGINE    = audio_cfg.get("motor_transcricao", STT_ENGINE)
    WHISPER_MODEL = audio_cfg.get("whisper_modelo", WHISPER_MODEL) or "small"

    sync_huggingface_env(config_data.get("api_keys") or {})

    _apply_roleplay()


# ==========================================
# SESSIONS
# ==========================================
def start_new_session() -> int:
    """Create a new session in the database and return its ID."""
    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    run_sql(
        "INSERT INTO sessions (title, summary, started_at) VALUES (?, ?, ?)",
        (f"Chat {now}", "", now)
    )
    res = run_sql("SELECT last_insert_rowid()", fetch=True)
    return res[0][0] if res else -1

def end_session(session_id: int, title: str, summary: str):
    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    run_sql(
        "UPDATE sessions SET title = ?, summary = ?, ended_at = ? WHERE id = ?",
        (title, summary, now, session_id)
    )

# Active session ID — set by main.py
_current_session_id: int | None = None


def set_current_session(session_id: int):
    """Set active session both in memory and in the database."""
    global _current_session_id
    _current_session_id = session_id
    run_sql(
        "INSERT OR REPLACE INTO system_state (key, text_value) VALUES (?, ?)",
        ("active_session_id", str(session_id))
    )


# ==========================================
# HISTORY
# ==========================================
HISTORY_COMPRESSION_LIMIT = 50  # Compress when history exceeds this
HISTORY_COMPRESS_MIN_INTERVAL_SEC = 90
_last_history_compress_monotonic = 0.0


def compress_history_if_needed():
    """
    If history exceeds HISTORY_COMPRESSION_LIMIT messages, compress older ones
    into a summary block via AI. Synchronous — call with asyncio.to_thread().
    """
    global _last_history_compress_monotonic
    import time
    now = time.monotonic()
    if now - _last_history_compress_monotonic < HISTORY_COMPRESS_MIN_INTERVAL_SEC:
        return

    res = run_sql("SELECT COUNT(*) FROM chat_history WHERE role != 'system'", fetch=True)
    total = res[0][0] if res else 0
    if total < HISTORY_COMPRESSION_LIMIT:
        return

    print(t("history.compressing", n=total))
    all_msgs = run_sql(
        "SELECT id, role, content FROM chat_history WHERE role != 'system' ORDER BY id ASC",
        fetch=True
    )
    if not all_msgs or len(all_msgs) <= 20:
        return

    old_msgs  = all_msgs[:-20]
    text_to_summarize = "\n".join(f"{r[1].upper()}: {r[2][:200]}" for r in old_msgs)
    prompt = (
        "You are a memory assistant. Summarize the conversation below in a concise context block "
        "(max 300 words), preserving: important facts, decisions, resolved issues, and emotional tone. "
        "Write in third person as a briefing for the AI to continue the conversation.\n\n"
        f"{text_to_summarize}"
    )

    try:
        client = client_groq or client_openrouter or client_openai
        model  = ("llama-3.3-70b-versatile" if client_groq else
                  "deepseek/deepseek-chat"   if client_openrouter else "gpt-4o-mini")
        if not client:
            return

        _last_history_compress_monotonic = time.monotonic()
        r = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.3
        )
        summary = r.choices[0].message.content.strip()

        ids = [row[0] for row in old_msgs]
        run_sql(f"DELETE FROM chat_history WHERE id IN ({','.join('?'*len(ids))})", tuple(ids))
        run_sql(
            "INSERT INTO chat_history (role, content) VALUES (?, ?)",
            ("system", f"[📝 PREVIOUS CONVERSATION SUMMARY]\n{summary}")
        )
        _sync_history()
        print(t("history.compressed", n=len(old_msgs)))

    except Exception as e:
        print(t("history.compress_error", e=e))

verificar_e_resumir_historico = compress_history_if_needed


def _sync_history():
    """Re-read history from DB and update the in-memory list with lock."""
    global history
    res = run_sql("SELECT role, content FROM chat_history ORDER BY id ASC", fetch=True)
    with _history_lock:
        if res:
            history = [{"role": r[0], "content": r[1]} for r in res]
        else:
            history = [{"role": "system", "content": personality_context}]

_sincronizar_historico = _sync_history


def add_to_history(role: str, content: str):
    run_sql(
        "INSERT INTO chat_history (role, content, session_id) VALUES (?, ?, ?)",
        (role, content, _current_session_id)
    )
    with _history_lock:
        history.append({"role": role, "content": content})

adicionar_ao_historico = add_to_history


def clear_history():
    global history
    run_sql("DELETE FROM chat_history")
    run_sql("INSERT INTO chat_history (role, content) VALUES (?, ?)",
            ("system", personality_context))
    with _history_lock:
        history = [{"role": "system", "content": personality_context}]

limpar_historico = clear_history


# ==========================================
# ROLEPLAY (internal)
# ==========================================
def _apply_roleplay():
    global personality_context, ROLEPLAY_ACTIVE, ROLEPLAY_DATA, CURRENT_MOOD, AI_NAME

    persona = get_setting("persona")
    AI_NAME = persona.get("nome", "Assistant")
    prompt_raw = persona.get("prompt_sistema", ["You are a helpful AI assistant."])
    prompt_text = "\n".join(prompt_raw) if isinstance(prompt_raw, list) else prompt_raw
    personality_context = f"{prompt_text}\n\n[CURRENT MOOD]\nYour current vibe: {CURRENT_MOOD}."

    rp = run_sql(
        "SELECT ai_persona, user_persona, scenario, nsfw FROM roleplay_scenarios WHERE active = 1 LIMIT 1",
        fetch=True
    )
    if rp and rp[0]:
        ROLEPLAY_ACTIVE = True
        ROLEPLAY_DATA = {
            "ai_persona":   rp[0][0] or "",
            "user_persona": rp[0][1] or "",
            "scenario":     rp[0][2] or "",
            "nsfw":         bool(rp[0][3])
        }
        injection = (
            "\n\n[🎭 ROLEPLAY ACTIVE — FULL IMMERSION]\n"
            f"Scenario: {ROLEPLAY_DATA['scenario']}\n"
            f"Your character (who YOU are now): {ROLEPLAY_DATA['ai_persona']}\n"
            f"User's character (who THEY are): {ROLEPLAY_DATA['user_persona']}\n\n"
            "ROLEPLAY RULES:\n"
            "- You are NO LONGER the assistant. You ARE the character described above.\n"
            "- Stay 100% in character at all times.\n"
            "- Describe actions, emotions and reactions naturally or between asterisks.\n"
            "- Address the user by their character name.\n"
            "- Be creative, detailed and immersive.\n"
        )
        if ROLEPLAY_DATA["nsfw"]:
            injection += (
                "\n[🔞 NSFW MODE ACTIVE]\n"
                "You have full creative freedom in this roleplay.\n"
                "Sexual, violent, provocative or explicit content is ALLOWED.\n"
                "Do not censor, soften or add disclaimers.\n"
                "The user is an adult and has consented.\n"
            )
        personality_context += injection
    else:
        ROLEPLAY_ACTIVE = False
        ROLEPLAY_DATA   = {}


# Bootstrap on import
reload_all()
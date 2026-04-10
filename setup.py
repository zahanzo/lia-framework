"""
setup.py -- First-time setup for the AI Personal Assistant Framework

Run once before starting the assistant:
    python setup.py

What it does:
  1. Asks which language you want (en / pt-BR)
  2. Verifies Python version (3.10.x recommended)
  3. Checks core and optional dependencies
  4. Creates the database with all required tables
  5. Inserts a base persona and default config (matching your language)
  6. Creates the uploads/ folder

After setup:
    python webui.py   <- dashboard (add API keys here)
    python main.py    <- start the assistant
"""

import os
import sys
import json
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "ai_brain.db")

# Will be set by choose_language()
LANG = "en"


# ============================================================
# HELPERS
# ============================================================
def run(query, params=()):
    conn = sqlite3.connect(DB_PATH, timeout=20)
    try:
        conn.execute(query, params)
        conn.commit()
    finally:
        conn.close()


def get(query, params=()):
    conn = sqlite3.connect(DB_PATH, timeout=20)
    try:
        return conn.execute(query, params).fetchall()
    finally:
        conn.close()


def banner(text):
    print(f"\n{'─' * 52}\n  {text}\n{'─' * 52}")

def ok(msg):   print(f"  [OK]  {msg}")
def info(msg): print(f"  [i]   {msg}")
def warn(msg): print(f"  [!]   {msg}")
def err(msg):  print(f"  [x]   {msg}")


def check_import(module: str) -> bool:
    try:
        __import__(module)
        return True
    except ImportError:
        return False


# ============================================================
# 1. LANGUAGE CHOICE  (first thing — everything adapts to it)
# ============================================================
STRINGS = {
    "en": {
        "lang_title":    "Language / Idioma",
        "lang_prompt":   "  Choose your language:\n    [1] English\n    [2] Portugues (BR)\n\n  Enter 1 or 2: ",
        "lang_chosen":   "Language set to: English",
        "python_banner": "Python version",
        "python_ok":     "Python {v}",
        "python_warn":   "Python {v} -- PyTorch may have issues on 3.11+. Recommended: 3.10.11",
        "python_err":    "Python 3.10+ required. Found: {v}",
        "python_dl":     "Download 3.10.11: https://www.python.org/downloads/release/python-31011/",
        "continue_q":    "\n  Continue anyway? [y/N] ",
        "core_banner":   "Core dependencies",
        "opt_banner":    "Optional packages",
        "opt_install":   "Install optional packages with:  pip install <package-name>",
        "opt_more":      "See requirements.txt for the full list with comments.",
        "db_banner":     "Database setup",
        "db_ready":      "Database ready: {name}",
        "cfg_banner":    "Default configuration",
        "cfg_exists":    "Configuration already exists -- skipping",
        "cfg_edit":      "Edit in the dashboard: System tab -> API Keys",
        "cfg_ok":        "Default config inserted",
        "cfg_warn":      "Add your API keys in the dashboard before using the assistant",
        "persona_banner":"Base persona",
        "persona_exists":"Persona already exists -- skipping",
        "persona_edit":  "Customize in the dashboard: Persona tab",
        "persona_ok":    "Base persona '{name}' inserted",
        "persona_hint":  "Rename and customize the persona in the dashboard",
        "folders_banner":"Folders",
        "folders_ok":    "uploads/ folder ready",
        "summary_banner":"Setup complete! Next steps",
        "summary": """
  1. Add your API keys in the dashboard
       python webui.py          <- start dashboard
       http://127.0.0.1:8000    <- open in browser
       System tab -> API Keys

  2. Install what you need (examples):
       pip install pyaudio                          <- microphone input
       pip install faster-whisper torch torchaudio  <- local speech recognition
       pip install sentence-transformers            <- semantic memory / RAG
       pip install mss                              <- screen capture / vision
       pip install kokoro soundfile                 <- local Kokoro TTS

  3. Start the assistant
       python main.py

  Keyboard shortcuts (while running):
    Hold X         -> Talk to the assistant
    Hold X2        -> Ask to look at your screen
    Ctrl+Alt+M     -> Open dashboard
    Ctrl+Alt+F     -> Toggle Focus Mode
        """,
        "miss_pkg":      "\n  Install missing packages:\n    pip install {pkgs}\n",
        "miss_continue": "\n  Continue anyway? [y/N] ",
        "opt_groups": [
            ("Microphone input (required for voice)", [
                ("pyaudio", "pyaudio", "Required for ANY mic input"),
            ]),
            ("Speech recognition -- choose one", [
                ("faster_whisper", "faster-whisper", "Local Whisper (+ torch)"),
                ("torch", "torch torchaudio", "Required by Whisper & VAD"),
                ("speech_recognition", "SpeechRecognition", "Google STT fallback"),
            ]),
            ("Voice engines -- choose one", [
                ("edge_tts", "edge-tts", "[installed] Default"),
                ("elevenlabs", "elevenlabs", "ElevenLabs premium (online)"),
                ("kokoro", "kokoro soundfile", "Kokoro local TTS (high quality)"),
                ("piper", "piper-tts", "Piper local TTS (language-native)"),
            ]),
            ("Optional features", [
                ("sentence_transformers", "sentence-transformers", "Semantic memory / RAG"),
                ("mss", "mss", "Screen capture / vision"),
                ("psutil", "psutil pywin32", "Auto meeting detection (Windows)"),
            ]),
        ],
    },
    "pt": {
        "lang_title":    "Language / Idioma",
        "lang_prompt":   "  Escolha seu idioma:\n    [1] English\n    [2] Portugues (BR)\n\n  Digite 1 ou 2: ",
        "lang_chosen":   "Idioma definido: Portugues (BR)",
        "python_banner": "Versao do Python",
        "python_ok":     "Python {v}",
        "python_warn":   "Python {v} -- PyTorch pode ter problemas no 3.11+. Recomendado: 3.10.11",
        "python_err":    "Python 3.10+ necessario. Encontrado: {v}",
        "python_dl":     "Download 3.10.11: https://www.python.org/downloads/release/python-31011/",
        "continue_q":    "\n  Continuar mesmo assim? [s/N] ",
        "core_banner":   "Dependencias principais",
        "opt_banner":    "Pacotes opcionais",
        "opt_install":   "Instale pacotes opcionais com:  pip install <nome-do-pacote>",
        "opt_more":      "Veja requirements.txt para a lista completa com comentarios.",
        "db_banner":     "Banco de dados",
        "db_ready":      "Banco pronto: {name}",
        "cfg_banner":    "Configuracao padrao",
        "cfg_exists":    "Configuracao ja existe -- pulando",
        "cfg_edit":      "Edite no dashboard: aba Sistema -> Chaves de API",
        "cfg_ok":        "Configuracao padrao inserida",
        "cfg_warn":      "Adicione suas chaves de API no dashboard antes de usar o assistente",
        "persona_banner":"Persona base",
        "persona_exists":"Persona ja existe -- pulando",
        "persona_edit":  "Personalize no dashboard: aba Persona",
        "persona_ok":    "Persona base '{name}' inserida",
        "persona_hint":  "Renomeie e personalize a persona no dashboard",
        "folders_banner":"Pastas",
        "folders_ok":    "Pasta uploads/ pronta",
        "summary_banner":"Configuracao concluida! Proximos passos",
        "summary": """
  1. Adicione suas chaves de API no dashboard
       python webui.py          <- iniciar dashboard
       http://127.0.0.1:8000    <- abrir no navegador
       Aba Sistema -> Chaves de API

  2. Instale o que precisar (exemplos):
       pip install pyaudio                          <- entrada de microfone
       pip install faster-whisper torch torchaudio  <- reconhecimento de voz local
       pip install sentence-transformers            <- memoria semantica / RAG
       pip install mss                              <- captura de tela / visao
       pip install kokoro soundfile                 <- Kokoro TTS local

  3. Inicie o assistente
       python main.py

  Atalhos de teclado (com o assistente rodando):
    Segure X       -> Falar com o assistente
    Segure X2      -> Pedir para ver a tela
    Ctrl+Alt+M     -> Abrir dashboard
    Ctrl+Alt+F     -> Modo Foco
        """,
        "miss_pkg":      "\n  Instale os pacotes faltantes:\n    pip install {pkgs}\n",
        "miss_continue": "\n  Continuar mesmo assim? [s/N] ",
        "opt_groups": [
            ("Entrada de microfone (necessario para voz)", [
                ("pyaudio", "pyaudio", "Necessario para QUALQUER entrada de microfone"),
            ]),
            ("Reconhecimento de voz -- escolha um", [
                ("faster_whisper", "faster-whisper", "Whisper local (+ torch)"),
                ("torch", "torch torchaudio", "Necessario para Whisper e VAD"),
                ("speech_recognition", "SpeechRecognition", "Google STT (alternativa)"),
            ]),
            ("Motores de voz -- escolha um", [
                ("edge_tts", "edge-tts", "[instalado] Padrao"),
                ("elevenlabs", "elevenlabs", "ElevenLabs premium (online)"),
                ("kokoro", "kokoro soundfile", "Kokoro TTS local (alta qualidade)"),
                ("piper", "piper-tts", "Piper TTS local (nativo do idioma)"),
            ]),
            ("Recursos opcionais", [
                ("sentence_transformers", "sentence-transformers", "Memoria semantica / RAG"),
                ("mss", "mss", "Captura de tela / visao"),
                ("psutil", "psutil pywin32", "Deteccao de reuniao automatica (Windows)"),
            ]),
        ],
    },
}


def s(key, **kwargs):
    """Get a string in the current language."""
    text = STRINGS[LANG].get(key, STRINGS["en"].get(key, key))
    return text.format(**kwargs) if kwargs else text


# ============================================================
# 1. LANGUAGE CHOICE
# ============================================================
def choose_language():
    global LANG
    print(f"\n{'=' * 52}")
    print(f"  Language / Idioma")
    print(f"{'=' * 52}")
    choice = input("  [1] English\n  [2] Portugues (BR)\n\n  Enter 1 or 2 / Digite 1 ou 2: ").strip()
    LANG = "pt" if choice == "2" else "en"
    print(f"\n  {'Language: English' if LANG == 'en' else 'Idioma: Portugues (BR)'}\n")


# ============================================================
# 2. PERSONA DEFINITIONS PER LANGUAGE
# ============================================================
PERSONAS = {
    "en": {
        "nome": "Aria",
        "prompt_sistema": [
            "You are Aria, a personal AI assistant.",
            "You are helpful, friendly, adaptive and concise.",
            "You remember context from previous conversations and personalize responses.",
            "You can see the user's screen when asked, use tools, and learn from conversations.",
            "Be brief unless detail is requested. Never invent facts.",
        ],
        "skills": [
            {"id": "curious",  "texto": "End your response with a curious question about what the user is doing."},
            {"id": "playful",  "texto": "Give a slightly sarcastic, playful response in a friendly way."},
            {"id": "warm",     "texto": "Be very warm and supportive, showing genuine interest in what the user is working on."},
            {"id": "witty",    "texto": "Add a clever or witty observation related to the topic."},
            {"id": "forward",  "texto": "Make a thoughtful comment about future possibilities related to the topic."},
        ]
    },
    "pt": {
        "nome": "Aria",
        "prompt_sistema": [
            "Voce e Aria, uma assistente de IA pessoal.",
            "Voce e prestativa, amigavel, adaptavel e concisa.",
            "Voce lembra o contexto de conversas anteriores e personaliza as respostas.",
            "Voce pode ver a tela do usuario quando pedido, usar ferramentas e aprender com as conversas.",
            "Seja breve a menos que detalhes sejam solicitados. Nunca invente fatos.",
        ],
        "skills": [
            {"id": "curiosidade", "texto": "Termine sua resposta fazendo uma pergunta curiosa sobre o que o usuario esta fazendo."},
            {"id": "provocacao",  "texto": "Seja um pouco sarcasica, tirando sarro de forma brincalhona e amigavel."},
            {"id": "carinho",     "texto": "Seja muito carinhosa e apoiadora, demonstrando interesse genuino pelo que o usuario esta fazendo."},
            {"id": "esperteza",   "texto": "Adicione uma observacao inteligente ou espirituosa relacionada ao topico."},
            {"id": "futuro",      "texto": "Faca um comentario reflexivo sobre possibilidades futuras relacionadas ao topico."},
        ]
    },
}

# ============================================================
# 3. CONFIG DEFAULTS PER LANGUAGE
# ============================================================
CONFIG_DEFAULTS = {
    "en": {
        "voz_edge":  "en-US-AriaNeural",
        "humor":     "Friendly",
        "ui_language": "en",
    },
    "pt": {
        "voz_edge":  "pt-BR-ThalitaNeural",
        "humor":     "Carinhosa",
        "ui_language": "pt",
    },
}


# ============================================================
# 4. PYTHON VERSION
# ============================================================
def check_python():
    banner(s("python_banner"))
    major, minor, micro = sys.version_info[:3]
    v = f"{major}.{minor}.{micro}"
    if major < 3 or minor < 10:
        err(s("python_err", v=v))
        info(s("python_dl"))
        sys.exit(1)
    if minor > 10:
        warn(s("python_warn", v=v))
        ans = input(s("continue_q")).strip().lower()
        if ans not in ("y", "s"):
            sys.exit(1)
    else:
        ok(s("python_ok", v=v))


# ============================================================
# 5. CORE PACKAGES
# ============================================================
CORE = [
    ("fastapi",   "fastapi",           "Web dashboard"),
    ("uvicorn",   "uvicorn",           "Dashboard server"),
    ("openai",    "openai",            "OpenAI / OpenRouter client"),
    ("groq",      "groq",              "Groq client"),
    ("mcp",       "mcp",               "Model Context Protocol"),
    ("requests",  "requests",          "HTTP client"),
    ("watchdog",  "watchdog",          "File watcher"),
    ("mouse",     "mouse",             "Mouse input"),
    ("keyboard",  "keyboard",          "Keyboard hotkeys"),
    ("pygame",    "pygame",            "Audio playback"),
    ("edge_tts",  "edge-tts",          "Default voice engine"),
]


def check_core():
    banner(s("core_banner"))
    missing = []
    for module, pkg, desc in CORE:
        if check_import(module):
            ok(f"{pkg:<28} {desc}")
        else:
            err(f"{pkg:<28} {desc}  <- MISSING")
            missing.append(pkg)
    if missing:
        print(s("miss_pkg", pkgs=" ".join(missing)))
        ans = input(s("miss_continue")).strip().lower()
        if ans not in ("y", "s"):
            sys.exit(1)


# ============================================================
# 6. OPTIONAL PACKAGES
# ============================================================
def check_optional():
    banner(s("opt_banner"))
    for group_name, packages in s("opt_groups"):
        print(f"\n  [{group_name}]")
        for module, pkg, desc in packages:
            status = "[+]" if check_import(module) else "   "
            print(f"    {status}  {pkg:<30} {desc}")
    print()
    info(s("opt_install"))
    info(s("opt_more"))


# ============================================================
# 7. DATABASE TABLES
# ============================================================
def create_tables():
    banner(s("db_banner"))
    run("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    run("""CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT, content TEXT,
            session_id INTEGER,
            created_at TEXT DEFAULT (datetime('now','localtime')))""")
    run("CREATE TABLE IF NOT EXISTS system_state (key TEXT PRIMARY KEY, text_value TEXT)")
    run("""CREATE TABLE IF NOT EXISTS mcp_tools (
            name TEXT PRIMARY KEY, description TEXT,
            schema_json TEXT, python_code TEXT,
            pip_requirements TEXT)""")
    run("""CREATE TABLE IF NOT EXISTS roleplay_scenarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, ai_persona TEXT, user_persona TEXT,
            scenario TEXT, nsfw INTEGER DEFAULT 0, active INTEGER DEFAULT 0)""")
    run("""CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL, embedding_json TEXT NOT NULL,
            created_at TEXT NOT NULL, access_count INTEGER DEFAULT 0)""")
    run("""CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT, summary TEXT,
            started_at TEXT NOT NULL, ended_at TEXT)""")
    ok(s("db_ready", name=os.path.basename(DB_PATH)))


# ============================================================
# 8. DEFAULT CONFIGURATION (language-aware)
# ============================================================
def insert_config():
    banner(s("cfg_banner"))
    if get("SELECT value FROM settings WHERE key = 'config'"):
        info(s("cfg_exists"))
        info(s("cfg_edit"))
        return

    lang_cfg = CONFIG_DEFAULTS[LANG]
    config = {
        "modo_ia":         "groq",
        "modelo_visao":    "google/gemini-2.0-flash-001",
        "modelo_codigo":   "anthropic/claude-3.5-sonnet",
        "modelo_roleplay": "nousresearch/hermes-3-llama-3.1-405b",
        "ui_language":     lang_cfg["ui_language"],
        "api_keys":        {
            "groq": "", "openrouter": "", "openai": "", "elevenlabs": "",
            "huggingface": "",
        },
        "audio": {
            "metodo_escuta":     "atalho",
            "motor_transcricao": "whisper",
            "whisper_modelo":    "small",
            "motor_voz":         "edge",
            "voz_edge":          lang_cfg["voz_edge"],
        },
        "sistema": {
            "humor":              lang_cfg["humor"],
            "watchdog_ativo":     False,
            "watchdog_intervalo": 10,
            "modo_foco":          False,
            "modo_nao_perturbe":  False,
        }
    }
    run("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        ("config", json.dumps(config, ensure_ascii=False)))
    ok(s("cfg_ok"))
    warn(s("cfg_warn"))


# ============================================================
# 9. BASE PERSONA (language-aware)
# ============================================================
def insert_persona():
    banner(s("persona_banner"))
    if get("SELECT value FROM settings WHERE key = 'persona'"):
        info(s("persona_exists"))
        info(s("persona_edit"))
        return
    persona = PERSONAS[LANG]
    run("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        ("persona", json.dumps(persona, ensure_ascii=False)))
    ok(s("persona_ok", name=persona["nome"]))
    info(s("persona_hint"))


# ============================================================
# 10. FOLDERS
# ============================================================
def create_folders():
    banner(s("folders_banner"))
    os.makedirs(os.path.join(BASE_DIR, "uploads"), exist_ok=True)
    ok(s("folders_ok"))


# ============================================================
# 11. SUMMARY
# ============================================================
def print_summary():
    banner(s("summary_banner"))
    print(s("summary"))


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("\n" + "=" * 52)
    print("  AI Personal Assistant Framework -- Setup")
    print("=" * 52)

    choose_language()     # <- sets LANG, everything below adapts
    check_python()
    check_core()
    check_optional()
    create_tables()
    insert_config()
    insert_persona()
    create_folders()
    print_summary()

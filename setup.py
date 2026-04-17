"""
setup.py -- First-time setup for the L.I.A. (Local Intelligent Assistant) Framework

Run once before starting the assistant:
    python setup.py
"""

import os
import sys
import json
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "ai_brain.db")

# Default language for strings
LANG = "en"

# ============================================================
# DATABASE HELPERS
# ============================================================
def run_query(query, params=()):
    conn = sqlite3.connect(DB_PATH, timeout=20)
    try:
        conn.execute(query, params)
        conn.commit()
    finally:
        conn.close()

def get_query(query, params=()):
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
# SYSTEM CHECKS
# ============================================================
def check_python():
    banner("Python Version Check")
    major, minor, micro = sys.version_info[:3]
    v = f"{major}.{minor}.{micro}"
    if major < 3 or minor < 10:
        err(f"Python 3.10+ required. Found: {v}")
        sys.exit(1)
    ok(f"Python {v} detected")

def check_dependencies():
    banner("Core Dependencies Check")
    core_pkgs = [
        ("fastapi", "fastapi"), ("uvicorn", "uvicorn"), ("openai", "openai"),
        ("groq", "groq"), ("mcp", "mcp"), ("requests", "requests"),
        ("watchdog", "watchdog"), ("mouse", "mouse"), ("keyboard", "keyboard"),
        ("pygame", "pygame"), ("edge_tts", "edge-tts")
    ]
    for mod, pkg in core_pkgs:
        if check_import(mod):
            ok(f"{pkg} is installed")
        else:
            warn(f"{pkg} is MISSING")

# ============================================================
# DATABASE INITIALIZATION
# ============================================================
def create_tables():
    banner("Database Initialization")
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        info(f"Created directory: {DATA_DIR}")

    # Core tables
    run_query("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    
    run_query("""CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT, content TEXT, session_id INTEGER,
            created_at TEXT DEFAULT (datetime('now','localtime')))""")
            
    run_query("CREATE TABLE IF NOT EXISTS system_state (key TEXT PRIMARY KEY, text_value TEXT)")
    
    run_query("""CREATE TABLE IF NOT EXISTS mcp_tools (
            name TEXT PRIMARY KEY, description TEXT, schema_json TEXT, 
            python_code TEXT, pip_requirements TEXT, parent_id TEXT DEFAULT NULL, 
            is_master INTEGER DEFAULT 0, name_pt TEXT, description_pt TEXT, 
            code_file TEXT, is_async INTEGER DEFAULT 0, is_builtin INTEGER DEFAULT 0)""")
            
    run_query("""CREATE TABLE IF NOT EXISTS tool_embeddings (
            tool_name TEXT PRIMARY KEY, description TEXT NOT NULL,
            embedding_json TEXT NOT NULL, indexed_at TEXT NOT NULL)""")
            
    run_query("""CREATE TABLE IF NOT EXISTS active_master (
            id INTEGER PRIMARY KEY CHECK (id = 1), master_name TEXT,
            activated_at TEXT DEFAULT (datetime('now','localtime')))""")

    run_query("""CREATE TABLE IF NOT EXISTS roleplay_scenarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, ai_persona TEXT, 
            user_persona TEXT, scenario TEXT, nsfw INTEGER DEFAULT 0, active INTEGER DEFAULT 0)""")
            
    run_query("""CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT NOT NULL, 
            embedding_json TEXT NOT NULL, created_at TEXT NOT NULL, access_count INTEGER DEFAULT 0)""")
            
    run_query("""CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, summary TEXT,
            started_at TEXT NOT NULL, ended_at TEXT)""")
    
    ok(f"Database ready at {DB_PATH}")

# ============================================================
# CONTENT SEEDING (Tools & Config)
# ============================================================
def insert_default_tools():
    banner("Seeding Global Master Control Tools")
    
    # 384-dimensional neutral vector for multilingual MiniLM models
    neutral_embedding = json.dumps([0.0] * 384)
    
    # These are the global tools the AI needs to manage the context states
    controllers = [
        {
            "name": "activate_master",
            "description": "Activates a master context tool, loading its contextual sub-tools into memory.",
            "schema_json": '{"type": "object", "properties": {"master_name": {"type": "string", "description": "The name of the master to activate"}}, "required": ["master_name"]}',
            "python_code": "# Built-in System Tool - Handled internally by tool_executor.py",
            "name_pt": "Ativar Master",
            "description_pt": "Ativa uma ferramenta de contexto master, carregando as suas sub-ferramentas contextuais para a memória."
        },
        {
            "name": "deactivate_master",
            "description": "Deactivates the currently active master context tool, returning to global tools only.",
            "schema_json": '{"type": "object", "properties": {}}',
            "python_code": "# Built-in System Tool - Handled internally by tool_executor.py",
            "name_pt": "Desativar Master",
            "description_pt": "Desativa a ferramenta de contexto master atualmente ativa, voltando a usar apenas as globais."
        },
        {
            "name": "get_active_master",
            "description": "Checks which master context tool is currently active in the system.",
            "schema_json": '{"type": "object", "properties": {}}',
            "python_code": "# Built-in System Tool - Handled internally by tool_executor.py",
            "name_pt": "Verificar Master Ativo",
            "description_pt": "Verifica qual é a ferramenta de contexto master atualmente ativa no sistema."
        },
        {
            "name": "list_available_masters",
            "description": "Lists all available master context tools that can be activated.",
            "schema_json": '{"type": "object", "properties": {}}',
            "python_code": "# Built-in System Tool - Handled internally by tool_executor.py",
            "name_pt": "Listar Masters Disponíveis",
            "description_pt": "Lista todas as ferramentas de contexto master disponíveis que podem ser ativadas."
        }
    ]
    
    for t in controllers:
        if not get_query("SELECT name FROM mcp_tools WHERE name = ?", (t["name"],)):
            # Note: is_master = 0 because these are GLOBAL tools, not masters themselves.
            # They control the masters.
            run_query("""INSERT INTO mcp_tools 
                   (name, description, schema_json, python_code, is_master, is_builtin, name_pt, description_pt)
                   VALUES (?, ?, ?, ?, 0, 1, ?, ?)""",
                (t["name"], t["description"], t["schema_json"], t["python_code"], 
                 t["name_pt"], t["description_pt"]))
            
            # Seed semantic memory for these tools (using PT/EN description logic)
            run_query("""INSERT OR REPLACE INTO tool_embeddings 
                   (tool_name, description, embedding_json, indexed_at)
                   VALUES (?, ?, ?, datetime('now','localtime'))""",
                (t["name"], t["description_pt"], neutral_embedding))
                
    ok("Master control tools and initial embeddings successfully seeded")

def insert_config():
    banner("Default Configuration")
    if get_query("SELECT value FROM settings WHERE key = 'config'"):
        info("Config already exists. Skipping.")
        return

    config = {
        "modo_ia": "groq",
        "modelo_visao": "google/gemini-2.0-flash-001",
        "modelo_codigo": "anthropic/claude-3.5-sonnet",
        "ui_language": "pt",
        "api_keys": { "groq": "", "openrouter": "", "openai": "" },
        "audio": {
            "metodo_escuta": "atalho",
            "motor_transcricao": "whisper",
            "motor_voz": "edge",
            "voz_edge": "pt-BR-ThalitaNeural"
        },
        "sistema": { "humor": "Friendly", "modo_foco": False }
    }
    run_query("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        ("config", json.dumps(config, ensure_ascii=False)))
    ok("Default system configuration saved")

def insert_persona():
    banner("Persona Initialization")
    if get_query("SELECT value FROM settings WHERE key = 'persona'"):
        info("Persona already exists. Skipping.")
        return
    
    persona = {
        "nome": "Maya",
        "prompt_sistema": [
            "You are Maya, a personal AI assistant.",
            "You are helpful, witty and concise.",
            "You can control the computer using tools and remember past facts."
        ]
    }
    run_query("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        ("persona", json.dumps(persona, ensure_ascii=False)))
    ok(f"Persona '{persona['nome']}' initialized")

def create_folders():
    banner("Directory Structure")
    os.makedirs(os.path.join(BASE_DIR, "uploads"), exist_ok=True)
    ok("Uploads directory ready")

# ============================================================
# MAIN EXECUTION
# ============================================================
if __name__ == "__main__":
    print(f"\n{'=' * 52}\n  L.I.A. Framework - Setup Wizard\n{'=' * 52}")
    
    check_python()
    check_dependencies()
    create_tables()
    insert_default_tools()
    insert_config()
    insert_persona()
    create_folders()
    
    banner("Setup Complete!")
    print("  1. Run 'python webui.py' to configure API keys.")
    print("  2. Run 'python main.py' to start your assistant.\n")
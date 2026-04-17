# ==========================================
# WEBUI MODULE - FastAPI Backend Server
# ==========================================
from fastapi import FastAPI, Response, Request, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
import uvicorn
import json
import os
import uuid
import sqlite3
import requests
from typing import List
from datetime import datetime

# Tool retrieval for auto-indexing
import core.tool_retrieval as tool_retrieval

# ==========================================
# FASTAPI APPLICATION INITIALIZATION
# ==========================================

app = FastAPI(title="L.I.A Panel")

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ==========================================
# CONFIGURATION PATHS
# ==========================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RELOAD_SIGNAL_FILE = os.path.join(BASE_DIR, "data", "reload_signal.flag")

def signal_reload():
    """Create a signal file to trigger main.py configuration reload."""
    try:
        with open(RELOAD_SIGNAL_FILE, "w") as f:
            f.write(str(datetime.now()))
        print(f"✅ [WebUI] Reload signal sent: {RELOAD_SIGNAL_FILE}")
    except Exception as e:
        print(f"⚠️ [WebUI] Error sending reload signal: {e}")

# ==========================================
# STORE CONFIGURATION
# ==========================================

STORE_GITHUB_REPO = "zahanzo/lia-store"
STORE_GITHUB_URL = f"https://raw.githubusercontent.com/{STORE_GITHUB_REPO}/main/v1/store.json"

# ==========================================
# DATABASE PATHS
# ==========================================

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "ai_brain.db")
VISION_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "last_vision.png")
UPLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
STORE_CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "store_cache.json")

os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"), exist_ok=True)

# ==========================================
# PYDANTIC MODELS
# ==========================================

class FileInfo(BaseModel):
    url: str
    tipo: str = Field(alias="type")
    nome: str = Field(alias="name")

    class Config:
        populate_by_name = True

class Message(BaseModel):
    texto: str = ""
    arquivos: list[FileInfo] = []

# ==========================================
# CHAT ENDPOINTS
# ==========================================

@app.post("/api/enviar")
async def send_message(msg: Message):
    """Receive a message and write to input_web.json for processing."""
    parts = []
    json_files = []
    print(f"📨 Recebido: {msg.texto}")

    for file in msg.arquivos:
        if file.tipo == "imagem":
            parts.append(f"[IMG:{file.url}]")
        else:
            parts.append(f"[FILE:{file.url}:{file.nome}]")
        # Use "type" em inglês para consistência
        json_files.append({"url": file.url, "type": file.tipo, "name": file.nome})

    if msg.texto:
        parts.append(msg.texto)

    full_content = "\n".join(parts)
    payload = {
        "texto": msg.texto,
        "arquivos": json_files,
        "conteudo_completo": full_content
    }

    input_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "input_web.json")
    with open(input_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)

    return {"status": "ok"}

# ==========================================
# DATABASE UTILITIES
# ==========================================

def execute_sql(query: str, params=(), fetch=False):
    """Execute a SQL query on the SQLite database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(query, params)
        if fetch:
            result = cursor.fetchall()
            conn.close()
            return result
        conn.commit()
        conn.close()
        return None
    except Exception as e:
        print(f"SQL Error: {e}")
        return None if fetch else None

def get_setting(key: str) -> dict:
    """Retrieve a setting from the database by key."""
    res = execute_sql("SELECT value FROM settings WHERE key = ?", (key,), fetch=True)
    return json.loads(res[0][0]) if res and res[0][0] else {}

def save_setting(key: str, data: dict):
    """Save a setting to the database."""
    execute_sql(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        (key, json.dumps(data, ensure_ascii=False))
    )

# ==========================================
# MAIN INTERFACE
# ==========================================

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve main HTML template."""
    return templates.TemplateResponse(request=request, name="index.html")

# ==========================================
# CHAT ENDPOINTS
# ==========================================

@app.get("/api/historico")
async def get_history():
    """Return chat history from database."""
    res = execute_sql(
        "SELECT role, content FROM chat_history ORDER BY rowid ASC",
        fetch=True
    )
    return [{"role": r[0], "content": r[1]} for r in res] if res else []

@app.post("/api/limpar_historico")
async def clear_history():
    """Clear chat history and signal main.py."""
    try:
        rows = execute_sql("SELECT content FROM chat_history", fetch=True)
        execute_sql("DELETE FROM chat_history")
        persona = get_setting("persona")
        prompt_raw = persona.get("prompt_sistema", "")
        context = "\n".join(prompt_raw) if isinstance(prompt_raw, list) else prompt_raw
        execute_sql(
            "INSERT INTO chat_history (role, content) VALUES (?, ?)",
            ("system", context)
        )
        _cleanup_orphan_uploads(rows or [])

        clear_session_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "clear_session.flag")
        with open(clear_session_file, "w") as f:
            f.write(str(datetime.now()))
        print("✅ [WebUI] Clear session signal sent")

        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

def _cleanup_orphan_uploads(deleted_rows):
    """Remove upload files no longer referenced."""
    import re
    if not deleted_rows:
        return
    deleted_files = set()
    for row in deleted_rows:
        for m in re.finditer(r'\[(?:IMG|FILE):(/api/uploads/[^:\]]+)', row[0] or ""):
            deleted_files.add(m.group(1).split("/")[-1])
    if not deleted_files:
        return
    still_used = set()
    for row in (execute_sql("SELECT content FROM chat_history", fetch=True) or []):
        for m in re.finditer(r'\[(?:IMG|FILE):(/api/uploads/[^:\]]+)', row[0] or ""):
            still_used.add(m.group(1).split("/")[-1])
    for name in deleted_files - still_used:
        path = os.path.join(UPLOADS_DIR, name)
        try:
            if os.path.exists(path):
                os.remove(path)
                print(f"🗑️ [Upload] Removed: {name}")
        except Exception as e:
            print(f"⚠️ [Upload] Error removing {name}: {e}")

# ==========================================
# CHAT MODE (BATE-PAPO) ENDPOINTS
# ==========================================

@app.get("/api/batepapo/status")
async def get_chat_mode_status():
    """Return current chat mode status."""
    res = execute_sql(
        "SELECT text_value FROM system_state WHERE key = 'chat_mode'",
        fetch=True
    )
    return {"active": bool(res and res[0][0] == "1")}

@app.post("/api/batepapo/toggle")
async def toggle_chat_mode():
    """Toggle chat mode on/off."""
    res = execute_sql(
        "SELECT text_value FROM system_state WHERE key = 'chat_mode'",
        fetch=True
    )
    current = bool(res and res[0][0] == "1")
    new_state = not current
    execute_sql(
        "INSERT OR REPLACE INTO system_state (key, text_value) VALUES (?, ?)",
        ("chat_mode", "1" if new_state else "0")
    )
    input_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "input_web.json")
    with open(input_file, "w", encoding="utf-8") as f:
        json.dump({"comando": "toggle_batepapo", "ativo": new_state}, f)
    return {"active": new_state}

# ==========================================
# SYSTEM STATUS
# ==========================================

@app.get("/api/status")
async def get_status():
    """Get current system status message."""
    res = execute_sql(
        "SELECT text_value FROM system_state WHERE key = 'status_msg'",
        fetch=True
    )
    return {"status": res[0][0] if res and res[0][0] else ""}

# ==========================================
# CONFIGURATION ENDPOINTS
# ==========================================

@app.get("/api/config")
async def get_config():
    return get_setting("config")

@app.post("/api/config/update")
async def update_config(data: dict):
    save_setting("config", data)
    signal_reload()
    return {"status": "ok"}

@app.post("/api/set_language")
async def set_language(data: dict):
    lang = data.get("lang", "en")
    cfg = get_setting("config")
    cfg["ui_language"] = lang
    save_setting("config", cfg)
    signal_reload()
    try:
        from core.i18n import set_language
        set_language(lang)
    except Exception:
        pass
    return {"status": "ok", "lang": lang}

# ==========================================
# PERSONA ENDPOINTS
# ==========================================

@app.get("/api/persona")
async def get_persona():
    return get_setting("persona")

@app.post("/api/persona/update")
async def update_persona(data: dict):
    save_setting("persona", data)
    signal_reload()
    return {"status": "ok"}

# ==========================================
# MODEL PROVIDERS
# ==========================================

@app.get("/api/openrouter_models")
async def get_openrouter_models():
    cfg = get_setting("config")
    api_key = cfg.get("api_keys", {}).get("openrouter")
    if not api_key:
        return []
    try:
        res = requests.get(
            "https://openrouter.ai/api/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        )
        if res.status_code == 200:
            return [{"id": m["id"], "name": m["name"]} for m in res.json().get("data", [])]
    except Exception:
        pass
    return []

@app.get("/api/groq_models")
async def get_groq_models():
    cfg = get_setting("config")
    api_key = cfg.get("api_keys", {}).get("groq")
    if not api_key:
        return []
    try:
        res = requests.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            timeout=15,
        )
        if res.status_code == 200:
            models = res.json().get("data", [])
            return [
                {"id": m["id"], "name": m.get("id", m["id"])}
                for m in sorted(models, key=lambda x: x["id"])
                if not any(x in m["id"] for x in ["whisper", "tts", "guard"])
            ]
    except Exception:
        pass
    return []

@app.get("/api/local_models")
def get_local_models(mode: str = "local_lm"):
    if mode == "local_lm":
        base_url = "http://127.0.0.1:1234/v1"
        prefix = "(LM)"
    else:
        base_url = "http://127.0.0.1:11434/v1"
        prefix = "(Ollama)"
    try:
        res = requests.get(f"{base_url}/models", timeout=2.0)
        if res.status_code == 200:
            data = res.json()
            return [{"id": m["id"], "name": f"{prefix} {m['id']}"} for m in data.get("data", [])]
        return []
    except Exception as e:
        print(f"Error connecting to {prefix}: {e}")
        return []

# ==========================================
# FILE UPLOAD
# ==========================================

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename or "")[1].lower() or ".bin"
    unique_name = f"{uuid.uuid4().hex}{ext}"
    dest_path = os.path.join(UPLOADS_DIR, unique_name)
    content = await file.read()
    with open(dest_path, "wb") as f:
        f.write(content)
    return {
        "url": f"/api/uploads/{unique_name}",
        "original_name": file.filename,
        "size": len(content)
    }

@app.get("/api/uploads/{filename}")
async def serve_upload(filename: str):
    path = os.path.join(UPLOADS_DIR, filename)
    if not os.path.exists(path):
        return Response(status_code=404)
    return FileResponse(path, headers={"Cache-Control": "public, max-age=86400"})

# ==========================================
# VISION
# ==========================================

@app.get("/api/last_vision")
async def get_last_vision():
    if os.path.exists(VISION_PATH):
        return FileResponse(VISION_PATH, headers={"Cache-Control": "no-cache, no-store"})
    return Response(status_code=404)

@app.get("/api/vision_description")
async def get_vision_description():
    res = execute_sql(
        "SELECT text_value FROM system_state WHERE key = 'vision_desc'",
        fetch=True
    )
    content = res[0][0] if res and res[0][0] else "Waiting for capture..."
    return Response(content=content, media_type="text/plain")

# ----------------------------------------------
# 1. GET MCP TOOLS (com name_pt e description_pt)
# ----------------------------------------------
@app.get("/api/mcp_tools")
async def get_mcp_tools(type: str = "global"):
    """Get MCP tools with multilingual support"""
    
    try:
        # Query with translation columns
        if type == "global":
            query = """
                SELECT name, description, schema_json, python_code, pip_requirements,
                       name_pt, description_pt
                FROM mcp_tools WHERE parent_id IS NULL OR parent_id = ''
            """
        else:
            query = """
                SELECT name, description, schema_json, python_code, pip_requirements,
                       name_pt, description_pt
                FROM mcp_tools
            """
        
        res = execute_sql(query, fetch=True)
        out = []
        
        for r in res or []:
            out.append({
                "nome": r[0],                                    # name
                "descricao": r[1],                               # description
                "schema_json": r[2],                             # ✅ CORRIGIDO
                "codigo_python": r[3],                           # ✅ CORRIGIDO
                "pip_requirements": r[4] or "",
                "nome_pt": r[5] if len(r) > 5 else None,        # ✅ NOVO
                "descricao_pt": r[6] if len(r) > 6 else None    # ✅ NOVO
            })
        
        #print(f"[DEBUG] Retornando {len(out)} plugins com traduções")
        #if out:
            #print(f"[DEBUG] Exemplo: {out[0]}")
        
        return out
        
    except Exception as e:
        # Fallback se colunas não existirem
        print(f"⚠️ Erro ao buscar traduções: {e}")
        
        if type == "global":
            query = """
                SELECT name, description, schema_json, python_code, pip_requirements
                FROM mcp_tools WHERE parent_id IS NULL OR parent_id = ''
            """
        else:
            query = """
                SELECT name, description, schema_json, python_code, pip_requirements
                FROM mcp_tools
            """
        
        res = execute_sql(query, fetch=True)
        out = []
        
        for r in res or []:
            out.append({
                "nome": r[0],
                "descricao": r[1],
                "schema_json": r[2],
                "codigo_python": r[3],
                "pip_requirements": r[4] or ""
            })
        
        return out
        
    except Exception as e:
        # Fallback se coluna description_pt não existir
        print(f"⚠️ Coluna description_pt não encontrada: {e}")
        
        if type == "global":
            query = """
                SELECT name, description, schema_json, python_code, pip_requirements
                FROM mcp_tools WHERE parent_id IS NULL OR parent_id = ''
            """
        else:
            query = """
                SELECT name, description, schema_json, python_code, pip_requirements
                FROM mcp_tools
            """
        
        res = execute_sql(query, fetch=True)
        out = []
        
        for r in res or []:
            out.append({
                "nome": r[0],
                "descricao": r[1],
                "schema_json": r[2],
                "codigo_python": r[3],
                "pip_requirements": r[4] or ""
            })
        
        return out
'''
@app.get("/api/mcp_tools")
async def get_mcp_tools(type: str = "global"):
    if type == "global":
        query = """
            SELECT name, description, schema_json, python_code, pip_requirements
            FROM mcp_tools WHERE parent_id IS NULL OR parent_id = ''
        """
    else:
        query = """
            SELECT name, description, schema_json, python_code, pip_requirements
            FROM mcp_tools
        """
    res = execute_sql(query, fetch=True)
    out = []
    for r in res or []:
        pip = r[4] if len(r) > 4 else ""
        out.append({
            "nome": r[0],
            "descricao": r[1],
            "schema": r[2],
            "codigo": r[3],
            "pip_requirements": pip or "",
        })
    return out'''

@app.get("/api/mcp_tools/get")
async def get_single_mcp_tool(name: str):
    res = execute_sql(
        """
        SELECT name, description, schema_json, python_code, pip_requirements, is_master, parent_id
        FROM mcp_tools WHERE name = ?
        """,
        (name,),
        fetch=True,
    )
    if res:
        pip = res[0][4] if len(res[0]) > 4 else ""
        is_master = res[0][5] if len(res[0]) > 5 else False
        parent_id = res[0][6] if len(res[0]) > 6 else None
        return {
            "nome": res[0][0],
            "descricao": res[0][1],
            "schema": res[0][2],
            "codigo": res[0][3],
            "pip_requirements": pip or "",
            "is_master": bool(is_master),
            "parent_id": parent_id,
        }
    return {"error": "Not found"}

@app.post("/api/mcp_tools/save")
async def save_mcp_tool(data: dict):
    name = data.get("nome")
    code = data.get("codigo_python", "")
    pip_req = (data.get("pip_requirements") or "").strip()
    is_master = data.get("is_master", False)
    parent_id = data.get("parent_id", None)

    if is_master:
        parent_id = None

    # Install dependencies in background
    import threading
    import subprocess
    import sys
    import re

    def install_dependencies():
        try:
            packages = set()
            if pip_req:
                for p in re.split(r"[,;\n]+", pip_req):
                    if p.strip():
                        packages.add(p.strip())
            imports = set(re.findall(r'^(?:import|from)\s+([a-zA-Z0-9_]+)', code, re.MULTILINE))
            stdlib = sys.stdlib_module_names if hasattr(sys, 'stdlib_module_names') else set()
            ignore = {"config", "eyes", "ears", "memory", "mouth", "mcp"}
            for lib in imports:
                if lib not in stdlib and lib not in ignore:
                    packages.add(lib)
            for package in packages:
                print(f"📦 [WebUI] Installing {package} for '{name}'")
                subprocess.run([sys.executable, "-m", "pip", "install", package], capture_output=True)
            if packages:
                print(f"✅ [WebUI] Dependencies for '{name}' ready")
        except Exception as e:
            print(f"⚠️ [WebUI] Error installing dependencies: {e}")

    threading.Thread(target=install_dependencies, daemon=True).start()

    execute_sql(
        """
        INSERT OR REPLACE INTO mcp_tools
        (name, description, schema_json, python_code, pip_requirements, is_master, parent_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (name, data.get("descricao"), data.get("schema_json"), code, pip_req or None, is_master, parent_id),
    )

    tool_retrieval.auto_index_on_save(name, data.get("descricao", ""))
    signal_reload()
    return {"status": "ok"}

@app.post("/api/mcp_tools/delete")
async def delete_mcp_tool(name: str):
    execute_sql("DELETE FROM mcp_tools WHERE name = ?", (name,))
    tool_retrieval.auto_remove_on_delete(name)
    signal_reload()
    return {"status": "ok"}

# ==========================================
# MASTERS
# ==========================================

@app.get("/api/masters/{master_name}/tools")
async def get_master_tools(master_name: str):
    res = execute_sql(
        """
        SELECT name, description, schema_json, python_code, pip_requirements
        FROM mcp_tools WHERE parent_id = ?
        """,
        (master_name,),
        fetch=True
    )
    out = []
    for r in res or []:
        out.append({
            "nome": r[0],
            "descricao": r[1],
            "schema": r[2],
            "codigo": r[3],
            "pip_requirements": r[4] if len(r) > 4 else "",
        })
    return out

@app.post("/api/masters/{master_name}/tools/save")
async def save_master_tool(master_name: str, request: Request):
    data = await request.json()
    name = data.get("nome", "").strip()
    code = data.get("codigo", "").strip()
    pip_req = data.get("pip_requirements", "").strip()

    if not name:
        return {"status": "error", "message": "Name is required"}

    execute_sql(
        """
        INSERT OR REPLACE INTO mcp_tools
        (name, description, schema_json, python_code, pip_requirements, is_master, parent_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (name, data.get("descricao"), data.get("schema_json"), code, pip_req or None, 0, master_name),
    )

    tool_retrieval.auto_index_on_save(name, data.get("descricao", ""))
    signal_reload()
    return {"status": "ok"}

@app.delete("/api/masters/{master_name}/tools/{tool_name}")
async def delete_master_tool(master_name: str, tool_name: str):
    execute_sql(
        "DELETE FROM mcp_tools WHERE name = ? AND parent_id = ?",
        (tool_name, master_name)
    )
    tool_retrieval.auto_remove_on_delete(tool_name)
    signal_reload()
    return {"status": "ok"}

@app.post("/api/masters/install")
async def install_master(request: Request):
    data = await request.json()
    master = data.get("master", {})
    tools = data.get("tools", [])

    if not master.get("name"):
        return {"status": "error", "message": "Master name required"}

    execute_sql(
        """
        INSERT OR REPLACE INTO mcp_tools
        (name, description, schema_json, python_code, pip_requirements, is_master, parent_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (master.get("name"), master.get("description", ""), "{}", "", None, 1, None),
    )

    for tool in tools:
        execute_sql(
            """
            INSERT OR REPLACE INTO mcp_tools
            (name, description, schema_json, python_code, pip_requirements, is_master, parent_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (tool["name"], tool["description"], tool["schema_json"], tool["python_code"],
             tool.get("pip_requirements"), 0, master["name"]),
        )
        tool_retrieval.auto_index_on_save(tool["name"], tool["description"])

    return {"status": "ok", "message": f"Master installed with {len(tools)} tools"}

@app.delete("/api/masters/{master_name}")
async def uninstall_master(master_name: str):
    execute_sql("DELETE FROM mcp_tools WHERE parent_id = ?", (master_name,))
    execute_sql("DELETE FROM mcp_tools WHERE name = ?", (master_name,))
    execute_sql("DELETE FROM active_master WHERE master_name = ?", (master_name,))
    return {"status": "ok"}

@app.get("/api/masters/list")
async def list_masters():
    res = execute_sql("SELECT name, description FROM mcp_tools WHERE is_master = 1", fetch=True)
    return [{"name": r[0], "description": r[1]} for r in res] if res else []

@app.get("/api/masters/active")
async def get_active_master():
    res = execute_sql("SELECT master_name, activated_at FROM active_master WHERE id = 1", fetch=True)
    if res and res[0][0]:
        return {"active": True, "master_name": res[0][0], "activated_at": res[0][1]}
    return {"active": False, "master_name": None}

@app.post("/api/masters/activate")
async def activate_master(request: Request):
    data = await request.json()
    master_name = data.get("master_name", "").strip()
    if not master_name:
        return {"success": False, "error": "master_name required"}
    res = execute_sql("SELECT name FROM mcp_tools WHERE name = ? AND is_master = 1", (master_name,), fetch=True)
    if not res:
        return {"success": False, "error": "Master not found"}
    execute_sql(
        "UPDATE active_master SET master_name = ?, activated_at = datetime('now','localtime') WHERE id = 1",
        (master_name,)
    )
    return {"success": True}

@app.post("/api/masters/deactivate")
async def deactivate_master():
    execute_sql("UPDATE active_master SET master_name = NULL WHERE id = 1")
    return {"success": True}

# ==========================================
# STORE
# ==========================================

def fetch_store_from_github():
    try:
        res = requests.get(STORE_GITHUB_URL, timeout=10)
        res.raise_for_status()
        data = res.json()
        with open(STORE_CACHE_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return data
    except Exception as e:
        print(f"❌ Error fetching store: {e}")
        if os.path.exists(STORE_CACHE_PATH):
            with open(STORE_CACHE_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"plugins": [], "masters": []}

@app.get("/api/store/items")
async def get_store_items():
    store = fetch_store_from_github()
    installed_plugins = set()
    installed_masters = set()
    tools = execute_sql("SELECT name, parent_id FROM mcp_tools", fetch=True)
    for name, parent_id in (tools or []):
        if not parent_id:
            installed_plugins.add(name)
    masters = execute_sql("SELECT name FROM mcp_tools WHERE is_master = 1", fetch=True)
    for (name,) in (masters or []):
        installed_masters.add(name)
    for p in store.get("plugins", []):
        p["installed"] = p["tool"]["name"] in installed_plugins
    for m in store.get("masters", []):
        m["installed"] = m["id"] in installed_masters
    return store

# ----------------------------------------------
# 2. INSTALL PLUGIN FROM STORE
# ----------------------------------------------
@app.post("/api/store/install/plugin/{plugin_id}")
async def install_store_plugin(plugin_id: str):
    """Install a plugin from the store - downloads .py from GitHub"""
    
    store = fetch_store_from_github()
    plugin = next((p for p in store.get("plugins", []) if p["id"] == plugin_id), None)
    
    if not plugin:
        return {"status": "error", "message": "Plugin not found"}
    
    tool = plugin["tool"]
    
    # Pega name_pt e description_pt do PLUGIN
    name_pt = plugin.get("name_pt")
    description_pt = plugin.get("description_pt")
    
    #print(f"[DEBUG] Instalando plugin: {tool['name']}")
    #print(f"[DEBUG] name_pt: {name_pt}")
    #print(f"[DEBUG] description_pt: {description_pt}")
    
    # ✅ Baixar código do GitHub
    code_url = tool.get("code_url")
    if not code_url:
        return {"status": "error", "message": "Plugin has no code_url"}
    
    try:
        print(f"⬇️ Baixando código de: {code_url}")
        response = requests.get(code_url, timeout=10)
        response.raise_for_status()
        python_code = response.text
        print(f"✅ Código baixado: {len(python_code)} bytes")
    except Exception as e:
        print(f"❌ Erro ao baixar código: {e}")
        return {"status": "error", "message": f"Failed to download code: {str(e)}"}
    
    # Criar arquivo .py
    try:
        file_dir = os.path.join(BASE_DIR, "plugins", "base")
        os.makedirs(file_dir, exist_ok=True)
        
        # Criar __init__.py se não existir
        init_file = os.path.join(file_dir, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, 'w', encoding='utf-8') as f:
                f.write('"""Base plugins - always available tools"""\n')
        
        # Salvar código baixado
        file_path = os.path.join(file_dir, f"{tool['name']}.py")
        module_path = f"base.{tool['name']}"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(python_code)
        
        print(f"✅ Arquivo criado: {file_path}")
        
    except Exception as e:
        print(f"❌ Erro ao criar arquivo: {e}")
        return {"status": "error", "message": f"Failed to create file: {str(e)}"}
    
    # Salvar no banco
    execute_sql(
        """
        INSERT OR REPLACE INTO mcp_tools
        (name, description, schema_json, code_file, pip_requirements, is_master, parent_id, name_pt, description_pt, is_async)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            tool["name"],
            tool["description"],
            tool["schema_json"],
            module_path,  # code_file ao invés de python_code
            tool.get("pip_requirements", ""),
            0,
            None,
            name_pt,
            description_pt,
            0
        ),
    )
    
    # Indexar no RAG
    tool_retrieval.auto_index_on_save(tool["name"], tool["description"])
    
    return {"status": "ok", "message": f"Plugin {tool['name']} installed successfully"}

# ----------------------------------------------
# 3. INSTALL MASTER FROM STORE
# ----------------------------------------------
@app.post("/api/store/install/master/{master_id}")
async def install_store_master(master_id: str):
    """Install a master from the store - downloads entire folder from GitHub with metadata"""
    
    store = fetch_store_from_github()
    master = next((m for m in store.get("masters", []) if m["id"] == master_id), None)
    
    if not master:
        return {"status": "error", "message": "Master not found"}
    
    # Install master entry (sem código, apenas metadados)
    execute_sql(
        """
        INSERT OR REPLACE INTO mcp_tools
        (name, description, schema_json, code_file, pip_requirements, is_master, parent_id, name_pt, description_pt)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            master["id"],
            master.get("description", ""),
            "{}",
            None,
            None,
            1,
            None,
            master.get("name_pt"),
            master.get("description_pt")
        ),
    )
    
    # ✅ Baixar pasta inteira do GitHub
    github_folder = master.get("github_folder")
    tools_metadata = master.get("tools_metadata", {})
    
    if not github_folder:
        return {"status": "error", "message": "Master has no github_folder"}
    
    try:
        print(f"📁 Baixando pasta do GitHub: {github_folder}")
        
        # Fazer request para a API do GitHub
        response = requests.get(github_folder, timeout=10)
        response.raise_for_status()
        files_list = response.json()
        
        # Criar diretório do master
        master_dir = os.path.join(BASE_DIR, "plugins", "masters", master["id"])
        os.makedirs(master_dir, exist_ok=True)
        
        # Criar __init__.py
        init_file = os.path.join(master_dir, "__init__.py")
        with open(init_file, 'w', encoding='utf-8') as f:
            master_name = master.get("name_pt") or master.get("name", master["id"])
            f.write(f'"""{master_name} - Master tools"""\n')
        
        print(f"✅ Diretório criado: {master_dir}")
        
        # Baixar cada arquivo .py da pasta
        tools_installed = 0
        for file_info in files_list:
            if file_info["type"] != "file" or not file_info["name"].endswith(".py"):
                continue
            
            if file_info["name"] == "__init__.py":
                continue  # Já criamos
            
            file_url = file_info["download_url"]
            tool_name = file_info["name"].replace(".py", "")
            
            print(f"⬇️ Baixando: {tool_name}.py")
            
            # Baixar código
            file_response = requests.get(file_url, timeout=10)
            file_response.raise_for_status()
            python_code = file_response.text
            
            # Salvar arquivo
            file_path = os.path.join(master_dir, file_info["name"])
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(python_code)
            
            print(f"✅ Arquivo salvo: {file_path}")
            
            # ✅ Pegar metadados do tools_metadata
            metadata = tools_metadata.get(tool_name, {})
            description = metadata.get("description", f"Tool from {master['id']} master")
            schema_json = metadata.get("schema_json", "{}")
            pip_reqs = metadata.get("pip_requirements", "")
            
            module_path = f"masters.{master['id']}.{tool_name}"
            
            # Salvar no banco com metadados completos
            execute_sql(
                """
                INSERT OR REPLACE INTO mcp_tools
                (name, description, schema_json, code_file, pip_requirements, is_master, parent_id, name_pt, description_pt, is_async)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tool_name,
                    description,
                    schema_json,
                    module_path,
                    pip_reqs,
                    0,
                    master["id"],
                    None,  # Pode adicionar name_pt no tools_metadata se quiser
                    None,  # Pode adicionar description_pt no tools_metadata se quiser
                    0
                ),
            )
            
            # Indexar no RAG
            tool_retrieval.auto_index_on_save(tool_name, description)
            
            tools_installed += 1
        
        print(f"✅ Master instalado: {tools_installed} ferramentas")
        
        return {"status": "ok", "message": f"Master {master['id']} installed with {tools_installed} tools"}
        
    except Exception as e:
        print(f"❌ Erro ao baixar master: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": f"Failed to download master: {str(e)}"}
 

@app.delete("/api/store/uninstall/plugin/{tool_name}")
async def uninstall_store_plugin(tool_name: str):
    execute_sql(
        "DELETE FROM mcp_tools WHERE name = ? AND is_master = 0 AND (parent_id IS NULL OR parent_id = '')",
        (tool_name,)
    )
    tool_retrieval.auto_remove_on_delete(tool_name)
    return {"status": "ok"}

@app.delete("/api/store/uninstall/master/{master_id}")
async def uninstall_store_master(master_id: str):
    tools = execute_sql("SELECT name FROM mcp_tools WHERE parent_id = ?", (master_id,), fetch=True)
    execute_sql("DELETE FROM mcp_tools WHERE parent_id = ?", (master_id,))
    execute_sql("DELETE FROM mcp_tools WHERE name = ? AND is_master = 1", (master_id,))
    for (name,) in (tools or []):
        tool_retrieval.auto_remove_on_delete(name)
    return {"status": "ok"}

@app.post("/api/store/submit")
async def submit_plugin_for_review(request: Request):
    """Generate GitHub Issue link for plugin/master submission"""
    try:
        import urllib.parse
        
        data = await request.json()
        
        # Validate required fields
        if data.get("type") == "plugin":
            required = ["name", "description", "author", "category", "tool"]
            if not all(k in data for k in required):
                return {"status": "error", "message": "Missing required fields"}
        elif data.get("type") == "master":
            required = ["name", "description", "author", "category", "tools"]
            if not all(k in data for k in required):
                return {"status": "error", "message": "Missing required fields"}
        else:
            return {"status": "error", "message": "Invalid type (must be 'plugin' or 'master')"}
        
        # Generate submission JSON
        submission = {
            "type": data.get("type"),
            "id": data.get("name", "").lower().replace(" ", "_"),
            "name": data.get("name"),
            "description": data.get("description"),
            "author": data.get("author"),
            "version": "1.0.0",
            "category": data.get("category"),
            "downloads": 0,
            "rating": 5.0
        }
        
        if data.get("type") == "plugin":
            submission["tool"] = data["tool"]
        else:
            submission["tools"] = data["tools"]
            submission["tools_count"] = len(data["tools"])
        
        # Format JSON nicely
        json_content = json.dumps(submission, indent=2, ensure_ascii=False)
        
        # Create GitHub Issue template
        issue_title = f"[Submission] {data.get('type').title()}: {data.get('name')}"
        
        issue_body = f"""## Plugin/Master Submission

**Type:** {data.get('type').title()}
**Name:** {data.get('name')}
**Author:** {data.get('author')}
**Category:** {data.get('category')}

### JSON for store.json

Add this to the appropriate section (`plugins` or `masters`) in `store.json`:

```json
{json_content}
```

---

**Submitted by:** {data.get('author')}
**Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        # Generate GitHub Issue URL
        github_url = f"https://github.com/{STORE_GITHUB_REPO}/issues/new"
        params = {
            "title": issue_title,
            "body": issue_body,
            "labels": "submission," + data.get("type")
        }
        
        issue_url = f"{github_url}?{urllib.parse.urlencode(params)}"
        
        print(f"✅ [Store] Submission prepared: {data.get('name')}")
        return {
            "status": "ok",
            "message": "Submission prepared! Click the link to create GitHub Issue.",
            "github_url": issue_url,
            "json": json_content
        }
    
    except Exception as e:
        print(f"❌ Error preparing submission: {e}")
        return {"status": "error", "message": str(e)}

# ==========================================
# MEMORIES
# ==========================================

@app.get("/api/memories")
async def get_memories():
    res = execute_sql(
        "SELECT id, content, created_at, access_count FROM memories ORDER BY created_at DESC",
        fetch=True
    )
    return [{"id": r[0], "content": r[1], "created_at": r[2], "access_count": r[3]} for r in res or []]

@app.delete("/api/memories/{memory_id}")
async def delete_memory(memory_id: int):
    execute_sql("DELETE FROM memories WHERE id = ?", (memory_id,))
    return {"status": "ok"}

@app.delete("/api/memories")
async def delete_all_memories():
    execute_sql("DELETE FROM memories")
    return {"status": "ok"}

# ==========================================
# ROLEPLAY
# ==========================================

@app.get("/api/roleplay")
async def get_roleplays():
    res = execute_sql(
        """
        SELECT id, name, ai_persona, user_persona, scenario, nsfw, active
        FROM roleplay_scenarios ORDER BY active DESC, id DESC
        """,
        fetch=True
    )
    return [
        {
            "id": r[0], "nome": r[1], "persona_ia": r[2], "persona_usuario": r[3],
            "cenario": r[4], "nsfw": bool(r[5]), "active": bool(r[6])
        } for r in res or []
    ]

@app.post("/api/roleplay/save")
async def save_roleplay(data: dict):
    execute_sql(
        """
        INSERT INTO roleplay_scenarios (name, ai_persona, user_persona, scenario, nsfw)
        VALUES (?, ?, ?, ?, ?)
        """,
        (data["nome"], data.get("persona_ia", ""), data.get("persona_usuario", ""),
         data.get("cenario", ""), data.get("nsfw", 0))
    )
    return {"status": "ok"}

@app.post("/api/roleplay/activate")
async def activate_roleplay(data: dict):
    execute_sql("UPDATE roleplay_scenarios SET active = 0")
    execute_sql("UPDATE roleplay_scenarios SET active = 1 WHERE id = ?", (data["id"],))
    return {"status": "ok"}

@app.post("/api/roleplay/deactivate")
async def deactivate_roleplay():
    execute_sql("UPDATE roleplay_scenarios SET active = 0")
    return {"status": "ok"}

@app.post("/api/roleplay/delete")
async def delete_roleplay(id: int):
    execute_sql("DELETE FROM roleplay_scenarios WHERE id = ?", (id,))
    return {"status": "ok"}

# ==========================================
# MODES (FOCUS / DND)
# ==========================================

@app.post("/api/modo/foco")
async def toggle_focus(data: dict):
    cfg = get_setting("config")
    cfg.setdefault("sistema", {})["modo_foco"] = data.get("ativo", False)
    save_setting("config", cfg)
    signal_reload()
    return {"status": "ok"}

@app.post("/api/modo/nao_perturbe")
async def toggle_dnd(data: dict):
    cfg = get_setting("config")
    cfg.setdefault("sistema", {})["modo_nao_perturbe"] = data.get("ativo", False)
    save_setting("config", cfg)
    signal_reload()
    return {"status": "ok"}

@app.get("/api/modo/status")
async def get_mode_status():
    s = get_setting("config").get("sistema", {})
    return {"modo_foco": s.get("modo_foco", False), "modo_nao_perturbe": s.get("modo_nao_perturbe", False)}

# ==========================================
# SERVER STARTUP
# ==========================================

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
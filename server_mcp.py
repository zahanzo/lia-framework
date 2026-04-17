"""
server_mcp.py — MCP Tool Server com Sistema de Mestres

Expõe ferramentas para a IA via Model Context Protocol (stdio transport).
Implementa sistema de camadas:
- Ferramentas GLOBAIS (parent_id = NULL): sempre disponíveis
- Ferramentas CONTEXTUAIS (parent_id = ID_MASTER): só quando o mestre está ativo

Suporta dois modos de execução:
- NOVO: Código em arquivos .py (sync e async)
- LEGACY: Código inline no banco (exec)
"""

from mcp.server.lowlevel import Server
import mcp.types as types
from mcp.server.stdio import stdio_server
import asyncio
import os
import json
import sqlite3
import sys

import core.config as config
from groq import Groq
from openai import OpenAI
from core.i18n import t

# ✅ NOVO: Importar executor de arquivos
from core.tool_executor import execute_tool

try:
    import pyautogui
except Exception:
    pyautogui = None

app = Server("ai-assistant-tools")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
from core.config import DB_PATH


def run_db(query, params=(), fetch=True):
    try:
        conn   = sqlite3.connect(config.DB_PATH, timeout=20)
        cursor = conn.cursor()
        cursor.execute(query, params)
        res = cursor.fetchall() if fetch else None
        conn.commit()
        conn.close()
        return res
    except Exception as e:
        print(f"❌ [MCP] SQL error: {e}", file=sys.stderr)
        return None


def init_ai_clients():
    """Load API keys from DB and initialize AI clients on startup."""
    try:
        res = run_db("SELECT value FROM settings WHERE key = 'config'")
        if res and res[0] and res[0][0]:
            data     = json.loads(res[0][0])
            keys     = data.get("api_keys", {})
            config.CURRENT_MODE = data.get("modo_ia", "groq")

            groq_key = keys.get("groq", "").strip()
            if groq_key:
                config.client_groq = Groq(api_key=groq_key)

            or_key = keys.get("openrouter", "").strip()
            if or_key:
                config.client_openrouter = OpenAI(
                    base_url="https://openrouter.ai/api/v1", api_key=or_key)

            oa_key = keys.get("openai", "").strip()
            if oa_key:
                config.client_openai = OpenAI(api_key=oa_key)

            print(t("server.keys_loaded"), file=sys.stderr)
    except Exception as e:
        print(t("server.key_error", e=e), file=sys.stderr)


init_ai_clients()


# ==========================================
# MASTERS SYSTEM
# ==========================================
def get_active_master() -> str | None:
    """Retorna o nome do mestre ativo ou None."""
    try:
        res = run_db("SELECT master_name FROM active_master WHERE id = 1")
        if res and res[0] and res[0][0]:
            return res[0][0]
    except Exception:
        pass
    return None


def activate_master(master_name: str) -> bool:
    """Ativa um mestre específico."""
    try:
        # Verifica se o mestre existe
        res = run_db("SELECT name FROM mcp_tools WHERE name = ? AND is_master = 1", (master_name,))
        if not res:
            print(f"⚠️ [MCP] Mestre '{master_name}' não encontrado", file=sys.stderr)
            return False
        
        run_db(
            "UPDATE active_master SET master_name = ?, activated_at = datetime('now','localtime') WHERE id = 1",
            (master_name,),
            fetch=False
        )
        print(f"✅ [MCP] Mestre '{master_name}' ativado", file=sys.stderr)
        return True
    except Exception as e:
        print(f"❌ [MCP] Erro ao ativar mestre: {e}", file=sys.stderr)
        return False


def deactivate_master() -> bool:
    """Desativa o mestre atual."""
    try:
        run_db("UPDATE active_master SET master_name = NULL WHERE id = 1", fetch=False)
        print("✅ [MCP] Mestre desativado", file=sys.stderr)
        return True
    except Exception as e:
        print(f"❌ [MCP] Erro ao desativar mestre: {e}", file=sys.stderr)
        return False


# ==========================================
# TOOL CATALOGUE (com sistema de camadas)
# ==========================================
@app.list_tools()
async def list_tools() -> list[types.Tool]:
    """
    Retorna lista de ferramentas disponíveis baseado no sistema de camadas:
    - Ferramentas GLOBAIS (parent_id = NULL): sempre incluídas
    - Ferramentas do MESTRE ATIVO: incluídas se há um mestre ativo
    """
    tools = [
        types.Tool(
            name="see_screen",
            description="Capture and analyze the current state of the user's screen.",
            inputSchema={"type": "object", "properties": {}}
        )
    ]
    
    # 1. Carregar ferramentas GLOBAIS (parent_id IS NULL AND is_master = 0)
    global_rows = run_db(
        "SELECT name, description, schema_json FROM mcp_tools WHERE parent_id IS NULL AND is_master = 0"
    )
    if global_rows:
        for row in global_rows:
            try:
                try:
                    schema = json.loads(row[2])
                except:
                    schema = {}

                # Garante que o schema tenha "type": "object"
                if not isinstance(schema, dict):
                    schema = {}
                if schema.get("type") != "object":
                    schema = {"type": "object", "properties": schema}

                tools.append(types.Tool(
                    name=row[0],
                    description=row[1],
                    inputSchema=schema
                ))
            except Exception as e:
                print(f"Error loading global tool {row[0]}: {e}", file=sys.stderr)
    
    # 2. Carregar ferramentas do MESTRE ATIVO (se houver)
    active_master = get_active_master()
    if active_master:
        contextual_rows = run_db(
            "SELECT name, description, schema_json FROM mcp_tools WHERE parent_id = ? AND is_master = 0",
            (active_master,)
        )
        if contextual_rows:
            print(f"🎯 [MCP] Carregando {len(contextual_rows)} ferramentas do mestre '{active_master}'", file=sys.stderr)
            for row in contextual_rows:
                try:
                    tools.append(types.Tool(
                        name=row[0],
                        description=row[1],
                        inputSchema=json.loads(row[2])
                    ))
                except Exception as e:
                    print(f"Error loading contextual tool {row[0]}: {e}", file=sys.stderr)
    
    print(f"📋 [MCP] Total de ferramentas disponíveis: {len(tools)}", file=sys.stderr)
    return tools


# ==========================================
# TOOL EXECUTOR (híbrido: arquivos + exec)
# ==========================================
@app.call_tool()
async def call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    arguments = arguments or {}
    print(t("server.tool_running", name=name), file=sys.stderr)

    try:
        # ── Comandos de Sistema (Mestres) ────────────────────────────────
        if name == "activate_master":
            master_name = arguments.get("master_name", "").strip()
            if not master_name:
                return [types.TextContent(type="text", text="Error: master_name is required")]
            
            success = activate_master(master_name)
            if success:
                return [types.TextContent(
                    type="text",
                    text=f"[DIRECT][EN]Master '{master_name}' activated. New contextual tools are now available.[/EN][PT]Mestre '{master_name}' ativado. Novas ferramentas contextuais estão disponíveis.[/PT]"
                )]
            else:
                return [types.TextContent(
                    type="text",
                    text=f"[DIRECT][EN]Failed to activate master '{master_name}'. Master not found.[/EN][PT]Falha ao ativar mestre '{master_name}'. Mestre não encontrado.[/PT]"
                )]
        
        if name == "deactivate_master":
            success = deactivate_master()
            if success:
                return [types.TextContent(
                    type="text",
                    text="[DIRECT][EN]Master deactivated. Contextual tools are no longer available.[/EN][PT]Mestre desativado. Ferramentas contextuais não estão mais disponíveis.[/PT]"
                )]
            else:
                return [types.TextContent(type="text", text="[DIRECT] Failed to deactivate master.")]
        
        if name == "get_active_master":
            active = get_active_master()
            if active:
                return [types.TextContent(
                    type="text",
                    text=f"[DIRECT][EN]Active master: '{active}'[/EN][PT]Mestre ativo: '{active}'[/PT]"
                )]
            else:
                return [types.TextContent(
                    type="text",
                    text="[DIRECT][EN]No master is currently active.[/EN][PT]Nenhum mestre está ativo no momento.[/PT]"
                )]
        
        if name == "list_available_masters":
            masters = run_db("SELECT name, description FROM mcp_tools WHERE is_master = 1")
            if masters:
                masters_list_en = "\n".join([f"- {m[0]}: {m[1]}" for m in masters])
                masters_list_pt = "\n".join([f"- {m[0]}: {m[1]}" for m in masters])
                return [types.TextContent(
                    type="text",
                    text=f"[DIRECT][EN]Available masters:\n{masters_list_en}[/EN][PT]Mestres disponíveis:\n{masters_list_pt}[/PT]"
                )]
            else:
                return [types.TextContent(
                    type="text",
                    text="[DIRECT][EN]No masters available.[/EN][PT]Nenhum mestre disponível.[/PT]"
                )]
        
        # ── Built-in: see_screen ──────────────────────────────────────
        if name in ("see_screen", "ver_tela"):
            import core.eyes as eyes
            analysis = await eyes.analisar_tela_groq(
                "Describe in detail and directly what is on the screen."
            )
            if analysis:
                run_db(
                    "INSERT OR REPLACE INTO system_state (key, text_value) VALUES (?, ?)",
                    ("vision_desc", analysis), fetch=False
                )
                try:
                    signal_file = os.path.join(BASE_DIR, "data", "new_vision.signal")
                    with open(signal_file, "w") as f:
                        f.write("update")
                except Exception:
                    pass
                print(t("server.vision_ok"), file=sys.stderr)
                return [types.TextContent(
                    type="text",
                    text=f"Screen context captured: {analysis}. Respond to the user based on this."
                )]
            return [types.TextContent(type="text", text="Vision capture failed.")]

        # ── ✅ NOVO: Verificar se tem code_file (sistema de arquivos) ────
        row = run_db(
            "SELECT code_file, python_code, is_async FROM mcp_tools WHERE name = ?", 
            (name,)
        )

        if not row or not row[0]:
            msg = t("server.tool_not_found", name=name)
            print(f"   └ ⚠️ {msg}", file=sys.stderr)
            return [types.TextContent(type="text", text=msg)]

        code_file, python_code, is_async = row[0]

        # ✅ MODO NOVO: Código em arquivo
        if code_file:
            print(f"📂 [MCP] Executando de arquivo: {code_file}", file=sys.stderr)
            try:
                result = await execute_tool(name, arguments, config.DB_PATH)
                print(t("server.tool_return", result=result[:100]), file=sys.stderr)
                return [types.TextContent(type="text", text=result)]
            except Exception as e:
                import traceback
                error_msg = f"Error executing file-based tool '{name}': {str(e)}\n{traceback.format_exc()}"
                print(f"❌ {error_msg}", file=sys.stderr)
                return [types.TextContent(type="text", text=f"[ERROR] {error_msg}")]

        # ⚠️ MODO LEGACY: Código inline (exec)
        if python_code:
            print(f"📜 [MCP] Executando código inline (legacy): {name}", file=sys.stderr)
            
            import subprocess as _sp
            import requests, time, webbrowser

            # Sandboxed subprocess wrapper
            class _SafeSubprocess:
                DEVNULL = _sp.DEVNULL
                PIPE    = _sp.PIPE

                @staticmethod
                def run(*a, **kw):
                    kw.setdefault("stdout", _sp.DEVNULL)
                    kw.setdefault("stderr", _sp.DEVNULL)
                    return _sp.run(*a, **kw)

                @staticmethod
                def Popen(*a, **kw):
                    kw.setdefault("stdout", _sp.DEVNULL)
                    kw.setdefault("stderr", _sp.DEVNULL)
                    return _sp.Popen(*a, **kw)

                @staticmethod
                def call(*a, **kw):
                    kw.setdefault("stdout", _sp.DEVNULL)
                    kw.setdefault("stderr", _sp.DEVNULL)
                    return _sp.call(*a, **kw)

            local_vars = {
                "arguments":  arguments,
                "os":         os,
                "sys":        sys,
                "subprocess": _SafeSubprocess,
                "requests":   requests,
                "time":       time,
                "pyautogui":  pyautogui,
                "webbrowser": webbrowser,
                "run_db":     run_db,
                "json":       json,
                "ai_response": "Action completed successfully."
            }

            builtins_copy = (
                __builtins__.copy() if isinstance(__builtins__, dict)
                else __builtins__.__dict__.copy()
            )
            builtins_copy["print"] = lambda *a, **kw: None

            def _run_plugin():
                exec(python_code, {"__builtins__": builtins_copy}, local_vars)

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _run_plugin)

            result = str(local_vars.get("ai_response", "Action completed."))
            print(t("server.tool_return", result=result[:100]), file=sys.stderr)
            return [types.TextContent(type="text", text=result)]

        # Se chegou aqui, a ferramenta não tem nem code_file nem python_code
        return [types.TextContent(
            type="text", 
            text=f"[ERROR] Tool '{name}' has no executable code (neither file nor inline)"
        )]

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"❌ [MCP] Error executing '{name}':\n{error_details}", file=sys.stderr)
        return [types.TextContent(type="text", text=f"Error executing '{name}': {e}")]


# ==========================================
# BOOT
# ==========================================
async def main():
    async with stdio_server() as (read_stream, write_stream):
        # Redirect stdout → stderr ONLY after stdio_server has captured the real stdout.
        sys.stdout = sys.stderr
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
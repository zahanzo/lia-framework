"""
server_mcp.py — MCP Tool Server

Exposes tools to the AI via the Model Context Protocol (stdio transport).
Each tool can be defined statically (ver_tela / see_screen) or dynamically
via plugins stored in the database (mcp_tools table).
"""

from mcp.server.lowlevel import Server
import mcp.types as types
from mcp.server.stdio import stdio_server
import asyncio
import os
import json
import sqlite3
import sys

# NOTE: Do NOT redirect stdout at the top of this file.
# The stdio_server() captures the real stdout for the MCP protocol.
# Redirection happens INSIDE main(), after stdio_server takes ownership.

import config
from groq import Groq
from openai import OpenAI
from i18n import t

try:
    import pyautogui
except Exception:
    pyautogui = None

app = Server("ai-assistant-tools")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, config.DB_PATH)


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
# TOOL CATALOGUE
# ==========================================
@app.list_tools()
async def list_tools() -> list[types.Tool]:
    tools = [
        types.Tool(
            name="see_screen",
            description="Capture and analyze the current state of the user's screen.",
            inputSchema={"type": "object", "properties": {}}
        )
    ]
    rows = run_db("SELECT name, description, schema_json FROM mcp_tools")
    if rows:
        for row in rows:
            try:
                tools.append(types.Tool(
                    name=row[0],
                    description=row[1],
                    inputSchema=json.loads(row[2])
                ))
            except Exception as e:
                print(f"Error loading tool {row[0]}: {e}", file=sys.stderr)
    return tools


# ==========================================
# TOOL EXECUTOR
# ==========================================
@app.call_tool()
async def call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    arguments = arguments or {}
    print(t("server.tool_running", name=name), file=sys.stderr)

    try:
        # ── Built-in: see_screen ──────────────────────────────────────
        if name in ("see_screen", "ver_tela"):
            import eyes
            analysis = await eyes.analisar_tela_groq(
                "Describe in detail and directly what is on the screen."
            )
            if analysis:
                run_db(
                    "INSERT OR REPLACE INTO system_state (key, text_value) VALUES (?, ?)",
                    ("vision_desc", analysis), fetch=False
                )
                try:
                    with open("new_vision.signal", "w") as f:
                        f.write("update")
                except Exception:
                    pass
                print(t("server.vision_ok"), file=sys.stderr)
                return [types.TextContent(
                    type="text",
                    text=f"Screen context captured: {analysis}. Respond to the user based on this."
                )]
            return [types.TextContent(type="text", text="Vision capture failed.")]

        # ── Dynamic plugin from DB ────────────────────────────────────
        row = run_db("SELECT python_code FROM mcp_tools WHERE name = ?", (name,))

        if not row or not row[0][0]:
            msg = t("server.tool_not_found", name=name)
            print(f"   └ ⚠️ {msg}", file=sys.stderr)
            return [types.TextContent(type="text", text=msg)]

        python_code = row[0][0]

        import subprocess as _sp
        import requests, time, webbrowser

        # Sandboxed subprocess wrapper (never writes to real stdout)
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
        builtins_copy["print"] = lambda *a, **kw: None  # silence prints inside plugins

        # Run exec in a thread so ANY blocking call (subprocess, requests,
        # time.sleep, webbrowser.open, etc.) doesn't freeze the MCP event loop.
        def _run_plugin():
            exec(python_code, {"__builtins__": builtins_copy}, local_vars)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _run_plugin)

        result = str(local_vars.get("ai_response", "Action completed."))
        print(t("server.tool_return", result=result), file=sys.stderr)
        return [types.TextContent(type="text", text=result)]

    except Exception as e:
        print(t("server.tool_error", name=name, e=e), file=sys.stderr)
        return [types.TextContent(type="text", text=f"Error executing '{name}': {e}")]


# ==========================================
# BOOT
# ==========================================
async def main():
    async with stdio_server() as (read_stream, write_stream):
        # Redirect stdout → stderr ONLY after stdio_server has captured the real stdout.
        # This prevents accidental prints from corrupting the MCP binary protocol.
        sys.stdout = sys.stderr
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
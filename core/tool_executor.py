"""
Tool Executor - Dynamically loads and executes tools from files
Supports both sync and async functions
"""

import importlib
import asyncio
import sqlite3
import sys
from typing import Any, Dict
from pathlib import Path

# Add plugins directory to Python path
PLUGINS_DIR = Path(__file__).parent.parent / "plugins"
if str(PLUGINS_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGINS_DIR))

# Global context (shared across tool executions)
EXECUTION_CONTEXT = {
    'browser_state': {},  # Browser instances for browser_control master
    'session_data': {},   # Session variables
}


async def execute_tool(tool_name: str, arguments: dict, db_path: str) -> str:
    """
    Execute a tool by loading its code from file.
    Supports both sync and async functions.
    
    Args:
        tool_name: Name of the tool to execute
        arguments: Arguments from AI
        db_path: Path to database
    
    Returns:
        AI response string
    """
    # Get tool info from database
    conn = sqlite3.connect(db_path, timeout=20)
    cursor = conn.cursor()
    
    try:
        row = cursor.execute("""
            SELECT code_file, is_async, python_code, pip_requirements
            FROM mcp_tools
            WHERE name = ?
        """, (tool_name,)).fetchone()
        
        if not row:
            return f"[ERROR] Tool '{tool_name}' not found in database"
        
        code_file, is_async, legacy_code, pip_requirements = row
        
        # Build context
        context = {
            'db': conn,
            'db_path': db_path,
            'run_db': lambda *args: _run_db(conn, *args),
            **EXECUTION_CONTEXT
        }
        
        # === NEW WAY: Load from file ===
        if code_file:
            try:
                # Import the module
                module = importlib.import_module(code_file)
                
                # Check if it has an execute function
                if not hasattr(module, 'execute'):
                    return f"[ERROR] Module '{code_file}' has no execute() function"
                
                # Execute (sync or async)
                if is_async:
                    # Run async function
                    result = await module.execute(arguments, context)
                else:
                    # Run sync function (wrap in thread to not block)
                    result = await asyncio.to_thread(module.execute, arguments, context)
                
                return result
                
            except ImportError as e:
                return f"[ERROR] Failed to import '{code_file}': {e}"
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                print(f"❌ Error executing {tool_name}:")
                print(error_details)
                return f"[ERROR] Failed to execute {tool_name}: {str(e)}"
        
        # === OLD WAY: exec() for legacy plugins ===
        elif legacy_code:
            # Inject context into exec namespace
            exec_namespace = {
                'arguments': arguments,
                'run_db': context['run_db'],
                'db': conn,
                **EXECUTION_CONTEXT
            }
            
            # Execute the legacy code
            exec(legacy_code, exec_namespace)
            result = exec_namespace.get('ai_response', '[ERROR] No ai_response set')
            return result
        
        else:
            return f"[ERROR] Tool '{tool_name}' has no code (neither file nor inline)"
    
    finally:
        conn.close()


def _run_db(connection: sqlite3.Connection, query: str, params: tuple = (), fetch: bool = None) -> list:
    """Helper to execute DB queries within tools"""
    cursor = connection.cursor()
    cursor.execute(query, params)
    
    # Auto-detect if we should fetch
    if fetch is None:
        fetch = query.strip().upper().startswith('SELECT')
    
    if fetch:
        return cursor.fetchall()
    else:
        connection.commit()
        return []


def reload_tool(tool_name: str, db_path: str):
    """
    Reload a tool module (useful during development).
    Call this after editing a plugin file.
    """
    conn = sqlite3.connect(db_path, timeout=20)
    try:
        row = conn.execute("""
            SELECT code_file FROM mcp_tools WHERE name = ?
        """, (tool_name,)).fetchone()
        
        if row and row[0]:
            code_file = row[0]
            module = importlib.import_module(code_file)
            importlib.reload(module)
            print(f"✅ Reloaded {tool_name} from {code_file}")
        else:
            print(f"⚠️ Tool {tool_name} has no code_file")
    finally:
        conn.close()
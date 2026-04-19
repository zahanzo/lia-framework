"""
tool_retrieval.py — Tool Retrieval via RAG (Semantic Search)

Instead of sending ALL 2000 tools to the AI, we do semantic search
and send only the Top-5 most relevant ones.

Works like the memory system (memory.py), but for tools.
"""

import sqlite3
import json
import math
import os
from datetime import datetime
from core.i18n import t

# Get DB_PATH directly to avoid import issues
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "ai_brain.db")

ALWAYS_AVAILABLE_TOOLS = [
    'activate_master',
    'deactivate_master', 
    'get_active_master',
    'list_available_masters'
]

# ==========================================
# EMBEDDING MODEL (shared with memory.py)
# ==========================================
_embedding_model = None

def _get_model():
    """Load embeddings model (lazy loading)"""
    global _embedding_model
    if _embedding_model is None:
        print(t("tool_retrieval.loading_model"))
        try:
            from sentence_transformers import SentenceTransformer
            _embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            print(t("tool_retrieval.model_loaded"))
        except ImportError:
            print(t("tool_retrieval.model_missing"))
            return None
    return _embedding_model

def _embed(text: str) -> list:
    """Generate embedding for text"""
    model = _get_model()
    if not model:
        return []
    return model.encode(text).tolist()

def _cosine_similarity(a: list, b: list) -> float:
    """Calculate cosine similarity between two vectors"""
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(y * y for y in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


# ==========================================
# TOOL INDEXING
# ==========================================

def index_tool(tool_name: str, description: str):
    """
    Index a tool in the vector database.
    Call this when creating/editing a tool.
    
    Args:
        tool_name: Tool name
        description: Tool description (will be vectorized)
    """
    # Generate embedding
    embedding = _embed(description)
    if not embedding:
        return
    
    embedding_json = json.dumps(embedding)
    
    # Save to database
    conn = sqlite3.connect(DB_PATH, timeout=20)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tool_embeddings (
                tool_name TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                embedding_json TEXT NOT NULL,
                indexed_at TEXT NOT NULL
            )
        """)
        
        conn.execute("""
            INSERT OR REPLACE INTO tool_embeddings 
            (tool_name, description, embedding_json, indexed_at)
            VALUES (?, ?, ?, ?)
        """, (tool_name, description, embedding_json, datetime.now().isoformat()))
        
        conn.commit()
        print(t("tool_retrieval.indexed", tool=tool_name))
    finally:
        conn.close()


def index_all_tools():
    """
    Index ALL tools from the database.
    Run this once to create the initial index.
    """
    conn = sqlite3.connect(DB_PATH, timeout=20)
    try:
        # Fetch all tools
        tools = conn.execute("""
            SELECT name, description 
            FROM mcp_tools 
            WHERE description IS NOT NULL AND description != ''
        """).fetchall()
        
        print(t("tool_retrieval.indexing_all", count=len(tools)))
        
        for tool_name, description in tools:
            index_tool(tool_name, description)
        
        print(t("tool_retrieval.indexing_complete", count=len(tools)))
    finally:
        conn.close()


def remove_tool_embedding(tool_name: str):
    """Remove embedding of a deleted tool"""
    conn = sqlite3.connect(DB_PATH, timeout=20)
    try:
        conn.execute("DELETE FROM tool_embeddings WHERE tool_name = ?", (tool_name,))
        conn.commit()
    finally:
        conn.close()


# ==========================================
# TOOL CATEGORIZATION
# ==========================================

# Tools that are always available (meta-control)
ALWAYS_AVAILABLE_TOOLS = [
    'activate_master',
    'deactivate_master', 
    'get_active_master',
    'list_available_masters'
]

# Thresholds de similaridade
SIMILARITY_THRESHOLD = {
    'informational': 0.25,  # Para ferramentas de consulta (mais permissivo)
    'action': 0.45          # Para ferramentas que executam ações (mais rigoroso)
}

def _is_action_tool(tool_name: str) -> bool:
    """
    Verifica se uma ferramenta é de ação (requer comando explícito).
    
    Todas as ferramentas são action tools, EXCETO as de meta-controle.
    Masters não aparecem aqui (são ativados via activate_master).
    """
    return tool_name not in ALWAYS_AVAILABLE_TOOLS

# ==========================================
# SEMANTIC SEARCH
# ==========================================

def search_tools(query: str, top_k: int = 5, active_master: str = None, exclude_tools: list = None, is_action_request: bool = True) -> list:
    """
    Search for relevant tools using semantic similarity.
    
    Args:
        query: User text
        top_k: Number of tools to return
        active_master: DEPRECATED - no longer used (kept for compatibility)
        exclude_tools: List of tool names to exclude from search
        is_action_request: Whether the user message is an action command (True) or question (False)
    """
    # Generate query embedding
    query_embedding = _embed(query)
    if not query_embedding:
        return []
    
    exclude_tools = exclude_tools or []
    
    conn = sqlite3.connect(DB_PATH, timeout=20)
    try:
        # Build exclusion clause
        exclude_clause = ""
        params = []
        
        if exclude_tools:
            placeholders = ','.join(['?'] * len(exclude_tools))
            exclude_clause = f"AND t.name NOT IN ({placeholders})"
            params = exclude_tools
        
        # ✅ CORREÇÃO: Buscar APENAS ferramentas GLOBAIS (parent_id IS NULL)
        # Ferramentas de masters ativos são adicionadas pela Layer 2
        query_sql = f"""
            SELECT t.name, t.description, t.schema_json, t.python_code, t.parent_id,
                   e.embedding_json
            FROM mcp_tools t
            LEFT JOIN tool_embeddings e ON t.name = e.tool_name
            WHERE e.embedding_json IS NOT NULL
              AND t.is_master = 0
              AND (t.parent_id IS NULL OR t.parent_id = '')  -- ✅ APENAS GLOBAIS
              {exclude_clause}
        """
        
        tools_data = conn.execute(query_sql, params).fetchall()
        
        # Calculate similarity for each tool
        results = []
        for tool_name, desc, schema, code, parent_id, emb_json in tools_data:
            tool_embedding = json.loads(emb_json)
            similarity = _cosine_similarity(query_embedding, tool_embedding)
            
            # ✅ Aplicar threshold baseado no tipo de ferramenta
            is_action = _is_action_tool(tool_name)
            threshold = SIMILARITY_THRESHOLD['action'] if is_action else SIMILARITY_THRESHOLD['informational']
            
            # Se é ferramenta de ação mas mensagem é PERGUNTA, bloquear
            if is_action and not is_action_request:
                print(f"🚫 Bloqueada '{tool_name}' (ação sem comando explícito, sim={similarity:.2f})")
                continue
            
            # Se similaridade abaixo do threshold, descartar
            if similarity < threshold:
                continue
            
            results.append({
                "name": tool_name,
                "description": desc,
                "schema_json": schema,
                "python_code": code,
                "similarity": similarity,
                "parent_id": parent_id,
                "is_action": is_action
            })
        
        # Sort by similarity (highest first)
        results.sort(key=lambda x: x["similarity"], reverse=True)
        
        # Return top-K
        return results[:top_k]
        
    finally:
        conn.close()
        
# Ferramentas que devem SEMPRE estar disponíveis (meta-controle)
ALWAYS_AVAILABLE_TOOLS = [
    'activate_master',
    'deactivate_master', 
    'get_active_master',
    'list_available_masters'
]


def get_relevant_tools_for_ai(user_input: str, top_k: int = 5, is_action_request: bool = True) -> list:
    """
    Return tools to send to the AI in 3 layers:
    
    1. ALWAYS PRESENT: Master control tools (activate, deactivate, etc.)
    2. ACTIVE MASTER: ALL tools from active master (if any)
    3. SEMANTIC SEARCH: Top-K relevant tools (excluding layers 1 & 2)
    
    Args:
        user_input: User message
        top_k: Number of tools from semantic search
        is_action_request: Whether the message is an action command (True) or question (False)
    
    This ensures:
    - User can always control masters
    - Active master tools are always available
    - Additional relevant tools are added via semantic search
    """
    conn = sqlite3.connect(DB_PATH, timeout=20)
    
    try:
        # Check if there's an active master
        active_master_row = conn.execute("""
            SELECT master_name FROM active_master WHERE id = 1
        """).fetchone()
        active_master = active_master_row[0] if active_master_row else None
        
        # ======================================
        # LAYER 1: Always-available tools
        # ======================================
        always_tools_data = conn.execute(f"""
            SELECT name, description, schema_json
            FROM mcp_tools
            WHERE name IN ({','.join(['?']*len(ALWAYS_AVAILABLE_TOOLS))})
              AND is_master = 0
        """, ALWAYS_AVAILABLE_TOOLS).fetchall()
        
        # ======================================
        # LAYER 2: ALL tools from active master
        # ======================================
        master_tools_data = []
        if active_master:
            master_tools_data = conn.execute("""
                SELECT name, description, schema_json
                FROM mcp_tools
                WHERE parent_id = ?
                  AND is_master = 0
                ORDER BY name
            """, (active_master,)).fetchall()
        
    finally:
        conn.close()
    
    # Build exclusion list (layer 1 + layer 2)
    exclude_from_search = ALWAYS_AVAILABLE_TOOLS.copy()
    master_tool_names = [name for name, _, _ in master_tools_data]
    exclude_from_search.extend(master_tool_names)
    
    # ======================================
    # LAYER 3: Semantic search (excluding layers 1 & 2)
    # ======================================
    semantic_tools = search_tools(
        user_input, 
        top_k=top_k,
        active_master=None,
        exclude_tools=exclude_from_search,
        is_action_request=is_action_request  # ✅ Passa classificação
    )
    
    # ======================================
    # Format all layers
    # ======================================
    
    # Get available masters for activate_master schema enrichment
    available_masters = []
    try:
        master_rows = conn.execute("""
            SELECT name FROM mcp_tools 
            WHERE is_master = 1
            ORDER BY name
        """).fetchall()
        available_masters = [row[0] for row in master_rows]
    except:
        pass
    
    # Format layer 1 (always-available)
    layer1_formatted = []
    for name, desc, schema_json in always_tools_data:
        try:
            schema = json.loads(schema_json) if schema_json else {}
        except:
            schema = {}
        
        # Enrich activate_master schema with available masters
        if name == "activate_master" and available_masters:
            if "properties" not in schema:
                schema["properties"] = {}
            if "master_name" not in schema["properties"]:
                schema["properties"]["master_name"] = {"type": "string"}
            
            # Add enum with available masters
            schema["properties"]["master_name"]["enum"] = available_masters
            schema["properties"]["master_name"]["description"] = (
                f"Name of the master to activate. Available masters: {', '.join(available_masters)}"
            )
        
        layer1_formatted.append({
            "name": name,
            "description": desc,
            "input_schema": schema
        })
    
    # Format layer 2 (active master tools)
    layer2_formatted = []
    for name, desc, schema_json in master_tools_data:
        try:
            schema = json.loads(schema_json) if schema_json else {}
        except:
            schema = {}
        layer2_formatted.append({
            "name": name,
            "description": desc,
            "input_schema": schema
        })
    
    # Format layer 3 (semantic search)
    layer3_formatted = []
    for tool in semantic_tools:
        try:
            schema = json.loads(tool["schema_json"]) if tool["schema_json"] else {}
        except:
            schema = {}
        layer3_formatted.append({
            "name": tool["name"],
            "description": tool["description"],
            "input_schema": schema
        })
    
    # ======================================
    # Logging (only show semantic layer)
    # ======================================
    total_tools = len(layer1_formatted) + len(layer2_formatted) + len(layer3_formatted)
    
    if active_master:
        print(f"🎯 [Master Ativo: {active_master}] {len(layer2_formatted)} ferramentas do master sempre presentes")
    
    if layer3_formatted:
        print(t("tool_retrieval.selected_tools", count=len(layer3_formatted)))
        for i, tool_data in enumerate(layer3_formatted, 1):
            sim = semantic_tools[i-1]["similarity"]
            is_action = semantic_tools[i-1].get("is_action", False)
            tool_type = "🎬 AÇÃO" if is_action else "📖 INFO"
            print(f"   {i}. 🔧 {tool_data['name']} [{tool_type}] ({t('tool_retrieval.similarity')}: {sim:.2f})")
    
    print(f"📊 Total de ferramentas enviadas para API: {total_tools}")
    print(f"   └─ Meta-controle: {len(layer1_formatted)}")
    if active_master:
        print(f"   └─ Master '{active_master}': {len(layer2_formatted)}")
    print(f"   └─ Busca semântica: {len(layer3_formatted)}")
    
    # ======================================
    # Return all 3 layers combined
    # ======================================
    return layer1_formatted + layer2_formatted + layer3_formatted


# ==========================================
# UTILITIES
# ==========================================

def get_stats():
    """Return tool index statistics"""
    conn = sqlite3.connect(DB_PATH, timeout=20)
    try:
        total_tools = conn.execute("SELECT COUNT(*) FROM mcp_tools").fetchone()[0]
        indexed_tools = conn.execute("SELECT COUNT(*) FROM tool_embeddings").fetchone()[0]
        
        return {
            "total_tools": total_tools,
            "indexed_tools": indexed_tools,
            "coverage": f"{(indexed_tools/total_tools*100):.1f}%" if total_tools > 0 else "0%"
        }
    finally:
        conn.close()


# ==========================================
# AUTO-INDEXING HOOKS
# ==========================================

def auto_index_on_save(tool_name: str, description: str):
    """
    Hook to be called when a tool is saved.
    Add this to /api/mcp_tools/save endpoint in webui.py
    """
    if description and description.strip():
        index_tool(tool_name, description)


def auto_remove_on_delete(tool_name: str):
    """
    Hook to be called when a tool is deleted.
    Add this to /api/mcp_tools/delete endpoint in webui.py
    """
    remove_tool_embedding(tool_name)


# ==========================================
# INITIALIZATION
# ==========================================

if __name__ == "__main__":
    print(t("tool_retrieval.test_header"))
    print("=" * 50)
    
    # Create initial index
    print(f"\n1. {t('tool_retrieval.test_indexing')}")
    index_all_tools()
    
    # Show statistics
    print(f"\n2. {t('tool_retrieval.test_stats')}")
    stats = get_stats()
    print(f"   {t('tool_retrieval.stats_total')}: {stats['total_tools']}")
    print(f"   {t('tool_retrieval.stats_indexed')}: {stats['indexed_tools']}")
    print(f"   {t('tool_retrieval.stats_coverage')}: {stats['coverage']}")
    
    # Search test
    print(f"\n3. {t('tool_retrieval.test_search')}")
    query = "decrease screen brightness"
    print(f"   Query: '{query}'")
    
    tools = search_tools(query, top_k=5)
    if tools:
        print(f"   {t('tool_retrieval.found_tools', count=len(tools))}")
        for i, tool in enumerate(tools, 1):
            print(f"   {i}. {tool['name']} ({t('tool_retrieval.similarity')}: {tool['similarity']:.3f})")
            print(f"      {tool['description'][:60]}...")
    else:
        print(f"   {t('tool_retrieval.no_tools_found')}")
    
    print("\n" + "=" * 50)
    print(t("tool_retrieval.test_complete"))
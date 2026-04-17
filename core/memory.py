"""
memory.py — Long-Term Semantic Memory (RAG)

Uses sentence-transformers for local embeddings + cosine similarity search.
Install: pip install sentence-transformers
"""

import json
import asyncio
import sqlite3
import os
import sys
import math
from datetime import datetime

import core.config as config
from core.i18n import t

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "ai_brain.db")

# ==========================================
# EMBEDDING MODEL (lazy load)
# ==========================================
_embedding_model = None

def _get_model():
    global _embedding_model
    if _embedding_model is None:
        print(t("memory.embed_loading"))
        try:
            from sentence_transformers import SentenceTransformer
            _embedding_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
            print(t("memory.embed_loaded"))
        except ImportError:
            print(t("memory.embed_no_pkg"))
            return None
        except Exception as e:
            print(t("memory.embed_error", e=e))
            return None
    return _embedding_model


def warmup_embedding_model() -> None:
    """Preload embeddings in daemon thread — first message doesn't block the turn."""
    def _go() -> None:
        try:
            _get_model()
        except Exception:
            pass

    import threading
    threading.Thread(target=_go, daemon=True).start()


def _generate_embedding(text: str) -> list | None:
    model = _get_model()
    if not model:
        return None
    try:
        vec = model.encode(text, convert_to_numpy=True)
        return vec.tolist()
    except Exception as e:
        print(t("memory.embed_error", e=e))
        return None


def _cosine_similarity(v1: list, v2: list) -> float:
    try:
        dot  = sum(a * b for a, b in zip(v1, v2))
        mag1 = math.sqrt(sum(a * a for a in v1))
        mag2 = math.sqrt(sum(b * b for b in v2))
        if mag1 == 0 or mag2 == 0:
            return 0.0
        return dot / (mag1 * mag2)
    except Exception:
        return 0.0


# ==========================================
# DATABASE
# ==========================================
def _run_sql(query, params=(), fetch=False):
    conn = sqlite3.connect(config.DB_PATH, timeout=20)
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        res = cursor.fetchall() if fetch else None
        conn.commit()
        return res
    except Exception as e:
        print(t("db.sql_error", e=e), file=sys.stderr)
        return None
    finally:
        conn.close()


def initialize_table():
    """Create the memories table if it does not exist. Safe to call multiple times."""
    _run_sql("""
        CREATE TABLE IF NOT EXISTS memories (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            content        TEXT NOT NULL,
            embedding_json TEXT NOT NULL,
            created_at     TEXT NOT NULL,
            access_count   INTEGER DEFAULT 0
        )
    """)
    print(t("memory.table_ready"))


# ==========================================
# SAVE MEMORY (with deduplication)
# ==========================================
def save_memory(content: str) -> bool:
    """Save a fact with its embedding. Rejects duplicates with >=85% similarity."""
    if not content or len(content.strip()) < 10:
        return False

    new_vec = _generate_embedding(content)
    if not new_vec:
        return False

    # Deduplication check
    rows = _run_sql("SELECT id, content, embedding_json FROM memories", fetch=True)
    if rows:
        for row in rows:
            try:
                existing_id = row[0]
                existing_content = row[1]
                existing_vec = json.loads(row[2])
                sim = _cosine_similarity(new_vec, existing_vec)
                if sim >= 0.85:  # ✅ CORRIGIDO: >= em vez de >
                    # Mostrar qual memória é similar
                    print(f"⚠️ [Memória] Duplicata detectada (sim={sim:.2f})")
                    print(f"   Nova: {content[:60]}...")
                    print(f"   Existente: {existing_content[:60]}...")
                    return False
            except Exception:
                continue

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _run_sql(
        "INSERT INTO memories (content, embedding_json, created_at, access_count) VALUES (?, ?, ?, 0)",
        (content.strip(), json.dumps(new_vec), now)
    )
    print(t("memory.saved", content=content[:70] + ("..." if len(content) > 70 else "")))
    return True


# ==========================================
# SEARCH MEMORIES
# ==========================================
def search_memories(query: str, top_k: int = 4, threshold: float = 0.42) -> list[str]:
    """Return the most relevant facts for the query using cosine similarity."""
    if not query or len(query.strip()) < 5:
        return []

    query_vec = _generate_embedding(query)
    if not query_vec:
        return []

    rows = _run_sql("SELECT id, content, embedding_json FROM memories", fetch=True)
    if not rows:
        return []

    scored = []
    for row in rows:
        try:
            mem_vec = json.loads(row[2])
            sim = _cosine_similarity(query_vec, mem_vec)
            if sim >= threshold:
                scored.append((sim, row[0], row[1]))
        except Exception:
            continue

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_k]

    for _, mem_id, _ in top:
        _run_sql("UPDATE memories SET access_count = access_count + 1 WHERE id = ?", (mem_id,))

    results = [content for _, _, content in top]
    if results:
        print(t("memory.found", n=len(results)))
    return results


# ==========================================
# AUTO-EXTRACT FACTS (async, non-blocking)
# ==========================================
async def extract_and_save_facts(user_message: str, ai_response: str):
    """
    Calls the AI in background to extract objective facts from the conversation.
    Does not block the main loop. Skipped during active roleplay.
    """
    if config.ROLEPLAY_ACTIVE:
        return
    if len(user_message.strip()) < 15:
        return

    prompt = (
        "You are an objective fact extractor. "
        "Analyze the conversation below and extract ONLY concrete, long-lasting facts about the user "
        "(name, preferences, possessions, recurring issues, projects, important people, etc.). "
        "Return ONLY a JSON list of strings, no explanations, no markdown. "
        "If there are no relevant facts, return []. "
        "Good fact examples: "
        "'User owns a motorcycle', "
        "'User works with Python programming', "
        "'User resolved a hardware issue in February 2025'. "
        "Do NOT extract questions, momentary opinions or greetings.\n\n"
        f"User said: {user_message}\n"
        f"AI responded: {ai_response[:300]}"
    )

    try:
        client = config.client_groq or config.client_openrouter or config.client_openai
        model  = ("llama-3.3-70b-versatile" if config.client_groq else
                  "deepseek/deepseek-chat"   if config.client_openrouter else "gpt-4o-mini")
        if not client:
            return

        def _call():
            return client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.1
            )

        r = await asyncio.to_thread(_call)
        text = r.choices[0].message.content.strip()
        text = text.replace("```json", "").replace("```", "").strip()

        facts = json.loads(text)
        if isinstance(facts, list):
            for fact in facts:
                if isinstance(fact, str) and len(fact) > 10:
                    await asyncio.to_thread(save_memory, fact)

    except json.JSONDecodeError:
        pass
    except Exception as e:
        print(t("memory.extract_error", e=e), file=sys.stderr)


# ==========================================
# LIST / MANAGE
# ==========================================
def list_all_memories() -> list[dict]:
    rows = _run_sql(
        "SELECT id, content, embedding_json, created_at, access_count FROM memories ORDER BY created_at DESC",
        fetch=True
    )
    return [
        {"id": r[0], "content": r[1], "embedding_json": r[2],
         "created_at": r[3], "access_count": r[4]}
        for r in (rows or [])
    ]


def delete_memory(memory_id: int) -> bool:
    _run_sql("DELETE FROM memories WHERE id = ?", (memory_id,))
    return True


def delete_all_memories() -> bool:
    _run_sql("DELETE FROM memories")
    return True


# ==========================================
# DECAY — REMOVE OBSOLETE MEMORIES
# ==========================================
def apply_decay(days: int = 30):
    """
    Delete memories that were never accessed (access_count = 0)
    and are older than `days` days. Run weekly.
    """
    from datetime import timedelta
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    res = _run_sql(
        "SELECT COUNT(*) FROM memories WHERE access_count = 0 AND created_at < ?",
        (cutoff,), fetch=True
    )
    count = res[0][0] if res else 0
    if count > 0:
        _run_sql("DELETE FROM memories WHERE access_count = 0 AND created_at < ?", (cutoff,))
        print(t("memory.decay", n=count, days=days))
    else:
        print(t("memory.decay_none"))
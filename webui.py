from fastapi import FastAPI, Response, Request, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from pydantic import BaseModel
import uvicorn
import json
import os
import uuid
import sqlite3
import asyncio
import requests
from typing import List

app = FastAPI(title="AI Assistant Panel")

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DB_PATH     = os.path.join(BASE_DIR, "ai_brain.db")
VISION_PATH = os.path.join(BASE_DIR, "last_vision.png")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

class ArquivoInfo(BaseModel):
    url:  str
    tipo: str
    nome: str

class Mensagem(BaseModel):
    texto:    str = ""
    arquivos: List[ArquivoInfo] = []

# ==========================================
# 🗄️ BANCO DE DADOS
# ==========================================
def executar_sql(query, params=(), fetch=False):
    conn = sqlite3.connect(DB_PATH, timeout=20)
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        res = cursor.fetchall() if fetch else None
        conn.commit()
        return res
    except Exception:
        return None
    finally:
        conn.close()

def obter_setting(key: str) -> dict:
    res = executar_sql("SELECT value FROM settings WHERE key = ?", (key,), fetch=True)
    return json.loads(res[0][0]) if res and res[0][0] else {}

def salvar_setting(key: str, data: dict):
    executar_sql("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                 (key, json.dumps(data, ensure_ascii=False)))

# ==========================================
# 📡 SSE
# ==========================================
@app.get("/api/eventos")
async def eventos_sse(request: Request):
    async def gen():
        ultimo_hash = ""
        while True:
            if await request.is_disconnected():
                break
            try:
                rows = executar_sql(
                    "SELECT role, content FROM chat_history ORDER BY id ASC",
                    fetch=True
                )
                hist = [{"role": r[0], "content": r[1]} for r in rows] if rows else []
                h    = str(hash(json.dumps(hist)))
                if h != ultimo_hash:
                    ultimo_hash = h
                    yield f"data: {json.dumps(hist, ensure_ascii=False)}\n\n"
            except Exception:
                pass
            await asyncio.sleep(0.4)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

# ==========================================
# 🌐 INTERFACE
# ==========================================
@app.get("/", response_class=HTMLResponse)
async def pagina_principal():
    html = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Assistant</title>
<style>
/* ── Reset & Base ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --bg:       #0f0f13;
  --surface:  #17171e;
  --card:     #1e1e28;
  --border:   #2a2a38;
  --border2:  #33334a;
  --text:     #e2e2f0;
  --muted:    #7878a0;
  --accent:   #7c6af7;
  --accent2:  #a78bfa;
  --green:    #4ade80;
  --red:      #f87171;
  --yellow:   #fbbf24;
  --blue:     #60a5fa;
  --sidebar-w: 220px;
  --sidebar-sm: 60px;
  --topbar-h:  52px;
  --nav-h:     60px;
  --radius:    10px;
  --radius-sm: 6px;
}
html, body { height: 100%; overflow: hidden; }
body { font-family: 'Segoe UI', system-ui, sans-serif; background: var(--bg); color: var(--text); font-size: 14px; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 99px; }

/* ── Layout principal ── */
#app { display: flex; height: 100vh; }

/* ── Sidebar ── */
#sidebar {
  width: var(--sidebar-w);
  background: var(--surface);
  border-right: 1px solid var(--border);
  display: flex; flex-direction: column;
  flex-shrink: 0;
  transition: width 0.25s ease;
  overflow: hidden;
  z-index: 100;
}
#sidebar.collapsed { width: var(--sidebar-sm); }

.sidebar-logo {
  display: flex; align-items: center; gap: 10px;
  padding: 16px 14px;
  border-bottom: 1px solid var(--border);
  min-height: var(--topbar-h);
  white-space: nowrap;
  overflow: hidden;
}
.sidebar-logo .logo-icon {
  width: 28px; height: 28px; border-radius: 8px;
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  display: flex; align-items: center; justify-content: center;
  font-size: 15px; flex-shrink: 0;
}
.sidebar-logo .logo-text { font-weight: 700; font-size: 15px; color: var(--text); overflow: hidden; white-space: nowrap; }
.sidebar-logo .logo-sub { font-size: 10px; color: var(--muted); margin-top: 1px; }

#sidebar-toggle {
  position: absolute; left: calc(var(--sidebar-w) - 13px);
  top: calc(var(--topbar-h)/2 - 13px);
  width: 26px; height: 26px; border-radius: 50%;
  background: var(--card); border: 1px solid var(--border2);
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  font-size: 12px; color: var(--muted); z-index: 110;
  transition: left 0.25s ease;
  box-shadow: 0 2px 8px rgba(0,0,0,0.4);
}
#sidebar.collapsed + #sidebar-toggle,
#sidebar.collapsed ~ * #sidebar-toggle { left: calc(var(--sidebar-sm) - 13px); }

.nav-section { padding: 10px 8px 4px; font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); overflow: hidden; white-space: nowrap; }
#sidebar.collapsed .nav-section { opacity: 0; }

.nav-item {
  display: flex; align-items: center; gap: 10px;
  padding: 9px 14px; border-radius: var(--radius-sm);
  cursor: pointer; transition: background 0.15s; white-space: nowrap; overflow: hidden;
  color: var(--muted); font-weight: 500; font-size: 13.5px;
  margin: 1px 6px;
  position: relative;
}
.nav-item:hover { background: var(--card); color: var(--text); }
.nav-item.active { background: rgba(124,106,247,0.15); color: var(--accent2); }
.nav-item .nav-icon { font-size: 16px; flex-shrink: 0; width: 20px; text-align: center; }
.nav-item .nav-label { overflow: hidden; }
#sidebar.collapsed .nav-item .nav-label { display: none; }
#sidebar.collapsed .nav-item { justify-content: center; padding: 9px; }

.sidebar-bottom {
  margin-top: auto;
  padding: 10px 6px;
  border-top: 1px solid var(--border);
}

/* Status badges na sidebar */
.status-pills { padding: 8px 14px; display: flex; flex-direction: column; gap: 5px; }
#sidebar.collapsed .status-pills { display: none; }
.status-pill {
  display: flex; align-items: center; gap: 7px;
  padding: 5px 10px; border-radius: 99px;
  font-size: 11px; font-weight: 600; cursor: pointer;
  transition: 0.2s; border: 1px solid transparent;
}
.status-pill.off { background: var(--card); color: var(--muted); border-color: var(--border); }
.status-pill.on-focus  { background: rgba(251,191,36,0.15); color: var(--yellow); border-color: rgba(251,191,36,0.3); }
.status-pill.on-dnd    { background: rgba(120,120,160,0.15); color: var(--muted); border-color: var(--border2); }
.pill-dot { width: 7px; height: 7px; border-radius: 50%; background: currentColor; flex-shrink: 0; }

/* ── Main content ── */
#main {
  flex: 1; display: flex; flex-direction: column;
  overflow: hidden; position: relative;
}

/* ── Topbar ── */
#topbar {
  height: var(--topbar-h);
  display: flex; align-items: center; gap: 12px;
  padding: 0 18px;
  border-bottom: 1px solid var(--border);
  background: var(--surface);
  flex-shrink: 0;
}
.topbar-brand {
  cursor: pointer; border-radius: var(--radius-sm); padding: 4px 10px; margin: -4px -10px;
  transition: background 0.15s; text-align: left;
}
.topbar-brand:hover { background: var(--card); }
.topbar-brand:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.topbar-title { font-weight: 700; font-size: 15px; }
.topbar-sub { font-size: 12px; color: var(--muted); }
.topbar-spacer { flex: 1; }
.topbar-mode-badge {
  padding: 4px 10px; border-radius: 99px; font-size: 11px; font-weight: 700;
  display: none;
}
.topbar-mode-badge.focus { background: rgba(251,191,36,0.2); color: var(--yellow); display: flex; align-items: center; gap: 5px; }
.topbar-mode-badge.dnd   { background: rgba(120,120,160,0.2); color: var(--muted);  display: flex; align-items: center; gap: 5px; }

/* ── Painéis ── */
#panels { flex: 1; overflow: hidden; display: flex; flex-direction: column; }
.panel { display: none; flex: 1; overflow: hidden; flex-direction: column; }
.panel.active { display: flex; }
.panel-body { flex: 1; overflow-y: auto; padding: 18px; display: flex; flex-direction: column; gap: 14px; }

/* ── Chat panel ── */
#panel-chat { flex-direction: column; }

.chat-area {
  flex: 1; display: flex; flex-direction: column;
  min-width: 0; overflow: hidden;
}
.chat-messages {
  flex: 1; overflow-y: auto; padding: 16px;
  display: flex; flex-direction: column; gap: 12px;
}
.msg-row { display: flex; }
.msg-row.user { justify-content: flex-end; }
.msg-row.assistant { justify-content: flex-start; }

.msg-bubble {
  max-width: 72%; padding: 10px 14px;
  border-radius: 14px; line-height: 1.55;
  word-break: break-word; font-size: 13.5px;
}
.msg-row.user .msg-bubble {
  background: var(--accent); color: #fff;
  border-bottom-right-radius: 3px;
}
.msg-row.assistant .msg-bubble {
  background: var(--card); color: var(--text);
  border-bottom-left-radius: 3px;
  border: 1px solid var(--border);
}
.msg-sender { font-size: 10px; font-weight: 700; margin-bottom: 4px; opacity: 0.7; }
.msg-row.user .msg-sender { text-align: right; }

.chat-input-wrap {
  padding: 12px 16px;
  border-top: 1px solid var(--border);
  background: var(--surface);
  display: flex; gap: 8px; align-items: center; flex-shrink: 0;
}
.chat-input {
  flex: 1; padding: 10px 14px; border-radius: 99px;
  background: var(--card); border: 1px solid var(--border2);
  color: var(--text); font-size: 13.5px; outline: none;
  transition: border-color 0.2s;
}
.chat-input:focus { border-color: var(--accent); }
.btn-icon {
  width: 38px; height: 38px; border-radius: 50%; border: none;
  background: var(--card); color: var(--muted); cursor: pointer;
  font-size: 16px; display: flex; align-items: center; justify-content: center;
  transition: 0.2s; flex-shrink: 0;
}
.btn-icon:hover { background: var(--border2); color: var(--text); }
.btn-icon.recording { background: var(--red); color: #fff; animation: pulse 1.2s infinite; }
.btn-send {
  width: 38px; height: 38px; border-radius: 50%; border: none;
  background: var(--accent); color: #fff; cursor: pointer;
  font-size: 16px; display: flex; align-items: center; justify-content: center;
  transition: 0.2s; flex-shrink: 0;
}
.btn-send:hover { background: var(--accent2); }
.btn-clear-chat {
  padding: 5px 12px; border-radius: var(--radius-sm); border: 1px solid var(--border2);
  background: transparent; color: var(--muted); cursor: pointer; font-size: 11.5px;
  transition: 0.2s;
}
.btn-clear-chat:hover { background: var(--card); color: var(--red); border-color: var(--red); }

@keyframes pulse { 0%,100% { transform: scale(1); } 50% { transform: scale(1.08); } }

/* Chat header */
.chat-header {
  padding: 10px 16px; border-bottom: 1px solid var(--border);
  display: flex; align-items: center; gap: 10px; flex-shrink: 0;
}
.ai-avatar {
  width: 34px; height: 34px; border-radius: 50%;
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  display: flex; align-items: center; justify-content: center; font-size: 16px;
}
.ai-info .ai-name { font-weight: 700; font-size: 14px; }
.ai-info .ai-status { font-size: 11px; color: var(--green); display: flex; align-items: center; gap: 4px; }
.ai-info .ai-status::before { content: ''; width: 6px; height: 6px; border-radius: 50%; background: var(--green); display: inline-block; }

/* ── Cards / Sections ── */
.card {
  background: var(--card); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 16px;
}
.card-title {
  font-size: 12px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.06em; color: var(--muted);
  margin-bottom: 12px; display: flex; align-items: center; gap: 7px;
}
.card-title .ct-icon { font-size: 14px; }

/* ── Forms ── */
.form-row { display: flex; flex-direction: column; gap: 5px; margin-bottom: 12px; }
.form-row:last-child { margin-bottom: 0; }
.form-label { font-size: 12px; color: var(--muted); font-weight: 600; }
.form-hint { font-size: 11px; color: var(--muted); margin-top: 6px; line-height: 1.45; max-width: 520px; }
.form-input, .form-select, .form-textarea {
  width: 100%; padding: 9px 11px; border-radius: var(--radius-sm);
  background: var(--surface); border: 1px solid var(--border2);
  color: var(--text); font-size: 13px; outline: none; font-family: inherit;
  transition: border-color 0.2s;
}
.form-input:focus, .form-select:focus, .form-textarea:focus { border-color: var(--accent); }
.form-textarea { resize: vertical; min-height: 80px; }
.form-select option { background: var(--surface); }

/* ── Buttons ── */
.btn { padding: 9px 16px; border-radius: var(--radius-sm); border: none; cursor: pointer; font-weight: 600; font-size: 13px; transition: 0.2s; display: inline-flex; align-items: center; gap: 6px; }
.btn-primary { background: var(--accent); color: #fff; }
.btn-primary:hover { background: var(--accent2); }
.btn-success { background: rgba(74,222,128,0.15); color: var(--green); border: 1px solid rgba(74,222,128,0.3); }
.btn-success:hover { background: rgba(74,222,128,0.25); }
.btn-danger  { background: rgba(248,113,113,0.15); color: var(--red); border: 1px solid rgba(248,113,113,0.3); }
.btn-danger:hover  { background: rgba(248,113,113,0.25); }
.btn-ghost  { background: transparent; color: var(--muted); border: 1px solid var(--border2); }
.btn-ghost:hover  { background: var(--card); color: var(--text); }
.btn-full { width: 100%; justify-content: center; }
.btn-save-all { width: 100%; padding: 11px; justify-content: center; background: var(--accent); color: #fff; border-radius: var(--radius-sm); border: none; cursor: pointer; font-weight: 700; font-size: 13.5px; transition: 0.2s; display: flex; align-items: center; gap: 8px; margin-top: 10px; flex-shrink: 0; }
.btn-save-all:hover { background: var(--accent2); }

/* ── Toggle switch ── */
.toggle-row { display: flex; align-items: center; justify-content: space-between; padding: 8px 0; }
.toggle-label { font-size: 13px; color: var(--text); }
.toggle-sub { font-size: 11px; color: var(--muted); margin-top: 2px; }
.toggle {
  position: relative; width: 40px; height: 22px; flex-shrink: 0;
}
.toggle input { opacity: 0; width: 0; height: 0; }
.toggle-slider {
  position: absolute; cursor: pointer; inset: 0;
  background: var(--border2); border-radius: 99px; transition: 0.2s;
}
.toggle-slider::before {
  content: ''; position: absolute; width: 16px; height: 16px;
  left: 3px; top: 3px; background: var(--muted); border-radius: 50%; transition: 0.2s;
}
.toggle input:checked + .toggle-slider { background: var(--accent); }
.toggle input:checked + .toggle-slider::before { transform: translateX(18px); background: #fff; }

/* ── Mode buttons ── */
.mode-btns { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 4px; }
.mode-btn {
  padding: 10px 8px; border-radius: var(--radius-sm); border: 1px solid var(--border2);
  background: var(--surface); cursor: pointer; text-align: center;
  font-size: 12px; font-weight: 600; color: var(--muted);
  transition: 0.2s;
}
.mode-btn:hover { border-color: var(--border2); color: var(--text); background: var(--card); }
.mode-btn.active-focus  { background: rgba(251,191,36,0.12); color: var(--yellow); border-color: rgba(251,191,36,0.4); }
.mode-btn.active-dnd    { background: rgba(120,120,160,0.12); color: var(--muted); border-color: var(--border2); }
.mode-btn .mbi { font-size: 18px; display: block; margin-bottom: 4px; }

/* ── List items ── */
.list-item {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-sm); padding: 11px 13px;
  margin-bottom: 7px; display: flex; align-items: flex-start; gap: 10px;
}
.list-item-body { flex: 1; min-width: 0; }
.list-item-title { font-weight: 600; font-size: 13px; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.list-item-sub { font-size: 11.5px; color: var(--muted); margin-top: 3px; line-height: 1.4; }
.list-item-actions { display: flex; gap: 5px; flex-shrink: 0; }
.btn-sm { padding: 4px 9px; font-size: 11px; border-radius: 4px; border: none; cursor: pointer; font-weight: 600; }
.btn-sm-edit { background: rgba(96,165,250,0.15); color: var(--blue); }
.btn-sm-del  { background: rgba(248,113,113,0.15); color: var(--red); }
.btn-sm-act  { background: rgba(74,222,128,0.15); color: var(--green); }

/* ── Search / filter ── */
.search-input {
  width: 100%; padding: 9px 12px 9px 34px; border-radius: var(--radius-sm);
  background: var(--surface); border: 1px solid var(--border2);
  color: var(--text); font-size: 13px; outline: none; position: relative;
  transition: border-color 0.2s;
}
.search-input:focus { border-color: var(--accent); }
.search-wrap { position: relative; margin-bottom: 12px; }
.search-wrap::before { content: '🔍'; position: absolute; left: 10px; top: 50%; transform: translateY(-50%); font-size: 12px; pointer-events: none; }

/* ── Tags / Badges ── */
.badge { padding: 2px 7px; border-radius: 99px; font-size: 10px; font-weight: 700; }
.badge-accent  { background: rgba(124,106,247,0.2); color: var(--accent2); }
.badge-green   { background: rgba(74,222,128,0.15); color: var(--green); }
.badge-yellow  { background: rgba(251,191,36,0.15); color: var(--yellow); }
.badge-red     { background: rgba(248,113,113,0.15); color: var(--red); }

/* ── Param row ── */
.param-row {
  display: flex; gap: 7px; align-items: center;
  background: var(--surface); padding: 9px 11px; border-radius: var(--radius-sm);
  border: 1px dashed var(--border2); margin-bottom: 8px;
}
.param-row .form-input, .param-row .form-select { padding: 6px 9px; font-size: 12px; }
.param-row .form-input { flex: 1; min-width: 0; }
.param-row .form-select { width: auto; min-width: 90px; }
.param-row .btn-rm { background: none; border: none; color: var(--muted); cursor: pointer; font-size: 16px; flex-shrink: 0; padding: 0 4px; }
.param-row .btn-rm:hover { color: var(--red); }

/* ── Vision panel ── */
.vision-img-wrap {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); overflow: hidden;
  display: flex; align-items: center; justify-content: center;
  min-height: 180px; margin-bottom: 12px;
}
.vision-img-wrap img { max-width: 100%; max-height: 260px; object-fit: contain; display: block; }
.vision-desc {
  width: 100%; min-height: 90px; padding: 11px 13px;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-sm); color: var(--muted);
  font-size: 12.5px; resize: none; font-family: inherit; outline: none;
}

/* ── Modal ── */
.modal-overlay {
  display: none; position: fixed; inset: 0;
  background: rgba(0,0,0,0.6); z-index: 500;
  align-items: center; justify-content: center; padding: 20px;
}
.modal-overlay.open { display: flex; }
.modal-box {
  background: var(--card); border: 1px solid var(--border2);
  border-radius: var(--radius); padding: 22px;
  width: 100%; max-width: 560px; max-height: 90vh; overflow-y: auto;
}
.modal-title { font-size: 16px; font-weight: 700; margin-bottom: 18px; display: flex; align-items: center; gap: 8px; }
.modal-footer { display: flex; gap: 8px; margin-top: 18px; }
.modal-footer .btn { flex: 1; justify-content: center; padding: 11px; }

/* ── Skill item ── */
.skill-row { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 9px 12px; margin-bottom: 7px; display: flex; align-items: center; gap: 10px; }
.skill-id { color: var(--accent2); font-weight: 700; font-size: 12px; flex-shrink: 0; }
.skill-text { flex: 1; font-size: 12.5px; color: var(--muted); }

/* ── RP active display ── */
.rp-active-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 12px; margin-bottom: 10px; }
.rp-active-card .rp-name { font-weight: 700; color: var(--green); margin-bottom: 5px; }
.rp-active-card .rp-detail { font-size: 12px; color: var(--muted); line-height: 1.4; }

/* ── Responsive: tablet ── */
@media (max-width: 900px) {
  #sidebar { width: var(--sidebar-sm); }
  #sidebar .nav-label, #sidebar .logo-text, #sidebar .logo-sub,
  #sidebar .nav-section, #sidebar .status-pills { display: none; }
  #sidebar .nav-item { justify-content: center; padding: 10px; }
  #sidebar .sidebar-logo { justify-content: center; padding: 14px; }
  #sidebar-toggle { display: none; }
}

/* ── Responsive: mobile ── */
@media (max-width: 600px) {
  #sidebar { display: none; }
  #sidebar-toggle { display: none; }
  #app { flex-direction: column; }
  #main { height: calc(100vh - var(--nav-h)); }
  #topbar { display: none; }
  #mobile-nav {
    display: flex !important;
    height: var(--nav-h);
    background: var(--surface);
    border-top: 1px solid var(--border);
    order: 2;
  }
  .panel-body { padding: 12px; }
}

/* Mobile bottom nav */
#mobile-nav {
  display: none;
  align-items: stretch;
  flex-shrink: 0;
}
.mnav-item {
  flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 3px; cursor: pointer; color: var(--muted); font-size: 10px; font-weight: 600;
  border-top: 2px solid transparent; transition: 0.15s;
}
.mnav-item.active { color: var(--accent2); border-top-color: var(--accent); }
.mnav-icon { font-size: 19px; }

/* ── Empty state ── */
.empty-state { text-align: center; padding: 40px 20px; color: var(--muted); }
.empty-state .es-icon { font-size: 36px; margin-bottom: 12px; opacity: 0.5; }
.empty-state p { font-size: 13px; line-height: 1.5; }

/* API key row */
.api-row { display: flex; gap: 8px; align-items: center; }
.api-row .form-input { flex: 1; }
.api-eye { background: none; border: none; color: var(--muted); cursor: pointer; font-size: 15px; flex-shrink: 0; }

/* ── Status bar ── */
#chat-status {
  display: none; align-items: center; gap: 8px;
  padding: 7px 16px; font-size: 12px; color: var(--muted);
  background: var(--surface); border-top: 1px solid var(--border);
  flex-shrink: 0;
}
#chat-status.visible { display: flex; }
.status-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--accent); flex-shrink: 0;
  animation: blink 1.2s ease-in-out infinite;
}
@keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0.2; } }

/* ── Upload / Arquivos ── */
.file-preview-strip {
  display: none; gap: 8px; padding: 10px 16px;
  background: var(--surface); border-top: 1px solid var(--border);
  flex-wrap: wrap; align-items: flex-start; flex-shrink: 0;
}
.file-preview-strip.visible { display: flex; }
.file-thumb {
  position: relative; border-radius: 8px; overflow: hidden;
  border: 1px solid var(--border2); background: var(--card); flex-shrink: 0;
}
.file-thumb img { width: 60px; height: 60px; object-fit: cover; display: block; }
.file-thumb-card {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 10px; max-width: 160px;
}
.file-thumb-icon { font-size: 22px; flex-shrink: 0; }
.file-thumb-name { font-size: 11px; color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.file-thumb-remove {
  position: absolute; top: 3px; right: 3px;
  background: rgba(0,0,0,0.75); border: none; border-radius: 50%;
  width: 18px; height: 18px; color: #fff; cursor: pointer;
  font-size: 10px; display: flex; align-items: center; justify-content: center;
  line-height: 1;
}
/* Mensagem com imagem */
.msg-img {
  max-width: 100%; max-height: 260px; border-radius: 8px;
  display: block; margin-top: 6px; cursor: zoom-in;
  object-fit: contain;
}
/* Card de arquivo no chat */
.msg-file {
  display: flex; align-items: center; gap: 10px;
  background: rgba(255,255,255,0.06); border-radius: 8px;
  padding: 10px 12px; margin-top: 6px;
  text-decoration: none; color: var(--text);
  border: 1px solid var(--border2); transition: 0.2s;
}
.msg-file:hover { background: rgba(255,255,255,0.1); }
.msg-file-icon { font-size: 24px; flex-shrink: 0; }
.msg-file-info { flex: 1; min-width: 0; }
.msg-file-name { font-size: 13px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.msg-file-size { font-size: 11px; color: var(--muted); margin-top: 2px; }
/* Lightbox */
#lightbox {
  display: none; position: fixed; inset: 0; z-index: 900;
  background: rgba(0,0,0,0.9); align-items: center; justify-content: center;
  cursor: zoom-out;
}
#lightbox.open { display: flex; }
#lightbox img { max-width: 92vw; max-height: 92vh; border-radius: 10px; object-fit: contain; }
/* Toast — feedback de salvamento */
#toast {
  position: fixed; bottom: 28px; left: 50%; transform: translateX(-50%);
  max-width: min(92vw, 420px); padding: 12px 18px; border-radius: var(--radius);
  background: var(--card); border: 1px solid var(--border2); color: var(--text);
  font-size: 13px; font-weight: 500; z-index: 9500; text-align: center;
  box-shadow: 0 8px 32px rgba(0,0,0,0.45);
  opacity: 0; pointer-events: none; transition: opacity 0.28s ease;
}
#toast.show { opacity: 1; pointer-events: auto; }
#toast.error { border-color: var(--red); color: #fecaca; }
</style>
</head>
<body>
<div id="toast" role="status" aria-live="polite"></div>
<div id="app">

  <!-- ═══ SIDEBAR ═══ -->
  <nav id="sidebar">
    <div class="sidebar-logo">
      <div class="logo-icon">🤖</div>
      <div>
        <div class="logo-text" id="sidebar-ai-name">Assistant</div>
        <div class="logo-sub">AI Framework</div>
      </div>
    </div>

    <div class="nav-item active" data-panel="chat" onclick="showPanel('chat',this)">
      <span class="nav-icon">💬</span><span class="nav-label" data-i18n="nav.chat">Chat</span>
    </div>

    <div class="nav-section" style="flex-shrink:0" data-i18n="nav.section_config">Configuration</div>
    <div class="nav-item" data-panel="sistema" onclick="showPanel('sistema',this)">
      <span class="nav-icon">⚙️</span><span class="nav-label" data-i18n="nav.system">System</span>
    </div>
    <div class="nav-item" data-panel="persona" onclick="showPanel('persona',this)">
      <span class="nav-icon">🎭</span><span class="nav-label" data-i18n="nav.persona">Persona</span>
    </div>
    <div class="nav-item" data-panel="plugins" onclick="showPanel('plugins',this)">
      <span class="nav-icon">🔌</span><span class="nav-label" data-i18n="nav.plugins_mcp">Plugins MCP</span>
    </div>
    <div class="nav-item" data-panel="roleplay" onclick="showPanel('roleplay',this)">
      <span class="nav-icon">🔞</span><span class="nav-label" data-i18n="nav.roleplay">Roleplay</span>
    </div>

    <div class="nav-section" data-i18n="nav.section_data">Data</div>
    <div class="nav-item" data-panel="visao" onclick="showPanel('visao',this)">
      <span class="nav-icon">👁️</span><span class="nav-label" data-i18n="nav.vision">Vision</span>
    </div>
    <div class="nav-item" data-panel="memorias" onclick="showPanel('memorias',this)">
      <span class="nav-icon">🧠</span><span class="nav-label" data-i18n="nav.memory">Memory</span>
    </div>

    <div class="sidebar-bottom">
      <div class="status-pills">
        <div class="status-pill off" id="pill-foco" onclick="toggleModo('foco')">
          <div class="pill-dot"></div> <span data-i18n="sys.focus_mode">Focus Mode</span>
        </div>
        <div class="status-pill off" id="pill-dnd" onclick="toggleModo('nao_perturbe')">
          <div class="pill-dot"></div> <span data-i18n="sys.dnd_mode">Do Not Disturb</span>
        </div>
      </div>
    </div>
  </nav>

  <!-- Toggle sidebar (desktop) -->
  <button id="sidebar-toggle" onclick="toggleSidebar()" title="Recolher menu">‹</button>

  <!-- ═══ MAIN ═══ -->
  <div id="main">

    <!-- Topbar -->
    <div id="topbar">
      <div class="topbar-brand" id="topbar-brand" role="button" tabindex="0"
        data-i18n-title="nav.back_to_chat" title="Back to chat"
        onclick="showPanel('chat', null)"
        onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();showPanel('chat',null);}">
        <div class="topbar-title" id="topbar-ai-name">Assistant</div>
        <div class="topbar-sub" id="topbar-section">Chat</div>
      </div>
      <div class="topbar-spacer"></div>
      <div class="topbar-mode-badge" id="badge-foco">🎯 <span data-i18n="sys.focus_mode">Focus Mode</span></div>
      <div class="topbar-mode-badge" id="badge-dnd">🔕 <span data-i18n="sys.dnd_mode">Do Not Disturb</span></div>
    </div>

    <!-- Painéis -->
    <div id="panels">

      <!-- ── CHAT ── -->
      <div class="panel active" id="panel-chat">
        <div class="chat-header">
          <div class="ai-avatar">🤖</div>
          <div class="ai-info">
            <div class="ai-name" id="chat-ai-name">Assistant</div>
            <div class="ai-status">online</div>
          </div>
          <div style="margin-left:auto;display:flex;gap:8px;align-items:center">
            <button id="btn-batepapo" onclick="toggleBatepapo()"
              title="Chat Mode — rotating skills for casual conversation"
              data-i18n-title="chat.mode_tooltip"
              style="padding:5px 12px;border-radius:99px;border:1px solid var(--border2);
                     background:transparent;color:var(--muted);font-size:12px;
                     font-weight:600;cursor:pointer;transition:0.2s;display:flex;align-items:center;gap:5px">
              💬 Chat Mode
            </button>
            <button class="btn-clear-chat" onclick="limparChat()" data-i18n="chat.clear">🗑 Clear</button>
          </div>
        </div>
        <div class="chat-messages" id="chat-messages">
          <div class="empty-state">
            <div class="es-icon">💬</div>
            <p data-i18n="chat.empty">No messages yet.<br>Start the conversation!</p>
          </div>
        </div>
        <div id="chat-status">
          <div class="status-dot"></div>
          <span id="chat-status-text"></span>
        </div>
        <div class="file-preview-strip" id="file-preview-strip"></div>
        <div class="chat-input-wrap">
          <input type="file" id="file-input" multiple
            accept="image/*,.pdf,.txt,.py,.js,.ts,.json,.csv,.md,.docx,.xlsx"
            style="display:none" onchange="arquivosSelecionados(this)">
          <button class="btn-icon" onclick="document.getElementById('file-input').click()" title="Attach file">📎</button>
          <button class="btn-icon" id="btn-mic" onclick="toggleGravacao()" title="Voice">🎤</button>
          <input class="chat-input" id="chat-input" placeholder="Type a message…" data-i18n-placeholder="chat.placeholder" onkeydown="if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();enviarMensagem()}" />
          <button class="btn-send" onclick="enviarMensagem()" title="Send">➤</button>
        </div>
      </div>

      <!-- ── SISTEMA ── -->
      <div class="panel" id="panel-sistema">
        <div class="panel-body">

          <div class="card">
            <div class="card-title"><span class="ct-icon">🌐</span> Language / Idioma</div>
            <div class="form-row">
              <label class="form-label">Interface & terminal language</label>
              <select class="form-select" id="ui_language" onchange="trocarIdioma(this.value)">
                <option value="en">🇺🇸 English</option>
                <option value="pt">🇧🇷 Português (BR)</option>
              </select>
            </div>
          </div>

          <div class="card">
            <div class="card-title"><span class="ct-icon">🤖</span> <span data-i18n="sys.ai_engine">AI Engine</span></div>
            <div class="form-row">
              <label class="form-label" data-i18n="sys.provider">Provider</label>
              <select class="form-select" id="modo_ia" onchange="verificarMotor()">
                <option value="groq">Groq</option>
                <option value="openrouter">OpenRouter</option>
                <option value="openai">OpenAI</option>
                <option value="local">Local (Ollama)</option>
              </select>
            </div>
            <div id="bloco_modelo_local" style="display:none">
              <div class="form-row">
                <label class="form-label" data-i18n="sys.local_model">Local Model</label>
                <input class="form-input" id="modelo_ia_local" placeholder="e.g. llama3.2:1b">
              </div>
            </div>
            <div id="bloco_especialistas">
            <div class="form-row">
              <label class="form-label" data-i18n="sys.main_model">Default Model</label>
              <select class="form-select" id="modelo_principal"></select>
            </div>
            <div class="form-row">
              <label class="form-label" data-i18n="sys.vision_model">Vision Specialist</label>
              <select class="form-select" id="modelo_visao"></select>
            </div>
            <div class="form-row">
              <label class="form-label" data-i18n="sys.code_model">Code Specialist</label>
              <select class="form-select" id="modelo_codigo"></select>
            </div>
            <div class="form-row">
              <label class="form-label" data-i18n="sys.roleplay_model">Roleplay / Persona Specialist</label>
              <select class="form-select" id="modelo_roleplay"></select>
            </div>
            </div>
          </div>

          <div class="card">
            <div class="card-title"><span class="ct-icon">🔑</span> <span data-i18n="sys.api_keys">API Keys</span></div>
            <div class="form-row">
              <label class="form-label">OpenRouter</label>
              <div class="api-row"><input class="form-input" type="password" id="api_openrouter" placeholder="sk-or-..."><button class="api-eye" onclick="toggleEye(this,'api_openrouter')">👁</button></div>
            </div>
            <div class="form-row">
              <label class="form-label">Groq</label>
              <div class="api-row"><input class="form-input" type="password" id="api_groq" placeholder="gsk_..."><button class="api-eye" onclick="toggleEye(this,'api_groq')">👁</button></div>
            </div>
            <div class="form-row">
              <label class="form-label">OpenAI</label>
              <div class="api-row"><input class="form-input" type="password" id="api_openai" placeholder="sk-..."><button class="api-eye" onclick="toggleEye(this,'api_openai')">👁</button></div>
            </div>
            <div class="form-row">
              <label class="form-label">ElevenLabs</label>
              <div class="api-row"><input class="form-input" type="password" id="api_elevenlabs" placeholder="..."><button class="api-eye" onclick="toggleEye(this,'api_elevenlabs')">👁</button></div>
            </div>
            <div class="form-row">
              <label class="form-label" data-i18n="sys.hf_token">Hugging Face</label>
              <div class="api-row"><input class="form-input" type="password" id="api_huggingface" placeholder="hf_..."><button class="api-eye" onclick="toggleEye(this,'api_huggingface')">👁</button></div>
              <p class="form-hint" data-i18n="sys.hf_hint">Token for embeddings / gated models. Optional if you only use public weights.</p>
            </div>
          </div>

          <div class="card">
            <div class="card-title"><span class="ct-icon">🎤</span> <span data-i18n="sys.audio">Audio</span></div>
            <div class="form-row">
              <label class="form-label" data-i18n="sys.listen_method">Listen Method</label>
              <select class="form-select" id="audio_metodo_escuta">
                <option value="atalho" data-i18n="sys.button_mode">Button (X mouse)</option>
                <option value="silero" data-i18n="sys.vad_mode">Continuous (VAD)</option>
              </select>
            </div>
            <div class="form-row">
              <label class="form-label" data-i18n="sys.stt_engine">Transcription Engine</label>
              <select class="form-select" id="audio_motor_transcricao" onchange="atualizarVisibilidadeSTT()">
                <option value="whisper">Whisper (local)</option>
                <option value="google">Google STT</option>
              </select>
            </div>
            <div class="form-row" id="row_whisper_model">
              <label class="form-label" data-i18n="sys.whisper_model">Whisper model size</label>
              <select class="form-select" id="audio_whisper_modelo">
                <option value="tiny">tiny (fastest)</option>
                <option value="base">base</option>
                <option value="small">small</option>
                <option value="medium">medium</option>
              </select>
            </div>
            <div class="form-row">
              <label class="form-label" data-i18n="sys.tts_engine">Voice Synthesizer</label>
              <select class="form-select" id="audio_motor_voz">
                <option value="edge">Edge TTS (online)</option>
                <option value="kokoro">Kokoro TTS (local, high quality)</option>
                <option value="piper">Piper TTS (local, language-native)</option>
                <option value="elevenlabs">ElevenLabs (online, premium)</option>
              </select>
            </div>
            <div class="form-row">
              <label class="form-label" data-i18n="sys.edge_voice">Edge TTS Voice</label>
              <input class="form-input" id="audio_voz_edge" placeholder="en-US-AriaNeural">
            </div>
          </div>

          <div class="card">
            <div class="card-title"><span class="ct-icon">🧭</span> <span data-i18n="sys.quick_modes">Quick Modes</span></div>
            <div class="mode-btns">
              <button class="mode-btn" id="btn-foco" onclick="toggleModo('foco')">
                <span class="mbi">🎯</span><span data-i18n="sys.focus_mode">Focus Mode</span>
              </button>
              <button class="mode-btn" id="btn-dnd" onclick="toggleModo('nao_perturbe')">
                <span class="mbi">🔕</span><span data-i18n="sys.dnd_mode">Do Not Disturb</span>
              </button>
            </div>
            <div style="height:12px"></div>
            <div class="toggle-row">
              <div>
                <div class="toggle-label" data-i18n="sys.watchdog">🐕 Proactive Watchdog</div>
                <div class="toggle-sub" data-i18n="sys.watchdog_sub">AI checks in periodically</div>
              </div>
              <label class="toggle"><input type="checkbox" id="watchdog_ativo"><span class="toggle-slider"></span></label>
            </div>
            <div class="form-row" style="margin-top:10px">
              <label class="form-label" data-i18n="sys.watchdog_interval">Watchdog Interval (minutes)</label>
              <input class="form-input" type="number" id="watchdog_intervalo" min="1" max="120" value="10">
            </div>
            <div style="height:12px"></div>
            <div class="toggle-row">
              <div>
                <div class="toggle-label" data-i18n="sys.vision_bg">👁️ Background Screen Analysis</div>
                <div class="toggle-sub" data-i18n="sys.vision_bg_sub">AI monitors screen context automatically (uses tokens)</div>
              </div>
              <label class="toggle"><input type="checkbox" id="vision_bg_ativo"><span class="toggle-slider"></span></label>
            </div>
            <div style="height:12px"></div>
            <div class="toggle-row">
              <div>
                <div class="toggle-label" data-i18n="sys.lipsync">🎤 VTube Studio Lip Sync</div>
                <div class="toggle-sub" data-i18n="sys.lipsync_sub">Animate model mouth when AI speaks (requires VTube Studio)</div>
              </div>
              <label class="toggle"><input type="checkbox" id="lipsync_ativo"><span class="toggle-slider"></span></label>
            </div>
            <div class="form-row">
              <label class="form-label" data-i18n="sys.mood">Current Mood / Vibe</label>
              <input class="form-input" id="humor_ia" placeholder="e.g. Friendly, Focused, Playful…">
            </div>
          </div>

          <button class="btn-save-all" onclick="salvarTudo()" data-i18n="sys.save">💾 Save Settings</button>
        </div>
      </div>

      <!-- PERSONA -->
      <div class="panel" id="panel-persona">
        <div class="panel-body">
          <div class="card">
            <div class="card-title"><span class="ct-icon">🤖</span> <span data-i18n="persona.identity">Identity</span></div>
            <div class="form-row">
              <label class="form-label" data-i18n="persona.ai_name">AI Name</label>
              <input class="form-input" id="nome_ia" placeholder="Assistant name">
            </div>
            <div class="form-row">
              <label class="form-label" data-i18n="persona.system_prompt">System Prompt</label>
              <textarea class="form-textarea" id="prompt_sistema" style="min-height:160px"></textarea>
            </div>
          </div>
          <div class="card">
            <div class="card-title"><span class="ct-icon">⚡</span> <span data-i18n="persona.skills">Skills</span></div>
            <div id="skills-container"></div>
            <div style="display:flex;gap:8px;margin-top:8px">
              <input class="form-input" id="new_skill_id" placeholder="ID" style="width:35%">
              <input class="form-input" id="new_skill_text" data-i18n-placeholder="persona.skill_desc" placeholder="Description">
            </div>
            <button class="btn btn-ghost btn-full" style="margin-top:8px" onclick="adicionarSkill()" data-i18n="persona.add_skill">+ Add Skill</button>
          </div>
          <button class="btn-save-all" onclick="salvarTudo()" data-i18n="persona.save">💾 Save Persona</button>
        </div>
      </div>

      <!-- PLUGINS MCP -->
      <div class="panel" id="panel-plugins">
        <div class="panel-body">
          <div class="card">
            <div class="card-title"><span class="ct-icon">🛠️</span> <span data-i18n="plugins.new">New Tool</span></div>
            <div class="form-row">
              <label class="form-label" data-i18n="plugins.name">Name / ID</label>
              <input class="form-input" id="mcp_nome" placeholder="e.g. open_browser">
            </div>
            <div class="form-row">
              <label class="form-label" data-i18n="plugins.desc">Description (helps AI know when to use it)</label>
              <input class="form-input" id="mcp_desc">
            </div>
            <div id="mcp-params-container"></div>
            <button class="btn btn-ghost" style="margin-bottom:10px" onclick="adicionarParametroVisual()" data-i18n="plugins.add_param">+ Parameter</button>
            <div class="form-row">
              <label class="form-label" data-i18n="plugins.pip_req">pip packages (optional)</label>
              <textarea class="form-textarea" id="mcp_pip" style="font-family:monospace;font-size:12px;min-height:52px" data-i18n-placeholder="plugins.pip_placeholder" placeholder="e.g. pywhatkit — one per line or comma-separated"></textarea>
              <p style="font-size:11px;color:var(--muted);margin:4px 0 0" data-i18n="plugins.pip_hint">Installed automatically before the tool runs (same Python as the assistant).</p>
            </div>
            <div class="form-row">
              <label class="form-label" data-i18n="plugins.code">Python Code</label>
              <textarea class="form-textarea" id="mcp_codigo" style="font-family:monospace;font-size:12px;min-height:100px">ai_response = "Action completed successfully!"</textarea>
            </div>
            <button class="btn btn-primary btn-full" onclick="salvarPluginVisual()" data-i18n="plugins.save">💾 Save Tool</button>
          </div>
          <div class="card">
            <div class="card-title"><span class="ct-icon">🔌</span> <span data-i18n="plugins.installed">Installed</span></div>
            <div id="mcp-list"><div class="empty-state"><div class="es-icon">🔌</div><p data-i18n="plugins.empty">No plugins installed.</p></div></div>
          </div>
        </div>
      </div>

      <!-- ROLEPLAY -->
      <div class="panel" id="panel-roleplay">
        <div class="panel-body">
          <div class="card">
            <div class="card-title"><span class="ct-icon">🎬</span> <span data-i18n="rp.active_scenario">Active Scenario</span></div>
            <div id="rp-active-display" class="rp-active-card">
              <div style="color:var(--muted);font-size:13px" data-i18n="rp.no_active">No roleplay active.</div>
            </div>
            <button id="btn-desativar-rp" class="btn btn-danger btn-full" style="display:none" onclick="desativarRoleplay()" data-i18n="rp.deactivate">🛑 Deactivate Roleplay</button>
          </div>
          <div class="card">
            <div class="card-title"><span class="ct-icon">✏️</span> <span data-i18n="rp.create">Create Scenario</span></div>
            <div class="form-row">
              <label class="form-label" data-i18n="rp.name">Scenario Name</label>
              <input class="form-input" id="rp_nome" placeholder="e.g. Medieval Castle, Cyberpunk…">
            </div>
            <div class="form-row">
              <label class="form-label" data-i18n="rp.ai_persona">AI Persona (who the AI will be)</label>
              <textarea class="form-textarea" id="rp_persona_ia" placeholder="e.g. You are Lyra, an elven archer…"></textarea>
            </div>
            <div class="form-row">
              <label class="form-label" data-i18n="rp.user_persona">User Persona (who you will be)</label>
              <textarea class="form-textarea" id="rp_persona_usuario" placeholder="e.g. You are Kael, a knight…"></textarea>
            </div>
            <div class="form-row">
              <label class="form-label" data-i18n="rp.setting">Setting / Scenario</label>
              <textarea class="form-textarea" id="rp_cenario" placeholder="e.g. A dark tavern on the frontier…"></textarea>
            </div>
            <div class="toggle-row">
              <div class="toggle-label" style="color:var(--red)" data-i18n="rp.nsfw">🔞 NSFW Content</div>
              <label class="toggle"><input type="checkbox" id="rp_nsfw"><span class="toggle-slider"></span></label>
            </div>
            <button class="btn btn-primary btn-full" style="margin-top:12px" onclick="salvarRoleplay()" data-i18n="rp.save">💾 Create Scenario</button>
          </div>
          <div class="card">
            <div class="card-title"><span class="ct-icon">📚</span> <span data-i18n="rp.saved">Saved Scenarios</span></div>
            <div id="rp-list"><div class="empty-state"><div class="es-icon">🎭</div><p data-i18n="rp.none">No scenarios saved.</p></div></div>
          </div>
        </div>
      </div>

      <!-- VISION -->
      <div class="panel" id="panel-visao">
        <div class="panel-body">
          <div class="card">
            <div class="card-title"><span class="ct-icon">📸</span> <span data-i18n="vision.screenshot">Last Screenshot</span></div>
            <div class="vision-img-wrap">
              <img id="img-last-vision" src="/api/last_vision" alt="No capture yet">
            </div>
          </div>
          <div class="card">
            <div class="card-title"><span class="ct-icon">📝</span> <span data-i18n="vision.context">Visual Context</span></div>
            <textarea id="box-visao-contexto" class="vision-desc" readonly data-i18n-placeholder="vision.waiting" placeholder="Waiting for capture…"></textarea>
          </div>
        </div>
      </div>

      <!-- MEMORIES -->
      <div class="panel" id="panel-memorias">
        <div class="panel-body">
          <div class="card">
            <div class="card-title">
              <span class="ct-icon">🧠</span> <span data-i18n="mem.title">Semantic Memory (RAG)</span>
              <span class="badge badge-accent" id="mem-count" style="margin-left:auto">0</span>
            </div>
            <p style="font-size:12px;color:var(--muted);margin-bottom:12px;line-height:1.5" data-i18n="mem.desc">
              Facts extracted automatically from conversations and indexed by semantic similarity.
              Used to personalize future responses without repeating context.
            </p>
            <div style="display:flex;gap:8px;margin-bottom:12px">
              <div class="search-wrap" style="flex:1;margin:0">
                <input class="search-input" id="mem-search" data-i18n-placeholder="mem.filter" placeholder="Filter memories…" oninput="filtrarMemorias()">
              </div>
              <button class="btn btn-danger" onclick="apagarTodasMemorias()" data-i18n="mem.delete_all">🗑 Delete All</button>
            </div>
            <div id="mem-list"><div class="empty-state"><div class="es-icon">🧠</div><p data-i18n="mem.none">No memories yet.<br>Chat so the assistant can learn.</p></div></div>
          </div>
        </div>
      </div>

    </div><!-- /panels -->

    <!-- Mobile bottom nav -->
    <nav id="mobile-nav">
      <div class="mnav-item active" onclick="showPanel('chat',this)"><span class="mnav-icon">💬</span><span data-i18n="nav.chat">Chat</span></div>
      <div class="mnav-item" onclick="showPanel('sistema',this)"><span class="mnav-icon">⚙️</span><span data-i18n="nav.system">Config</span></div>
      <div class="mnav-item" onclick="showPanel('persona',this)"><span class="mnav-icon">🎭</span><span data-i18n="nav.persona">Persona</span></div>
      <div class="mnav-item" onclick="showPanel('memorias',this)"><span class="mnav-icon">🧠</span><span data-i18n="nav.memory">Memory</span></div>
      <div class="mnav-item" onclick="showPanel('plugins',this)"><span class="mnav-icon">🔌</span><span data-i18n="nav.plugins">Plugins</span></div>
    </nav>

  </div><!-- /main -->
</div><!-- /app -->

<!-- Modal Editar Plugin -->
<div class="modal-overlay" id="modal-editar">
  <div class="modal-box">
    <div class="modal-title">✏️ <span data-i18n="modal.edit_tool">Edit Tool</span></div>
    <div class="form-row">
      <label class="form-label" data-i18n="plugins.id_readonly">ID (read only)</label>
      <input class="form-input" id="edit_nome" readonly>
    </div>
    <div class="form-row">
      <label class="form-label" data-i18n="plugins.desc">Description</label>
      <input class="form-input" id="edit_desc">
    </div>
    <div class="form-row">
      <label class="form-label" data-i18n="plugins.params">Parameters</label>
      <div id="edit-params-container"></div>
      <button class="btn btn-ghost" style="margin-top:6px" onclick="adicionarParametroEdicao()" data-i18n="plugins.add_param">+ Parameter</button>
    </div>
    <div class="form-row">
      <label class="form-label" data-i18n="plugins.pip_req">pip packages (optional)</label>
      <textarea class="form-textarea" id="edit_pip" style="font-family:monospace;font-size:12px;min-height:52px" data-i18n-placeholder="plugins.pip_placeholder" placeholder="e.g. pywhatkit"></textarea>
    </div>
    <div class="form-row">
      <label class="form-label" data-i18n="plugins.code">Python Code</label>
      <textarea class="form-textarea" id="edit_codigo" style="font-family:monospace;font-size:12px;min-height:130px"></textarea>
    </div>
    <div class="modal-footer">
      <button class="btn btn-success" onclick="salvarEdicao()">✓ Salvar</button>
      <button class="btn btn-ghost" onclick="fecharModal()">Cancelar</button>
    </div>
  </div>
</div>

<script>
// ═══════════════════════════════════════════
// STATE
// ═══════════════════════════════════════════
let nomeIA = "Assistant";
let skillsAtuais = [];
let recognition;
let isRecording = false;
let _sseAtivo = false;
let _todasMemorias = [];
let _modoFoco = false;
let _modoDND  = false;
let _sidebarCollapsed = false;
let _arquivosPendentes = []; // {file, url_local, url_servidor, tipo, nome}

// ═══════════════════════════════════════════
// i18n — UI TRANSLATIONS
// ═══════════════════════════════════════════
const _uiStrings = {
  en: {
    // Chat
    "chat.placeholder":   "Type a message…",
    "chat.clear":         "🗑 Clear",
    "chat.empty":         "No messages yet.\nStart the conversation!",
    "chat.loading":       "Loading conversation…",
    "chat.new_started":   "New chat started!\nYou can start talking.",
    "chat.mode_on":       "💬 Chat ✓",
    "chat.mode_off":      "💬 Chat Mode",
    "chat.mode_tooltip":  "Chat Mode — rotating skills for casual conversation",
    "chat.mode_toast":    "💬 Chat mode activated!",
    // Mem
    "mem.none":           "No memories yet.\nChat so the assistant can learn.",
    "mem.title":          "Semantic Memory (RAG)",
    "mem.desc":           "Facts extracted automatically from conversations and indexed by semantic similarity.\nUsed to personalize future responses without repeating context.",
    "mem.filter":         "Filter memories…",
    "mem.delete_all":     "🗑 Delete All",
    // System panel
    "sys.ai_engine":      "AI Engine",
    "sys.provider":       "Provider",
    "sys.local_model":    "Local Model",
    "sys.main_model":     "Default Model",
    "sys.vision_model":   "Vision Specialist",
    "sys.code_model":     "Code Specialist",
    "sys.roleplay_model": "Roleplay / Persona Specialist",
    "sys.api_keys":       "API Keys",
    "sys.hf_token":       "Hugging Face token",
    "sys.hf_hint":        "Used for semantic memory embeddings and private Hub downloads. Leave empty if you only use public models.",
    "sys.whisper_model":  "Whisper model size",
    "ui.toast_saved":     "Settings saved.",
    "ui.toast_error":     "Could not save. Check the console.",
    "ui.save_working":    "Saving…",
    "ui.save_done":       "Saved!",
    "sys.audio":          "Audio",
    "sys.listen_method":  "Listen Method",
    "sys.button_mode":    "Button (X mouse)",
    "sys.vad_mode":       "Continuous (VAD)",
    "sys.stt_engine":     "Transcription Engine",
    "sys.tts_engine":     "Voice Synthesizer",
    "sys.edge_voice":     "Edge TTS Voice",
    "sys.quick_modes":    "Quick Modes",
    "sys.focus_mode":     "Focus Mode",
    "sys.dnd_mode":       "Do Not Disturb",
    "sys.watchdog":       "🐕 Proactive Watchdog",
    "sys.watchdog_sub":   "AI checks in periodically",
    "sys.watchdog_interval": "Watchdog Interval (minutes)",
    "sys.vision_bg":      "👁️ Background Screen Analysis",
    "sys.vision_bg_sub":  "AI monitors screen context automatically (uses tokens)",
    "sys.lipsync":        "🎤 VTube Studio Lip Sync",
    "sys.lipsync_sub":    "Animate model mouth when AI speaks (requires VTube Studio)",
    "sys.mood":           "Current Mood / Vibe",
    "sys.save":           "💾 Save Settings",
    // Persona panel
    "persona.identity":   "Identity",
    "persona.ai_name":    "AI Name",
    "persona.system_prompt": "System Prompt",
    "persona.skills":     "Skills",
    "persona.skill_desc": "Description",
    "persona.add_skill":  "+ Add Skill",
    "persona.save":       "💾 Save Persona",
    // Plugins panel
    "plugins.new":        "New Tool",
    "plugins.name":       "Name / ID",
    "plugins.desc":       "Description (helps AI know when to use it)",
    "plugins.add_param":  "+ Parameter",
    "plugins.code":       "Python Code",
    "plugins.pip_req":    "pip packages (optional)",
    "plugins.pip_placeholder": "e.g. pywhatkit — one per line or comma-separated",
    "plugins.pip_hint":   "Installed automatically before the tool runs (same Python as the assistant).",
    "plugins.save":       "💾 Save Tool",
    "plugins.installed":  "Installed",
    "plugins.empty":      "No plugins installed.",
    "plugins.params":     "Parameters",
    "plugins.id_readonly":"ID (read only)",
    // Roleplay panel
    "rp.active_scenario": "Active Scenario",
    "rp.no_active":       "No roleplay active.",
    "rp.deactivate":      "🛑 Deactivate Roleplay",
    "rp.create":          "Create Scenario",
    "rp.name":            "Scenario Name",
    "rp.ai_persona":      "AI Persona (who the AI will be)",
    "rp.user_persona":    "User Persona (who you will be)",
    "rp.setting":         "Setting / Scenario",
    "rp.nsfw":            "🔞 NSFW Content",
    "rp.save":            "💾 Create Scenario",
    "rp.saved":           "Saved Scenarios",
    "rp.none":            "No scenarios saved.",
    // Vision panel
    "vision.screenshot":  "Last Screenshot",
    "vision.context":     "Visual Context",
    "vision.waiting":     "Waiting for capture…",
    // Modal
    "modal.edit_tool":    "Edit Tool",
    // Nav
    "nav.chat":           "Chat",
    "nav.back_to_chat":   "Back to chat",
    "nav.system":         "System",
    "nav.persona":        "Persona",
    "nav.memory":         "Memory",
    "nav.plugins":        "Plugins",
    "nav.plugins_mcp":    "Plugins MCP",
    "nav.roleplay":       "Roleplay",
    "nav.vision":         "Vision",
    "nav.section_config": "Configuration",
    "nav.section_data":   "Data",
    // Confirms
    "confirm.clear":      "Delete all messages in this conversation?",
    "confirm.mem_all":    "Delete ALL memories? This cannot be undone.",
    "rp.confirm_del":     "Delete this scenario?",
    "chat.you":           "You",
    "persona.no_skills":  "No skills added yet.",
    "ai_name_default":    "Assistant",
    // Status
    "status.uploading":   "📎 Uploading file…",
    "status.image":       "🖼️ Analyzing image…",
    "status.file":        "📄 Reading file…",
    "status.generating":  "⚙️ Generating response…",
    "status.listening":   "🎤 Listening…",
  },
  pt: {
    "chat.placeholder":   "Digite uma mensagem…",
    "chat.clear":         "🗑 Limpar",
    "chat.empty":         "Nenhuma mensagem ainda.\nComece a conversar!",
    "chat.loading":       "Carregando conversa…",
    "chat.new_started":   "Novo bate-papo iniciado!\nPode começar a conversar.",
    "chat.mode_on":       "💬 Bate-papo ✓",
    "chat.mode_off":      "💬 Bate-papo",
    "chat.mode_tooltip":  "Modo Bate-papo — skills rotativas para conversa descontraída",
    "chat.mode_toast":    "💬 Modo Bate-papo ativado!",
    "mem.none":           "Nenhuma memória ainda.\nConverse para o assistente aprender.",
    "mem.title":          "Memória Semântica (RAG)",
    "mem.desc":           "Fatos extraídos automaticamente das conversas e indexados por similaridade semântica.\nUsados para personalizar respostas futuras sem precisar repetir contexto.",
    "mem.filter":         "Filtrar memórias…",
    "mem.delete_all":     "🗑 Apagar Tudo",
    "sys.ai_engine":      "Motor de IA",
    "sys.provider":       "Provedor",
    "sys.local_model":    "Modelo Local",
    "sys.main_model":     "Modelo Padrão",
    "sys.vision_model":   "Especialista — Visão",
    "sys.code_model":     "Especialista — Código",
    "sys.roleplay_model": "Especialista — Roleplay / Afeto",
    "sys.api_keys":       "Chaves de API",
    "sys.hf_token":       "Token Hugging Face",
    "sys.hf_hint":        "Usado nos embeddings da memória semântica e downloads privados no Hub. Deixe vazio se só usa modelos públicos.",
    "sys.whisper_model":  "Tamanho do modelo Whisper",
    "ui.toast_saved":     "Configurações salvas.",
    "ui.toast_error":     "Não foi possível salvar. Veja o console.",
    "ui.save_working":    "Salvando…",
    "ui.save_done":       "Salvo!",
    "sys.audio":          "Áudio",
    "sys.listen_method":  "Método de Escuta",
    "sys.button_mode":    "Botão (X do mouse)",
    "sys.vad_mode":       "Contínuo (VAD)",
    "sys.stt_engine":     "Motor de Transcrição",
    "sys.tts_engine":     "Sintetizador de Voz",
    "sys.edge_voice":     "Voz Edge TTS",
    "sys.quick_modes":    "Modos Rápidos",
    "sys.focus_mode":     "Modo Foco",
    "sys.dnd_mode":       "Não Perturbe",
    "sys.watchdog":       "🐕 Watchdog Proativo",
    "sys.watchdog_sub":   "IA verifica periodicamente",
    "sys.watchdog_interval": "Intervalo do Watchdog (minutos)",
    "sys.vision_bg":      "👁️ Análise de Tela em Segundo Plano",
    "sys.vision_bg_sub":  "IA monitora o contexto da tela automaticamente (consome tokens)",
    "sys.lipsync":        "🎤 Lip Sync VTube Studio",
    "sys.lipsync_sub":    "Anima a boca do modelo quando a IA fala (requer VTube Studio)",
    "sys.mood":           "Humor / Vibe atual",
    "sys.save":           "💾 Salvar Configurações",
    "persona.identity":   "Identidade",
    "persona.ai_name":    "Nome da IA",
    "persona.system_prompt": "Prompt de Sistema",
    "persona.skills":     "Skills",
    "persona.skill_desc": "Descrição",
    "persona.add_skill":  "+ Adicionar Skill",
    "persona.save":       "💾 Salvar Persona",
    "plugins.new":        "Nova Habilidade",
    "plugins.name":       "Nome / ID",
    "plugins.desc":       "Descrição (para a IA entender quando usar)",
    "plugins.add_param":  "+ Parâmetro",
    "plugins.code":       "Código Python",
    "plugins.pip_req":    "Pacotes pip (opcional)",
    "plugins.pip_placeholder": "ex.: pywhatkit — um por linha ou separados por vírgula",
    "plugins.pip_hint":   "Instalados automaticamente antes de executar a ferramenta (mesmo Python do assistente).",
    "plugins.save":       "💾 Salvar Habilidade",
    "plugins.installed":  "Instalados",
    "plugins.empty":      "Nenhum plugin instalado.",
    "plugins.params":     "Parâmetros",
    "plugins.id_readonly":"ID (somente leitura)",
    "rp.active_scenario": "Cenário Ativo",
    "rp.no_active":       "Nenhum roleplay ativo.",
    "rp.deactivate":      "🛑 Desativar Roleplay",
    "rp.create":          "Criar Cenário",
    "rp.name":            "Nome do Cenário",
    "rp.ai_persona":      "Persona da IA (quem ela será)",
    "rp.user_persona":    "Persona do Usuário (quem você será)",
    "rp.setting":         "Ambientação / Cenário",
    "rp.nsfw":            "🔞 Conteúdo NSFW",
    "rp.save":            "💾 Criar Cenário",
    "rp.saved":           "Cenários Salvos",
    "rp.none":            "Nenhum cenário salvo.",
    "vision.screenshot":  "Último Screenshot",
    "vision.context":     "Contexto Visual",
    "vision.waiting":     "Aguardando captura…",
    "modal.edit_tool":    "Editar Habilidade",
    "nav.chat":           "Chat",
    "nav.back_to_chat":   "Voltar ao chat",
    "nav.system":         "Sistema",
    "nav.persona":        "Persona",
    "nav.memory":         "Memória",
    "nav.plugins":        "Plugins",
    "nav.plugins_mcp":    "Plugins MCP",
    "nav.roleplay":       "Roleplay",
    "nav.vision":         "Visão",
    "nav.section_config": "Configuração",
    "nav.section_data":   "Dados",
    "confirm.clear":      "Apagar todo o histórico desta conversa?",
    "confirm.mem_all":    "Apagar TODAS as memórias? Não pode ser desfeito.",
    "rp.confirm_del":     "Apagar este cenário?",
    "chat.you":           "Você",
    "persona.no_skills":  "Nenhuma skill adicionada.",
    "ai_name_default":    "Assistente",
    "status.uploading":   "📎 Enviando arquivo…",
    "status.image":       "🖼️ Analisando imagem…",
    "status.file":        "📄 Lendo arquivo…",
    "status.generating":  "⚙️ Gerando resposta…",
    "status.listening":   "🎤 Ouvindo áudio…",
  }
};

let _currentLang = "en";

function _(key) {
  return (_uiStrings[_currentLang] || _uiStrings["en"])[key] || (_uiStrings["en"][key] || key);
}

function showToast(msg, isError) {
  const el = document.getElementById('toast');
  if (!el) return;
  el.textContent = msg;
  el.className = 'show' + (isError ? ' error' : '');
  clearTimeout(el._hideT);
  el._hideT = setTimeout(() => { el.classList.remove('show'); }, 2800);
}

function atualizarVisibilidadeSTT() {
  const stt = document.getElementById('audio_motor_transcricao')?.value;
  const row = document.getElementById('row_whisper_model');
  if (row) row.style.display = stt === 'whisper' ? '' : 'none';
}

function applyLangToUI() {
  // Apply to all elements with data-i18n attribute (text content)
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    const val = _(key);
    if (val && val !== key) el.textContent = val;
  });

  // Apply to placeholder attributes
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    const key = el.getAttribute('data-i18n-placeholder');
    const val = _(key);
    if (val && val !== key) el.placeholder = val;
  });

  // Apply to title attributes
  document.querySelectorAll('[data-i18n-title]').forEach(el => {
    const key = el.getAttribute('data-i18n-title');
    const val = _(key);
    if (val && val !== key) el.title = val;
  });

  // Update chat mode button state
  _atualizarBotaoBatepapo();

  // Update html lang attribute
  document.documentElement.lang = _currentLang === 'pt' ? 'pt-BR' : 'en';
}

async function trocarIdioma(lang) {
  _currentLang = lang;
  applyLangToUI();
  // Save in config
  const cfg = await (await fetch("/api/config", {cache:"no-store"})).json();
  cfg.ui_language = lang;
  await fetch("/api/config/update", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(cfg)
  });
  // Signal backend to update terminal language
  await fetch("/api/set_language", {method:"POST",
    headers:{"Content-Type":"application/json"},
    body: JSON.stringify({lang})});
}

// ═══════════════════════════════════════════
// LAYOUT
// ═══════════════════════════════════════════
function showPanel(name, el) {
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.querySelectorAll('.mnav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('panel-' + name).classList.add('active');
  if (el) el.classList.add('active');
  else if (name === 'chat') {
    const chatNav = document.querySelector('.nav-item[data-panel="chat"]');
    if (chatNav) chatNav.classList.add('active');
  }
  // Sincroniza mobile nav
  document.querySelectorAll('.mnav-item').forEach(m => {
    if(m.getAttribute('onclick') && m.getAttribute('onclick').includes("'"+name+"'")) m.classList.add('active');
  });
  document.getElementById('topbar-section').textContent = ({
    chat:     _('nav.chat'),
    sistema:  _('nav.system'),
    persona:  _('nav.persona'),
    plugins:  _('nav.plugins'),
    roleplay: _('nav.roleplay'),
    visao:    _('nav.vision'),
    memorias: _('nav.memory'),
  })[name] || name;
  // Lazy loads
  if (name === 'plugins')  carregarPlugins();
  if (name === 'visao')    atualizarVisao();
  if (name === 'roleplay') carregarRoleplays();
  if (name === 'memorias') carregarMemorias();
}

function toggleSidebar() {
  _sidebarCollapsed = !_sidebarCollapsed;
  const sb = document.getElementById('sidebar');
  const tog = document.getElementById('sidebar-toggle');
  sb.classList.toggle('collapsed', _sidebarCollapsed);
  tog.textContent = _sidebarCollapsed ? '›' : '‹';
  tog.style.left = _sidebarCollapsed
    ? 'calc(var(--sidebar-sm) - 13px)'
    : 'calc(var(--sidebar-w) - 13px)';
}

function fecharModal() {
  document.getElementById('modal-editar').classList.remove('open');
}

function toggleEye(btn, inputId) {
  const inp = document.getElementById(inputId);
  inp.type = inp.type === 'password' ? 'text' : 'password';
  btn.textContent = inp.type === 'password' ? '👁' : '🙈';
}

// ═══════════════════════════════════════════
// MODO BATE-PAPO
// ═══════════════════════════════════════════
let _batePapoAtivo = false;

async function carregarEstadoBatepapo() {
  try {
    const { ativo } = await (await fetch('/api/batepapo/status')).json();
    _batePapoAtivo = ativo;
    _atualizarBotaoBatepapo();
  } catch(_) {}
}

function _atualizarBotaoBatepapo() {
  const btn = document.getElementById('btn-batepapo');
  if (!btn) return;
  if (_batePapoAtivo) {
    btn.style.background = 'rgba(124,106,247,0.2)';
    btn.style.color = 'var(--accent2)';
    btn.style.borderColor = 'rgba(124,106,247,0.5)';
    btn.textContent = _('chat.mode_on');
  } else {
    btn.style.background = 'transparent';
    btn.style.color = 'var(--muted)';
    btn.style.borderColor = 'var(--border2)';
    btn.textContent = _('chat.mode_off');
  }
  btn.title = _('chat.mode_tooltip');
}

async function toggleBatepapo() {
  try {
    const { ativo } = await (await fetch('/api/batepapo/toggle', { method: 'POST' })).json();
    _batePapoAtivo = ativo;
    _atualizarBotaoBatepapo();
    mostrarStatus(ativo ? _('chat.mode_toast') : '');
    if (ativo) setTimeout(() => mostrarStatus(''), 2500);
  } catch(_) {}
}

// ═══════════════════════════════════════════
// STATUS BAR
// ═══════════════════════════════════════════
let _statusPoller = null;

function mostrarStatus(msg) {
  const bar = document.getElementById('chat-status');
  const txt = document.getElementById('chat-status-text');
  if (!bar || !txt) return;
  if (msg) { txt.textContent = msg; bar.classList.add('visible'); }
  else      { bar.classList.remove('visible'); txt.textContent = ''; }
}

function iniciarPollingStatus() {
  if (_statusPoller) return;
  _statusPoller = setInterval(async () => {
    try {
      const { status } = await (await fetch('/api/status', { cache:'no-store' })).json();
      mostrarStatus(status || '');
      if (!status) { clearInterval(_statusPoller); _statusPoller = null; }
    } catch(_) {}
  }, 500);
}

// ═══════════════════════════════════════════
// SSE
// ═══════════════════════════════════════════
function iniciarSSE() {
  if (_sseAtivo) return;
  _sseAtivo = true;
  const src = new EventSource('/api/eventos');
  src.onmessage = e => {
    try {
      const hist = JSON.parse(e.data);
      renderizarHistorico(hist);
      // Se chegou mensagem nova do assistente, limpa o status
      const ultimas = hist.filter(m => m.role !== 'system');
      if (ultimas.length && ultimas[ultimas.length-1].role === 'assistant') {
        mostrarStatus('');
        if (_statusPoller) { clearInterval(_statusPoller); _statusPoller = null; }
      }
    } catch(_){}
  };
  src.onerror = () => {
    _sseAtivo = false; src.close();
    setInterval(async () => {
      try { renderizarHistorico(await (await fetch('/api/historico',{cache:'no-store'})).json()); } catch(_){}
    }, 2000);
  };
}

function _renderizarConteudo(raw) {
  let txt = (raw || '')
    .replace(/\[SKILL.*?\]/gi, '')
    .replace(/<MEMORIA_VISUAL>[\s\S]*?<\/MEMORIA_VISUAL>/gi,
             '<em style="color:var(--muted);font-size:0.85em">👁 [Contexto Visual]</em>');

  // Imagens: [IMG:/api/uploads/xyz.jpg]
  txt = txt.replace(/\[IMG:([^\]]+)\]/g, (_, url) =>
    `<img src="${url}" class="msg-img" onclick="abrirLightbox('${url}')" alt="imagem">`
  );

  // Arquivos: [FILE:/api/uploads/xyz.pdf:nome_original.pdf]
  txt = txt.replace(/\[FILE:([^:]+):([^\]]+)\]/g, (_, url, nome) => {
    const ext = nome.split('.').pop().toLowerCase();
    const icones = {pdf:'📄',txt:'📝',py:'🐍',js:'📜',ts:'📜',json:'🗂️',csv:'📊',md:'📝',docx:'📄',xlsx:'📊'};
    const icone = icones[ext] || '📁';
    return `<a href="${url}" target="_blank" class="msg-file">
      <span class="msg-file-icon">${icone}</span>
      <span class="msg-file-info"><span class="msg-file-name">${nome}</span><span class="msg-file-size">clique para abrir</span></span>
      <span style="color:var(--muted);font-size:12px">↗</span>
    </a>`;
  });

  return txt.replace(/\n/g, '<br>');
}

function abrirLightbox(url) {
  document.getElementById('lightbox-img').src = url;
  document.getElementById('lightbox').classList.add('open');
}

let _ultimoHistHash = "";

function renderizarHistorico(hist) {
  const msgs = hist.filter(m => m.role !== 'system');
  // Hash do conteúdo evita re-render se o SSE reenviar o mesmo histórico
  const h = msgs.map(m => m.role + m.content).join('|').slice(0, 500);
  if (h === _ultimoHistHash) return;
  _ultimoHistHash = h;

  const box = document.getElementById('chat-messages');
  const atBottom = box.scrollHeight - box.scrollTop <= box.clientHeight + 60;
  box.innerHTML = '';
  if (!msgs.length) {
    box.innerHTML = `<div class="empty-state"><div class="es-icon">💬</div><p>${_('chat.empty').replace('\n','<br>')}</p></div>`;
    return;
  }
  msgs.forEach(m => {
    const isUser = m.role === 'user';
    const row = document.createElement('div');
    row.className = 'msg-row ' + (isUser ? 'user' : 'assistant');
    row.innerHTML = `<div class="msg-bubble"><div class="msg-sender">${isUser ? (_('chat.you') || 'You') : nomeIA}</div>${_renderizarConteudo(m.content)}</div>`;
    box.appendChild(row);
  });
  if (atBottom) box.scrollTop = box.scrollHeight;
}

// ═══════════════════════════════════════════
// CHAT
// ═══════════════════════════════════════════
function _iconeArquivo(nome) {
  const ext = (nome.split('.').pop() || '').toLowerCase();
  const mapa = {pdf:'📄',txt:'📝',py:'🐍',js:'📜',ts:'📜',json:'🗂️',csv:'📊',md:'📝',docx:'📄',xlsx:'📊'};
  return mapa[ext] || '📁';
}

function arquivosSelecionados(input) {
  Array.from(input.files).forEach(f => {
    const url_local = URL.createObjectURL(f);
    const tipo = f.type.startsWith('image/') ? 'imagem' : 'arquivo';
    _arquivosPendentes.push({ file: f, url_local, url_servidor: null, tipo, nome: f.name });
  });
  input.value = ''; // permite selecionar o mesmo arquivo novamente
  renderizarPreview();
}

function renderizarPreview() {
  const strip = document.getElementById('file-preview-strip');
  if (!_arquivosPendentes.length) { strip.classList.remove('visible'); strip.innerHTML = ''; return; }
  strip.classList.add('visible');
  strip.innerHTML = _arquivosPendentes.map((a, i) => {
    if (a.tipo === 'imagem') {
      return `<div class="file-thumb">
        <img src="${a.url_local}" alt="${a.nome}">
        <button class="file-thumb-remove" onclick="removerArquivo(${i})">✕</button>
      </div>`;
    }
    return `<div class="file-thumb">
      <div class="file-thumb-card">
        <span class="file-thumb-icon">${_iconeArquivo(a.nome)}</span>
        <span class="file-thumb-name" title="${a.nome}">${a.nome}</span>
      </div>
      <button class="file-thumb-remove" onclick="removerArquivo(${i})">✕</button>
    </div>`;
  }).join('');
}

function removerArquivo(i) {
  URL.revokeObjectURL(_arquivosPendentes[i].url_local);
  _arquivosPendentes.splice(i, 1);
  renderizarPreview();
}

async function _uploadArquivo(arquivo) {
  const formData = new FormData();
  formData.append('file', arquivo.file);
  try {
    const res = await fetch('/api/upload', { method: 'POST', body: formData });
    const data = await res.json();
    return data.url; // ex: /api/uploads/uuid_nome.jpg
  } catch(_) { return null; }
}

async function enviarMensagem() {
  const inp = document.getElementById('chat-input');
  const txt = inp.value.trim();
  const temArquivos = _arquivosPendentes.length > 0;
  if (!txt && !temArquivos) return;
  inp.value = '';

  if (temArquivos) {
    const btnSend = document.querySelector('.btn-send');
    if (btnSend) { btnSend.textContent = '⏳'; btnSend.disabled = true; }
    mostrarStatus('📎 Enviando arquivo…');
    const urlsArquivos = [];
    for (const arq of _arquivosPendentes) {
      const url = await _uploadArquivo(arq);
      if (url) urlsArquivos.push({ url, tipo: arq.tipo, nome: arq.nome });
    }
    _arquivosPendentes.forEach(a => URL.revokeObjectURL(a.url_local));
    _arquivosPendentes = [];
    renderizarPreview();
    if (btnSend) { btnSend.textContent = '➤'; btnSend.disabled = false; }

    const tipoStatus = urlsArquivos.some(a => a.tipo === 'imagem')
      ? '🖼️ Analisando imagem…'
      : '📄 Lendo arquivo…';
    mostrarStatus(tipoStatus);
    iniciarPollingStatus();

    await fetch('/api/enviar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ texto: txt, arquivos: urlsArquivos })
    });
  } else {
    mostrarStatus('⚙️ Gerando resposta…');
    iniciarPollingStatus();
    await fetch('/api/enviar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ texto: txt, arquivos: [] })
    });
  }
}

async function limparChat() {
  if (!confirm(_('confirm.clear'))) return;
  await fetch('/api/limpar_historico', { method:'POST' });
}

function toggleGravacao() {
  const btn = document.getElementById('btn-mic');
  const inp = document.getElementById('chat-input');
  if (!('webkitSpeechRecognition' in window)) return alert('Reconhecimento de voz não suportado neste navegador.');
  if (!recognition) {
    recognition = new webkitSpeechRecognition();
    recognition.lang = 'pt-BR';
    recognition.onstart = () => {
      isRecording=true; btn.classList.add('recording'); btn.textContent='⏹';
      mostrarStatus('🎤 Ouvindo áudio…');
    };
    recognition.onresult = e => {
      inp.value = e.results[0][0].transcript;
      mostrarStatus('⚙️ Gerando resposta…');
      iniciarPollingStatus();
      enviarMensagem();
    };
    recognition.onend = () => {
      isRecording=false; btn.classList.remove('recording'); btn.textContent='🎤';
    };
  }
  isRecording ? recognition.stop() : recognition.start();
}

// Tecla Enter no input
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('chat-input').addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); enviarMensagem(); }
  });
});

// ═══════════════════════════════════════════
// CARREGAR DADOS DE CONFIG
// ═══════════════════════════════════════════

const OPENAI_MODELS = [
  {id: "gpt-4o",        name: "GPT-4o"},
  {id: "gpt-4o-mini",   name: "GPT-4o Mini"},
  {id: "gpt-4-turbo",   name: "GPT-4 Turbo"},
  {id: "gpt-3.5-turbo", name: "GPT-3.5 Turbo"},
  {id: "o1-mini",       name: "o1 Mini"},
];

function _fillSpecialists(models) {
  ['modelo_principal','modelo_visao','modelo_codigo','modelo_roleplay'].forEach(id => {
    const sel   = document.getElementById(id);
    if (!sel) return;
    const saved = sel.getAttribute('data-salvo') || sel.value;
    sel.innerHTML = models.map(m => `<option value="${m.id}">${m.name}</option>`).join('');
    if (saved) sel.value = saved;
  });
}

async function verificarMotor() {
  const m     = document.getElementById('modo_ia').value;
  const bloco = document.getElementById('bloco_especialistas');
  document.getElementById('bloco_modelo_local').style.display = m === 'local' ? 'block' : 'none';

  if (m === 'openrouter') {
    bloco.style.display = 'block';
    await carregarModelosOpenRouter();
  } else if (m === 'groq') {
    bloco.style.display = 'block';
    await carregarModelosGroq();
  } else if (m === 'openai') {
    bloco.style.display = 'block';
    _fillSpecialists(OPENAI_MODELS);
  } else {
    bloco.style.display = 'none';
  }
}

async function carregarModelosOpenRouter() {
  try {
    const modelos = await (await fetch('/api/openrouter_models')).json();
    if (modelos.length) _fillSpecialists(modelos);
  } catch(_){}
}

async function carregarModelosGroq() {
  try {
    const modelos = await (await fetch('/api/groq_models')).json();
    if (modelos.length) {
      _fillSpecialists(modelos);
    } else {
      // Fallback to static list if API key missing or request failed
      _fillSpecialists([
        {id: "llama-3.3-70b-versatile",       name: "Llama 3.3 70B Versatile"},
        {id: "llama-3.1-8b-instant",          name: "Llama 3.1 8B Instant"},
        {id: "llama3-70b-8192",               name: "Llama 3 70B"},
        {id: "mixtral-8x7b-32768",            name: "Mixtral 8x7B"},
        {id: "gemma2-9b-it",                  name: "Gemma 2 9B"},
        {id: "llama-3.2-11b-vision-preview",  name: "Llama 3.2 11B Vision"},
        {id: "deepseek-r1-distill-llama-70b", name: "DeepSeek R1 70B"},
      ]);
    }
  } catch(_){}
}

async function carregarDados() {
  try {
    const cfg = await (await fetch('/api/config',{cache:'no-store'})).json();
    if (cfg) {
      // Language — apply first so UI renders in correct language
      const lang = cfg.ui_language || 'en';
      _currentLang = lang;
      const langSel = document.getElementById('ui_language');
      if (langSel) langSel.value = lang;
      applyLangToUI();

      document.getElementById('modo_ia').value = cfg.modo_ia || 'groq';
      document.getElementById('modelo_ia_local').value = cfg.modelo_ia_local || '';
      ['modelo_principal','modelo_visao','modelo_codigo','modelo_roleplay'].forEach(id => {
        document.getElementById(id).setAttribute('data-salvo', cfg[id] || '');
      });
      if (cfg.modo_ia === 'openrouter' || cfg.modo_ia === 'groq' || cfg.modo_ia === 'openai') await verificarMotor();
      document.getElementById('api_openrouter').value = cfg.api_keys?.openrouter || '';
      document.getElementById('api_groq').value       = cfg.api_keys?.groq || '';
      document.getElementById('api_openai').value     = cfg.api_keys?.openai || '';
      document.getElementById('api_elevenlabs').value = cfg.api_keys?.elevenlabs || '';
      document.getElementById('api_huggingface').value = cfg.api_keys?.huggingface || '';
      document.getElementById('audio_metodo_escuta').value    = cfg.audio?.metodo_escuta || 'atalho';
      document.getElementById('audio_motor_transcricao').value = cfg.audio?.motor_transcricao || 'whisper';
      document.getElementById('audio_whisper_modelo').value   = cfg.audio?.whisper_modelo || 'small';
      document.getElementById('audio_motor_voz').value        = cfg.audio?.motor_voz || 'edge';
      document.getElementById('audio_voz_edge').value         = cfg.audio?.voz_edge || '';
      atualizarVisibilidadeSTT();
      document.getElementById('humor_ia').value          = cfg.sistema?.humor || '';
      document.getElementById('watchdog_ativo').checked  = cfg.sistema?.watchdog_ativo || false;
      document.getElementById('watchdog_intervalo').value = cfg.sistema?.watchdog_intervalo || 10;
      document.getElementById('vision_bg_ativo').checked  = cfg.sistema?.vision_bg_ativo || false;
      document.getElementById('lipsync_ativo').checked    = cfg.sistema?.lipsync_ativo || false;
      _modoFoco = cfg.sistema?.modo_foco || false;
      _modoDND  = cfg.sistema?.modo_nao_perturbe || false;
      atualizarModeUI();
    }
  } catch(_){}

  try {
    const persona = await (await fetch('/api/persona',{cache:'no-store'})).json();
    if (persona) {
      nomeIA = persona.nome || _('ai_name_default');
      document.getElementById('nome_ia').value = nomeIA;
      document.getElementById('prompt_sistema').value = Array.isArray(persona.prompt_sistema) ? persona.prompt_sistema.join('\n') : persona.prompt_sistema || '';
      document.getElementById('sidebar-ai-name').textContent = nomeIA;
      document.getElementById('topbar-ai-name').textContent  = nomeIA;
      document.getElementById('chat-ai-name').textContent    = nomeIA;
      document.title = nomeIA + ' — AI Panel';
      skillsAtuais = persona.skills || [];
      renderizarSkills();
    }
  } catch(_){}

  verificarMotor();
}

// ═══════════════════════════════════════════
// SALVAR
// ═══════════════════════════════════════════
async function salvarTudo() {
  const btn = document.querySelector('.btn-save-all');
  if (btn) { btn.textContent = _('ui.save_working'); btn.disabled = true; }
  try {
    const novaConfig = {
      ui_language: document.getElementById('ui_language').value,
      modo_ia: document.getElementById('modo_ia').value,
      modelo_ia_local: document.getElementById('modelo_ia_local').value,
      modelo_principal: document.getElementById('modelo_principal').value,
      modelo_visao: document.getElementById('modelo_visao').value,
      modelo_codigo: document.getElementById('modelo_codigo').value,
      modelo_roleplay: document.getElementById('modelo_roleplay').value,
      api_keys: {
        openrouter: document.getElementById('api_openrouter').value,
        groq:       document.getElementById('api_groq').value,
        openai:     document.getElementById('api_openai').value,
        elevenlabs: document.getElementById('api_elevenlabs').value,
        huggingface: document.getElementById('api_huggingface').value,
      },
      audio: {
        metodo_escuta:    document.getElementById('audio_metodo_escuta').value,
        motor_transcricao: document.getElementById('audio_motor_transcricao').value,
        whisper_modelo:   document.getElementById('audio_whisper_modelo').value,
        motor_voz:        document.getElementById('audio_motor_voz').value,
        voz_edge:         document.getElementById('audio_voz_edge').value,
      },
      sistema: {
        humor:            document.getElementById('humor_ia').value,
        watchdog_ativo:   document.getElementById('watchdog_ativo').checked,
        watchdog_intervalo: parseInt(document.getElementById('watchdog_intervalo').value) || 10,
        vision_bg_ativo:  document.getElementById('vision_bg_ativo').checked,
        lipsync_ativo:    document.getElementById('lipsync_ativo').checked,
        watchdog_intervalo: parseInt(document.getElementById('watchdog_intervalo').value) || 10,
        modo_foco:        _modoFoco,
        modo_nao_perturbe: _modoDND,
      }
    };
    await fetch('/api/config/update', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(novaConfig) });

    const novaPersona = {
      nome: document.getElementById('nome_ia').value,
      prompt_sistema: document.getElementById('prompt_sistema').value.split('\n'),
      skills: skillsAtuais
    };
    await fetch('/api/persona/update', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(novaPersona) });

    if (btn) { btn.textContent = _('ui.save_done'); setTimeout(()=>{ btn.textContent=_('sys.save'); btn.disabled=false; }, 2000); }
    showToast(_('ui.toast_saved'));
    await carregarDados();
  } catch(_) {
    if (btn) { btn.textContent = '❌ Erro'; btn.disabled=false; }
    showToast(_('ui.toast_error'), true);
  }
}

// ═══════════════════════════════════════════
// MODOS (Foco / Não Perturbe)
// ═══════════════════════════════════════════
async function toggleModo(tipo) {
  if (tipo === 'foco')         _modoFoco = !_modoFoco;
  else if (tipo === 'nao_perturbe') _modoDND = !_modoDND;
  atualizarModeUI();
  const endpoint = tipo === 'foco' ? '/api/modo/foco' : '/api/modo/nao_perturbe';
  const ativo    = tipo === 'foco' ? _modoFoco : _modoDND;
  await fetch(endpoint, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({ativo}) });
}

function atualizarModeUI() {
  // Sidebar pills
  const pF = document.getElementById('pill-foco');
  const pD = document.getElementById('pill-dnd');
  pF.className = 'status-pill ' + (_modoFoco ? 'on-focus' : 'off');
  pD.className = 'status-pill ' + (_modoDND  ? 'on-dnd'   : 'off');
  // Mode buttons (sistema panel)
  const bF = document.getElementById('btn-foco');
  const bD = document.getElementById('btn-dnd');
  if (bF) bF.className = 'mode-btn ' + (_modoFoco ? 'active-focus' : '');
  if (bD) bD.className = 'mode-btn ' + (_modoDND  ? 'active-dnd'   : '');
  // Topbar badges
  const tF = document.getElementById('badge-foco');
  const tD = document.getElementById('badge-dnd');
  if (tF) tF.className = 'topbar-mode-badge ' + (_modoFoco ? 'focus' : '');
  if (tD) tD.className = 'topbar-mode-badge ' + (_modoDND  ? 'dnd'   : '');
}

// ═══════════════════════════════════════════
// SKILLS
// ═══════════════════════════════════════════
function renderizarSkills() {
  const c = document.getElementById('skills-container');
  if (!skillsAtuais.length) { c.innerHTML = `<div class="empty-state" style="padding:20px 0"><p>${_('persona.no_skills')}</p></div>`; return; }
  c.innerHTML = skillsAtuais.map((s,i) => `
    <div class="skill-row">
      <span class="skill-id">⚡ ${s.id}</span>
      <span class="skill-text">${s.texto}</span>
      <button class="btn-sm btn-sm-del" onclick="apagarSkill(${i})">✕</button>
    </div>`).join('');
}
function apagarSkill(i) { skillsAtuais.splice(i,1); renderizarSkills(); }
function adicionarSkill() {
  const id = document.getElementById('new_skill_id');
  const tx = document.getElementById('new_skill_text');
  if (!id.value || !tx.value) return;
  skillsAtuais.push({ id: id.value.replace(/\s+/g,'_').toLowerCase(), texto: tx.value });
  id.value = ''; tx.value = '';
  renderizarSkills();
}

// ═══════════════════════════════════════════
// PLUGINS MCP
// ═══════════════════════════════════════════
async function carregarPlugins() {
  const lista = await (await fetch('/api/mcp_tools')).json();
  const c = document.getElementById('mcp-list');
  if (!lista.length) { c.innerHTML = `<div class="empty-state"><div class="es-icon">🔌</div><p>${_('plugins.empty')}</p></div>`; return; }
  c.innerHTML = lista.map(p => `
    <div class="list-item">
      <div class="list-item-body">
        <div class="list-item-title">🔧 ${p.nome}</div>
        <div class="list-item-sub">${p.descricao}</div>
      </div>
      <div class="list-item-actions">
        <button class="btn-sm btn-sm-edit" onclick="abrirEditor('${p.nome}')">✏️</button>
        <button class="btn-sm btn-sm-del" onclick="deletarPlugin('${p.nome}')">🗑</button>
      </div>
    </div>`).join('');
}

async function abrirEditor(nome) {
  const data = await (await fetch(`/api/mcp_tools/get?nome=${nome}`)).json();
  if (!data.nome) return;
  document.getElementById('edit_nome').value = data.nome;
  document.getElementById('edit_desc').value = data.descricao;
  document.getElementById('edit_pip').value = data.pip_requirements || '';
  document.getElementById('edit_codigo').value = data.codigo;
  const c = document.getElementById('edit-params-container');
  c.innerHTML = '';
  try {
    const schema = JSON.parse(data.schema);
    const req = schema.required || [];
    for (const [k,v] of Object.entries(schema.properties || {}))
      adicionarParametroEdicao(k, v.type||'string', v.description||'', req.includes(k));
  } catch(_){}
  document.getElementById('modal-editar').classList.add('open');
}

async function salvarEdicao() {
  const schema = { type:'object', properties:{}, required:[] };
  document.querySelectorAll('#edit-params-container .param-row').forEach(row => {
    const n = row.querySelector('.param-nome').value.trim();
    if (n) {
      schema.properties[n] = { type: row.querySelector('.param-tipo').value, description: row.querySelector('.param-desc').value };
      if (row.querySelector('.param-req').checked) schema.required.push(n);
    }
  });
  if (!schema.required.length) delete schema.required;
  await fetch('/api/mcp_tools/save', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({
    nome: document.getElementById('edit_nome').value,
    descricao: document.getElementById('edit_desc').value,
    codigo_python: document.getElementById('edit_codigo').value,
    pip_requirements: document.getElementById('edit_pip').value,
    schema_json: JSON.stringify(schema)
  })});
  fecharModal();
  carregarPlugins();
}

function _paramRow(nome='', tipo='string', desc='', req=true, containerId='mcp-params-container') {
  const id = 'pr-' + Date.now() + Math.random().toString(36).slice(2);
  document.getElementById(containerId).insertAdjacentHTML('beforeend', `
    <div class="param-row" id="${id}">
      <input class="form-input param-nome" placeholder="Nome" value="${nome}">
      <select class="form-select param-tipo">
        <option value="string"  ${tipo==='string'?'selected':''}>Texto</option>
        <option value="number"  ${tipo==='number'?'selected':''}>Número</option>
        <option value="boolean" ${tipo==='boolean'?'selected':''}>Sim/Não</option>
      </select>
      <input class="form-input param-desc" placeholder="Descrição" value="${desc}" style="flex:1.5">
      <label style="font-size:11px;color:var(--muted);white-space:nowrap">
        <input type="checkbox" class="param-req" ${req?'checked':''}> Req
      </label>
      <button class="btn-rm" onclick="document.getElementById('${id}').remove()">✕</button>
    </div>`);
}
function adicionarParametroVisual() { _paramRow('','string','',true,'mcp-params-container'); }
function adicionarParametroEdicao(n,t,d,r) { _paramRow(n,t,d,r,'edit-params-container'); }

async function salvarPluginVisual() {
  const nome = document.getElementById('mcp_nome').value.trim();
  if (!nome) return alert('Nome obrigatório');
  const schema = { type:'object', properties:{}, required:[] };
  document.querySelectorAll('#mcp-params-container .param-row').forEach(row => {
    const n = row.querySelector('.param-nome').value.trim();
    if (n) {
      schema.properties[n] = { type: row.querySelector('.param-tipo').value, description: row.querySelector('.param-desc').value };
      if (row.querySelector('.param-req').checked) schema.required.push(n);
    }
  });
  if (!schema.required.length) delete schema.required;
  await fetch('/api/mcp_tools/save', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({
    nome, descricao: document.getElementById('mcp_desc').value,
    schema_json: JSON.stringify(schema),
    codigo_python: document.getElementById('mcp_codigo').value,
    pip_requirements: document.getElementById('mcp_pip').value
  })});
  document.getElementById('mcp_nome').value = '';
  document.getElementById('mcp_desc').value = '';
  document.getElementById('mcp_pip').value = '';
  document.getElementById('mcp-params-container').innerHTML = '';
  document.getElementById('mcp_codigo').value = 'resposta_ia = "Ação executada com sucesso!"';
  carregarPlugins();
}

async function deletarPlugin(nome) {
  if (!confirm(`Apagar o plugin "${nome}"?`)) return;
  await fetch('/api/mcp_tools/delete?nome=' + nome, { method:'POST' });
  carregarPlugins();
}

// ═══════════════════════════════════════════
// ROLEPLAY
// ═══════════════════════════════════════════
async function carregarRoleplays() {
  const lista = await (await fetch('/api/roleplay')).json();
  const displayEl = document.getElementById('rp-active-display');
  const btnDes    = document.getElementById('btn-desativar-rp');
  const listEl    = document.getElementById('rp-list');
  let ativo = null;

  lista.forEach(rp => { if (rp.ativo) ativo = rp; });

  if (ativo) {
    displayEl.innerHTML = `<div class="rp-name">🎭 ${ativo.nome} ${ativo.nsfw?'<span class="badge badge-red">NSFW</span>':''}</div>
      <div class="rp-detail"><strong>IA:</strong> ${(ativo.persona_ia||'').slice(0,100)}…</div>
      <div class="rp-detail"><strong>Você:</strong> ${(ativo.persona_usuario||'').slice(0,80)}…</div>`;
    btnDes.style.display = 'flex';
  } else {
    displayEl.innerHTML = `<div style="color:var(--muted);font-size:13px">${_('rp.no_active')}</div>`;
    btnDes.style.display = 'none';
  }

  if (!lista.length) { listEl.innerHTML = `<div class="empty-state"><div class="es-icon">🎭</div><p>${_('rp.none')}</p></div>`; return; }
  listEl.innerHTML = lista.map(rp => `
    <div class="list-item">
      <div class="list-item-body">
        <div class="list-item-title">${rp.ativo?'✅':'🎭'} ${rp.nome} ${rp.nsfw?'<span class="badge badge-red">NSFW</span>':''}</div>
        <div class="list-item-sub">${(rp.persona_ia||'').slice(0,80)}…</div>
      </div>
      <div class="list-item-actions">
        ${!rp.ativo ? `<button class="btn-sm btn-sm-act" onclick="ativarRoleplay(${rp.id})">▶</button>` : ''}
        <button class="btn-sm btn-sm-del" onclick="deletarRoleplay(${rp.id})">🗑</button>
      </div>
    </div>`).join('');
}

async function salvarRoleplay() {
  const nome = document.getElementById('rp_nome').value.trim();
  if (!nome) return alert('Nome obrigatório!');
  await fetch('/api/roleplay/save', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({
    nome, persona_ia: document.getElementById('rp_persona_ia').value,
    persona_usuario: document.getElementById('rp_persona_usuario').value,
    cenario: document.getElementById('rp_cenario').value,
    nsfw: document.getElementById('rp_nsfw').checked ? 1 : 0
  })});
  ['rp_nome','rp_persona_ia','rp_persona_usuario','rp_cenario'].forEach(id => document.getElementById(id).value='');
  document.getElementById('rp_nsfw').checked = false;
  carregarRoleplays();
}
async function ativarRoleplay(id) { await fetch('/api/roleplay/activate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})}); carregarRoleplays(); }
async function desativarRoleplay() { await fetch('/api/roleplay/deactivate',{method:'POST'}); carregarRoleplays(); }
async function deletarRoleplay(id) { if(confirm(_('rp.confirm_del') || 'Delete scenario?')) { await fetch('/api/roleplay/delete?id='+id,{method:'POST'}); carregarRoleplays(); } }

// ═══════════════════════════════════════════
// VISÃO
// ═══════════════════════════════════════════
async function atualizarVisao() {
  const img = document.getElementById('img-last-vision');
  if (img) img.src = '/api/last_vision?t=' + Date.now();
  try {
    const txt = await (await fetch('/api/vision_description',{cache:'no-store'})).text();
    document.getElementById('box-visao-contexto').value = txt.trim() || 'Aguardando captura…';
  } catch(_){}
}

// ═══════════════════════════════════════════
// MEMÓRIAS
// ═══════════════════════════════════════════
async function carregarMemorias() {
  _todasMemorias = await (await fetch('/api/memories')).json();
  document.getElementById('mem-count').textContent = _todasMemorias.length;
  renderizarMemorias(_todasMemorias);
}
function renderizarMemorias(lista) {
  const c = document.getElementById('mem-list');
  if (!lista.length) { c.innerHTML = `<div class="empty-state"><div class="es-icon">🧠</div><p>${_('mem.none').replace('\n','<br>')}</p></div>`; return; }
  c.innerHTML = lista.map(m => `
    <div class="list-item">
      <div class="list-item-body">
        <div class="list-item-title" style="white-space:normal;font-weight:500">${m.content}</div>
        <div class="list-item-sub">📅 ${m.created_at} &nbsp;·&nbsp; 🔍 ${m.access_count}× acessada</div>
      </div>
      <button class="btn-sm btn-sm-del" onclick="apagarMemoria(${m.id})">✕</button>
    </div>`).join('');
}
function filtrarMemorias() {
  const q = document.getElementById('mem-search').value.toLowerCase();
  renderizarMemorias(q ? _todasMemorias.filter(m=>m.content.toLowerCase().includes(q)) : _todasMemorias);
}
async function apagarMemoria(id) { await fetch('/api/memories/'+id,{method:'DELETE'}); carregarMemorias(); }
async function apagarTodasMemorias() {
  if (!confirm(_('confirm.mem_all'))) return;
  await fetch('/api/memories',{method:'DELETE'}); carregarMemorias();
}

// ═══════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════
window.addEventListener('DOMContentLoaded', () => {
  carregarDados();
  iniciarSSE();
  carregarEstadoBatepapo();
});
</script>
</body>
</html>"""
    return html


# ==========================================
# 🔌 ROTAS DA API
# ==========================================
@app.get("/api/openrouter_models")
async def get_openrouter_models():
    cfg = obter_setting("config")
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
    cfg = obter_setting("config")
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
            # Sort by id and exclude deprecated/whisper/tts models
            chat_models = [
                {"id": m["id"], "name": m.get("id", m["id"])}
                for m in sorted(models, key=lambda x: x["id"])
                if not any(x in m["id"] for x in ["whisper", "tts", "guard"])
            ]
            return chat_models
    except Exception:
        pass
    return []

@app.get("/api/historico")
async def get_historico():
    res = executar_sql("SELECT role, content FROM chat_history ORDER BY rowid ASC", fetch=True)
    return [{"role": r[0], "content": r[1]} for r in res] if res else []

@app.get("/api/config")
async def get_config(): return obter_setting("config")

@app.get("/api/persona")
async def get_persona(): return obter_setting("persona")

@app.post("/api/config/update")
async def update_config(data: dict): salvar_setting("config", data); return {"status": "ok"}

@app.post("/api/persona/update")
async def update_persona(data: dict): salvar_setting("persona", data); return {"status": "ok"}

@app.post("/api/set_language")
async def set_language_endpoint(data: dict):
    """Update UI language in config and apply to terminal (i18n module)."""
    lang = data.get("lang", "en")
    cfg = obter_setting("config")
    cfg["ui_language"] = lang
    salvar_setting("config", cfg)
    # Apply to terminal prints immediately
    try:
        from i18n import set_language
        set_language(lang)
    except Exception:
        pass
    return {"status": "ok", "lang": lang}

@app.post("/api/enviar")
async def enviar_mensagem(msg: Mensagem):
    partes = []
    json_arquivos = []

    for arq in msg.arquivos:
        if arq.tipo == "imagem":
            partes.append(f"[IMG:{arq.url}]")
        else:
            partes.append(f"[FILE:{arq.url}:{arq.nome}]")
        json_arquivos.append({"url": arq.url, "tipo": arq.tipo, "nome": arq.nome})

    if msg.texto:
        partes.append(msg.texto)

    conteudo_chat = "\n".join(partes)

    # Escreve APENAS o JSON — o main.py é responsável por salvar no banco
    payload = {
        "texto": msg.texto,
        "arquivos": json_arquivos,
        "conteudo_completo": conteudo_chat
    }
    with open("input_web.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)

    return {"status": "ok"}


@app.post("/api/upload")
async def upload_arquivo(file: UploadFile = File(...)):
    """Recebe um arquivo, salva em /uploads/ com nome único e retorna a URL."""
    ext = os.path.splitext(file.filename or "")[1].lower() or ".bin"
    nome_unico = f"{uuid.uuid4().hex}{ext}"
    destino = os.path.join(UPLOADS_DIR, nome_unico)
    conteudo = await file.read()
    with open(destino, "wb") as f:
        f.write(conteudo)
    return {"url": f"/api/uploads/{nome_unico}", "nome_original": file.filename, "tamanho": len(conteudo)}


@app.get("/api/uploads/{filename}")
async def serve_upload(filename: str):
    path = os.path.join(UPLOADS_DIR, filename)
    if not os.path.exists(path):
        return Response(status_code=404)
    return FileResponse(path, headers={"Cache-Control": "public, max-age=86400"})


@app.get("/api/batepapo/status")
async def get_batepapo_status():
    res = executar_sql(
        "SELECT text_value FROM system_state WHERE key = 'chat_mode'",
        fetch=True
    )
    return {"ativo": bool(res and res[0][0] == "1")}

@app.post("/api/batepapo/toggle")
async def toggle_batepapo():
    res = executar_sql("SELECT text_value FROM system_state WHERE key = 'chat_mode'", fetch=True)
    atual = bool(res and res[0][0] == "1")
    novo  = not atual
    executar_sql(
        "INSERT OR REPLACE INTO system_state (key, text_value) VALUES (?, ?)",
        ("chat_mode", "1" if novo else "0")
    )
    with open("input_web.json", "w", encoding="utf-8") as f:
        json.dump({"comando": "toggle_batepapo", "ativo": novo}, f)
    return {"ativo": novo}


@app.get("/api/status")
async def get_status():
    res = executar_sql("SELECT text_value FROM system_state WHERE key = 'status_msg'", fetch=True)
    return {"status": res[0][0] if res and res[0][0] else ""}


# ── MCP Tools ──
@app.get("/api/mcp_tools")
async def get_mcp_tools():
    res = executar_sql(
        "SELECT name, description, schema_json, python_code, pip_requirements FROM mcp_tools",
        fetch=True,
    )
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
    return out

@app.get("/api/mcp_tools/get")
async def get_single_mcp_tool(nome: str):
    res = executar_sql(
        "SELECT name, description, schema_json, python_code, pip_requirements FROM mcp_tools WHERE name = ?",
        (nome,),
        fetch=True,
    )
    if res:
        pip = res[0][4] if len(res[0]) > 4 else ""
        return {
            "nome": res[0][0],
            "descricao": res[0][1],
            "schema": res[0][2],
            "codigo": res[0][3],
            "pip_requirements": pip or "",
        }
    return {"error": "Not found"}

@app.post("/api/mcp_tools/save")
async def save_mcp_tool(data: dict):
    nome    = data.get("nome")
    codigo  = data.get("codigo_python", "")
    pip_req = (data.get("pip_requirements") or "").strip()

    # Instala pacotes Python necessários para a ferramenta MCP customizada em background,
    # sem travar a WebUI. Usa uma thread para não impactar a responsividade HTTP.
    import threading
    import subprocess
    import sys
    import re

    def instalar_dependencias():
        try:
            pacotes_para_instalar = set()

            # 1. Pega os pacotes declarados manualmente no painel (pip_requirements)
            if pip_req:
                for p in re.split(r"[,;\n]+", pip_req):
                    if p.strip():
                        pacotes_para_instalar.add(p.strip())

            # 2. Auto-detecta imports do código Python do usuário
            imports = set(re.findall(r'^(?:import|from)\s+([a-zA-Z0-9_]+)', codigo, re.MULTILINE))
            stdlib = sys.stdlib_module_names if hasattr(sys, 'stdlib_module_names') else set()
            ignore_list = {"config", "eyes", "ears", "memory", "mouth", "mcp"}
            for lib in imports:
                if lib not in stdlib and lib not in ignore_list:
                    pacotes_para_instalar.add(lib)

            # 3. Instala em background sem travar interface
            for pacote in pacotes_para_instalar:
                print(f"📦 [WebUI] Preparando ambiente para '{nome}'. Instalando: {pacote}")
                subprocess.run([sys.executable, "-m", "pip", "install", pacote], capture_output=True)
            if pacotes_para_instalar:
                print(f"✅ [WebUI] Dependências de '{nome}' prontas!")

        except Exception as e:
            print(f"⚠️ [WebUI] Erro ao instalar dependências: {e}")

    threading.Thread(target=instalar_dependencias, daemon=True).start()

    # Salva entrada no banco de dados via executar_sql do config.py
    executar_sql(
        "INSERT OR REPLACE INTO mcp_tools (name, description, schema_json, python_code, pip_requirements) VALUES (?, ?, ?, ?, ?)",
        (nome, data.get("descricao"), data.get("schema_json"), codigo, pip_req or None),
    )
    return {"status": "ok"}

@app.post("/api/mcp_tools/delete")
async def delete_mcp_tool(nome: str):
    executar_sql("DELETE FROM mcp_tools WHERE name = ?", (nome,))
    return {"status": "ok"}


# ── Vision ──
@app.get("/api/last_vision")
async def get_last_vision():
    if os.path.exists(VISION_PATH):
        return FileResponse(VISION_PATH, headers={"Cache-Control": "no-cache, no-store"})
    return Response(status_code=404)

@app.get("/api/vision_description")
async def get_vision_description():
    res     = executar_sql("SELECT text_value FROM system_state WHERE key = 'vision_desc'", fetch=True)
    content = res[0][0] if res and res[0][0] else "Waiting for capture..."
    return Response(content=content, media_type="text/plain")


# ── Clear history ──
@app.post("/api/limpar_historico")
async def clear_history_api():
    try:
        # With single continuous history, clear everything and re-insert system prompt
        rows = executar_sql("SELECT content FROM chat_history", fetch=True)
        executar_sql("DELETE FROM chat_history")
        persona    = obter_setting("persona")
        prompt_raw = persona.get("prompt_sistema", "")
        context    = "\n".join(prompt_raw) if isinstance(prompt_raw, list) else prompt_raw
        executar_sql("INSERT INTO chat_history (role, content) VALUES (?, ?)",
                     ("system", context))
        _cleanup_orphan_uploads(rows or [])
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


def _cleanup_orphan_uploads(deleted_rows):
    """Remove upload files that are no longer referenced in any message."""
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
    for row in (executar_sql("SELECT content FROM chat_history", fetch=True) or []):
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


# ── Memories ──
@app.get("/api/memories")
async def get_memories():
    res = executar_sql(
        "SELECT id, content, created_at, access_count FROM memories ORDER BY created_at DESC",
        fetch=True)
    return [{"id": r[0], "content": r[1], "created_at": r[2], "access_count": r[3]}
            for r in (res or [])]

@app.delete("/api/memories/{memory_id}")
async def delete_memory(memory_id: int):
    executar_sql("DELETE FROM memories WHERE id = ?", (memory_id,))
    return {"status": "ok"}

@app.delete("/api/memories")
async def delete_all_memories():
    executar_sql("DELETE FROM memories")
    return {"status": "ok"}


# ── Roleplay ──
@app.get("/api/roleplay")
async def get_roleplays():
    res = executar_sql(
        "SELECT id, name, ai_persona, user_persona, scenario, nsfw, active "
        "FROM roleplay_scenarios ORDER BY active DESC, id DESC",
        fetch=True)
    return [{"id":r[0],"nome":r[1],"persona_ia":r[2],"persona_usuario":r[3],
             "cenario":r[4],"nsfw":bool(r[5]),"ativo":bool(r[6])} for r in (res or [])]

@app.post("/api/roleplay/save")
async def save_roleplay(data: dict):
    executar_sql(
        "INSERT INTO roleplay_scenarios (name, ai_persona, user_persona, scenario, nsfw) "
        "VALUES (?, ?, ?, ?, ?)",
        (data["nome"], data.get("persona_ia",""), data.get("persona_usuario",""),
         data.get("cenario",""), data.get("nsfw", 0))
    )
    return {"status": "ok"}

@app.post("/api/roleplay/activate")
async def activate_roleplay(data: dict):
    executar_sql("UPDATE roleplay_scenarios SET active = 0")
    executar_sql("UPDATE roleplay_scenarios SET active = 1 WHERE id = ?", (data["id"],))
    return {"status": "ok"}

@app.post("/api/roleplay/deactivate")
async def deactivate_roleplay():
    executar_sql("UPDATE roleplay_scenarios SET active = 0")
    return {"status": "ok"}

@app.post("/api/roleplay/delete")
async def delete_roleplay(id: int):
    executar_sql("DELETE FROM roleplay_scenarios WHERE id = ?", (id,))
    return {"status": "ok"}



# ── Modes ──
@app.post("/api/modo/foco")
async def toggle_focus(data: dict):
    cfg = obter_setting("config")
    cfg.setdefault("sistema", {})["modo_foco"] = data.get("ativo", False)
    salvar_setting("config", cfg)
    return {"status": "ok"}

@app.post("/api/modo/nao_perturbe")
async def toggle_dnd(data: dict):
    cfg = obter_setting("config")
    cfg.setdefault("sistema", {})["modo_nao_perturbe"] = data.get("ativo", False)
    salvar_setting("config", cfg)
    return {"status": "ok"}

@app.get("/api/modo/status")
async def get_mode_status():
    s = obter_setting("config").get("sistema", {})
    return {"modo_foco": s.get("modo_foco", False), "modo_nao_perturbe": s.get("modo_nao_perturbe", False)}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
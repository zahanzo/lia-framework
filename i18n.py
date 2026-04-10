"""
i18n.py — Internationalization module
Supports: pt-BR (Brazilian Portuguese) and en-US (English)

Usage:
    from i18n import t
    print(t("db.tables_verified"))
    # → "✅ [DB] All tables verified." (en) or "✅ [DB] Todas as tabelas verificadas." (pt)
"""

# Current language — set at boot from database via config.set_language()
_lang = "en"

# ==========================================
# TRANSLATIONS
# ==========================================
_translations: dict[str, dict[str, str]] = {

    # ── Database ──────────────────────────────────────────────────────
    "db.tables_verified":         {"en": "✅ [DB] All tables verified.",
                                   "pt": "✅ [DB] Todas as tabelas verificadas."},
    "db.sql_error":               {"en": "❌ [DB] SQL error: {e}",
                                   "pt": "❌ Erro SQL no Config: {e}"},
    "db.migrated_orphans":        {"en": "📦 [DB] {n} orphan message(s) migrated to legacy session #{id}.",
                                   "pt": "📦 [DB] {n} mensagem(s) migrada(s) para sessão legada #{id}."},
    "db.migration_error":         {"en": "⚠️ [DB] Migration error: {e}",
                                   "pt": "⚠️ [DB] Migração de mensagens antigas: {e}"},

    # ── History / Summary ─────────────────────────────────────────────
    "history.compressing":        {"en": "📝 [Summary] History has {n} messages. Compressing...",
                                   "pt": "📝 [Resumo] Histórico com {n} msgs. Comprimindo..."},
    "history.compressed":         {"en": "✅ [Summary] Compressed {n} messages → 1 context block.",
                                   "pt": "✅ [Resumo] Histórico comprimido. {n} msgs → 1 bloco de contexto."},
    "history.compress_error":     {"en": "❌ [Summary] Compression error: {e}",
                                   "pt": "❌ [Resumo] Erro ao comprimir histórico: {e}"},

    # ── Sessions (DB lifecycle — voice/MCP turns) ─────────────────────
    "session.new":                {"en": "✨ [Session] New session #{id} created.",
                                   "pt": "✨ [Sessão] Nova sessão #{id} criada."},

    # ── MCP ──────────────────────────────────────────────────────────
    "mcp.connecting":             {"en": "🔗 Connecting to MCP server...",
                                   "pt": "🔗 Conectando ao Servidor MCP..."},
    "mcp.connected":              {"en": "✅ MCP connected! {n} skills active.",
                                   "pt": "✅ MCP conectado! {n} habilidades ativas."},
    "mcp.error":                  {"en": "❌ MCP error:\n{e}",
                                   "pt": "❌ Erro MCP:\n{e}"},
    "mcp.reconnecting":           {"en": "⏳ Reconnecting in 5 seconds...",
                                   "pt": "⏳ Reconectando em 5 segundos..."},
    "mcp.tool_using":             {"en": "⚙️ [MCP] Using: {tools}",
                                   "pt": "⚙️ [MCP] Usando: {tools}"},
    "mcp.tool_result":            {"en": "   └ {result}",
                                   "pt": "   └ {result}"},
    "mcp.tool_timeout":           {"en": "The tool '{name}' took too long to finish. It may still be running (e.g. installing a package or opening the browser). Check if it worked; if not, try again.",
                                   "pt": "A ferramenta '{name}' demorou demais para responder. Ela pode ainda estar rodando (ex.: instalando pacote ou abrindo o navegador). Veja se funcionou; se não, tente de novo."},
    "mcp.tool_timeout_log":       {"en": "⏱️ [MCP] Tool '{name}' timed out after {sec}s",
                                   "pt": "⏱️ [MCP] Ferramenta '{name}' estourou o tempo ({sec}s)"},
    "mcp.tool_failed":            {"en": "Tool error: {detail}",
                                   "pt": "Erro na ferramenta: {detail}"},
    "mcp.tool_exception_log":     {"en": "❌ [MCP] Tool '{name}': {e}",
                                   "pt": "❌ [MCP] Ferramenta '{name}': {e}"},
    "mcp.reload":                 {"en": "🔄 [System] Reloading MCP tools...",
                                   "pt": "🔄 [Sistema] Recarregando ferramentas MCP..."},

    # ── Voice ─────────────────────────────────────────────────────────
    "voice.consumer_started":     {"en": "✅ [Voice] Queue consumer started.",
                                   "pt": "✅ [Voz] Consumidor de fila iniciado."},
    "voice.error":                {"en": "❌ [Voice] Consumer error: {e}",
                                   "pt": "❌ [Voz] Erro no consumidor: {e}"},
    "voice.elevenlabs_error":     {"en": "❌ [ElevenLabs] Error: {e}",
                                   "pt": "❌ [ElevenLabs] Erro: {e}"},
    "voice.elevenlabs_no_client": {"en": "❌ [ElevenLabs] Client unavailable. Check API key.",
                                   "pt": "❌ [ElevenLabs] Cliente indisponível. Verifique a chave."},
    "voice.edge_error":           {"en": "❌ [Edge-TTS] Error: {e}",
                                   "pt": "❌ [Edge-TTS] Erro: {e}"},
    "voice.kokoro_error":         {"en": "❌ [Kokoro] Generation error: {e}",
                                   "pt": "❌ [Kokoro] Erro na geração: {e}"},
    "voice.kokoro_load_error":    {"en": "❌ [Kokoro] Failed to load: {e}",
                                   "pt": "❌ [Kokoro] Erro ao carregar: {e}"},
    "voice.kokoro_not_installed": {"en": "❌ [Kokoro] Not installed. Run: pip install kokoro soundfile",
                                   "pt": "❌ [Kokoro] Não instalado. Rode: pip install kokoro soundfile"},
    "voice.kokoro_loaded":        {"en": "✅ [Kokoro] Pipeline loaded!",
                                   "pt": "✅ [Kokoro] Pipeline carregado!"},
    "voice.piper_not_found":      {"en": "❌ [Piper] Model file not found: {path}",
                                   "pt": "❌ [Piper] Arquivo não encontrado: {path}"},
    "voice.piper_not_installed":  {"en": "❌ [Piper] Not installed. Run: pip install piper-tts",
                                   "pt": "❌ [Piper] Não instalado. Rode: pip install piper-tts"},
    "voice.piper_loaded":         {"en": "✅ [Piper] Model '{name}' loaded!",
                                   "pt": "✅ [Piper] Modelo '{name}' carregado!"},
    "voice.piper_error":          {"en": "❌ [Piper] Generation error: {e}",
                                   "pt": "❌ [Piper] Erro na geração: {e}"},

    # ── Memory / RAG ──────────────────────────────────────────────────
    "memory.table_ready":         {"en": "✅ [Memory] Table ready.",
                                   "pt": "✅ [Memória] Tabela pronta."},
    "memory.saved":               {"en": "💾 [Memory] Saved: {content}",
                                   "pt": "💾 [Memória] Salvo: {content}"},
    "memory.duplicate":           {"en": "🔁 [Memory] Similar fact already exists (sim={sim:.2f}), skipping.",
                                   "pt": "🔁 [Memória] Fato similar já existe (sim={sim:.2f}), ignorando."},
    "memory.found":               {"en": "🔍 [Memory] {n} relevant memory(ies) injected.",
                                   "pt": "🔍 [Memória] {n} memória(s) relevante(s) injetada(s)."},
    "memory.extract_error":       {"en": "⚠️ [Memory] Extraction error: {e}",
                                   "pt": "⚠️ [Memória] Erro na extração: {e}"},
    "memory.decay":               {"en": "⏳ [Decay] {n} obsolete memory(ies) removed (+{days} days, never accessed).",
                                   "pt": "⏳ [Decay] {n} memória(s) obsoleta(s) apagada(s) (nunca acessadas, +{days} dias)."},
    "memory.decay_none":          {"en": "⏳ [Decay] No obsolete memories found.",
                                   "pt": "⏳ [Decay] Nenhuma memória obsoleta encontrada."},
    "memory.embed_loading":       {"en": "🧠 [Memory] Loading embedding model... (first time ~30s)",
                                   "pt": "🧠 [Memória] Carregando modelo de embedding... (primeira vez ~30s)"},
    "memory.embed_loaded":        {"en": "✅ [Memory] Embedding model loaded!",
                                   "pt": "✅ [Memória] Modelo de embedding carregado!"},
    "memory.embed_no_pkg":        {"en": "❌ [Memory] sentence-transformers not installed. Run: pip install sentence-transformers",
                                   "pt": "❌ [Memória] sentence-transformers não instalado. Rode: pip install sentence-transformers"},
    "memory.embed_error":         {"en": "❌ [Memory] Model load error: {e}",
                                   "pt": "❌ [Memória] Erro ao carregar modelo: {e}"},

    # ── Skills / Chat mode ───────────────────────────────────────────
    "skills.activated":           {"en": "💬 [Skills] Chat mode ACTIVATED!",
                                   "pt": "💬 [Skills] Modo Bate-papo ATIVADO!"},
    "skills.deactivated":         {"en": "💬 [Skills] Chat mode deactivated.",
                                   "pt": "💬 [Skills] Modo Bate-papo desativado."},
    "skills.rolled":              {"en": "🎲 [Skills] Rolled: '{id}' | On cooldown: {cooldowns}",
                                   "pt": "🎲 [Skills] Skill sorteada: '{id}' | Cooldowns ativos: {cooldowns}"},

    # ── System / Boot ────────────────────────────────────────────────
    "system.boot":                {"en": "✨ Assistant initialized! (Mode: {mode})",
                                   "pt": "✨ Assistente inicializado! (Modo: {mode})"},
    "system.hotkeys":             {"en": "👉 X = Talk | X2 = Screen | Ctrl+Alt+F = Focus | Ctrl+Alt+M = Web panel | Ctrl+C = Quit",
                                   "pt": "👉 X = Falar | X2 = Tela | Ctrl+Alt+F = Foco | Ctrl+Alt+M = Painel web | Ctrl+C = Sair"},
    "system.shutdown":            {"en": "\n👋 Shutting down... Goodbye!",
                                   "pt": "\n👋 Encerrando... Até logo!"},
    "system.focus_on":            {"en": "🎯 Focus Mode ACTIVATED",
                                   "pt": "🎯 Modo Foco ATIVADO"},
    "system.focus_off":           {"en": "🎯 Focus Mode deactivated",
                                   "pt": "🎯 Modo Foco desativado"},
    "system.meeting_on":          {"en": "[Meeting] Do Not Disturb ACTIVATED 🔕",
                                   "pt": "[Reunião] Modo Não Perturbe ATIVADO 🔕"},
    "system.meeting_off":         {"en": "[Meeting] Do Not Disturb deactivated 🔔",
                                   "pt": "[Reunião] Modo Não Perturbe desativado 🔔"},
    "system.maintenance":         {"en": "🧹 [Maintenance] Applying memory decay...",
                                   "pt": "🧹 [Manutenção] Aplicando decay de memórias..."},
    "system.watchdog":            {"en": "🐕 [Watchdog] Injecting proactive message...",
                                   "pt": "🐕 [Watchdog] Injetando mensagem proativa..."},
    "system.vision_bg":           {"en": "👁️ [Vision BG] Screen changed, updating context...",
                                   "pt": "👁️ [Visão BG] Tela mudou, atualizando contexto..."},
    "system.vision_error":        {"en": "⚠️ [Vision BG] {e}",
                                   "pt": "⚠️ [Visão BG] {e}"},

    # ── AI routing ───────────────────────────────────────────────────
    "ai.intent":                  {"en": "🎯 [Intent: {intent}] {model}",
                                   "pt": "🎯 [Intenção: {intent}] {model}"},
    "ai.vision":                  {"en": "👁️ [Vision/Image] {model}",
                                   "pt": "👁️ [Visão/Imagem] {model}"},
    "ai.roleplay":                {"en": "🎭 [Roleplay] {model}",
                                   "pt": "🎭 [Roleplay] {model}"},
    "ai.image_loading":           {"en": "   🖼️ Image: {name} ({size}KB)",
                                   "pt": "   🖼️ Imagem: {name} ({size}KB)"},
    "ai.image_error":             {"en": "   ⚠️ Error loading image {name}: {e}",
                                   "pt": "   ⚠️ Erro ao carregar imagem {name}: {e}"},
    "ai.error":                   {"en": "❌ [AI] Communication error: {e}",
                                   "pt": "❌ Erro na IA: {e}"},

    # ── Turn / Input ─────────────────────────────────────────────────
    "turn.you":                   {"en": "🗣️ You: {text}",
                                   "pt": "🗣️ Você: {text}"},
    "turn.ai":                    {"en": "\n🤖 AI: {text}",
                                   "pt": "\n🌸 IA: {text}"},
    "turn.attachment":            {"en": "📎 [{n} file(s)] Text: {text}",
                                   "pt": "📎 [{n} arquivo(s)] Texto: {text}"},
    "turn.web_received":          {"en": "💻 [Web/Watchdog] Message received!",
                                   "pt": "💻 [Web/Watchdog] Mensagem recebida!"},
    "turn.reload_mcp":            {"en": "🔄 [System] Reload command accepted.",
                                   "pt": "🔄 [Sistema] Comando de reinicialização aceito."},
    "turn.error_recovery":        {"en": "⚠️ Turn error (recovering): {e}",
                                   "pt": "⚠️ Erro no turno (recuperando): {e}"},

    # ── Ears / STT ───────────────────────────────────────────────────
    "ears.whisper_loaded":        {"en": "✅ [Whisper] Model '{size}' loaded.",
                                   "pt": "✅ [Whisper] Modelo '{size}' carregado."},
    "ears.whisper_missing_pkg":   {"en": "❌ [Whisper] faster-whisper not installed. Run: pip install faster-whisper torch",
                                   "pt": "❌ [Whisper] faster-whisper não instalado. Rode: pip install faster-whisper torch"},
    "ears.whisper_load_error":    {"en": "❌ [Whisper] Failed to load model: {e}",
                                   "pt": "❌ [Whisper] Falha ao carregar modelo: {e}"},
    "ears.whisper_heard":         {"en": "✅ [Whisper] Heard: '{text}'",
                                   "pt": "✅ [Whisper] Ouvi: '{text}'"},
    "ears.whisper_empty":         {"en": "⚠️ [Whisper] No speech detected in this segment.",
                                   "pt": "⚠️ [Whisper] Nenhuma fala detectada neste trecho."},
    "ears.whisper_error":         {"en": "❌ [Whisper] Error: {e}",
                                   "pt": "❌ [Whisper] Erro: {e}"},
    "ears.google_stt_working":    {"en": "☁️ [Google STT] Transcribing...",
                                   "pt": "☁️ [Google STT] Transcrevendo..."},
    "ears.google_stt_heard":      {"en": "✅ [Google STT] Heard: '{text}'",
                                   "pt": "✅ [Google STT] Ouvi: '{text}'"},
    "ears.google_stt_missing":    {"en": "❌ [Google STT] Install: pip install SpeechRecognition",
                                   "pt": "❌ [Google STT] Instale: pip install SpeechRecognition"},
    "ears.google_stt_fail":       {"en": "⚠️ [Google STT] Could not understand audio.",
                                   "pt": "⚠️ [Google STT] Não entendi o áudio."},
    "ears.vad_open":              {"en": "🎙️ [VAD] Microphone open — speak naturally...",
                                   "pt": "🎙️ [VAD] Microfone aberto — fale naturalmente..."},
    "ears.vad_detected":          {"en": "🗣️ [VAD] Voice detected — recording...",
                                   "pt": "🗣️ [VAD] Voz detectada — gravando..."},

    # ── Upload ───────────────────────────────────────────────────────
    "upload.removed":             {"en": "🗑️ [Upload] Removed: {name}",
                                   "pt": "🗑️ [Upload] Removido: {name}"},
    "upload.remove_error":        {"en": "⚠️ [Upload] Error removing {name}: {e}",
                                   "pt": "⚠️ [Upload] Erro ao remover {name}: {e}"},

    # ── MCP Server ───────────────────────────────────────────────────
    "server.keys_loaded":         {"en": "🔑 [MCP] AI engines initialized!",
                                   "pt": "🔑 [MCP] Motores de IA inicializados!"},
    "server.key_error":           {"en": "❌ [MCP] Error loading keys: {e}",
                                   "pt": "❌ [MCP] Erro ao carregar chaves: {e}"},
    "server.tool_running":        {"en": "\n⚙️ [MCP] Running: {name}",
                                   "pt": "\n⚙️ [MCP] Executando: {name}"},
    "server.vision_ok":           {"en": "   └ Vision OK",
                                   "pt": "   └ Visão OK"},
    "server.tool_not_found":      {"en": "Tool '{name}' not found or has no code.",
                                   "pt": "Ferramenta '{name}' não encontrada ou sem código."},
    "server.tool_return":         {"en": "   └ Return: {result}",
                                   "pt": "   └ Retorno: {result}"},
    "server.tool_error":          {"en": "   └ ❌ Error in '{name}': {e}",
                                   "pt": "   └ ❌ Erro em '{name}': {e}"},
    "server.mcp_pip_install":     {"en": "📦 [MCP] Installing for '{name}': {pkgs}",
                                   "pt": "📦 [MCP] Instalando para '{name}': {pkgs}"},
    "server.mcp_pip_ok":          {"en": "   └ pip install OK",
                                   "pt": "   └ pip install OK"},
    "server.mcp_pip_fail":        {"en": "   └ pip install failed: {detail}",
                                   "pt": "   └ falha no pip install: {detail}"},
    "server.mcp_pip_retry":       {"en": "   └ Retrying after missing module '{mod}'…",
                                   "pt": "   └ Tentando de novo após módulo ausente '{mod}'…"},
}


# ==========================================
# PUBLIC API
# ==========================================
def set_language(lang: str):
    """Set active language. Accepts 'en' or 'pt'."""
    global _lang
    _lang = lang if lang in ("en", "pt") else "en"


def get_language() -> str:
    return _lang


def t(key: str, **kwargs) -> str:
    """
    Translate a key to the active language.
    Supports format kwargs: t("db.migrated_orphans", n=5, id=3)
    Falls back to the key itself if not found.
    """
    entry = _translations.get(key)
    if not entry:
        return key
    text = entry.get(_lang) or entry.get("en") or key
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError):
            pass
    return text

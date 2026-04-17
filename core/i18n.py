"""
i18n.py — Internationalization module
Supports: pt-BR (Brazilian Portuguese) and en-US (English)

Usage:
    from core.i18n import t
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
    # ══════════════════════════════════════════════════════════════════════════════
    # memory.py i18n keys
    # ══════════════════════════════════════════════════════════════════════════════

    "memory.embed_loading": {
        "en": "🧠 [Memory] Loading embedding model...",
        "pt": "🧠 [Memória] Carregando modelo de embeddings..."
    },

    "memory.embed_loaded": {
        "en": "✅ [Memory] Embedding model ready.",
        "pt": "✅ [Memória] Modelo de embeddings pronto."
    },

    "memory.embed_no_pkg": {
        "en": "❌ [Memory] sentence-transformers not installed. Run: pip install sentence-transformers",
        "pt": "❌ [Memória] sentence-transformers não instalado. Execute: pip install sentence-transformers"
    },

    "memory.embed_error": {
        "en": "❌ [Memory] Embedding error: {e}",
        "pt": "❌ [Memória] Erro de embedding: {e}"
    },

    "memory.table_ready": {
        "en": "✅ [Memory] Table ready.",
        "pt": "✅ [Memória] Tabela pronta."
    },

    "memory.duplicate": {
        "en": "⚠️ [Memory] Duplicate detected (similarity: {sim:.2f}). Skipping.",
        "pt": "⚠️ [Memória] Duplicata detectada (similaridade: {sim:.2f}). Ignorando."
    },

    "memory.saved": {
        "en": "💾 [Memory] Saved: {content}",
        "pt": "💾 [Memória] Salvo: {content}"
    },

    "memory.found": {
        "en": "🔍 [Memory] Found {n} relevant memories.",
        "pt": "🔍 [Memória] Encontradas {n} memórias relevantes."
    },

    "memory.extract_error": {
        "en": "❌ [Memory] Fact extraction error: {e}",
        "pt": "❌ [Memória] Erro na extração de fatos: {e}"
    },

    "memory.decay": {
        "en": "🧹 [Memory] Removed {n} obsolete memories (older than {days} days).",
        "pt": "🧹 [Memória] Removidas {n} memórias obsoletas (mais antigas que {days} dias)."
    },

    "memory.decay_none": {
        "en": "✅ [Memory] No obsolete memories to remove.",
        "pt": "✅ [Memória] Nenhuma memória obsoleta para remover."
    },

    # ── Skills / Chat mode ───────────────────────────────────────────
    "skills.activated":           {"en": "💬 [Skills] Chat mode ACTIVATED!",
                                   "pt": "💬 [Skills] Modo Bate-papo ATIVADO!"},
    "skills.deactivated":         {"en": "💬 [Skills] Chat mode deactivated.",
                                   "pt": "💬 [Skills] Modo Bate-papo desativado."},
    "skills.rolled":              {"en": "🎲 [Skills] Rolled: '{id}' | On cooldown: {cooldowns}",
                                   "pt": "🎲 [Skills] Skill sorteada: '{id}' | Cooldowns ativos: {cooldowns}"},
    # ══════════════════════════════════════════════════════════════════════════════
# skills.py i18n keys
# ══════════════════════════════════════════════════════════════════════════════

"skills.activated": {
    "en": "💬 [Chat Mode] Activated.",
    "pt": "💬 [Modo Chat] Ativado."
},

"skills.deactivated": {
    "en": "💬 [Chat Mode] Deactivated.",
    "pt": "💬 [Modo Chat] Desativado."
},

"skills.rolled": {
    "en": "🎭 [Skills] Rolled: {id} | On cooldown: {cooldowns}",
    "pt": "🎭 [Skills] Sorteado: {id} | Em cooldown: {cooldowns}"
},

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
    "system.reloading_config":     {"en": "🔄 Reloading configuration...",
                                    "pt": "🔄 Recarregando configurações..."},
    "system.config_reloaded":      {"en": "✅ Configuration reloaded successfully!",
                                    "pt": "✅ Configuração recarregada com sucesso!"},

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
    # ══════════════════════════════════════════════════════════════════════════════
# mouth.py i18n keys
# ══════════════════════════════════════════════════════════════════════════════

"voice.error": {
    "en": "❌ [Voice] Error: {e}",
    "pt": "❌ [Voz] Erro: {e}"
},

"voice.elevenlabs_error": {
    "en": "❌ [ElevenLabs] Error: {e}",
    "pt": "❌ [ElevenLabs] Erro: {e}"
},

"voice.elevenlabs_no_client": {
    "en": "❌ [ElevenLabs] No API key configured.",
    "pt": "❌ [ElevenLabs] Nenhuma chave de API configurada."
},

"voice.edge_not_installed": {
    "en": "❌ [Edge-TTS] Not installed. Run: pip install edge-tts",
    "pt": "❌ [Edge-TTS] Não instalado. Execute: pip install edge-tts"
},

"voice.edge_error": {
    "en": "❌ [Edge-TTS] Error: {e}",
    "pt": "❌ [Edge-TTS] Erro: {e}"
},

"voice.kokoro_loaded": {
    "en": "✅ [Kokoro] TTS engine loaded.",
    "pt": "✅ [Kokoro] Engine TTS carregado."
},

"voice.kokoro_not_installed": {
    "en": "❌ [Kokoro] Not installed. Run: pip install kokoro soundfile",
    "pt": "❌ [Kokoro] Não instalado. Execute: pip install kokoro soundfile"
},

"voice.kokoro_load_error": {
    "en": "❌ [Kokoro] Load error: {e}",
    "pt": "❌ [Kokoro] Erro ao carregar: {e}"
},

"voice.kokoro_error": {
    "en": "❌ [Kokoro] Synthesis error: {e}",
    "pt": "❌ [Kokoro] Erro de síntese: {e}"
},

"voice.piper_not_found": {
    "en": "❌ [Piper] Model not found: {path}",
    "pt": "❌ [Piper] Modelo não encontrado: {path}"
},

"voice.piper_loaded": {
    "en": "✅ [Piper] Loaded model: {name}",
    "pt": "✅ [Piper] Modelo carregado: {name}"
},

"voice.piper_not_installed": {
    "en": "❌ [Piper] Not installed. Run: pip install piper-tts",
    "pt": "❌ [Piper] Não instalado. Execute: pip install piper-tts"
},

"voice.piper_error": {
    "en": "❌ [Piper] Error: {e}",
    "pt": "❌ [Piper] Erro: {e}"
},

"voice.lipsync_started": {
    "en": "[Voice] LipSync started.",
    "pt": "[Voz] LipSync iniciado."
},

"voice.lipsync_disabled": {
    "en": "[Voice] LipSync disabled (enable in dashboard → System).",
    "pt": "[Voz] LipSync desabilitado (habilite no painel → Sistema)."
},

"voice.consumer_started": {
    "en": "✅ [Voice] Queue consumer started.",
    "pt": "✅ [Voz] Consumidor de fila iniciado."
},
    # ══════════════════════════════════════════════════════════════════════════════
    # ears.py i18n keys
    # ══════════════════════════════════════════════════════════════════════════════

    "ears.vad_loaded": {
        "en": "✅ [VAD] Silero VAD loaded.",
        "pt": "✅ [VAD] Silero VAD carregado."
    },

    "ears.vad_torch_error": {
        "en": "❌ [VAD] Torch error: {e}",
        "pt": "❌ [VAD] Erro do Torch: {e}"
    },

    "ears.vad_load_error": {
        "en": "❌ [VAD] Failed to load model: {e}",
        "pt": "❌ [VAD] Falha ao carregar modelo: {e}"
    },

    "ears.pyaudio_missing": {
        "en": "❌ [Audio] pyaudio not installed. Run: pip install pyaudio",
        "pt": "❌ [Audio] pyaudio não instalado. Execute: pip install pyaudio"
    },

    "ears.button_released": {
        "en": "⏳ [Button] Released — processing...",
        "pt": "⏳ [Botão] Solto — processando..."
    },

    "ears.vad_fallback": {
        "en": "⚠️ [VAD] Model unavailable — falling back to button mode.",
        "pt": "⚠️ [VAD] Modelo indisponível — voltando para modo botão."
    },

    "ears.vad_deps_missing": {
        "en": "❌ [VAD] torch/numpy not installed. Run: pip install torch numpy",
        "pt": "❌ [VAD] torch/numpy não instalados. Execute: pip install torch numpy"
    },

    "ears.vad_capture_error": {
        "en": "❌ [VAD] Capture error: {e}",
        "pt": "❌ [VAD] Erro de captura: {e}"
    },

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
    # ══════════════════════════════════════════════════════════════════════════════
    # eyes.py i18n keys
    # ══════════════════════════════════════════════════════════════════════════════

    "vision.mss_missing": {
        "en": "❌ [Vision] mss not installed. Run: pip install mss",
        "pt": "❌ [Visão] mss não instalado. Execute: pip install mss"
    },

    "vision.capture_failed": {
        "en": "❌ [Vision] Screen capture failed: {error}",
        "pt": "❌ [Visão] Falha na captura de tela: {error}"
    },

    "vision.capture_unavailable": {
        "en": "Screen capture unavailable.",
        "pt": "Captura de tela indisponível."
    },

    "vision.no_client": {
        "en": "No AI client initialized (Local / Groq / OpenRouter / OpenAI). Add your API keys or configure local server in the dashboard.",
        "pt": "Nenhum client de IA inicializado (Local / Groq / OpenRouter / OpenAI). Adicione suas chaves de API ou configure servidor local no painel."
    },

    "vision.analysis_failed": {
        "en": "❌ [Vision] Analysis failed: {error}",
        "pt": "❌ [Visão] Análise falhou: {error}"
    },

    "vision.error": {
        "en": "Vision error: {error}",
        "pt": "Erro de visão: {error}"
    },

    # ── Store ─────────────────────────────────────────────────────────
    "store.title":                {"en": "Plugin & Master Store",
                                   "pt": "Loja de Plugins & Masters"},
    "store.search":               {"en": "Search plugins, masters...",
                                   "pt": "Buscar plugins, masters..."},
    "store.all_categories":       {"en": "All Categories",
                                   "pt": "Todas as Categorias"},
    "store.all_types":            {"en": "All",
                                   "pt": "Todos"},
    "store.plugins":              {"en": "Plugins",
                                   "pt": "Plugins"},
    "store.masters":              {"en": "Masters",
                                   "pt": "Masters"},
    "store.submit":               {"en": "Submit Plugin",
                                   "pt": "Enviar Plugin"},
    "store.plugins_section":      {"en": "Plugins",
                                   "pt": "Plugins"},
    "store.masters_section":      {"en": "Masters",
                                   "pt": "Masters"},
    "store.install":              {"en": "Install",
                                   "pt": "Instalar"},
    "store.installed":            {"en": "Installed",
                                   "pt": "Instalado"},
    "store.uninstall":            {"en": "Uninstall",
                                   "pt": "Desinstalar"},
    "store.tools_count":          {"en": "tools",
                                   "pt": "ferramentas"},
    "store.downloads":            {"en": "downloads",
                                   "pt": "downloads"},
    "store.submit_title":         {"en": "Submit to Store",
                                   "pt": "Enviar para Loja"},
    "store.submit_type":          {"en": "Type",
                                   "pt": "Tipo"},
    "store.type_plugin":          {"en": "Plugin (Single Tool)",
                                   "pt": "Plugin (Uma Ferramenta)"},
    "store.type_master":          {"en": "Master (Multiple Tools)",
                                   "pt": "Master (Várias Ferramentas)"},
    "store.name_id":              {"en": "Name / ID",
                                   "pt": "Nome / ID"},
    "store.name_placeholder":     {"en": "e.g. screen_brightness",
                                   "pt": "ex: brilho_tela"},
    "store.description":          {"en": "Description",
                                   "pt": "Descrição"},
    "store.desc_placeholder":     {"en": "What does this plugin/master do?",
                                   "pt": "O que este plugin/master faz?"},
    "store.author":               {"en": "Author (Name or Email)",
                                   "pt": "Autor (Nome ou Email)"},
    "store.author_placeholder":   {"en": "Your name",
                                   "pt": "Seu nome"},
    "store.category":             {"en": "Category",
                                   "pt": "Categoria"},
    "store.cat_system":           {"en": "System",
                                   "pt": "Sistema"},
    "store.cat_media":            {"en": "Media",
                                   "pt": "Mídia"},
    "store.cat_web":              {"en": "Web",
                                   "pt": "Web"},
    "store.cat_automation":       {"en": "Automation",
                                   "pt": "Automação"},
    "store.tool_details":         {"en": "Tool Details",
                                   "pt": "Detalhes da Ferramenta"},
    "store.tool_name":            {"en": "Tool Name",
                                   "pt": "Nome da Ferramenta"},
    "store.tool_name_placeholder": {"en": "e.g. set_brightness",
                                   "pt": "ex: ajustar_brilho"},
    "store.tool_desc":            {"en": "Tool Description",
                                   "pt": "Descrição da Ferramenta"},
    "store.tool_desc_placeholder": {"en": "What this tool does",
                                   "pt": "O que esta ferramenta faz"},
    "store.json_schema":          {"en": "JSON Schema",
                                   "pt": "Schema JSON"},
    "store.python_code":          {"en": "Python Code",
                                   "pt": "Código Python"},
    "store.pip_requirements":     {"en": "pip requirements (optional)",
                                   "pt": "Requisitos pip (opcional)"},
    "store.pip_placeholder":      {"en": "e.g. screen-brightness-control",
                                   "pt": "ex: screen-brightness-control"},
    "store.tools_list":           {"en": "Tools",
                                   "pt": "Ferramentas"},
    "store.add_tool":             {"en": "+ Add Tool",
                                   "pt": "+ Adicionar Ferramenta"},
    "store.no_tools":             {"en": "No tools added yet. Click + Add Tool to start.",
                                   "pt": "Nenhuma ferramenta adicionada. Clique + Adicionar Ferramenta."},
    "store.generate_issue":       {"en": "Generate GitHub Issue",
                                   "pt": "Gerar GitHub Issue"},
    "store.cancel":               {"en": "Cancel",
                                   "pt": "Cancelar"},
    "store.edit":                 {"en": "Edit",
                                   "pt": "Editar"},
    "store.delete":               {"en": "Delete",
                                   "pt": "Deletar"},
    "store.save_tool":            {"en": "Save Tool",
                                   "pt": "Salvar Ferramenta"},
    "store.add_tool_to_master":   {"en": "Add Tool to Master",
                                   "pt": "Adicionar Ferramenta ao Master"},
    "store.json_generated":       {"en": "JSON Generated",
                                   "pt": "JSON Gerado"},
    "store.create_github_issue":  {"en": "Create GitHub Issue",
                                   "pt": "Criar GitHub Issue"},
    "store.copy_json":            {"en": "Copy JSON",
                                   "pt": "Copiar JSON"},
    "store.json_copied":          {"en": "JSON copied to clipboard!",
                                   "pt": "JSON copiado!"},
    "store.fill_required":        {"en": "Please fill all required fields",
                                   "pt": "Preencha todos os campos obrigatórios"},
    "store.fill_tool_fields":     {"en": "Please fill all tool fields",
                                   "pt": "Preencha todos os campos da ferramenta"},
    "store.add_one_tool":         {"en": "Please add at least one tool",
                                   "pt": "Adicione pelo menos uma ferramenta"},
    "store.confirm_delete":       {"en": "Delete this tool?",
                                   "pt": "Deletar esta ferramenta?"},
    
    # ══════════════════════════════════════════════════════════════════════════════
# tool_retrieval.py i18n keys
# ══════════════════════════════════════════════════════════════════════════════

"tool_retrieval.loading_model": {
    "en": "🔧 [Tool Retrieval] Loading embeddings model...",
    "pt": "🔧 [Busca de Ferramentas] Carregando modelo de embeddings..."
},

"tool_retrieval.model_loaded": {
    "en": "✅ [Tool Retrieval] Model loaded!",
    "pt": "✅ [Busca de Ferramentas] Modelo carregado!"
},

"tool_retrieval.model_missing": {
    "en": "❌ [Tool Retrieval] sentence-transformers not installed\n   Run: pip install sentence-transformers",
    "pt": "❌ [Busca de Ferramentas] sentence-transformers não instalado\n   Execute: pip install sentence-transformers"
},

"tool_retrieval.indexed": {
    "en": "✅ [Tool Retrieval] Indexed: {tool}",
    "pt": "✅ [Busca de Ferramentas] Indexado: {tool}"
},

"tool_retrieval.indexing_all": {
    "en": "🔧 [Tool Retrieval] Indexing {count} tools...",
    "pt": "🔧 [Busca de Ferramentas] Indexando {count} ferramentas..."
},

"tool_retrieval.indexing_complete": {
    "en": "✅ [Tool Retrieval] {count} tools indexed!",
    "pt": "✅ [Busca de Ferramentas] {count} ferramentas indexadas!"
},

"tool_retrieval.selected_tools": {
    "en": "\n🔍 [Tool Retrieval] Selected {count} relevant tools:",
    "pt": "\n🔍 [Busca de Ferramentas] Selecionadas {count} ferramentas relevantes:"
},

"tool_retrieval.similarity": {
    "en": "similarity",
    "pt": "similaridade"
},

"tool_retrieval.test_header": {
    "en": "🔧 Tool Retrieval System - Test",
    "pt": "🔧 Sistema de Busca de Ferramentas - Teste"
},

"tool_retrieval.test_indexing": {
    "en": "Indexing all tools...",
    "pt": "Indexando todas as ferramentas..."
},

"tool_retrieval.test_stats": {
    "en": "Statistics:",
    "pt": "Estatísticas:"
},

"tool_retrieval.stats_total": {
    "en": "Total tools",
    "pt": "Total de ferramentas"
},

"tool_retrieval.stats_indexed": {
    "en": "Indexed tools",
    "pt": "Ferramentas indexadas"
},

"tool_retrieval.stats_coverage": {
    "en": "Coverage",
    "pt": "Cobertura"
},

"tool_retrieval.test_search": {
    "en": "Semantic search test:",
    "pt": "Teste de busca semântica:"
},

"tool_retrieval.found_tools": {
    "en": "Found {count} relevant tools:",
    "pt": "Encontradas {count} ferramentas relevantes:"
},

"tool_retrieval.no_tools_found": {
    "en": "No tools found",
    "pt": "Nenhuma ferramenta encontrada"
},

"tool_retrieval.test_complete": {
    "en": "✅ Test completed!",
    "pt": "✅ Teste concluído!"
},
    
    # ══════════════════════════════════════════════════════════════════════════════
    # lipsync.py i18n keys
    # ══════════════════════════════════════════════════════════════════════════════

    "lipsync.authenticated": {
        "en": "[LipSync] Authenticated.",
        "pt": "[LipSync] Autenticado."
    },

    "lipsync.no_token": {
        "en": "[LipSync] Could not get token. Enable the API in VTube Studio settings.",
        "pt": "[LipSync] Não foi possível obter token. Habilite a API nas configurações do VTube Studio."
    },

    "lipsync.click_allow": {
        "en": "[LipSync] Click ALLOW in VTube Studio...",
        "pt": "[LipSync] Clique em PERMITIR no VTube Studio..."
    },

    "lipsync.token_saved": {
        "en": "[LipSync] Authenticated! Token saved.",
        "pt": "[LipSync] Autenticado! Token salvo."
    },

    "lipsync.auth_failed": {
        "en": "[LipSync] Authentication failed.",
        "pt": "[LipSync] Falha na autenticação."
    },

    "lipsync.running": {
        "en": "[LipSync] Mouth animation running.",
        "pt": "[LipSync] Animação de boca em execução."
    },

    "lipsync.websockets_missing": {
        "en": "[LipSync] websockets not installed. Run: pip install websockets",
        "pt": "[LipSync] websockets não instalado. Execute: pip install websockets"
    },

    "lipsync.connecting": {
        "en": "[LipSync] Connecting to {url}...",
        "pt": "[LipSync] Conectando a {url}..."
    },

    "lipsync.max_retries": {
        "en": "[LipSync] Could not connect. Make sure VTube Studio is open\n          with API enabled (Settings -> General -> Start API).",
        "pt": "[LipSync] Não foi possível conectar. Certifique-se de que o VTube Studio está aberto\n          com a API habilitada (Configurações -> Geral -> Iniciar API)."
    },

    "lipsync.reconnecting": {
        "en": "[LipSync] Connection lost ({current}/{max}), retrying in 5s...",
        "pt": "[LipSync] Conexão perdida ({current}/{max}), tentando novamente em 5s..."
    },

    "lipsync.test_start": {
        "en": "LipSync test — simulates 5 seconds of speaking.\nWatch the MouthOpen parameter in VTube Studio.",
        "pt": "Teste de LipSync — simula 5 segundos de fala.\nObserve o parâmetro MouthOpen no VTube Studio."
    },

    "lipsync.test_speaking": {
        "en": "Speaking...",
        "pt": "Falando..."
    },

    "lipsync.test_stopped": {
        "en": "Stopped.",
        "pt": "Parado."
    },
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
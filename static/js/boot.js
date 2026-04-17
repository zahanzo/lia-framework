// ==========================================
// BOOT LOADER v2 - Full Cache Strategy
// ==========================================
console.log('⚡ [BOOT] v2 - Full cache enabled');

(function() {
    const startTime = performance.now();
    
    // ═══════════════════════════════════════════
    // INSTANT RESTORE FROM CACHE
    // ═══════════════════════════════════════════
    
    // 1. Nome da IA
    const cachedName = localStorage.getItem('ai_name_cache');
    if (cachedName) {
        window.nomeIA = cachedName;
        const elements = ['sidebar-ai-name', 'topbar-ai-name', 'chat-ai-name', 'nome_ia'];
        elements.forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                if (el.tagName === 'INPUT') el.value = cachedName;
                else el.textContent = cachedName;
            }
        });
    }
    
    // 2. Idioma
    const cachedLang = localStorage.getItem('ui_language_cache') || 'en';
    window._currentLang = cachedLang;
    const langSelect = document.getElementById('ui_language');
    if (langSelect) langSelect.value = cachedLang;
    
    // 3. Provider atual
    const cachedProvider = localStorage.getItem('provider_cache');
    if (cachedProvider) {
        const providerSelect = document.getElementById('modo_ia');
        if (providerSelect) providerSelect.value = cachedProvider;
    }
    
    // 4. API Keys (NÃO salvar valores, só indicar que existem)
    const hasKeys = localStorage.getItem('has_api_keys');
    if (hasKeys === 'true') {
        // Mostrar indicador visual que keys estão configuradas
        const apiSection = document.querySelector('.api-keys-section');
        if (apiSection) apiSection.classList.add('configured');
    }
    
    console.log(`⚡ [BOOT] Cache restored: ${(performance.now() - startTime).toFixed(0)}ms`);
    
    // ═══════════════════════════════════════════
    // SHOW INTERFACE
    // ═══════════════════════════════════════════
    
    const app = document.getElementById('app');
    if (app) app.style.opacity = '1';
    
    const skeleton = document.getElementById('skeleton-screen');
    if (skeleton) {
        skeleton.classList.add('hidden');
        setTimeout(() => skeleton.remove(), 300);
    }
    
    console.log(`⚡ [BOOT] UI visible: ${(performance.now() - startTime).toFixed(0)}ms`);
})();

// ═══════════════════════════════════════════
// PROGRESSIVE MODULE LOADING
// ═══════════════════════════════════════════

const moduleLoadOrder = [
    '/static/js/i18n.js',
    '/static/js/api.js',
    '/static/js/ui.js',
    '/static/js/chat.js',
    '/static/js/settings.js',
    '/static/js/persona.js',
    '/static/js/memory.js',
    '/static/js/plugins.js',
    '/static/js/tools.js',
    '/static/js/store.js',
    '/static/js/main.js'
];

async function loadModulesProgressively() {
    console.log('⚡ [BOOT] Loading modules...');
    const startTime = performance.now();
    
    for (const modulePath of moduleLoadOrder) {
        try {
            await import(modulePath);
        } catch (err) {
            console.error(`❌ Failed: ${modulePath}`, err);
        }
    }
    
    console.log(`✅ [BOOT] Modules loaded: ${(performance.now() - startTime).toFixed(0)}ms`);
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadModulesProgressively);
} else {
    loadModulesProgressively();
}

// ═══════════════════════════════════════════
// CACHE UPDATE HELPERS
// ═══════════════════════════════════════════

window.updateBootCache = function(config, persona) {
    try {
        // Nome da IA
        if (persona?.nome) {
            localStorage.setItem('ai_name_cache', persona.nome);
        }
        
        // Idioma
        if (config?.ui_language) {
            localStorage.setItem('ui_language_cache', config.ui_language);
        }
        
        // Provider
        if (config?.modo_ia) {
            localStorage.setItem('provider_cache', config.modo_ia);
        }
        
        // Indicador de API keys (não salva valores!)
        const hasKeys = config?.api_keys && 
            (config.api_keys.groq || config.api_keys.openrouter || config.api_keys.openai);
        localStorage.setItem('has_api_keys', hasKeys ? 'true' : 'false');
        
    } catch (err) {
        console.warn('[BOOT] Cache update failed:', err);
    }
};

// Clear cache (útil para debug)
window.clearBootCache = function() {
    const keys = ['ai_name_cache', 'ui_language_cache', 'provider_cache', 'has_api_keys'];
    keys.forEach(k => localStorage.removeItem(k));
    console.log('🗑️ [BOOT] Cache cleared');
};
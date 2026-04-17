// ==========================================
// API MODULE - Full Backend Communication
// ==========================================
console.log('✅ [API] Module loaded with full coverage');

/**
 * Internal utility for standardized requests
 */
async function request(url, options = {}) {
    try {
        const res = await fetch(url, options);
        const contentType = res.headers.get("content-type");
        if (contentType && contentType.includes("application/json")) {
            return await res.json();
        }
        return await res.text();
    } catch (error) {
        console.error(`❌ [API] Error fetching ${url}:`, error);
        throw error;
    }
}

export const API = {
    // --- Configuration & Language ---
    config: {
        get: () => request('/api/config', { cache: 'no-store' }),
        update: (data) => request('/api/config/update', { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify(data) 
        }),
        setLanguage: (lang) => request('/api/set_language', { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify({ lang }) 
        })
    },

    // --- System Status & Modes ---
    system: {
        getStatus: () => request('/api/status', { cache: 'no-store' }),
        toggleFocus: (active) => request('/api/modo/foco', { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify({ ativo: active })  // Backend still expects 'ativo'
        }),
        toggleDND: (active) => request('/api/modo/nao_perturbe', { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify({ ativo: active })  // Backend still expects 'ativo'
        })
    },

    // --- Persona & Identity ---
    persona: {
        get: () => request('/api/persona', { cache: 'no-store' }),
        update: (data) => request('/api/persona/update', { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify(data) 
        })
    },

    // --- Specialist Models (LLMs) ---
    models: {
        getLocal: (mode) => request(`/api/local_models?modo=${mode}`),  // Backend still expects 'modo'
        getOpenRouter: () => request('/api/openrouter_models'),
        getGroq: () => request('/api/groq_models')
    },

    // --- Chat, Messaging & Voice ---
    // NOTE: Endpoints will be renamed when webui.py is standardized
    // batepapo -> chat, historico -> history, limpar_historico -> clear_history, enviar -> send
    chat: {
        getModeStatus: () => request('/api/batepapo/status'),
        toggleMode: () => request('/api/batepapo/toggle', { method: 'POST' }),
        getHistory: () => request('/api/historico', { cache: 'no-store' }),
        clearHistory: () => request('/api/limpar_historico', { method: 'POST' }),
        send: (text, files) => request('/api/enviar', { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify({ texto: text, arquivos: files })  // files: [{url, type, name}]
        }),
        uploadFile: (formData) => request('/api/upload', { 
            method: 'POST', 
            body: formData 
        })
    },

    // --- Semantic Memory (RAG) ---
    memory: {
        getAll: () => request('/api/memories'),
        delete: (id) => request(`/api/memories/${id}`, { method: 'DELETE' }),
        deleteAll: () => request('/api/memories', { method: 'DELETE' })
    },

    // --- Roleplay System ---
    roleplay: {
        getAll: () => request('/api/roleplay'),
        save: (data) => request('/api/roleplay/save', { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify(data) 
        }),
        activate: (id) => request('/api/roleplay/activate', { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify({ id }) 
        }),
        deactivate: () => request('/api/roleplay/deactivate', { method: 'POST' }),
        delete: (id) => request(`/api/roleplay/delete?id=${id}`, { method: 'POST' })
    },

    // --- Vision Context ---
    vision: {
        getDescription: () => request('/api/vision_description', { cache: 'no-store' })
    },

    // --- MCP Tools & Plugins ---
    plugins: {
        getGlobals: () => request('/api/mcp_tools?type=global'),
        getOne: (name) => request(`/api/mcp_tools/get?nome=${name}`),  // Backend still expects 'nome'
        save: (data) => request('/api/mcp_tools/save', { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify(data) 
        }),
        delete: (name) => request(`/api/mcp_tools/delete?nome=${name}`, { method: 'POST' })  // Backend still expects 'nome'
    },

    // --- Masters System ---
    masters: {
        getAvailable: () => request('/api/masters/list'),
        getTools: (masterName) => request(`/api/masters/${masterName}/tools`),
        saveTool: (masterName, data) => request(`/api/masters/${masterName}/tools/save`, { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify(data) 
        }),
        deleteTool: (masterName, toolName) => request(`/api/masters/${masterName}/tools/${toolName}`, { method: 'DELETE' })
    },

    // --- Store Integration ---
    store: {
        getItems: () => request('/api/store/items'),
        installPlugin: (id) => request(`/api/store/install/plugin/${id}`, { method: 'POST' }),
        installMaster: (id) => request(`/api/store/install/master/${id}`, { method: 'POST' }),
        uninstallPlugin: (name) => request(`/api/store/uninstall/plugin/${name}`, { method: 'DELETE' }),
        uninstallMaster: (id) => request(`/api/store/uninstall/master/${id}`, { method: 'DELETE' }),
        submit: (data) => request('/api/store/submit', { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify(data) 
        })
    }
};
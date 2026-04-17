// ==========================================
// MAESTRO MODULE - Optimized Performance
// ==========================================
import { API } from './api.js';
import * as UI from './ui.js';
import * as Chat from './chat.js';
import * as Settings from './settings.js';
import * as Persona from './persona.js';
import * as Memory from './memory.js';
import * as Plugins from './plugins.js';
import * as Tools from './tools.js';

console.log('✅ [MAIN] Maestro orchestrating modules (Performance Mode)');

// ==========================================
// GLOBAL BRIDGE - Minimal exposure for onclick handlers
// ==========================================

// UI Module bindings
window.showPanel = UI.showPanel;
window.toggleSidebar = UI.toggleSidebar;
window.toggleEye = UI.toggleEye;
window.fecharModal = UI.fecharModal;

// Chat Module bindings  
window.enviarMensagem = Chat.sendMessage;
window.toggleGravacao = Chat.toggleRecording;
window.arquivosSelecionados = (inputElement) => {
    Array.from(inputElement.files).forEach(file => Chat.addPendingFile(file));
    inputElement.value = '';
};
window.limparChat = async () => {
    if (confirm(window._('confirm.clear'))) {
        await API.chat.clearHistory();
        const chatBox = document.getElementById('chat-messages');
        if (chatBox) chatBox.innerHTML = '';
    }
};

// Settings Module bindings
window.verificarMotor = Settings.verifyEngine;

// Plugins Module - Namespace pattern
window.plugins = {
    load: Plugins.loadPlugins,
    editPlugin: Plugins.editPlugin,
    deletePlugin: Plugins.deletePlugin,
    saveEdit: Plugins.saveEdit,
    savePluginVisual: Plugins.savePluginVisual,
    addParamRowVisual: Plugins.addParamRowVisual,
    addParamRowEdit: Plugins.addParamRowEdit
};
Plugins.loadPlugins();

// Backwards compatibility bindings
window.carregarPlugins = Plugins.loadPlugins;
window.abrirEditor = Plugins.editPlugin;
window.salvarEdicao = Plugins.saveEdit;
window.salvarPluginVisual = Plugins.savePluginVisual;
window.deletarPlugin = Plugins.deletePlugin;
window.adicionarParametroVisual = Plugins.addParamRowVisual;
window.adicionarParametroEdicao = Plugins.addParamRowEdit;

// Tools Module - Namespace pattern
window.tools = {
    loadMasterTools: Tools.loadMasterTools,
    editMasterTool: Tools.editMasterTool,
    saveMasterTool: Tools.saveMasterTool,
    deleteMasterTool: Tools.deleteMasterTool
};

// Backwards compatibility bindings
window.carregarToolsDeMaster = Tools.loadMasterTools;
window.abrirEditorToolMaster = Tools.editMasterTool;
window.salvarToolMaster = Tools.saveMasterTool;
window.deletarToolMaster = Tools.deleteMasterTool;

// Persona Module - Namespace pattern
window.persona = {
    loadRoleplays: Persona.loadRoleplays,
    saveRoleplay: Persona.saveRoleplay,
    activateRoleplay: Persona.activateRoleplay,
    deactivateRoleplay: Persona.deactivateRoleplay,
    deleteRoleplay: Persona.deleteRoleplay,
    loadPlugins: Persona.loadPlugins
};

// Direct bindings
window.salvarRoleplay = Persona.saveRoleplay;
window.desativarRoleplay = Persona.deactivateRoleplay;

// Memory Module - Namespace pattern
window.memory = {
    loadMemories: Memory.loadMemories,
    filterMemories: Memory.filterMemories,
    deleteMemory: Memory.deleteMemory,
    deleteAllMemories: Memory.deleteAllMemories,
    updateVisualContext: Memory.updateVisualContext
};

window.filtrarMemorias = Memory.filterMemories;
window.apagarTodasMemorias = Memory.deleteAllMemories;

// ==========================================
// GLOBAL STATE VARIABLES
// ==========================================

/** @type {boolean} Focus mode state */
window._modoFoco = false;

/** @type {boolean} Do Not Disturb mode state */
window._modoDND = false;

/** @type {string} Current AI name displayed in UI */
window.nomeIA = "Assistant";

// ==========================================
// SYSTEM FUNCTIONS
// ==========================================

window.toggleModo = async (modeType) => {
    if (modeType === 'foco') {
        window._modoFoco = !window._modoFoco;
    } else {
        window._modoDND = !window._modoDND;
    }
    
    UI.atualizarModeUI(window._modoFoco, window._modoDND);
    
    if (modeType === 'foco') {
        await API.system.toggleFocus(window._modoFoco);
    } else {
        await API.system.toggleDND(window._modoDND);
    }
};

window.toggleBatepapo = async function() {
    try {
        const response = await API.chat.toggleMode();
        const chatButton = document.getElementById('btn-batepapo');
        if (!chatButton) return;
        
        if (response.ativo) {
            chatButton.innerHTML = `<span style="color:#22c55e">✓</span> ${window._('chat.mode_on')}`;
            chatButton.style.background = 'rgba(34, 197, 94, 0.1)';
            chatButton.style.borderColor = '#22c55e';
            UI.showToast(window._('chat.mode_toast'));
        } else {
            chatButton.innerHTML = window._('chat.mode_off');
            chatButton.style.background = '';
            chatButton.style.borderColor = 'var(--border2)';
        }
    } catch (error) {
        console.error('Error toggling chat mode:', error);
    }
};

window.trocarIdioma = async function(languageCode) {
    window._currentLang = languageCode;
    if (typeof window.applyLangToUI === 'function') window.applyLangToUI();
    if (typeof renderStore === 'function') renderStore();
    
    const config = await API.config.get();
    config.ui_language = languageCode;
    await API.config.update(config);
};

// ==========================================
// SKILLS MANAGEMENT
// ==========================================

window.adicionarSkill = function() {
    const skillName = prompt('Skill name:');
    if (!skillName) return;
    const skillDescription = prompt('Description:');
    
    Persona.currentSkills.push({ 
        name: skillName, 
        description: skillDescription || '' 
    });
    renderizarSkills();
};

window.apagarSkill = function(skillIndex) {
    if (!confirm('Remove this skill?')) return;
    Persona.currentSkills.splice(skillIndex, 1);
    renderizarSkills();
};

function renderizarSkills() {
    const skillsContainer = document.getElementById('skills-container');
    if (!skillsContainer) return;
    
    if (Persona.currentSkills.length === 0) {
        skillsContainer.innerHTML = `<p style="color:var(--muted);font-size:13px">${window._('persona.no_skills')}</p>`;
        return;
    }
    
    skillsContainer.innerHTML = Persona.currentSkills.map((skill, index) => `
        <div class="list-item">
            <div class="list-item-body">
                <div class="list-item-title">${skill.name || 'Unnamed'}</div>
                <div class="list-item-sub">${skill.description || ''}</div>
            </div>
            <button class="btn-sm btn-sm-del" onclick="apagarSkill(${index})">✕</button>
        </div>
    `).join('');
}

// ==========================================
// SAVE ALL SETTINGS
// ==========================================

window.salvarTudo = async function() {
    const saveButton = document.querySelector('.btn-save-all');
    if (saveButton) { 
        saveButton.textContent = window._('ui.save_working'); 
        saveButton.disabled = true; 
    }
    
    try {
        const providerSelect = document.getElementById('modo_ia');
        const provider = providerSelect.value;
        
        const currentProfile = {
            modelo_principal: document.getElementById('modelo_principal').value,
            modelo_visao:     document.getElementById('modelo_visao').value,
            modelo_codigo:    document.getElementById('modelo_codigo').value,
            modelo_roleplay:  document.getElementById('modelo_roleplay').value
        };
        Settings.savedModelPreferences[provider] = currentProfile; // Corrigido

        const currentConfig = await API.config.get();
        const updatedConfig = {
            ...currentConfig,
            ui_language: document.getElementById('ui_language').value,
            modo_ia: provider,
            modelo_ia_local: document.getElementById('modelo_ia_local')?.value || null,
            modelos: Settings.savedModelPreferences, // Corrigido
            api_keys: {
                openrouter: document.getElementById('api_openrouter').value,
                groq:       document.getElementById('api_groq').value,
                openai:     document.getElementById('api_openai').value,
                elevenlabs: document.getElementById('api_elevenlabs').value,
                huggingface: document.getElementById('api_huggingface').value,
            },
            audio: {
                metodo_escuta: document.getElementById('audio_metodo_escuta').value,
                motor_transcricao: document.getElementById('audio_motor_transcricao').value,
                whisper_modelo: document.getElementById('audio_whisper_modelo').value,
                motor_voz: document.getElementById('audio_motor_voz').value,
                voz_edge: document.getElementById('audio_voz_edge').value,
            },
            sistema: {
                humor: document.getElementById('humor_ia').value,
                watchdog_ativo: document.getElementById('watchdog_ativo').checked,
                watchdog_intervalo: parseInt(document.getElementById('watchdog_intervalo').value) || 10,
                vision_bg_ativo: document.getElementById('vision_bg_ativo').checked,
                lipsync_ativo: document.getElementById('lipsync_ativo').checked,
                modo_foco: window._modoFoco,
                modo_nao_perturbe: window._modoDND,
            }
        };

        await API.config.update(updatedConfig);
        await API.persona.update({
            nome: document.getElementById('nome_ia').value,
            prompt_sistema: document.getElementById('prompt_sistema').value.split('\n'),
            skills: Persona.currentSkills
        });

        if (saveButton) { 
            saveButton.textContent = window._('ui.save_done'); 
            setTimeout(() => { 
                saveButton.textContent = window._('sys.save'); 
                saveButton.disabled = false; 
            }, 2000); 
        }
        UI.showToast(window._('ui.toast_saved'));
    } catch (error) {
        console.error('❌ Error saving settings:', error);
        UI.showToast(window._('ui.toast_error'), true);
        if (saveButton) {
            saveButton.textContent = window._('sys.save');
            saveButton.disabled = false;
        }
    }
};

// ==========================================
// INITIALIZATION
// ==========================================

async function initCritical(config, persona) {
    console.log('⚡ [INIT] Phase 1: Critical data');
    
    window._currentLang = config.ui_language || 'en';
    const languageSelect = document.getElementById('ui_language');
    if (languageSelect) languageSelect.value = config.ui_language || 'en';
    if (typeof window.applyLangToUI === 'function') window.applyLangToUI();

    window.nomeIA = persona.nome || "Assistant";
    Persona.updateIdentityUI(window.nomeIA);
    
    if (typeof window.updateBootCache === 'function') {
        window.updateBootCache(config, persona);
    }
}

async function initUI(config, persona) {
    console.log('⚡ [INIT] Phase 2: UI sync');
    
    const promptElement = document.getElementById('prompt_sistema');
    if (promptElement) {
        promptElement.value = Array.isArray(persona.prompt_sistema) 
            ? persona.prompt_sistema.join('\n') 
            : (persona.prompt_sistema || '');
    }
    
    Persona.setSkills(persona.skills);
    renderizarSkills();

    Settings.setModelPreferences(config.modelos);
    const provider = config.modo_ia || 'groq';
    const profile = config.modelos?.[provider] || {};
    
    const modelFields = ['modelo_principal', 'modelo_visao', 'modelo_codigo', 'modelo_roleplay'];
    modelFields.forEach(fieldId => {
        const element = document.getElementById(fieldId);
        if (element) element.setAttribute('data-salvo', profile[fieldId] || '');
    });

    const engineSelect = document.getElementById('modo_ia');
    if (engineSelect) {
        engineSelect.value = provider;
        Settings.verifyEngine();
    }

    if (config.api_keys) {
        const apiKeys = config.api_keys;
        document.getElementById('api_openrouter').value = apiKeys.openrouter || '';
        document.getElementById('api_groq').value = apiKeys.groq || '';
        document.getElementById('api_openai').value = apiKeys.openai || '';
        document.getElementById('api_elevenlabs').value = apiKeys.elevenlabs || '';
        document.getElementById('api_huggingface').value = apiKeys.huggingface || '';
    }

    if (config.audio) {
        const audioConfig = config.audio;
        const setIfExists = (elementId, value) => {
            const element = document.getElementById(elementId);
            if (element) element.value = value;
        };
        setIfExists('audio_metodo_escuta', audioConfig.metodo_escuta || 'button');
        setIfExists('audio_motor_transcricao', audioConfig.motor_transcricao || 'browser');
        setIfExists('audio_whisper_modelo', audioConfig.whisper_modelo || 'base');
        setIfExists('audio_motor_voz', audioConfig.motor_voz || 'edge');
        setIfExists('audio_voz_edge', audioConfig.voz_edge || 'en-US-AriaNeural');
    }

    if (config.sistema) {
        const systemConfig = config.sistema;
        const setIfExists = (elementId, value, isCheckbox = false) => {
            const element = document.getElementById(elementId);
            if (element) {
                if (isCheckbox) element.checked = value;
                else element.value = value;
            }
        };
        setIfExists('humor_ia', systemConfig.humor || '');
        setIfExists('watchdog_ativo', systemConfig.watchdog_ativo || false, true);
        setIfExists('watchdog_intervalo', systemConfig.watchdog_intervalo || 10);
        setIfExists('vision_bg_ativo', systemConfig.vision_bg_ativo || false, true);
        setIfExists('lipsync_ativo', systemConfig.lipsync_ativo || false, true);
        
        window._modoFoco = systemConfig.modo_foco || false;
        window._modoDND = systemConfig.modo_nao_perturbe || false;
        UI.atualizarModeUI(window._modoFoco, window._modoDND);
    }
}

async function initBackground() {
    console.log('⚡ [INIT] Phase 3: Background services');
    Memory.startVisionPolling();
    UI.iniciarPollingStatus(API.system.getStatus);
}

async function initHeavyData() {
    console.log('⚡ [INIT] Phase 4: Heavy data (deferred)');
    
    try {
        const chatModeStatus = await API.chat.getModeStatus();
        const chatButton = document.getElementById('btn-batepapo');
        if (chatButton && chatModeStatus) {
            if (chatModeStatus.ativo) {
                chatButton.innerHTML = `<span style="color:#22c55e">✓</span> ${window._('chat.mode_on')}`;
                chatButton.style.background = 'rgba(34, 197, 94, 0.1)';
                chatButton.style.borderColor = '#22c55e';
            } else {
                chatButton.innerHTML = window._('chat.mode_off');
            }
        }
    } catch (error) {
        console.warn('Chat mode status error:', error);
    }
    
    try {
        const history = await API.chat.getHistory();
        const chatBox = document.getElementById('chat-messages');
        if (chatBox && history) {
            chatBox.innerHTML = '';
            const filteredMessages = history.filter(message => message.role !== 'system');
            const CHUNK_SIZE = 10;
            for (let i = 0; i < filteredMessages.length; i += CHUNK_SIZE) {
                const messageChunk = filteredMessages.slice(i, i + CHUNK_SIZE);
                messageChunk.forEach(message => Chat.addMessage(message.role, message.content));
                if (i + CHUNK_SIZE < filteredMessages.length) {
                    await new Promise(resolve => setTimeout(resolve, 0));
                }
            }
        }
    } catch (error) {
        console.warn('History load error:', error);
    }
}

async function init() {
    const startTime = performance.now();
    try {
        const [config, persona] = await Promise.all([
            API.config.get(),
            API.persona.get()
        ]);
        
        await initCritical(config, persona);
        console.log(`⚡ Phase 1 complete: ${(performance.now() - startTime).toFixed(0)}ms`);
        
        await initUI(config, persona);
        console.log(`⚡ Phase 2 complete: ${(performance.now() - startTime).toFixed(0)}ms`);
        
        initBackground();
        setTimeout(() => initHeavyData(), 100);
        
        console.log(`✅ [INIT] Core ready in ${(performance.now() - startTime).toFixed(0)}ms`);
    } catch (error) {
        console.error('❌ [INIT] Critical failure:', error);
    }
}

document.addEventListener('panel-changed', (event) => {
    const panelName = event.detail.panelName;
    switch (panelName) {
        case 'roleplay': Persona.loadRoleplays(); break;
        case 'memorias': Memory.loadMemories(); break;
        case 'visao': Memory.updateVisualContext(); break;
        case 'plugins': Plugins.loadPlugins(); break;
    }
});

window.addEventListener('DOMContentLoaded', init);
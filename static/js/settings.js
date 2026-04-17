// ==========================================
// SETTINGS MODULE - Provider and Model Management
// ==========================================
import { API } from './api.js';

console.log('✅ [SETTINGS] Module loaded successfully');

// ==========================================
// INTERNAL STATE
// ==========================================

/** @type {Object} Cached model preferences per provider */
export let savedModelPreferences = {};

/** @type {string|null} Last selected provider for change detection */
let lastProvider = null;

// ==========================================
// MODEL DROPDOWN POPULATION
// ==========================================

/**
 * Populate specialist dropdowns with available models for the current provider
 * @param {Array<Object>} models - List of model objects {id, name}
 * @returns {void}
 */
export function populateSpecialistDropdowns(models) {
    const specialistSelectIds = [
        'modelo_principal',
        'modelo_visao',
        'modelo_codigo',
        'modelo_roleplay'
    ];

    specialistSelectIds.forEach(selectId => {
        const selectElement = document.getElementById(selectId);
        if (!selectElement) return;

        const savedValue = selectElement.getAttribute('data-salvo');

        selectElement.innerHTML = models
            .map(model => `<option value="${model.id}">${escapeHtml(model.name)}</option>`)
            .join('');

        if (savedValue && Array.from(selectElement.options).some(option => option.value === savedValue)) {
            selectElement.value = savedValue;
        }
    });
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ==========================================
// PROVIDER SWITCHING AND MODEL LOADING
// ==========================================

export async function verifyEngine() {
    const providerSelect = document.getElementById('modo_ia');
    const currentProvider = providerSelect.value;

    const specialistsBlock = document.getElementById('bloco_especialistas');
    const localModelBlock = document.getElementById('bloco_modelo_local');

    if (lastProvider && lastProvider !== currentProvider) {
        savedModelPreferences[lastProvider] = {
            modelo_principal: document.getElementById('modelo_principal').value,
            modelo_visao: document.getElementById('modelo_visao').value,
            modelo_codigo: document.getElementById('modelo_codigo').value,
            modelo_roleplay: document.getElementById('modelo_roleplay').value
        };
    }
    lastProvider = currentProvider;

    const isLocalProvider = currentProvider === 'local_lm' || currentProvider === 'local_ollama';

    if (localModelBlock) localModelBlock.style.display = isLocalProvider ? 'block' : 'none';
    if (specialistsBlock) specialistsBlock.style.display = isLocalProvider ? 'none' : 'block';

    const profile = savedModelPreferences[currentProvider] || {};
    const modelFieldIds = ['modelo_principal', 'modelo_visao', 'modelo_codigo', 'modelo_roleplay'];
    modelFieldIds.forEach(fieldId => {
        const element = document.getElementById(fieldId);
        if (element) element.setAttribute('data-salvo', profile[fieldId] || '');
    });

    try {
        if (isLocalProvider) {
            await loadLocalModels(currentProvider);
        } else {
            await loadCloudProviderModels(currentProvider);
        }
    } catch (error) {
        console.error('[SETTINGS] Error loading provider models:', error);
    }
}

async function loadCloudProviderModels(provider) {
    switch (provider) {
        case 'openrouter': {
            const models = await API.models.getOpenRouter();
            if (models && models.length) populateSpecialistDropdowns(models);
            break;
        }
        case 'groq': {
            const models = await API.models.getGroq();
            if (models && models.length) populateSpecialistDropdowns(models);
            break;
        }
        case 'openai': {
            const openAIModels = [
                { id: 'gpt-4o', name: 'GPT-4o' },
                { id: 'gpt-4o-mini', name: 'GPT-4o Mini' },
                { id: 'o1-mini', name: 'o1 Mini' },
                { id: 'gpt-4-turbo', name: 'GPT-4 Turbo' }
            ];
            populateSpecialistDropdowns(openAIModels);
            break;
        }
        default:
            console.warn(`[SETTINGS] Unknown cloud provider: ${provider}`);
    }
}

export async function loadLocalModels(providerMode) {
    const localModelSelect = document.getElementById('modelo_ia_local');
    if (!localModelSelect) return;

    const savedValue = localModelSelect.getAttribute('data-salvo') || localModelSelect.value;
    localModelSelect.innerHTML = `<option value="">${window._('sys.local_searching')}</option>`;

    try {
        const models = await API.models.getLocal(providerMode);
        if (models && models.length > 0) {
            localModelSelect.innerHTML = models
                .map(model => `<option value="${model.id}">${escapeHtml(model.name)}</option>`)
                .join('');
            if (savedValue) localModelSelect.value = savedValue;
        } else {
            localModelSelect.innerHTML = `<option value="">${window._('sys.local_none')}</option>`;
        }
    } catch (error) {
        console.error('[SETTINGS] Local model fetch error:', error);
        localModelSelect.innerHTML = `<option value="">${window._('sys.local_error')}</option>`;
    }
}

export function updateTranscriptionUI() {
    const transcriptionEngine = document.getElementById('audio_motor_transcricao')?.value;
    const whisperRow = document.getElementById('row_whisper_model');
    if (whisperRow) {
        const isWhisperSelected = transcriptionEngine === 'whisper' || transcriptionEngine === 'whisper_local';
        whisperRow.style.display = isWhisperSelected ? '' : 'none';
    }
}

export function setModelPreferences(preferences) {
    savedModelPreferences = preferences || {};
}
// ==========================================
// PERSONA MODULE - Identity and Roleplay Management
// ==========================================
import { API } from './api.js';
import { showToast } from './ui.js';

console.log('✅ [PERSONA] Module loaded successfully');

// ==========================================
// INTERNAL STATE
// ==========================================

/** @type {Array<Object>} Current persona skills */
export let currentSkills = [];

/** @type {string} Current AI name displayed in UI */
let aiName = "Assistant";

// ==========================================
// IDENTITY MANAGEMENT
// ==========================================

export function updateIdentityUI(name) {
    aiName = name || _('ai_name_default');

    const nameElementIds = [
        'sidebar-ai-name',
        'topbar-ai-name',
        'chat-ai-name',
        'nome_ia'
    ];

    nameElementIds.forEach(elementId => {
        const element = document.getElementById(elementId);
        if (element) {
            if (element.tagName === 'INPUT') element.value = aiName;
            else element.textContent = aiName;
        }
    });

    document.title = `${aiName} — AI Panel`;
}

export function getAiName() {
    return aiName;
}

// ==========================================
// SKILLS MANAGEMENT
// ==========================================

export function setSkills(skills) {
    currentSkills = skills || [];
}

export function renderSkills() {
    const skillsContainer = document.getElementById('persona-skills-list');
    if (!skillsContainer) return;

    if (currentSkills.length === 0) {
        skillsContainer.innerHTML = `<p class="empty-text">${_('persona.no_skills')}</p>`;
        return;
    }

    skillsContainer.innerHTML = currentSkills.map((skill, index) => `
        <div class="list-item">
            <div class="list-item-body">
                <div class="list-item-title">${escapeHtml(skill.name) || 'Unnamed Skill'}</div>
                <div class="list-item-sub">${escapeHtml(skill.description) || ''}</div>
            </div>
            <div class="list-item-actions">
                <button class="btn-sm" onclick="persona.editSkill(${index})">✏️</button>
                <button class="btn-sm btn-sm-del" onclick="persona.deleteSkill(${index})">✕</button>
            </div>
        </div>
    `).join('');
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ==========================================
// ROLEPLAY SCENARIO MANAGEMENT
// ==========================================

export async function loadRoleplays() {
    const scenarioList = document.getElementById('rp-list');
    if (!scenarioList) return;

    try {
        const scenarios = await API.roleplay.getAll();

        if (!scenarios || scenarios.length === 0) {
            scenarioList.innerHTML = `<div class="empty-state"><div class="es-icon">🎭</div><p>${_('rp.none')}</p></div>`;
            return;
        }

        scenarioList.innerHTML = scenarios.map(scenario => `
            <div class="list-item ${scenario.active ? 'active-scenario' : ''}">
                <div class="list-item-body">
                    <div class="list-item-title">${escapeHtml(scenario.name)} ${scenario.nsfw ? '🔞' : ''}</div>
                    <div class="list-item-sub">${escapeHtml(scenario.scenario.substring(0, 60))}...</div>
                </div>
                <div class="list-item-actions">
                    ${scenario.active
                        ? `<span class="badge badge-success">Active</span>`
                        : `<button class="btn btn-sm btn-primary" onclick="persona.activateRoleplay(${scenario.id})">Play</button>`
                    }
                    <button class="btn btn-sm btn-sm-del" onclick="persona.deleteRoleplay(${scenario.id})">✕</button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('[PERSONA] Failed to load roleplays:', error);
    }
}

export async function activateRoleplay(scenarioId) {
    try {
        const response = await API.roleplay.activate(scenarioId);
        if (response.success) {
            showToast?.('🎭 Roleplay activated!');
            await loadRoleplays();
            // Removida chamada a carregarDados (não definida)
        }
    } catch (error) {
        console.error('[PERSONA] Activation failed:', error);
        showToast?.('Error activating scenario', true);
    }
}

export async function deactivateRoleplay() {
    try {
        const response = await API.roleplay.deactivate();
        if (response.success) {
            showToast?.('🛑 Roleplay deactivated');
            await loadRoleplays();
            // Removida chamada a carregarDados (não definida)
        }
    } catch (error) {
        console.error('[PERSONA] Deactivation failed:', error);
    }
}

export async function saveRoleplay() {
    const scenarioData = {
        name: document.getElementById('rp_nome').value,
        ai_persona: document.getElementById('rp_persona_ia').value,
        user_persona: document.getElementById('rp_persona_usuario').value,
        scenario: document.getElementById('rp_cenario').value,
        nsfw: document.getElementById('rp_nsfw').checked ? 1 : 0
    };

    if (!scenarioData.name || !scenarioData.ai_persona) {
        showToast?.(_('store.fill_required'), true);
        return;
    }

    try {
        const response = await API.roleplay.save(scenarioData);
        if (response.success) {
            showToast?.('💾 Scenario saved!');
            const formFieldIds = ['rp_nome', 'rp_persona_ia', 'rp_persona_usuario', 'rp_cenario'];
            formFieldIds.forEach(fieldId => {
                const element = document.getElementById(fieldId);
                if (element) element.value = '';
            });
            const nsfwCheckbox = document.getElementById('rp_nsfw');
            if (nsfwCheckbox) nsfwCheckbox.checked = false;
            await loadRoleplays();
        }
    } catch (error) {
        console.error('[PERSONA] Save failed:', error);
        showToast?.('Error saving scenario', true);
    }
}

export async function deleteRoleplay(scenarioId) {
    if (!confirm(_('rp.confirm_del'))) return;
    try {
        const response = await API.roleplay.delete(scenarioId);
        if (response.success) await loadRoleplays();
    } catch (error) {
        console.error('[PERSONA] Deletion failed:', error);
    }
}

// ==========================================
// PLUGIN MANAGEMENT (MCP)
// ==========================================

export async function loadPlugins() {
    const pluginList = document.getElementById('mcp-list');
    if (!pluginList) return;

    try {
        const plugins = await API.plugins.getGlobals();

        if (!plugins || plugins.length === 0) {
            pluginList.innerHTML = `<div class="empty-state"><div class="es-icon">🔌</div><p>${_('plugins.empty')}</p></div>`;
            return;
        }

        pluginList.innerHTML = plugins.map(plugin => `
            <div class="list-item">
                <div class="list-item-body">
                    <div class="list-item-title">🔧 ${escapeHtml(plugin.nome)}</div>
                    <div class="list-item-sub">${escapeHtml(plugin.descricao)}</div>
                </div>
                <div class="list-item-actions">
                    <button class="btn-sm" onclick="persona.editPlugin('${escapeHtml(plugin.nome)}')">✏️</button>
                    <button class="btn-sm btn-sm-del" onclick="persona.deletePlugin('${escapeHtml(plugin.nome)}')">🗑</button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('[PERSONA] Error loading plugins:', error);
    }
}
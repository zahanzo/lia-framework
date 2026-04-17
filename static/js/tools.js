// ==========================================
// TOOLS MODULE - Master Tools Management
// ==========================================
import { API } from './api.js';

console.log('✅ [TOOLS] Module loaded successfully');

// ==========================================
// TOOL DISPLAY
// ==========================================

/**
 * Load and display tools for a specific master
 * @param {string} masterName - Name of the master
 * @returns {Promise<void>}
 */
export async function loadMasterTools(masterName) {
    const tools = await API.masters.getTools(masterName);
    const container = document.getElementById('master-tools-list');

    if (!container) return;

    // Empty state
    if (!tools || tools.length === 0) {
        container.innerHTML = `<div class="empty-state-mini">📦 No tools added yet</div>`;
        return;
    }

    // Build tools list HTML
    container.innerHTML = tools.map(tool => `
        <div class="master-tool-item">
            <div class="tool-info">
                <strong>${escapeHtml(tool.nome)}</strong>
                <span class="tool-desc">${escapeHtml(tool.descricao) || 'No description'}</span>
            </div>
            <div class="tool-actions">
                <button class="btn-xs btn-edit" onclick="tools.editMasterTool('${escapeHtml(masterName)}', '${escapeHtml(tool.nome)}')">✏️</button>
                <button class="btn-xs btn-del" onclick="tools.deleteMasterTool('${escapeHtml(masterName)}', '${escapeHtml(tool.nome)}')">🗑</button>
            </div>
        </div>
    `).join('');
}

/**
 * Escape HTML special characters to prevent XSS
 * @param {string} text - Raw text to escape
 * @returns {string} Escaped HTML-safe string
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ==========================================
// TOOL EDITING
// ==========================================

/**
 * Open editor modal for a master tool (create or edit)
 * @param {string} masterName - Name of the master
 * @param {string|null} toolName - Name of tool to edit, or null for new tool
 * @returns {Promise<void>}
 */
export async function editMasterTool(masterName, toolName = null) {
    const modal = document.getElementById('modal-tool-master');
    if (!modal) return;

    // Set hidden fields
    document.getElementById('tool-master-name-input').value = masterName;
    document.getElementById('tool-master-creating').value = toolName ? '0' : '1';

    if (toolName) {
        // Edit existing tool
        const tools = await API.masters.getTools(masterName);
        const tool = tools.find(t => t.nome === toolName);

        if (!tool) return;

        document.getElementById('tool_nome').value = tool.nome;
        document.getElementById('tool_desc').value = tool.descricao;
        document.getElementById('tool_schema').value = tool.schema;
        document.getElementById('tool_codigo').value = tool.codigo;
        document.getElementById('tool_pip').value = tool.pip_requirements || '';
        document.getElementById('tool_nome').disabled = true;
    } else {
        // Create new tool
        document.getElementById('tool_nome').value = '';
        document.getElementById('tool_desc').value = '';
        document.getElementById('tool_schema').value = '{}';
        document.getElementById('tool_codigo').value = '';
        document.getElementById('tool_pip').value = '';
        document.getElementById('tool_nome').disabled = false;
    }

    modal.classList.add('open');
}

/**
 * Save a master tool (create or update)
 * @returns {Promise<void>}
 */
export async function saveMasterTool() {
    const masterName = document.getElementById('tool-master-name-input').value;

    const toolData = {
        nome: document.getElementById('tool_nome').value.trim(),
        descricao: document.getElementById('tool_desc').value.trim(),
        schema_json: document.getElementById('tool_schema').value.trim(),
        codigo: document.getElementById('tool_codigo').value.trim(),
        pip_requirements: document.getElementById('tool_pip').value.trim()
    };

    // Validation
    if (!toolData.nome) {
        alert('Tool name is required!');
        return;
    }

    await API.masters.saveTool(masterName, toolData);

    document.getElementById('modal-tool-master').classList.remove('open');
    await loadMasterTools(masterName);
}

// ==========================================
// TOOL DELETION
// ==========================================

/**
 * Delete a master tool after confirmation
 * @param {string} masterName - Name of the master
 * @param {string} toolName - Name of tool to delete
 * @returns {Promise<void>}
 */
export async function deleteMasterTool(masterName, toolName) {
    if (!confirm(`Delete tool "${toolName}"?`)) return;

    await API.masters.deleteTool(masterName, toolName);
    await loadMasterTools(masterName);
}
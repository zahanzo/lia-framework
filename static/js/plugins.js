// ==========================================
// PLUGINS MODULE - MCP Tools Management
// ==========================================
import { API } from './api.js';
import { showToast } from './ui.js';

console.log('✅ [PLUGINS] Module loaded successfully');

// ==========================================
// LANGUAGE HELPER
// ==========================================

/**
 * Get current language code
 * @returns {string} Language code ('pt' or 'en')
 */
function getCurrentLanguage() {
    // Tentar múltiplas fontes
    const lang = window._currentLang || window.currentLang || _currentLang || 'pt';
    console.log('[PLUGINS] Current language:', lang);
    return lang;
}

// ==========================================
// PLUGIN DISPLAY
// ==========================================

/**
 * Load and display all installed MCP plugins in the UI
 * @returns {Promise<void>}
 */
export async function loadPlugins() {
    console.log('[PLUGINS] Loading plugins...');
    
    const pluginList = await API.plugins.getGlobals();
    const container = document.getElementById('mcp-list');

    if (!container) {
        console.error('[PLUGINS] Container #mcp-list not found!');
        return;
    }

    // Renderização da lista (vazia ou preenchida)
    if (!pluginList || pluginList.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="es-icon">🔌</div>
                <p>${window._('plugins.empty')}</p>
            </div>
        `;
    } else {
        const language = getCurrentLanguage();
        container.innerHTML = pluginList.map(plugin => {
            const displayName = language === 'pt' && plugin.nome_pt 
                ? plugin.nome_pt 
                : plugin.nome || plugin.name;
            
            const displayDescription = language === 'pt' && plugin.descricao_pt 
                ? plugin.descricao_pt 
                : plugin.descricao || plugin.description;

            return `
                <div class="list-item" data-plugin-name="${escapeHtml(plugin.nome || plugin.name)}">
                    <div class="list-item-body">
                        <div class="list-item-title">🔧 ${escapeHtml(displayName)}</div>
                        <div class="list-item-sub">${escapeHtml(displayDescription)}</div>
                    </div>
                    <div class="list-item-actions">
                        <button class="btn-sm btn-edit" data-action="edit">✏️</button>
                        <button class="btn-sm btn-sm-del" data-action="delete">🗑</button>
                    </div>
                </div>
            `;
        }).join('');
    }

    // Remove listener antigo (se existir) para não acumular
    if (container._clickHandler) {
        container.removeEventListener('click', container._clickHandler);
    }

    // Novo listener com delegação de eventos
    const clickHandler = (e) => {
        const button = e.target.closest('button');
        if (!button) return;
        
        const listItem = button.closest('.list-item');
        if (!listItem) return;
        
        const pluginName = listItem.dataset.pluginName;
        const action = button.dataset.action;
        
        if (action === 'edit') {
            editPlugin(pluginName);
        } else if (action === 'delete') {
            deletePlugin(pluginName);
        }
    };

    container.addEventListener('click', clickHandler);
    container._clickHandler = clickHandler; // guarda referência para remoção futura
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
// PLUGIN EDITING
// ==========================================

/**
 * Open editor modal for an existing plugin
 * @param {string} pluginName - Name/ID of the plugin to edit
 * @returns {Promise<void>}
 */
export async function editPlugin(pluginName) {
    console.log('✏️ editPlugin chamado com:', pluginName);
    
    const response = await fetch(`/api/mcp_tools/get?name=${encodeURIComponent(pluginName)}`);
    if (!response.ok) {
        console.error('Erro ao buscar plugin:', response.status);
        showToast('Plugin não encontrado ou erro na API.', true);
        return;
    }
    
    const data = await response.json();
    if (data.error) {
        console.error('Erro retornado pela API:', data.error);
        showToast('Plugin não encontrado.', true);
        return;
    }
    
    // Preenche os campos com os nomes corretos retornados pela API
    document.getElementById('edit_nome').value = data.nome || pluginName;
    document.getElementById('edit_desc').value = data.descricao || '';
    document.getElementById('edit_codigo').value = data.codigo || '';
    document.getElementById('edit_pip').value = data.pip_requirements || '';

    // Schema (a API retorna como "schema", não "schema_json")
    const schema = typeof data.schema === 'string' ? JSON.parse(data.schema) : data.schema;

    const paramsContainer = document.getElementById('edit-params-container');
    paramsContainer.innerHTML = '';

    if (schema && schema.properties) {
        Object.entries(schema.properties).forEach(([paramName, paramDef]) => {
            const isRequired = schema.required && schema.required.includes(paramName);
            addParamRowEdit(
                paramName,
                paramDef.type || 'string',
                paramDef.description || '',
                isRequired
            );
        });
    }

    document.getElementById('modal-editar').classList.add('open');
}

/**
 * Save edited plugin changes
 * @returns {Promise<void>}
 */
export async function saveEdit() {
    const schema = buildSchemaFromContainer('edit-params-container');

    await fetch('/api/mcp_tools/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            nome: document.getElementById('edit_nome').value,
            descricao: document.getElementById('edit_desc').value,
            codigo_python: document.getElementById('edit_codigo').value,
            pip_requirements: document.getElementById('edit_pip').value,
            schema_json: JSON.stringify(schema)
        })
    });

    document.getElementById('modal-editar').classList.remove('open');
    await loadPlugins();
    
}

// ==========================================
// PLUGIN CREATION
// ==========================================

/**
 * Save new plugin from the visual creation form
 * @returns {Promise<void>}
 */
export async function savePluginVisual() {
    const pluginName = document.getElementById('mcp_nome').value.trim();

    if (!pluginName) {
        alert('Plugin name is required');
        return;
    }

    const schema = buildSchemaFromContainer('mcp-params-container');

    await fetch('/api/mcp_tools/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            nome: pluginName,
            descricao: document.getElementById('mcp_desc').value,
            schema_json: JSON.stringify(schema),
            codigo_python: document.getElementById('mcp_codigo').value,
            pip_requirements: document.getElementById('mcp_pip').value
        })
    });

    // Reset form fields
    document.getElementById('mcp_nome').value = '';
    document.getElementById('mcp_desc').value = '';
    document.getElementById('mcp_pip').value = '';
    document.getElementById('mcp-params-container').innerHTML = '';
    document.getElementById('mcp_codigo').value = 'resposta_ia = "Action executed successfully!"';

    await loadPlugins();
}

// ==========================================
// PLUGIN DELETION
// ==========================================

/**
 * Delete a plugin after confirmation
 * @param {string} pluginName - Name/ID of the plugin to delete
 * @returns {Promise<void>}
 */
export async function deletePlugin(pluginName) {
    console.log('🗑 deletePlugin chamado com:', pluginName);
    if (!confirm(`Delete plugin "${pluginName}"?`)) return;

    await API.plugins.delete(pluginName);
    await loadPlugins();
}

// ==========================================
// PARAMETER ROW MANAGEMENT
// ==========================================

/**
 * Add a new parameter row to the visual creation form
 * @returns {void}
 */
export function addParamRowVisual() {
    createParameterRow('', 'string', '', true, 'mcp-params-container');
}

/**
 * Add a parameter row to the edit modal
 * @param {string} paramName - Parameter name
 * @param {string} paramType - Parameter type (string/number/boolean)
 * @param {string} paramDescription - Parameter description
 * @param {boolean} isRequired - Whether the parameter is required
 * @returns {void}
 */
export function addParamRowEdit(paramName = '', paramType = 'string', paramDescription = '', isRequired = true) {
    createParameterRow(paramName, paramType, paramDescription, isRequired, 'edit-params-container');
}

/**
 * Internal function to create a parameter row HTML element
 * @param {string} paramName - Parameter name
 * @param {string} paramType - Parameter type
 * @param {string} paramDescription - Parameter description
 * @param {boolean} isRequired - Whether required
 * @param {string} containerId - ID of container element
 * @returns {void}
 */
function createParameterRow(paramName = '', paramType = 'string', paramDescription = '', isRequired = true, containerId = 'mcp-params-container') {
    const rowId = `param-row-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

    const typeOptions = [
        { value: 'string', label: 'Text' },
        { value: 'number', label: 'Number' },
        { value: 'boolean', label: 'Yes/No' }
    ];

    const typeSelectHtml = typeOptions.map(option => `
        <option value="${option.value}" ${paramType === option.value ? 'selected' : ''}>
            ${option.label}
        </option>
    `).join('');

    const rowHtml = `
        <div class="param-row" id="${rowId}">
            <input class="form-input param-nome" placeholder="Name" value="${escapeHtml(paramName)}">
            <select class="form-select param-tipo">
                ${typeSelectHtml}
            </select>
            <input class="form-input param-desc" placeholder="Description" value="${escapeHtml(paramDescription)}" style="flex:1.5">
            <label style="font-size:11px;color:var(--muted);white-space:nowrap">
                <input type="checkbox" class="param-req" ${isRequired ? 'checked' : ''}> Req
            </label>
            <button class="btn-rm" onclick="document.getElementById('${rowId}').remove()">✕</button>
        </div>
    `;

    document.getElementById(containerId).insertAdjacentHTML('beforeend', rowHtml);
}

/**
 * Build JSON schema object from parameter rows in a container
 * @param {string} containerId - ID of the container element
 * @returns {Object} JSON schema object
 */
function buildSchemaFromContainer(containerId) {
    const schema = {
        type: 'object',
        properties: {},
        required: []
    };

    const container = document.getElementById(containerId);
    if (!container) return schema;

    const rows = container.querySelectorAll('.param-row');

    rows.forEach(row => {
        const nameInput = row.querySelector('.param-nome');
        const typeSelect = row.querySelector('.param-tipo');
        const descInput = row.querySelector('.param-desc');
        const requiredCheckbox = row.querySelector('.param-req');

        const paramName = nameInput?.value.trim();
        if (!paramName) return;

        schema.properties[paramName] = {
            type: typeSelect?.value || 'string',
            description: descInput?.value || ''
        };

        if (requiredCheckbox?.checked) {
            schema.required.push(paramName);
        }
    });

    // Remove required array if empty
    if (schema.required.length === 0) {
        delete schema.required;
    }

    return schema;
}
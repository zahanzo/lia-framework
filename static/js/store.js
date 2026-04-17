// ==========================================
// STORE MODULE - Plugin and Master Management
// ==========================================
import { showToast } from './ui.js';

console.log('✅ [STORE] Module loaded successfully');

// ==========================================
// GLOBAL STATE
// ==========================================

/** @type {Object} Store data containing plugins and masters */
const DEFAULT_STORE = { plugins: [], masters: [] };

if (typeof window.storeData === 'undefined') {
    window.storeData = { ...DEFAULT_STORE };
}
let storeData = window.storeData;

/** @type {Array<Object>} Temporary storage for master tools during submission */
let masterToolsTemp = [];

// ==========================================
// HELPER FUNCTIONS
// ==========================================

/**
 * Translation helper with fallback to Portuguese
 * @param {string} key - i18n key
 * @param {string} fallback - Fallback text in Portuguese
 * @returns {string} Translated text
 */
const translate = (key, fallback) => {
    if (typeof _ === 'function') {
        const result = _(key);
        if (result && result !== key) return result;
    }
    return fallback;
};

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

/**
 * Get current language code
 * @returns {string} Language code ('pt' or 'en')
 */
function getCurrentLanguage() {
    return typeof _currentLang !== 'undefined' ? _currentLang :
           typeof window._currentLang !== 'undefined' ? window._currentLang : 'pt';
}

// ==========================================
// STORE DATA LOADING
// ==========================================

/**
 * Load store items from the API
 * @returns {Promise<void>}
 */
async function loadStoreItems() {
    console.log('🔄 [STORE] Loading items from API...');
    try {
        const response = await fetch('/api/store/items');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();
        
        // Garantir que a resposta tenha a estrutura esperada
        storeData = {
            plugins: Array.isArray(data.plugins) ? data.plugins : [],
            masters: Array.isArray(data.masters) ? data.masters : []
        };
        window.storeData = storeData;
        renderStore();
    } catch (error) {
        console.error('❌ [STORE] Error loading store:', error);
        showToast?.('❌ ' + translate('store.error_loading', 'Erro ao carregar a loja'), 'error');
        // Fallback para dados vazios em caso de erro
        storeData = { ...DEFAULT_STORE };
        window.storeData = storeData;
        renderStore();
    }
}

// ==========================================
// STORE RENDERING
// ==========================================

/**
 * Render the store based on current filters
 * @returns {void}
 */
function renderStore() {
    console.log('🎨 [STORE] Rendering store...');
    
    // Verificação de segurança: garantir que storeData e suas propriedades existam
    if (!storeData || !Array.isArray(storeData.plugins) || !Array.isArray(storeData.masters)) {
        console.warn('[STORE] Invalid storeData, resetting to default');
        storeData = { ...DEFAULT_STORE };
        window.storeData = storeData;
    }
    
    const searchInput = document.getElementById('store-search');
    const categorySelect = document.getElementById('store-category');
    const typeSelect = document.getElementById('store-type');

    const searchTerm = searchInput?.value.toLowerCase() || '';
    const category = categorySelect?.value || '';
    const selectedType = typeSelect?.value || 'all';

    const pluginsContainer = document.getElementById('store-plugins');
    const pluginsSection = document.getElementById('plugins-section');

    // Render plugins section
    if (pluginsContainer && pluginsSection) {
        if (selectedType === 'all' || selectedType === 'plugins') {
            const filteredPlugins = storeData.plugins.filter(plugin => {
                const matchesSearch = !searchTerm ||
                    plugin.name.toLowerCase().includes(searchTerm) ||
                    plugin.description.toLowerCase().includes(searchTerm);
                const matchesCategory = !category || plugin.category === category;
                return matchesSearch && matchesCategory;
            });

            pluginsContainer.innerHTML = filteredPlugins.length > 0
                ? filteredPlugins.map(renderPluginCard).join('')
                : `<div class="store-empty">${translate('store.no_plugins_found', 'Nenhum plugin encontrado')}</div>`;

            pluginsSection.classList.remove('hidden');
        } else {
            pluginsSection.classList.add('hidden');
        }
    }

    // Render masters section
    const mastersContainer = document.getElementById('store-masters');
    const mastersSection = document.getElementById('masters-section');

    if (mastersContainer && mastersSection) {
        if (selectedType === 'all' || selectedType === 'masters') {
            const filteredMasters = storeData.masters.filter(master => {
                const matchesSearch = !searchTerm ||
                    master.name.toLowerCase().includes(searchTerm) ||
                    master.description.toLowerCase().includes(searchTerm);
                const matchesCategory = !category || master.category === category;
                return matchesSearch && matchesCategory;
            });

            mastersContainer.innerHTML = filteredMasters.length > 0
                ? filteredMasters.map(renderMasterCard).join('')
                : `<div class="store-empty">${translate('store.no_masters_found', 'Nenhum master encontrado')}</div>`;

            mastersSection.classList.remove('hidden');
        } else {
            mastersSection.classList.add('hidden');
        }
    }

    // Re-apply translations after rendering
    if (typeof applyLangToUI === 'function') {
        setTimeout(applyLangToUI, 50);
    }
}

/**
 * Render a plugin card HTML
 * @param {Object} plugin - Plugin data
 * @returns {string} HTML string for the plugin card
 */
function renderPluginCard(plugin) {
    const language = getCurrentLanguage();
    const displayName = language === 'pt' && plugin.name_pt ? plugin.name_pt : plugin.name;
    const displayDescription = language === 'pt' && plugin.description_pt ? plugin.description_pt : plugin.description;
    const displayCategory = language === 'pt' && plugin.category_pt ? plugin.category_pt : plugin.category;

    return `
        <div class="store-item ${plugin.installed ? 'installed' : ''}">
            <div class="store-item-header">
                <h4 class="store-item-title">${escapeHtml(displayName)}</h4>
                <span class="store-item-badge">Plugin</span>
            </div>
            <div class="store-item-meta">
                <span>📦 ${escapeHtml(displayCategory)}</span>
                <span>⭐ ${plugin.rating || 'N/A'}</span>
                <span>⬇️ ${plugin.downloads || 0} <span data-i18n="store.downloads">${translate('store.downloads', 'downloads')}</span></span>
            </div>
            <p class="store-item-description">${escapeHtml(displayDescription)}</p>
            <div class="store-item-footer">
                <span class="store-item-author">v${plugin.version} • ${escapeHtml(plugin.author)}</span>
                ${plugin.installed
                    ? `<button class="store-btn store-btn-uninstall" onclick="uninstallPlugin('${escapeHtml(plugin.tool.name)}', this)">${translate('store.uninstall', 'Desinstalar')}</button>`
                    : `<button class="store-btn store-btn-install" onclick="installPlugin('${escapeHtml(plugin.id)}', this)">${translate('store.install', 'Instalar')}</button>`
                }
            </div>
        </div>
    `;
}

/**
 * Render a master card HTML
 * @param {Object} master - Master data
 * @returns {string} HTML string for the master card
 */
function renderMasterCard(master) {
    const language = getCurrentLanguage();
    const displayName = language === 'pt' && master.name_pt ? master.name_pt : master.name;
    const displayDescription = language === 'pt' && master.description_pt ? master.description_pt : master.description;
    const displayCategory = language === 'pt' && master.category_pt ? master.category_pt : master.category;

    return `
        <div class="store-item ${master.installed ? 'installed' : ''}">
            <div class="store-item-header">
                <h4 class="store-item-title">${escapeHtml(displayName)}</h4>
                <span class="store-item-badge master">Master</span>
            </div>
            <div class="store-item-meta">
                <span>📦 ${escapeHtml(displayCategory)}</span>
                <span>🔧 ${master.tools_count || master.tools?.length || 0} <span data-i18n="store.tools_count">${translate('store.tools_count', 'ferramentas')}</span></span>
                <span>⭐ ${master.rating || 'N/A'}</span>
                <span>⬇️ ${master.downloads || 0} <span data-i18n="store.downloads">${translate('store.downloads', 'downloads')}</span></span>
            </div>
            <p class="store-item-description">${escapeHtml(displayDescription)}</p>
            <div class="store-item-footer">
                <span class="store-item-author">v${master.version} • ${escapeHtml(master.author)}</span>
                ${master.installed
                    ? `<button class="store-btn store-btn-uninstall" onclick="uninstallMaster('${escapeHtml(master.id)}', this)">${translate('store.uninstall', 'Desinstalar')}</button>`
                    : `<button class="store-btn store-btn-install" onclick="installMaster('${escapeHtml(master.id)}', this)">${translate('store.install', 'Instalar')}</button>`
                }
            </div>
        </div>
    `;
}

// ==========================================
// INSTALLATION OPERATIONS
// ==========================================

/**
 * Install a plugin from the store
 * @param {string} pluginId - Plugin ID to install
 * @param {HTMLButtonElement} button - Button element that triggered the action
 * @returns {Promise<void>}
 */
async function installPlugin(pluginId, button) {
    button.disabled = true;
    button.textContent = translate('store.installing', 'Instalando...');

    try {
        const response = await fetch(`/api/store/install/plugin/${pluginId}`, { method: 'POST' });
        const data = await response.json();

        if (data.status === 'ok') {
            showToast?.('✅ ' + data.message, 'success');
            await loadStoreItems();
        } else {
            showToast?.('❌ ' + data.message, 'error');
            button.disabled = false;
            button.textContent = translate('store.install', 'Instalar');
        }
    } catch (error) {
        showToast?.('❌ ' + translate('store.error_installing', 'Erro ao instalar plugin'), 'error');
        button.disabled = false;
        button.textContent = translate('store.install', 'Instalar');
    }
}

/**
 * Install a master from the store
 * @param {string} masterId - Master ID to install
 * @param {HTMLButtonElement} button - Button element that triggered the action
 * @returns {Promise<void>}
 */
async function installMaster(masterId, button) {
    button.disabled = true;
    button.textContent = translate('store.installing', 'Instalando...');

    try {
        const response = await fetch(`/api/store/install/master/${masterId}`, { method: 'POST' });
        const data = await response.json();

        if (data.status === 'ok') {
            showToast?.('✅ ' + data.message, 'success');
            await loadStoreItems();
        } else {
            showToast?.('❌ ' + data.message, 'error');
            button.disabled = false;
            button.textContent = translate('store.install', 'Instalar');
        }
    } catch (error) {
        showToast?.('❌ ' + translate('store.error_installing', 'Erro ao instalar master'), 'error');
        button.disabled = false;
        button.textContent = translate('store.install', 'Instalar');
    }
}

/**
 * Uninstall a plugin
 * @param {string} toolName - Name of the plugin tool to uninstall
 * @param {HTMLButtonElement} button - Button element that triggered the action
 * @returns {Promise<void>}
 */
async function uninstallPlugin(toolName, button) {
    if (!confirm('❌ ' + translate('store.confirm_uninstall_plugin', 'Realmente desinstalar este plugin?'))) return;

    button.disabled = true;
    button.textContent = translate('store.uninstalling', 'Desinstalando...');

    try {
        const response = await fetch(`/api/store/uninstall/plugin/${toolName}`, { method: 'DELETE' });
        const data = await response.json();

        if (data.status === 'ok') {
            showToast?.('✅ ' + translate('store.plugin_uninstalled', 'Plugin desinstalado'), 'success');
            await loadStoreItems();
        } else {
            showToast?.('❌ ' + data.message, 'error');
            button.disabled = false;
            button.textContent = translate('store.uninstall', 'Desinstalar');
        }
    } catch (error) {
        showToast?.('❌ ' + translate('store.error_uninstalling', 'Erro ao desinstalar'), 'error');
        button.disabled = false;
        button.textContent = translate('store.uninstall', 'Desinstalar');
    }
}

/**
 * Uninstall a master
 * @param {string} masterId - Master ID to uninstall
 * @param {HTMLButtonElement} button - Button element that triggered the action
 * @returns {Promise<void>}
 */
async function uninstallMaster(masterId, button) {
    if (!confirm('❌ ' + translate('store.confirm_uninstall_master', 'Realmente desinstalar este master e suas ferramentas?'))) return;

    button.disabled = true;
    button.textContent = translate('store.uninstalling', 'Desinstalando...');

    try {
        const response = await fetch(`/api/store/uninstall/master/${masterId}`, { method: 'DELETE' });
        const data = await response.json();

        if (data.status === 'ok') {
            showToast?.('✅ ' + translate('store.master_uninstalled', 'Master desinstalado'), 'success');
            await loadStoreItems();
        } else {
            showToast?.('❌ ' + data.message, 'error');
            button.disabled = false;
            button.textContent = translate('store.uninstall', 'Desinstalar');
        }
    } catch (error) {
        showToast?.('❌ ' + translate('store.error_uninstalling', 'Erro ao desinstalar'), 'error');
        button.disabled = false;
        button.textContent = translate('store.uninstall', 'Desinstalar');
    }
}

// ==========================================
// SUBMISSION DIALOG MANAGEMENT
// ==========================================

/**
 * Show the submission dialog
 * @returns {void}
 */
function showSubmitDialog() {
    document.getElementById('submit-dialog').style.display = 'block';
}

/**
 * Close the submission dialog and reset form
 * @returns {void}
 */
function closeSubmitDialog() {
    document.getElementById('submit-dialog').style.display = 'none';

    // Reset form fields
    document.getElementById('submit-name').value = '';
    document.getElementById('submit-description').value = '';
    document.getElementById('submit-author').value = '';
    document.getElementById('submit-tool-name').value = '';
    document.getElementById('submit-tool-desc').value = '';
    document.getElementById('submit-tool-code').value = '';
    document.getElementById('submit-tool-schema').value = '';
    document.getElementById('submit-tool-pip').value = '';

    masterToolsTemp = [];
    renderMasterToolsList();

    const existingPreview = document.querySelector('.json-preview');
    if (existingPreview) existingPreview.remove();
}

/**
 * Toggle visibility of fields based on submission type (plugin vs master)
 * @returns {void}
 */
function toggleSubmitType() {
    const typeSelect = document.getElementById('submit-type');
    const selectedType = typeSelect.value;

    document.getElementById('submit-plugin-fields').style.display = selectedType === 'plugin' ? 'block' : 'none';
    document.getElementById('submit-master-fields').style.display = selectedType === 'master' ? 'block' : 'none';
}

// ==========================================
// MASTER TOOLS MANAGEMENT (FOR SUBMISSION)
// ==========================================

/**
 * Open dialog to add a new master tool
 * @returns {void}
 */
function addMasterTool() {
    document.getElementById('mt-edit-index').value = '';
    document.getElementById('mt-name').value = '';
    document.getElementById('mt-desc').value = '';
    document.getElementById('mt-schema').value = '';
    document.getElementById('mt-code').value = '';
    document.getElementById('mt-pip').value = '';

    document.getElementById('master-tool-dialog').classList.add('open');
}

/**
 * Open dialog to edit an existing master tool
 * @param {number} index - Index of the tool in masterToolsTemp
 * @returns {void}
 */
function editMasterTool(index) {
    const tool = masterToolsTemp[index];

    document.getElementById('mt-edit-index').value = index;
    document.getElementById('mt-name').value = tool.name;
    document.getElementById('mt-desc').value = tool.description;
    document.getElementById('mt-schema').value = tool.schema_json;
    document.getElementById('mt-code').value = tool.python_code;
    document.getElementById('mt-pip').value = tool.pip_requirements || '';

    document.getElementById('master-tool-dialog').classList.add('open');
}

/**
 * Delete a master tool from temporary list
 * @param {number} index - Index of the tool to delete
 * @returns {void}
 */
function deleteMasterTool(index) {
    if (confirm('❌ ' + translate('store.confirm_delete', 'Deletar esta ferramenta?'))) {
        masterToolsTemp.splice(index, 1);
        renderMasterToolsList();
    }
}

/**
 * Save the current master tool (add or update)
 * @returns {void}
 */
function saveMasterTool() {
    const tool = {
        name: document.getElementById('mt-name').value.trim(),
        description: document.getElementById('mt-desc').value.trim(),
        schema_json: document.getElementById('mt-schema').value.trim(),
        python_code: document.getElementById('mt-code').value.trim(),
        pip_requirements: document.getElementById('mt-pip').value.trim()
    };

    if (!tool.name || !tool.description || !tool.python_code) {
        showToast?.('❌ ' + translate('store.fill_required', 'Preencha os campos obrigatórios'), 'error');
        return;
    }

    const editIndex = document.getElementById('mt-edit-index').value;

    if (editIndex === '') {
        masterToolsTemp.push(tool);
    } else {
        masterToolsTemp[parseInt(editIndex)] = tool;
    }

    renderMasterToolsList();
    closeMasterToolDialog();
}

/**
 * Render the list of temporary master tools
 * @returns {void}
 */
function renderMasterToolsList() {
    const container = document.getElementById('submit-master-tools-list');

    if (masterToolsTemp.length === 0) {
        container.innerHTML = `<p style="color: var(--muted); font-size: 13px;">${translate('store.no_tools', 'Nenhuma ferramenta')}</p>`;
        return;
    }

    container.innerHTML = masterToolsTemp.map((tool, index) => `
        <div class="master-tool-item" style="background: var(--card); padding: 12px; margin-bottom: 8px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center;">
            <div>
                <strong>${escapeHtml(tool.name)}</strong>
                <div style="color: var(--muted); font-size: 12px;">${escapeHtml(tool.description)}</div>
            </div>
            <div>
                <button class="btn btn-sm btn-ghost" onclick="editMasterTool(${index})">✏️ ${translate('store.edit', 'Editar')}</button>
                <button class="btn btn-sm btn-ghost" onclick="deleteMasterTool(${index})" style="color: var(--red);">🗑️</button>
            </div>
        </div>
    `).join('');
}

/**
 * Close the master tool dialog
 * @returns {void}
 */
function closeMasterToolDialog() {
    document.getElementById('master-tool-dialog').classList.remove('open');
}

// ==========================================
// STORE SUBMISSION
// ==========================================

/**
 * Submit plugin/master to the store
 * @returns {Promise<void>}
 */
async function submitToStore() {
    const typeSelect = document.getElementById('submit-type');
    const submissionType = typeSelect.value;

    const submission = {
        type: submissionType,
        name: document.getElementById('submit-name').value.trim(),
        description: document.getElementById('submit-description').value.trim(),
        author: document.getElementById('submit-author').value.trim(),
        category: document.getElementById('submit-category').value,
    };

    // Validate basic fields
    if (!submission.name || !submission.description || !submission.author) {
        showToast?.('❌ ' + translate('store.fill_required', 'Preencha os campos obrigatórios'), 'error');
        return;
    }

    // Handle plugin-specific fields
    if (submissionType === 'plugin') {
        const toolName = document.getElementById('submit-tool-name').value.trim();
        const toolDesc = document.getElementById('submit-tool-desc').value.trim();
        const toolCode = document.getElementById('submit-tool-code').value.trim();
        const toolSchema = document.getElementById('submit-tool-schema').value.trim();

        if (!toolName || !toolDesc || !toolCode || !toolSchema) {
            showToast?.('❌ ' + translate('store.fill_tool_fields', 'Preencha os campos da ferramenta'), 'error');
            return;
        }

        submission.tool = {
            name: toolName,
            description: toolDesc,
            schema_json: toolSchema,
            python_code: toolCode,
            pip_requirements: document.getElementById('submit-tool-pip').value.trim()
        };
    } else {
        // Handle master-specific fields
        if (masterToolsTemp.length === 0) {
            showToast?.('❌ ' + translate('store.add_one_tool', 'Adicione uma ferramenta'), 'error');
            return;
        }
        submission.tools = masterToolsTemp;
    }

    try {
        const response = await fetch('/api/store/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(submission)
        });

        const data = await response.json();

        if (data.status === 'ok') {
            const escapedJson = escapeHtml(data.json).replace(/`/g, '\\`').replace(/\$/g, '\\$');
            const jsonPreview = `
                <div class="json-preview" style="margin-top: 20px; padding: 20px; background: var(--surface); border-radius: 8px;">
                    <h3>📋 ${translate('store.json_generated', 'JSON Gerado')}</h3>
                    <pre style="background: var(--bg); padding: 15px; border-radius: 6px; overflow-x: auto; font-size: 12px;">${escapeHtml(data.json)}</pre>
                    <p style="margin-top: 15px; color: var(--muted);">${translate('store.click_to_create_issue', 'Clique abaixo para criar a Issue no GitHub:')}</p>
                    <a href="${data.github_url}" target="_blank" class="btn-submit" style="display: inline-block; margin-top: 10px;">
                        🚀 ${translate('store.create_github_issue', 'Criar GitHub Issue')}
                    </a>
                    <button onclick="copyToClipboard(\`${escapedJson}\`)" class="btn btn-ghost" style="margin-left: 10px;">
                        📋 ${translate('store.copy_json', 'Copiar JSON')}
                    </button>
                </div>
            `;

            const existingPreview = document.querySelector('.json-preview');
            if (existingPreview) existingPreview.remove();

            document.querySelector('#submit-dialog .modal-content').insertAdjacentHTML('beforeend', jsonPreview);
            showToast?.('✅ ' + data.message, 'success');
        } else {
            showToast?.('❌ ' + data.message, 'error');
        }
    } catch (error) {
        showToast?.('❌ ' + translate('store.error_submitting', 'Erro ao enviar'), 'error');
    }
}

/**
 * Copy text to clipboard
 * @param {string} text - Text to copy
 * @returns {Promise<void>}
 */
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showToast?.('✅ ' + translate('store.json_copied', 'JSON copiado!'), 'success');
    } catch (error) {
        showToast?.('❌ ' + translate('store.error_copying', 'Erro ao copiar'), 'error');
    }
}

// ==========================================
// EXPORT FUNCTIONS TO GLOBAL SCOPE
// ==========================================

window.loadStoreItems = loadStoreItems;
window.renderStore = renderStore;
window.installPlugin = installPlugin;
window.installMaster = installMaster;
window.uninstallPlugin = uninstallPlugin;
window.uninstallMaster = uninstallMaster;
window.showSubmitDialog = showSubmitDialog;
window.closeSubmitDialog = closeSubmitDialog;
window.toggleSubmitType = toggleSubmitType;
window.addMasterTool = addMasterTool;
window.editMasterTool = editMasterTool;
window.deleteMasterTool = deleteMasterTool;
window.saveMasterTool = saveMasterTool;
window.closeMasterToolDialog = closeMasterToolDialog;
window.submitToStore = submitToStore;
window.copyToClipboard = copyToClipboard;

// ==========================================
// INITIALIZATION
// ==========================================

/**
 * Initialize the store module
 * @returns {void}
 */
function initStore() {
    // Apply translations after a short delay
    if (typeof applyLangToUI === 'function') {
        setTimeout(applyLangToUI, 50);
    }

    // Set up event listeners for filters
    const searchInput = document.getElementById('store-search');
    const categorySelect = document.getElementById('store-category');
    const typeSelect = document.getElementById('store-type');

    if (searchInput) searchInput.addEventListener('input', renderStore);
    if (categorySelect) categorySelect.addEventListener('change', renderStore);
    if (typeSelect) typeSelect.addEventListener('change', renderStore);

    // Lazy load store items when panel becomes active
    const storePanel = document.getElementById('panel-store');
    if (storePanel) {
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.attributeName === 'class' && storePanel.classList.contains('active')) {
                    loadStoreItems();
                    observer.disconnect();
                }
            });
        });
        observer.observe(storePanel, { attributes: true });

        // If panel is already active, load immediately
        if (storePanel.classList.contains('active')) {
            loadStoreItems();
        }
    }
}

// Start initialization when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initStore);
} else {
    initStore();
}
// ==========================================
// UI MODULE - Layout and Visual Feedback
// ==========================================
console.log('✅ [UI] Module loaded successfully');

// ==========================================
// INTERNAL STATE
// ==========================================

/** @type {boolean} Sidebar collapsed state */
let sidebarCollapsed = false;

/** @type {number|null} Status polling interval ID */
let statusPoller = null;

// ==========================================
// NOTIFICATIONS
// ==========================================

/**
 * Display a toast notification
 * @param {string} message - Message to display
 * @param {boolean} isError - Whether this is an error toast
 * @returns {void}
 */
export function showToast(message, isError = false) {
    const toastElement = document.getElementById('toast');
    if (!toastElement) return;

    toastElement.textContent = message;
    toastElement.className = 'show' + (isError ? ' error' : '');

    clearTimeout(toastElement._hideTimeout);
    toastElement._hideTimeout = setTimeout(() => {
        toastElement.classList.remove('show');
    }, 2800);
}

// ==========================================
// PANEL MANAGEMENT
// ==========================================

/**
 * Switch between panels with lazy loading support
 * @param {string} panelName - Name of the panel to show
 * @param {HTMLElement|null} clickedElement - Element that triggered the switch
 * @returns {void}
 */
export function showPanel(panelName, clickedElement = null) {
    // Deactivate all panels and navigation items
    document.querySelectorAll('.panel').forEach(panel => panel.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));
    document.querySelectorAll('.mnav-item').forEach(item => item.classList.remove('active'));

    // Activate target panel
    const targetPanel = document.getElementById('panel-' + panelName);
    if (targetPanel) targetPanel.classList.add('active');

    // Activate clicked navigation item
    if (clickedElement) {
        clickedElement.classList.add('active');
    } else if (panelName === 'chat') {
        const chatNav = document.querySelector('.nav-item[data-panel="chat"]');
        if (chatNav) chatNav.classList.add('active');
    }

    // Sync mobile navigation
    document.querySelectorAll('.mnav-item').forEach(mobileItem => {
        const onclickAttr = mobileItem.getAttribute('onclick');
        if (onclickAttr && onclickAttr.includes("'" + panelName + "'")) {
            mobileItem.classList.add('active');
        }
    });

    // Update topbar title using i18n
    const topbarTitle = document.getElementById('topbar-section');
    if (topbarTitle && typeof window._ === 'function') {
        const panelTitles = {
            chat: window._('nav.chat'),
            sistema: window._('nav.system'),
            persona: window._('nav.persona'),
            plugins: window._('nav.plugins'),
            store: 'Store',
            roleplay: window._('nav.roleplay'),
            visao: window._('nav.vision'),
            memorias: window._('nav.memory')
        };
        topbarTitle.textContent = panelTitles[panelName] || panelName;
    }

    // Dispatch event for modular lazy loading
    document.dispatchEvent(new CustomEvent('panel-changed', {
        detail: { panelName: panelName }
    }));
}

// ==========================================
// SIDEBAR MANAGEMENT
// ==========================================

/**
 * Toggle desktop sidebar collapsed state
 * @returns {void}
 */
export function toggleSidebar() {
    sidebarCollapsed = !sidebarCollapsed;

    const sidebar = document.getElementById('sidebar');
    const toggleButton = document.getElementById('sidebar-toggle');

    if (!sidebar || !toggleButton) return;

    sidebar.classList.toggle('collapsed', sidebarCollapsed);
    toggleButton.textContent = sidebarCollapsed ? '›' : '‹';
    toggleButton.style.left = sidebarCollapsed
        ? 'calc(var(--sidebar-sm) - 13px)'
        : 'calc(var(--sidebar-w) - 13px)';
}

// ==========================================
// MODAL MANAGEMENT
// ==========================================

/**
 * Close the editor modal
 * @returns {void}
 */
export function fecharModal() {
    const modal = document.getElementById('modal-editar');
    if (modal) modal.classList.remove('open');
}

// ==========================================
// FORM UTILITIES
// ==========================================

/**
 * Toggle password field visibility
 * @param {HTMLElement} button - Button that triggered the toggle
 * @param {string} inputId - ID of the password input element
 * @returns {void}
 */
export function toggleEye(button, inputId) {
    const inputElement = document.getElementById(inputId);
    if (!inputElement) return;

    inputElement.type = inputElement.type === 'password' ? 'text' : 'password';
    button.textContent = inputElement.type === 'password' ? '👁' : '🙈';
}

// ==========================================
// MODE INDICATORS (FOCUS / DND)
// ==========================================

/**
 * Update focus and DND mode UI indicators
 * @param {boolean} isFocusMode - Whether focus mode is active
 * @param {boolean} isDNDMode - Whether do-not-disturb mode is active
 * @returns {void}
 */
export function atualizarModeUI(isFocusMode, isDNDMode) {
    // Update status pills
    const focusPill = document.getElementById('pill-foco');
    const dndPill = document.getElementById('pill-dnd');

    if (focusPill) focusPill.className = 'status-pill ' + (isFocusMode ? 'on-focus' : 'off');
    if (dndPill) dndPill.className = 'status-pill ' + (isDNDMode ? 'on-dnd' : 'off');

    // Update mode buttons
    const focusButton = document.getElementById('btn-foco');
    const dndButton = document.getElementById('btn-dnd');

    if (focusButton) focusButton.className = 'mode-btn ' + (isFocusMode ? 'active-focus' : '');
    if (dndButton) dndButton.className = 'mode-btn ' + (isDNDMode ? 'active-dnd' : '');

    // Update topbar badges
    const focusBadge = document.getElementById('badge-foco');
    const dndBadge = document.getElementById('badge-dnd');

    if (focusBadge) focusBadge.className = 'topbar-mode-badge ' + (isFocusMode ? 'focus' : '');
    if (dndBadge) dndBadge.className = 'topbar-mode-badge ' + (isDNDMode ? 'dnd' : '');
}

// ==========================================
// STATUS BAR MANAGEMENT
// ==========================================

/**
 * Control the status bar visibility and message
 * @param {string} message - Status message to display, empty to hide
 * @returns {void}
 */
export function mostrarStatus(message) {
    const statusBar = document.getElementById('chat-status');
    const statusText = document.getElementById('chat-status-text');

    if (!statusBar || !statusText) return;

    if (message) {
        statusText.textContent = message;
        statusBar.classList.add('visible');
    } else {
        statusBar.classList.remove('visible');
        statusText.textContent = '';
    }
}

/**
 * Alias for mostrarStatus (compatibility with chat.js)
 * @param {string} message - Status message to display
 * @returns {void}
 */
export const showStatus = mostrarStatus;

// ==========================================
// STATUS POLLING
// ==========================================

/**
 * Start polling for backend status updates
 * @param {Function} apiCall - Async function that returns status data
 * @returns {void}
 */
export function iniciarPollingStatus(apiCall) {
    if (statusPoller) return;

    const POLLING_INTERVAL_MS = 500;

    statusPoller = setInterval(async () => {
        try {
            const data = await apiCall();
            const currentStatus = data.status || '';

            mostrarStatus(currentStatus);

            if (!currentStatus) {
                clearInterval(statusPoller);
                statusPoller = null;
            }
        } catch (error) {
            console.error('[UI] Status polling error:', error);
        }
    }, POLLING_INTERVAL_MS);
}
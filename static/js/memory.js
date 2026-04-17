// ==========================================
// MEMORY MODULE - RAG and Visual Context
// ==========================================
import { API } from './api.js';

console.log('✅ [MEMORY] Module loaded successfully');

// ==========================================
// INTERNAL STATE
// ==========================================

/** @type {Array<Object>} Cached list of all memory entries */
let cachedMemories = [];

// ==========================================
// MEMORY MANAGEMENT
// ==========================================

/**
 * Fetch and display all semantic memories from the database
 * @returns {Promise<void>}
 */
export async function loadMemories() {
    try {
        const memories = await API.memory.getAll();
        cachedMemories = memories || [];

        // Update memory count badge if present
        const countBadge = document.getElementById('mem-count');
        if (countBadge) {
            countBadge.textContent = cachedMemories.length;
        }

        renderMemories(cachedMemories);
    } catch (error) {
        console.error('[MEMORY] Failed to load memories:', error);
    }
}

/**
 * Render the memory list into the UI container
 * @param {Array<Object>} memoryList - Array of memory objects
 * @returns {void}
 */
export function renderMemories(memoryList) {
    const container = document.getElementById('mem-list');
    if (!container) return;

    // Empty state
    if (!memoryList || memoryList.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="es-icon">🧠</div>
                <p>${_('mem.none').replace('\n', '<br>')}</p>
            </div>
        `;
        return;
    }

    // Build memories list HTML
    container.innerHTML = memoryList.map(memory => `
        <div class="list-item">
            <div class="list-item-body">
                <div class="list-item-title" style="white-space:normal;font-weight:500">
                    ${escapeHtml(memory.content)}
                </div>
                <div class="list-item-sub">
                    📅 ${memory.created_at} &nbsp;·&nbsp; 🔍 ${memory.access_count}× accessed
                </div>
            </div>
            <button class="btn-sm btn-sm-del" onclick="memory.deleteMemory(${memory.id})">✕</button>
        </div>
    `).join('');
}

/**
 * Escape HTML special characters to prevent XSS
 * @param {string} text - Raw text to escape
 * @returns {string} Escaped HTML-safe string
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Filter memories locally based on search input
 * @returns {void}
 */
export function filterMemories() {
    const searchInput = document.getElementById('mem-search');
    const query = searchInput?.value.toLowerCase();

    if (!query) {
        renderMemories(cachedMemories);
        return;
    }

    const filtered = cachedMemories.filter(memory =>
        memory.content.toLowerCase().includes(query)
    );
    renderMemories(filtered);
}

/**
 * Delete a single memory entry
 * @param {number} memoryId - Memory ID in database
 * @returns {Promise<void>}
 */
export async function deleteMemory(memoryId) {
    try {
        await API.memory.delete(memoryId);
        await loadMemories();
    } catch (error) {
        console.error('[MEMORY] Deletion failed:', error);
    }
}

/**
 * Delete all memories after user confirmation
 * @returns {Promise<void>}
 */
export async function deleteAllMemories() {
    if (!confirm(_('confirm.mem_all'))) return;

    try {
        await API.memory.deleteAll();
        await loadMemories();
    } catch (error) {
        console.error('[MEMORY] Bulk deletion failed:', error);
    }
}

// ==========================================
// VISUAL CONTEXT MANAGEMENT
// ==========================================

/**
 * Fetch and update the background vision context display
 * @returns {Promise<void>}
 */
export async function updateVisualContext() {
    const contextTextArea = document.getElementById('box-visao-contexto');
    const screenshotImage = document.getElementById('img-last-vision');

    if (!contextTextArea) return;

    try {
        const description = await API.vision.getDescription();
        contextTextArea.value = description || _('vision.waiting');

        // Refresh screenshot with cache-busting timestamp
        if (screenshotImage) {
            screenshotImage.src = `/api/last_vision?t=${Date.now()}`;
        }
    } catch (error) {
        console.error('[MEMORY] Vision update failed:', error);
    }
}

/**
 * Initialize periodic updates for visual context
 * Refreshes every 30 seconds when the vision panel is active
 * @returns {void}
 */
export function startVisionPolling() {
    const POLLING_INTERVAL_MS = 30000;

    setInterval(() => {
        const visionPanel = document.getElementById('panel-visao');
        const isPanelActive = visionPanel?.classList.contains('active');

        if (isPanelActive) {
            updateVisualContext();
        }
    }, POLLING_INTERVAL_MS);
}
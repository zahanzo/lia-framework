// ==========================================
// CHAT MODULE - Messages, and Voice
// ==========================================
import { API } from './api.js';
import { showStatus, showToast } from './ui.js';

console.log('✅ [CHAT] Module aligned with CSS and HTML');

// Internal State
let sseActive = false;
let pendingFiles = []; // {file, local_url, server_url, type, name}
let recognition = null;
let isRecording = false;

/**
 * Internal content formatter (Markdown, Images, Files)
 */
function _renderContent(raw) {
  let txt = (raw || '')
    .replace(/\[SKILL.*?\]/gi, '')
    .replace(/<MEMORIA_VISUAL>[\s\S]*?<\/MEMORIA_VISUAL>/gi,
             '<em style="color:var(--muted);font-size:0.85em">👁 [Visual Context]</em>');

  // Regex for Images
  txt = txt.replace(/\[IMG:([^\]]+)\]/g, (_, url) =>
    `<img src="${url}" class="msg-img" alt="image">`
  );

  // Regex for Files
  txt = txt.replace(/\[FILE:([^:]+):([^\]]+)\]/g, (_, url, name) => {
    return `<a href="${url}" target="_blank" class="msg-file">
      <span class="msg-file-icon">📁</span>
      <span class="msg-file-info"><span class="msg-file-name">${name}</span></span>
    </a>`;
  });

  // Formatting
  return txt
    .replace(/\n/g, '<br>')
    .replace(/\*\*(.*?)\*\*/g, '<b>$1</b>');
}

/**
 * Append a message bubble to the chat
 * @param {string} role - 'user' or 'assistant'
 * @param {string} text - Message content
 */
export function addMessage(role, text) {
  const box = document.getElementById('chat-messages'); // ID from index.html
  if (!box) return;

  // Remove empty state
  const empty = box.querySelector('.empty-state');
  if (empty) empty.remove();

  const isUser = role === 'user';
  const row = document.createElement('div');
  row.className = 'msg-row ' + (isUser ? 'user' : 'assistant'); // Classes from main.css
  
  row.innerHTML = `
    <div class="msg-bubble">
      <div class="msg-sender">${isUser ? (_('chat.you') || 'You') : (window.nomeIA || 'AI')}</div>
      <div class="msg-text">${_renderContent(text)}</div>
    </div>
  `;

  box.appendChild(row);
  box.scrollTop = box.scrollHeight;
}

/**
 * Process and send the user message
 */
export async function sendMessage() {
  const input = document.getElementById('chat-input');
  const text = input.value.trim();
  
  if (!text && pendingFiles.length === 0) return;

  addMessage('user', text);
  input.value = '';
  
  if (typeof showStatus === 'function') showStatus(_('status.generating'));

  try {
    // Mapeia os arquivos usando "type" (inglês) para o backend
    const filesPayload = pendingFiles.map(f => ({
      url: f.url,
      type: f.type,   // antes: tipo
      name: f.name    // antes: nome
    }));
    
    await API.chat.send(text, filesPayload);
    try{
      console.log('✅ Message sent, awaiting response...');
    }catch(e){
      console.error('Error sending message:', e);
    }
    
    // Poll for assistant response...
    let attempts = 0;
    const maxAttempts = 30;
    
    while (attempts < maxAttempts) {
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      const history = await API.chat.getHistory();
      const lastMsg = history[history.length - 1];
      
      if (lastMsg && lastMsg.role === 'assistant' && lastMsg.content !== '') {
        addMessage('assistant', lastMsg.content);
        break;
      }
      
      attempts++;
    }
    
    pendingFiles = [];
    renderPendingFiles();
  } catch (err) {
    console.error('[CHAT] Send failed:', err);
  } finally {
    if (typeof showStatus === 'function') showStatus('');
  }
}

/**
 * Voice Recognition using WebSpeech API
 */
export function initSpeechRecognition() {
  const Speech = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Speech) return;

  recognition = new Speech();
  recognition.lang = window._currentLang === 'pt' ? 'pt-BR' : 'en-US';
  recognition.continuous = false;

  recognition.onstart = () => {
    isRecording = true;
    document.getElementById('btn-mic')?.classList.add('recording');
    if (typeof showStatus === 'function') showStatus(_('status.listening'));
  };

  recognition.onresult = (event) => {
    const text = event.results[0][0].transcript;
    const input = document.getElementById('chat-input');
    if (input) {
      input.value = text;
      sendMessage();
    }
  };

  recognition.onend = () => {
    isRecording = false;
    document.getElementById('btn-mic')?.classList.remove('recording');
    if (typeof showStatus === 'function') showStatus('');
  };
}

/**
 * Toggle Recording State
 */
export function toggleRecording() {
  if (!recognition) initSpeechRecognition();
  if (isRecording) recognition.stop();
  else recognition.start();
}

/**
 * Handle file upload and add to pending list
 */
export async function addPendingFile(file) {
  if (typeof showStatus === 'function') showStatus(_('status.uploading'));
  
  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await API.chat.uploadFile(formData);
    if (res.url) {
      pendingFiles.push({
        file: file,
        name: file.name,
        type: file.type.startsWith('image/') ? 'imagem' : 'arquivo', // Backend still expects these values
        url: res.url
      });
      renderPendingFiles();
    }
  } catch (err) {
    if (typeof showToast === 'function') showToast('Upload failed', true);
  } finally {
    if (typeof showStatus === 'function') showStatus('');
  }
}

/**
 * Render file badges above the input
 */
export function renderPendingFiles() {
  const container = document.getElementById('file-preview-strip'); // Correct ID
  if (!container) return;

  if (pendingFiles.length === 0) {
    container.classList.remove('visible');
    container.innerHTML = '';
    return;
  }

  container.classList.add('visible');
  container.innerHTML = pendingFiles.map((f, i) => `
    <div class="file-thumb">
      <div class="file-thumb-card">
        <span class="file-thumb-icon">📁</span>
        <span class="file-thumb-name">${f.name}</span>
      </div>
      <button class="file-thumb-remove" onclick="removeFile(${i})">✕</button>
    </div>
  `).join('');
}

/**
 * Remove file from queue
 */
export function removeFile(index) {
  pendingFiles.splice(index, 1);
  renderPendingFiles();
}

// Global hook for the "onclick" in HTML
window.removeFile = removeFile;
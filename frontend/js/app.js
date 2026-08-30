/**
 * CONVERT.io - Streamlined UI
 * With bulk download and rate limit display
 */

const state = { files: [], presets: [], isConverting: false, limits: null };

const el = {
    presetsGrid: document.getElementById('presets-grid'),
    dropArea: document.getElementById('drop-area'),
    filesList: document.getElementById('files-list'),
    fileInput: document.getElementById('file-input'),
    outputFormat: document.getElementById('output-format'),
    convertBtn: document.getElementById('convert-btn'),
    clearBtn: document.getElementById('clear-btn'),
    toastContainer: document.getElementById('toast-container'),
    downloadAllBtn: document.getElementById('download-all-btn')
};

const ICONS = {
    heic: '📷', heif: '📷', jpg: '🖼️', jpeg: '🖼️', png: '🖼️',
    webp: '🌐', gif: '🎞️', doc: '📄', docx: '📄', pdf: '📕', default: '📁'
};

const MAX_FILES = 25;

// Init
async function init() {
    await loadPresets();
    setupEvents();
}

async function loadPresets() {
    try {
        const res = await fetch('/api/presets');
        const data = await res.json();
        state.presets = data.presets;
        renderPresets();
    } catch (e) { console.error('Failed to load presets:', e); }
}

async function loadLimits() {
    // Limits are loaded silently, only shown when exceeded
    try {
        const res = await fetch('/api/limits');
        state.limits = await res.json();
    } catch (e) { /* silent */ }
}

function renderPresets() {
    el.presetsGrid.innerHTML = state.presets.map(p => `
        <button class="preset-btn ${!p.available ? 'disabled' : ''}" 
                data-id="${p.id}" data-from="${p.from}" data-to="${p.to}"
                ${!p.available ? 'disabled' : ''}>
            <span class="preset-icon">${p.icon}</span>
            <span class="preset-name">${p.name}</span>
            <span class="preset-arrow">→</span>
        </button>
    `).join('');

    el.presetsGrid.querySelectorAll('.preset-btn:not(.disabled)').forEach(btn => {
        btn.onclick = () => {
            const preset = state.presets.find(p => p.id === btn.dataset.id);
            if (preset) {
                el.outputFormat.value = preset.to;
                el.fileInput.accept = `.${preset.from}`;
                el.fileInput.click();
                toast(`Select ${preset.from.toUpperCase()} files`, 'info');
            }
        };
    });
}

function setupEvents() {
    el.dropArea.onclick = (e) => {
        if (e.target.closest('.file-btn')) return;
        el.fileInput.accept = '';
        el.fileInput.click();
    };

    el.fileInput.onchange = e => {
        addFiles(Array.from(e.target.files));
        e.target.value = '';
    };

    el.dropArea.ondragover = e => {
        e.preventDefault();
        el.dropArea.classList.add('drag-over');
    };

    el.dropArea.ondragleave = e => {
        e.preventDefault();
        el.dropArea.classList.remove('drag-over');
    };

    el.dropArea.ondrop = e => {
        e.preventDefault();
        el.dropArea.classList.remove('drag-over');
        addFiles(Array.from(e.dataTransfer.files));
    };

    el.outputFormat.onchange = updateBtn;
    el.convertBtn.onclick = convert;
    el.clearBtn.onclick = clearAll;

    if (el.downloadAllBtn) {
        el.downloadAllBtn.onclick = downloadAll;
    }
}

function addFiles(files) {
    // Check limit
    const pendingCount = state.files.filter(f => f.status === 'pending').length;
    const available = MAX_FILES - pendingCount;

    if (available <= 0) {
        toast(`Maximum ${MAX_FILES} files at once`, 'error');
        return;
    }

    const toAdd = files.slice(0, available);
    if (toAdd.length < files.length) {
        toast(`Added ${toAdd.length} of ${files.length} files (limit: ${MAX_FILES})`, 'info');
    }

    toAdd.forEach(file => {
        state.files.push({
            id: Math.random().toString(36).slice(2, 9),
            file,
            name: file.name,
            size: file.size,
            ext: file.name.split('.').pop().toLowerCase(),
            status: 'pending',
            result: null
        });
    });

    render();
    updateBtn();
    if (toAdd.length && files.length === toAdd.length) {
        toast(`Added ${toAdd.length} file(s)`, 'success');
    }
}

function render() {
    el.dropArea.classList.toggle('has-files', state.files.length > 0);

    if (!state.files.length) {
        el.filesList.innerHTML = `
            <div class="drop-zone" id="drop-zone">
                <div class="drop-content">
                    <div class="drop-icon">📂</div>
                    <p class="drop-text">Drop files here <span>or click to browse</span></p>
                    <p class="drop-limit">Max ${MAX_FILES} files per batch</p>
                </div>
            </div>
        `;
        if (el.downloadAllBtn) el.downloadAllBtn.style.display = 'none';
        return;
    }

    el.filesList.innerHTML = state.files.map(f => `
        <div class="file-item ${f.status}" data-id="${f.id}">
            <span class="file-icon">${f.status === 'done' ? '✅' : ICONS[f.ext] || ICONS.default}</span>
            <div class="file-info">
                <div class="file-name">${esc(f.status === 'done' ? f.result.name : f.name)}</div>
                <div class="file-meta">
                    <span class="file-size">${formatSize(f.status === 'done' ? f.result.blob.size : f.size)}</span>
                    <span class="file-status ${f.status}">${statusText(f.status)}</span>
                </div>
                ${f.status === 'converting' ? '<div class="progress-bar"><div class="progress-fill" style="width:60%"></div></div>' : ''}
            </div>
            <div class="file-actions">
                ${f.status === 'done' ? `<button class="file-btn download" data-id="${f.id}" title="Download">↓</button>` : ''}
                <button class="file-btn remove" data-id="${f.id}" title="Remove">×</button>
            </div>
        </div>
    `).join('');

    el.filesList.querySelectorAll('.file-btn.download').forEach(btn => {
        btn.onclick = (e) => { e.stopPropagation(); download(btn.dataset.id); };
    });

    el.filesList.querySelectorAll('.file-btn.remove').forEach(btn => {
        btn.onclick = (e) => {
            e.stopPropagation();
            state.files = state.files.filter(f => f.id !== btn.dataset.id);
            render();
            updateBtn();
        };
    });

    // Show download all button if there are completed files
    const doneCount = state.files.filter(f => f.status === 'done').length;
    if (el.downloadAllBtn) {
        el.downloadAllBtn.style.display = doneCount > 1 ? 'inline-flex' : 'none';
    }
}

function statusText(s) {
    return { pending: 'Ready', converting: 'Converting...', done: 'Complete', error: 'Failed' }[s] || s;
}

function updateBtn() {
    const hasFiles = state.files.some(f => f.status === 'pending');
    const hasFormat = el.outputFormat.value !== '';
    el.convertBtn.disabled = !hasFiles || !hasFormat || state.isConverting;
}

async function convert() {
    const format = el.outputFormat.value;
    if (!format) return;

    state.isConverting = true;
    el.convertBtn.innerHTML = '<span class="spinner"></span> Converting...';
    updateBtn();

    for (const f of state.files) {
        if (f.status !== 'pending') continue;

        f.status = 'converting';
        render();

        try {
            const formData = new FormData();
            formData.append('file', f.file);
            formData.append('output_format', format);
            formData.append('quality', '100');

            const res = await fetch('/api/convert', { method: 'POST', body: formData });

            if (res.status === 429) {
                const err = await res.json();
                f.status = 'error';
                toast(err.detail, 'error');
                break; // Stop processing more files
            }

            if (!res.ok) throw new Error('Conversion failed');

            // Update remaining from header
            const remaining = res.headers.get('X-Remaining-Conversions');
            if (remaining && state.limits) {
                state.limits.remaining_today = parseInt(remaining);
                updateLimitDisplay();
            }

            f.status = 'done';
            f.result = {
                name: f.name.replace(/\.[^/.]+$/, '') + '.' + format,
                blob: await res.blob()
            };
        } catch (e) {
            f.status = 'error';
            console.error(e);
        }

        render();
    }

    state.isConverting = false;
    el.convertBtn.innerHTML = '<span class="btn-glow"></span>⚡ Convert';
    updateBtn();

    const done = state.files.filter(f => f.status === 'done').length;
    if (done) toast(`Converted ${done} file(s)!`, 'success');

    // Refresh limits
    loadLimits();
}

function download(id) {
    const f = state.files.find(x => x.id === id);
    if (!f?.result) return;
    const url = URL.createObjectURL(f.result.blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = f.result.name;
    a.click();
    URL.revokeObjectURL(url);
}

async function downloadAll() {
    const doneFiles = state.files.filter(f => f.status === 'done' && f.result);
    if (doneFiles.length === 0) return;

    // Single file - just download directly
    if (doneFiles.length === 1) {
        download(doneFiles[0].id);
        return;
    }

    // Multiple files - create ZIP
    toast('Creating ZIP file...', 'info');

    try {
        const zip = new JSZip();

        // Add each file to the ZIP
        for (const f of doneFiles) {
            zip.file(f.result.name, f.result.blob);
        }

        // Generate ZIP
        const zipBlob = await zip.generateAsync({ type: 'blob' });

        // Download the ZIP
        const url = URL.createObjectURL(zipBlob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `converted_${Date.now()}.zip`;
        a.click();
        URL.revokeObjectURL(url);

        toast(`Downloaded ${doneFiles.length} files as ZIP`, 'success');
    } catch (e) {
        console.error('Failed to create ZIP:', e);
        toast('Failed to create ZIP file', 'error');
    }
}

function clearAll() {
    if (state.files.length === 0) return;

    const confirmed = confirm('Are you sure you want to clear all files?');
    if (!confirmed) return;

    state.files = [];
    el.outputFormat.value = '';
    render();
    updateBtn();
}

function formatSize(b) {
    if (!b) return '0 B';
    const k = 1024, s = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(b) / Math.log(k));
    return (b / Math.pow(k, i)).toFixed(1) + ' ' + s[i];
}

function esc(t) { const d = document.createElement('div'); d.textContent = t; return d.innerHTML; }

function toast(msg, type = 'info') {
    const icons = { success: '✓', error: '✕', info: '◈' };
    const t = document.createElement('div');
    t.className = `toast ${type}`;
    t.innerHTML = `<span class="toast-icon">${icons[type]}</span><span class="toast-message">${esc(msg)}</span>`;
    el.toastContainer.appendChild(t);
    setTimeout(() => { t.classList.add('toast-out'); setTimeout(() => t.remove(), 250); }, 3500);
}

document.addEventListener('DOMContentLoaded', init);

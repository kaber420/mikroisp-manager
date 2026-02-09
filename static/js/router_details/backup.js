// static/js/router_details/backup.js
import { ApiClient, DomUtils } from './utils.js';
import { CONFIG, DOM_ELEMENTS } from './config.js';

// --- STATE ---
let currentFiles = [];
let activeCreateBackupModal = null;

// --- MODAL FUNCTIONS ---

function openCreateBackupModal() {
    const template = DOM_ELEMENTS.createBackupFormTemplate;
    if (!template) {
        console.error('Create Backup form template not found');
        return;
    }

    const content = template.content.cloneNode(true);
    const wrapper = document.createElement('div');
    wrapper.appendChild(content);

    activeCreateBackupModal = window.ModalUtils.showCustomModal({
        title: 'Crear Backup',
        content: wrapper,
        modalId: 'create-backup-modal',
        size: 'md',
        actions: [
            {
                text: 'Cancelar',
                handler: () => { },
                closeOnClick: true
            },
            {
                text: 'Crear Backup',
                icon: 'backup',
                primary: true,
                handler: () => handleCreateBackupSubmit(activeCreateBackupModal),
                closeOnClick: false
            }
        ]
    });
}

// --- RENDERIZADOR PARA ARCHIVOS EN ROUTER ---

function renderBackupFiles(files) {
    currentFiles = files || [];
    DOM_ELEMENTS.backupFilesList.innerHTML = (!files || files.length === 0) ? '<p class="text-text-secondary col-span-full">No hay backups.</p>' : '';
    files?.forEach(file => {
        const isBackup = file.type === 'backup';
        const card = document.createElement('div');
        card.className = `bg-surface-2 rounded-md p-2 flex justify-between items-center`;
        card.style.borderLeft = `4px solid ${isBackup ? CONFIG.COLORS.BACKUP : CONFIG.COLORS.RSC}`;

        card.innerHTML = `
            <div class="flex-1 min-w-0">
                <p class="text-sm font-medium truncate" title="${file.name}">${file.name}</p>
                <p class="text-xs text-text-secondary ml-2">${DomUtils.formatBytes(file.size)}</p>
            </div>
            <div class="flex items-center gap-1">
                <button data-filename="${file.name}" title="Guardar en servidor"
                        class="save-to-server-btn flex items-center gap-1 px-2 py-1 rounded text-xs font-semibold
                               bg-primary/10 text-primary
                               hover:bg-primary hover:text-white
                               transition-colors">
                    <span class="material-symbols-outlined text-sm">cloud_upload</span>
                </button>
                <button data-id="${file['.id'] || file.id}"
                        class="delete-backup-btn flex items-center gap-1 px-2 py-1 rounded text-xs font-semibold
                               bg-danger/10 text-danger
                               hover:bg-danger hover:text-white
                               transition-colors">
                    <span class="material-symbols-outlined text-sm">delete</span>
                </button>
            </div>
        `;
        DOM_ELEMENTS.backupFilesList.appendChild(card);
    });
    document.querySelectorAll('.delete-backup-btn').forEach(btn => btn.addEventListener('click', handleDeleteBackupFile));
    document.querySelectorAll('.save-to-server-btn').forEach(btn => btn.addEventListener('click', handleSaveToServer));
}

// --- RENDERIZADOR PARA BACKUPS LOCALES (SERVIDOR) ---

function renderLocalBackupFiles(files) {
    if (!DOM_ELEMENTS.localBackupFilesList) return;

    DOM_ELEMENTS.localBackupFilesList.innerHTML = (!files || files.length === 0)
        ? '<p class="text-text-secondary col-span-full">No hay respaldos locales para este router.</p>'
        : '';

    files?.forEach(file => {
        const isBackup = file.type === 'backup';
        const card = document.createElement('div');
        card.className = `bg-surface-2 rounded-md p-3 flex flex-col gap-2`;
        card.style.borderLeft = `4px solid ${isBackup ? CONFIG.COLORS.BACKUP : CONFIG.COLORS.RSC}`;

        // Format date from timestamp
        const modDate = new Date(file.modified * 1000);
        const dateStr = modDate.toLocaleDateString();
        const timeStr = modDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        card.innerHTML = `
            <div class="flex-1 min-w-0">
                <p class="text-sm font-medium truncate" title="${file.name}">${file.name}</p>
                <div class="flex items-center gap-2 text-xs text-text-secondary mt-1">
                    <span>${DomUtils.formatBytes(file.size)}</span>
                    <span>•</span>
                    <span>${dateStr} ${timeStr}</span>
                </div>
            </div>
            <div class="flex gap-2">
                <a href="/api/routers/${CONFIG.currentHost}/system/local-backups/download?host=${CONFIG.currentHost}&filename=${encodeURIComponent(file.name)}"
                   class="flex-1 flex items-center justify-center gap-1 px-3 py-1.5 rounded text-xs font-semibold
                          bg-primary/10 text-primary hover:bg-primary hover:text-white transition-colors"
                   download="${file.name}">
                    <span class="material-symbols-outlined text-sm">download</span>
                    <span>Descargar</span>
                </a>
                <button data-filename="${file.name}"
                   class="delete-local-backup-btn flex items-center justify-center gap-1 px-3 py-1.5 rounded text-xs font-semibold
                          bg-danger/10 text-danger hover:bg-danger hover:text-white transition-colors">
                    <span class="material-symbols-outlined text-sm">delete</span>
                </button>
            </div>
        `;
        DOM_ELEMENTS.localBackupFilesList.appendChild(card);
    });

    // Add delete event listeners
    document.querySelectorAll('.delete-local-backup-btn').forEach(btn => {
        btn.addEventListener('click', handleDeleteLocalBackup);
    });
}

// --- MANEJADORES (HANDLERS) ---

async function handleCreateBackupSubmit(modalRef) {
    const form = document.getElementById('create-backup-form');
    if (!form) return;

    const backupName = document.getElementById('modal-backup-name')?.value;
    const backupType = form.querySelector('input[name="backup_type"]:checked')?.value || 'backup';

    if (!backupName) {
        DomUtils.updateFeedback('El nombre del backup no puede estar vacío.', false);
        return;
    }

    if (modalRef) modalRef.close();
    await handleCreateBackup(backupName, backupType);
}

const handleCreateBackup = async (name, type, overwrite = false) => {
    try {
        await ApiClient.request(`/api/routers/${CONFIG.currentHost}/system/create-backup`, {
            method: 'POST',
            body: JSON.stringify({ backup_name: name, backup_type: type, overwrite: overwrite })
        });
        DomUtils.updateFeedback('Backup creado', true);
        setTimeout(window.loadFullDetailsData, 2000);
    } catch (e) {
        // Handle 409 Conflict (File Exists)
        if (e.message.includes("409") || e.message.includes("ya existe")) {
            window.ModalUtils.showConflictModal(name, type, async (action) => {
                if (action === 'overwrite') {
                    handleCreateBackup(name, type, true);
                } else if (action === 'copy') {
                    // Copia Inteligente
                    let baseName = name;
                    const match = name.match(/^(.*)\((\d+)\)$/);
                    if (match) {
                        baseName = match[1];
                    }

                    let counter = 1;
                    let nextCandidate = `${baseName}(${counter})`;

                    if (typeof currentFiles !== 'undefined' && Array.isArray(currentFiles)) {
                        const existingNames = new Set(currentFiles.map(f => f.name));
                        const ext = type === 'backup' ? '.backup' : '.rsc';

                        while (existingNames.has(nextCandidate + ext) || existingNames.has(nextCandidate)) {
                            counter++;
                            nextCandidate = `${baseName}(${counter})`;
                            if (counter > 100) break;
                        }
                    } else {
                        const matchold = name.match(/^(.*)\((\d+)\)$/);
                        if (matchold) {
                            nextCandidate = `${matchold[1]}(${parseInt(matchold[2]) + 1})`;
                        } else {
                            nextCandidate = `${name}(1)`;
                        }
                    }

                    handleCreateBackup(nextCandidate, type, false);
                }
            });
        } else {
            DomUtils.updateFeedback(e.message, false);
        }
    }
};

const handleDeleteBackupFile = (e) => {
    const fileId = e.currentTarget.dataset.id;
    DomUtils.confirmAndExecute('¿Borrar este archivo de backup del router?', async () => {
        try {
            await ApiClient.request(`/api/routers/${CONFIG.currentHost}/system/files/${encodeURIComponent(fileId)}`, { method: 'DELETE' });
            DomUtils.updateFeedback('Archivo Eliminado', true);
            window.loadFullDetailsData();
        } catch (err) { DomUtils.updateFeedback(err.message, false); }
    });
};

const handleDeleteLocalBackup = (e) => {
    const filename = e.currentTarget.dataset.filename;
    DomUtils.confirmAndExecute(`¿Eliminar el respaldo "${filename}" del servidor?`, async () => {
        try {
            await ApiClient.request(
                `/api/routers/${CONFIG.currentHost}/system/local-backups?host=${CONFIG.currentHost}&filename=${encodeURIComponent(filename)}`,
                { method: 'DELETE' }
            );
            DomUtils.updateFeedback('Respaldo eliminado del servidor', true);
            loadLocalBackupData();
        } catch (err) { DomUtils.updateFeedback(err.message, false); }
    });
};

const handleSaveToServer = async (e) => {
    const filename = e.currentTarget.dataset.filename;
    const btn = e.currentTarget;

    const originalContent = btn.innerHTML;
    btn.innerHTML = '<span class="material-symbols-outlined text-sm animate-spin">sync</span>';
    btn.disabled = true;

    try {
        await ApiClient.request(
            `/api/routers/${CONFIG.currentHost}/system/save-to-server?host=${CONFIG.currentHost}&filename=${encodeURIComponent(filename)}`,
            { method: 'POST' }
        );
        DomUtils.updateFeedback(`"${filename}" guardado en servidor`, true);
        loadLocalBackupData();
    } catch (err) {
        DomUtils.updateFeedback(err.message, false);
    } finally {
        btn.innerHTML = originalContent;
        btn.disabled = false;
    }
};

// --- CARGADOR DE DATOS ---

export function loadBackupData(fullDetails) {
    try {
        if (fullDetails && fullDetails.files) {
            renderBackupFiles(fullDetails.files);
        }
    } catch (e) {
        console.error("Error en loadBackupData:", e);
        DOM_ELEMENTS.backupFilesList.innerHTML = `<p class="text-danger">${e.message}</p>`;
    }
}

// --- CARGADOR DE BACKUPS LOCALES ---

export async function loadLocalBackupData() {
    if (!DOM_ELEMENTS.localBackupFilesList) return;

    DOM_ELEMENTS.localBackupFilesList.innerHTML = '<p class="text-text-secondary col-span-full">Cargando...</p>';

    try {
        const files = await ApiClient.request(`/api/routers/${CONFIG.currentHost}/system/local-backups?host=${CONFIG.currentHost}`);
        renderLocalBackupFiles(files);
    } catch (e) {
        console.error("Error loading local backups:", e);
        DOM_ELEMENTS.localBackupFilesList.innerHTML = `<p class="text-text-secondary col-span-full">No se pudieron cargar los respaldos locales.</p>`;
    }
}

// --- INICIALIZADOR ---

export function initBackupModule() {
    // Modal button
    DOM_ELEMENTS.createBackupBtn?.addEventListener('click', openCreateBackupModal);
    DOM_ELEMENTS.refreshLocalBackupsBtn?.addEventListener('click', loadLocalBackupData);

    // Cargar backups locales al inicio
    loadLocalBackupData();
}
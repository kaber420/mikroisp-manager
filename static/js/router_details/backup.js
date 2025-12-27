// static/js/router_details/backup.js
import { ApiClient, DomUtils } from './utils.js';
import { CONFIG, DOM_ELEMENTS } from './config.js';

// --- RENDERIZADOR PARA ARCHIVOS EN ROUTER ---

function renderBackupFiles(files) {
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

const handleCreateBackup = async (name, type, overwrite = false) => {
    try {
        await ApiClient.request(`/api/routers/${CONFIG.currentHost}/system/create-backup`, {
            method: 'POST',
            body: JSON.stringify({ backup_name: name, backup_type: type, overwrite: overwrite })
        });
        DomUtils.updateFeedback('Backup creado', true);
        setTimeout(window.loadFullDetailsData, 2000); // Recarga todo después de 2 segundos
    } catch (e) {
        // Handle 409 Conflict (File Exists)
        if (e.message.includes("409") || e.message.includes("ya existe")) {
            showConflictModal(name, type, async (action) => {
                if (action === 'overwrite') {
                    // Retry with overwrite=true
                    handleCreateBackup(name, type, true);
                } else if (action === 'copy') {
                    // Retry with new name suffix
                    // Generate new name: name(1) or name(2)...
                    // Simple heuristic: append (1) if not present, or increment if present.
                    let newName = name;
                    const match = name.match(/^(.*)\((\d+)\)$/);
                    if (match) {
                        const base = match[1];
                        const num = parseInt(match[2]) + 1;
                        newName = `${base}(${num})`;
                    } else {
                        newName = `${name}(1)`;
                    }
                    handleCreateBackup(newName, type, false);
                }
            });
        } else {
            DomUtils.updateFeedback(e.message, false);
        }
    }
};

/**
 * Muestra un modal personalizado para resolver conflictos de nombres.
 * @param {string} filename - Nombre del archivo conflictivo
 * @param {string} type - Tipo de backup
 * @param {Function} callback - (action) => void. action puede ser 'overwrite', 'copy'
 */
function showConflictModal(filename, type, callback) {
    const existingModal = document.getElementById('conflict-modal');
    if (existingModal) existingModal.remove();

    const currentThemeClass = document.documentElement.className.includes('dark') ? 'dark' : '';

    const modalHtml = `
    <div id="conflict-modal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 ${currentThemeClass}">
        <div class="bg-surface-1 rounded-xl shadow-2xl max-w-md w-full border border-border overflow-hidden animate-in fade-in zoom-in duration-200">
            <!-- Header -->
            <div class="p-4 border-b border-border flex justify-between items-center bg-surface-2">
                <h3 class="text-lg font-semibold text-text-primary flex items-center gap-2">
                    <span class="material-symbols-outlined text-warning">warning</span>
                    Archivo Existente
                </h3>
                <button id="btn-cancel-x" class="text-text-secondary hover:text-text-primary transition-colors">
                    <span class="material-symbols-outlined">close</span>
                </button>
            </div>
            
            <!-- Body -->
            <div class="p-6">
                <p class="text-text-secondary mb-4">
                    El archivo <span class="font-bold text-text-primary">"${filename}"</span> ya existe en el router.
                </p>
                <p class="text-sm text-text-tertiary">
                    ¿Deseas sobrescribirlo o crear una copia con un nuevo nombre?
                </p>
            </div>
            
            <!-- Footer -->
            <div class="p-4 border-t border-border bg-surface-2 flex justify-end gap-3">
                <button id="btn-cancel" class="px-4 py-2 rounded-lg text-sm font-medium text-text-secondary hover:bg-surface-3 transition-colors">
                    Cancelar
                </button>
                <button id="btn-copy" class="px-4 py-2 rounded-lg text-sm font-medium bg-primary/10 text-primary hover:bg-primary hover:text-white transition-colors flex items-center gap-1">
                    <span class="material-symbols-outlined text-sm">filter_none</span>
                    Crear Copia
                </button>
                <button id="btn-overwrite" class="px-4 py-2 rounded-lg text-sm font-medium bg-danger/10 text-danger hover:bg-danger hover:text-white transition-colors flex items-center gap-1">
                    <span class="material-symbols-outlined text-sm">save_as</span>
                    Sobrescribir
                </button>
            </div>
        </div>
    </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHtml);

    const modal = document.getElementById('conflict-modal');
    const cleanup = () => modal.remove();

    document.getElementById('btn-cancel').onclick = cleanup;
    document.getElementById('btn-cancel-x').onclick = cleanup;

    document.getElementById('btn-copy').onclick = () => {
        callback('copy');
        cleanup();
    };

    document.getElementById('btn-overwrite').onclick = () => {
        callback('overwrite');
        cleanup();
    };
}

const handleCreateBackupForm = (e) => {
    e.preventDefault();
    const backupNameEl = DOM_ELEMENTS.backupNameInput;
    if (backupNameEl && backupNameEl.value) {
        handleCreateBackup(backupNameEl.value, e.submitter.dataset.type);
    } else {
        DomUtils.updateFeedback('El nombre del backup no puede estar vacío.', false);
    }
};

const handleDeleteBackupFile = (e) => {
    const fileId = e.currentTarget.dataset.id;
    DomUtils.confirmAndExecute('¿Borrar este archivo de backup del router?', async () => {
        try {
            await ApiClient.request(`/api/routers/${CONFIG.currentHost}/system/files/${encodeURIComponent(fileId)}`, { method: 'DELETE' });
            DomUtils.updateFeedback('Archivo Eliminado', true);
            window.loadFullDetailsData(); // Recarga todo
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
            loadLocalBackupData(); // Recarga solo los backups locales
        } catch (err) { DomUtils.updateFeedback(err.message, false); }
    });
};

const handleSaveToServer = async (e) => {
    const filename = e.currentTarget.dataset.filename;
    const btn = e.currentTarget;

    // Mostrar estado de carga
    const originalContent = btn.innerHTML;
    btn.innerHTML = '<span class="material-symbols-outlined text-sm animate-spin">sync</span>';
    btn.disabled = true;

    try {
        await ApiClient.request(
            `/api/routers/${CONFIG.currentHost}/system/save-to-server?host=${CONFIG.currentHost}&filename=${encodeURIComponent(filename)}`,
            { method: 'POST' }
        );
        DomUtils.updateFeedback(`"${filename}" guardado en servidor`, true);
        loadLocalBackupData(); // Actualizar la lista de backups locales
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
        // La data de archivos ahora viene del loader principal
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
    DOM_ELEMENTS.createBackupForm?.addEventListener('submit', handleCreateBackupForm);
    DOM_ELEMENTS.refreshLocalBackupsBtn?.addEventListener('click', loadLocalBackupData);

    // Cargar backups locales al inicio
    loadLocalBackupData();
}
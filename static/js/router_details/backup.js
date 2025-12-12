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
            <button data-id="${file['.id'] || file.id}"
                    class="delete-backup-btn flex items-center gap-1 px-2 py-1 rounded text-xs font-semibold
                           bg-danger/10 text-danger
                           hover:bg-danger hover:text-white
                           transition-colors">
                <span class="material-symbols-outlined text-sm">delete</span>
                <span>Delete</span>
            </button>
        `;
        DOM_ELEMENTS.backupFilesList.appendChild(card);
    });
    document.querySelectorAll('.delete-backup-btn').forEach(btn => btn.addEventListener('click', handleDeleteBackupFile));
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
            <a href="/api/routers/${CONFIG.currentHost}/system/local-backups/download?host=${CONFIG.currentHost}&filename=${encodeURIComponent(file.name)}"
               class="download-local-backup-btn flex items-center justify-center gap-1 px-3 py-1.5 rounded text-xs font-semibold
                      bg-primary/10 text-primary
                      hover:bg-primary hover:text-white
                      transition-colors"
               download="${file.name}">
                <span class="material-symbols-outlined text-sm">download</span>
                <span>Descargar</span>
            </a>
        `;
        DOM_ELEMENTS.localBackupFilesList.appendChild(card);
    });
}

// --- MANEJADORES (HANDLERS) ---

const handleCreateBackup = async (name, type) => {
    try {
        await ApiClient.request(`/api/routers/${CONFIG.currentHost}/system/create-backup`, {
            method: 'POST',
            body: JSON.stringify({ backup_name: name, backup_type: type })
        });
        DomUtils.updateFeedback('Backup creado', true);
        setTimeout(window.loadFullDetailsData, 2000); // Recarga todo después de 2 segundos
    } catch (e) { DomUtils.updateFeedback(e.message, false); }
};

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
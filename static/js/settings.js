document.addEventListener('DOMContentLoaded', () => {

    const API_BASE_URL = window.location.origin;
    const settingsForm = document.getElementById('settings-form');
    const saveStatus = document.getElementById('save-status');
    const saveButton = document.getElementById('save-button');
    const saveSpinner = document.getElementById('save-spinner');
    const forceBillingBtn = document.getElementById('force-billing-btn');

    async function loadSettings() {
        if (!settingsForm) return;

        try {
            const response = await fetch(`${API_BASE_URL}/api/settings`);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || "Failed to load settings");
            }
            const settings = await response.json();

            for (const [key, value] of Object.entries(settings)) {
                const inputElement = document.getElementById(key);
                if (inputElement) {
                    inputElement.value = value;
                }
            }
        } catch (error) {
            console.error("Error loading settings:", error);
            showToast("Could not load settings. Please check the API connection.", 'danger');
        }
    }

    async function handleSettingsSubmit(event) {
        event.preventDefault();
        saveStatus.classList.add('hidden');
        saveButton.disabled = true;
        saveSpinner.classList.remove('hidden');

        const formData = new FormData(settingsForm);
        const settingsData = Object.fromEntries(formData.entries());

        try {
            const response = await fetch(`${API_BASE_URL}/api/settings`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(settingsData)
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || "Failed to save settings");
            }

            saveStatus.textContent = "Settings saved successfully!";
            saveStatus.classList.remove('hidden', 'text-danger');
            saveStatus.classList.add('text-success');
            setTimeout(() => {
                saveStatus.classList.add('hidden');
            }, 3000);

        } catch (error) {
            console.error("Error saving settings:", error);
            saveStatus.textContent = `Error: ${error.message}`;
            saveStatus.classList.remove('hidden', 'text-success');
            saveStatus.classList.add('text-danger');
        } finally {
            saveButton.disabled = false;
            saveSpinner.classList.add('hidden');
        }
    }

    // --- Manejo del Botón de Fuerza (Fase 6) ---
    if (forceBillingBtn) {
        forceBillingBtn.addEventListener('click', async () => {
            if (!confirm("Are you sure? This will update statuses (Active/Pending/Suspended) for ALL clients based on their payments.")) return;

            const originalText = forceBillingBtn.innerHTML;
            forceBillingBtn.innerHTML = '<span class="material-symbols-outlined animate-spin">sync</span> Processing...';
            forceBillingBtn.disabled = true;

            try {
                const res = await fetch(`${API_BASE_URL}/api/settings/force-billing`, { method: 'POST' });
                if (!res.ok) throw new Error('Request failed');
                const data = await res.json();
                showToast(`Done! Processed: ${data.stats.processed}, Active: ${data.stats.active || 0}, Pending: ${data.stats.pendiente || 0}, Suspended: ${data.stats.suspended || 0}`, 'success', 5000);
            } catch (e) {
                showToast("Error updating statuses: " + e.message, 'danger');
            } finally {
                forceBillingBtn.innerHTML = originalText;
                forceBillingBtn.disabled = false;
            }
        });
    }

    if (settingsForm) {
        settingsForm.addEventListener('submit', handleSettingsSubmit);
        loadSettings();
    }

    // --- AUDIT LOGS FUNCTIONALITY ---
    initAuditLogs();
});

// === AUDIT LOGS MODULE ===

// Global state for audit logs pagination
let auditCurrentPage = 1;
let auditPageSize = 20;
let auditTotalPages = 1;
let auditActionFilter = 'all';
let auditUserFilter = 'all';

const API_AUDIT_URL = window.location.origin;

// Expose functions to window for inline event handlers
window.loadAuditLogs = loadAuditLogs;
window.changeAuditPageSize = changeAuditPageSize;
window.changeAuditPage = changeAuditPage;

async function initAuditLogs() {
    const auditSection = document.getElementById('audit-section');
    if (!auditSection) return;

    // Load filter options first
    await loadAuditFilters();
    // Then load the logs
    await loadAuditLogs();
}

async function loadAuditFilters() {
    const actionSelect = document.getElementById('audit-action-filter');
    const userSelect = document.getElementById('audit-user-filter');

    if (!actionSelect || !userSelect) return;

    try {
        const res = await fetch(`${API_AUDIT_URL}/api/settings/audit-logs/filters`);
        if (!res.ok) return;

        const filters = await res.json();

        // Populate action filter
        filters.actions.forEach(action => {
            const opt = document.createElement('option');
            opt.value = action;
            opt.textContent = action;
            actionSelect.appendChild(opt);
        });

        // Populate user filter
        filters.usernames.forEach(username => {
            const opt = document.createElement('option');
            opt.value = username;
            opt.textContent = username;
            userSelect.appendChild(opt);
        });
    } catch (e) {
        console.error('Error loading audit filters:', e);
    }
}

async function loadAuditLogs() {
    const tbody = document.getElementById('audit-logs-body');
    const infoSpan = document.getElementById('audit-pagination-info');
    const btnPrev = document.getElementById('audit-btn-prev');
    const btnNext = document.getElementById('audit-btn-next');

    if (!tbody) return;

    // Get current filter values
    const actionSelect = document.getElementById('audit-action-filter');
    const userSelect = document.getElementById('audit-user-filter');

    if (actionSelect) auditActionFilter = actionSelect.value;
    if (userSelect) auditUserFilter = userSelect.value;

    tbody.innerHTML = `
        <tr>
            <td colspan="6" class="px-4 py-8 text-center text-text-secondary">
                <span class="material-symbols-outlined animate-spin">sync</span>
                Cargando...
            </td>
        </tr>
    `;

    try {
        let url = `${API_AUDIT_URL}/api/settings/audit-logs?page=${auditCurrentPage}&page_size=${auditPageSize}`;
        if (auditActionFilter !== 'all') url += `&action=${encodeURIComponent(auditActionFilter)}`;
        if (auditUserFilter !== 'all') url += `&username=${encodeURIComponent(auditUserFilter)}`;

        const res = await fetch(url);
        if (!res.ok) {
            throw new Error('Failed to load audit logs');
        }

        const data = await res.json();
        const logs = data.items;
        auditTotalPages = data.total_pages;

        tbody.innerHTML = '';

        if (logs.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="px-4 py-8 text-center text-text-secondary">
                        <span class="material-symbols-outlined text-4xl mb-2">security</span>
                        <p>No hay logs de auditoría.</p>
                    </td>
                </tr>
            `;
        } else {
            logs.forEach(log => {
                const row = createAuditLogRow(log);
                tbody.innerHTML += row;
            });
        }

        // Update pagination info
        if (infoSpan) {
            const start = (auditCurrentPage - 1) * auditPageSize + 1;
            const end = Math.min(start + auditPageSize - 1, data.total);
            infoSpan.textContent = data.total > 0
                ? `Mostrando ${start}-${end} de ${data.total}`
                : 'Sin resultados';
        }

        // Update button states
        if (btnPrev) btnPrev.disabled = auditCurrentPage <= 1;
        if (btnNext) btnNext.disabled = auditCurrentPage >= auditTotalPages;

    } catch (error) {
        console.error('Error loading audit logs:', error);
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="px-4 py-8 text-center text-danger">
                    <span class="material-symbols-outlined text-4xl mb-2">error</span>
                    <p>Error cargando logs de auditoría.</p>
                </td>
            </tr>
        `;
    }
}

function createAuditLogRow(log) {
    // Format timestamp
    const dateObj = new Date(log.timestamp);
    const timeStr = dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const dateStr = dateObj.toLocaleDateString();

    // Action badge colors
    const actionColors = {
        'DELETE': 'text-danger bg-danger/10 border-danger/20',
        'CREATE': 'text-success bg-success/10 border-success/20',
        'UPDATE': 'text-warning bg-warning/10 border-warning/20',
        'LOGIN': 'text-primary bg-primary/10 border-primary/20',
    };
    const actionColor = actionColors[log.action] || 'text-text-secondary bg-surface-2 border-white/10';

    // Status badge
    const statusBadge = log.status === 'success'
        ? '<span class="inline-flex items-center gap-1 text-success"><span class="material-symbols-outlined text-sm">check_circle</span> OK</span>'
        : '<span class="inline-flex items-center gap-1 text-danger"><span class="material-symbols-outlined text-sm">error</span> Error</span>';

    // Resource display
    const resource = `${log.resource_type}/${log.resource_id}`;

    return `
        <tr class="border-b border-white/5 hover:bg-white/5 transition-colors">
            <td class="px-4 py-3 whitespace-nowrap">
                <span class="block text-text-primary font-medium">${timeStr}</span>
                <span class="text-xs text-text-secondary">${dateStr}</span>
            </td>
            <td class="px-4 py-3">
                <span class="text-text-primary font-medium">${log.username}</span>
                <span class="text-xs text-text-secondary block">${log.user_role || ''}</span>
            </td>
            <td class="px-4 py-3">
                <span class="inline-flex items-center px-2 py-1 rounded text-xs font-bold border ${actionColor}">
                    ${log.action}
                </span>
            </td>
            <td class="px-4 py-3 text-text-secondary">
                <span class="font-mono text-xs">${resource}</span>
            </td>
            <td class="px-4 py-3 text-text-secondary">
                <span class="font-mono text-xs">${log.ip_address || 'N/A'}</span>
            </td>
            <td class="px-4 py-3">
                ${statusBadge}
            </td>
        </tr>
    `;
}

function changeAuditPageSize(size) {
    auditPageSize = parseInt(size);
    auditCurrentPage = 1;
    loadAuditLogs();
}

function changeAuditPage(direction) {
    const newPage = auditCurrentPage + direction;
    if (newPage > 0 && newPage <= auditTotalPages) {
        auditCurrentPage = newPage;
        loadAuditLogs();
    }
}
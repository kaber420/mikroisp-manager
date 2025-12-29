// static/js/router_details/ssl.js
/**
 * SSL/TLS Configuration Module
 * Handles: Security badge, SSL status check, SSL provisioning modal
 */

import { ApiClient, DomUtils } from './utils.js';
import { CONFIG } from './config.js';

// DOM Elements Getter
function getSslElements() {
    return {
        sslBadge: document.getElementById('ssl-security-badge'),
        sslModal: document.getElementById('ssl-modal'),
        sslForm: document.getElementById('ssl-provision-form'),
        sslMethodSelect: document.getElementById('ssl-method'),
        sslInstallCaCheckbox: document.getElementById('ssl-install-ca'),
        sslStatusInfo: document.getElementById('ssl-status-info'),
        closeSslModalBtn: document.getElementById('close-ssl-modal-btn'),
        cancelSslBtn: document.getElementById('cancel-ssl-btn')
    };
}

/**
 * Fetch and display the SSL status for the current router.
 * Updates the security badge in the header.
 */
export async function loadSslStatus() {
    const { sslBadge } = getSslElements();
    try {
        const status = await ApiClient.request(`/api/routers/${CONFIG.currentHost}/ssl/status`);
        updateSecurityBadge(status);
        return status;
    } catch (e) {
        console.error('Error loading SSL status:', e);
        // Show badge as unknown/error
        if (sslBadge) {
            sslBadge.classList.remove('hidden'); // Ensure visible
            sslBadge.textContent = '⚠️ SSL Desconocido';
            sslBadge.className = 'text-xs font-semibold px-2 py-1 rounded-full bg-gray-500 text-white';
        }
        return null;
    }
}

/**
 * Update the security badge based on SSL status.
 */
function updateSecurityBadge(status) {
    const { sslBadge } = getSslElements();
    if (!sslBadge) return;

    // FORCE VISIBILITY
    sslBadge.classList.remove('hidden');

    if (!status) {
        // Unknown status but show badge to allow retry
        sslBadge.textContent = '❓ Estado SSL';
        sslBadge.className = 'text-xs font-semibold px-2 py-1 rounded-full bg-gray-500 text-white cursor-pointer hover:bg-gray-600';
        sslBadge.title = 'No se pudo obtener estado SSL. Click para intentar de nuevo.';
        return;
    }

    if (!status.ssl_enabled) {
        // Insecure
        sslBadge.textContent = '🔴 INSEGURO';
        sslBadge.className = 'text-xs font-semibold px-2 py-1 rounded-full bg-red-600 text-white cursor-pointer hover:bg-red-700';
        sslBadge.title = 'SSL no está habilitado. Haz click para configurar.';
    } else if (status.is_trusted) {
        // Secure
        sslBadge.textContent = '🟢 SEGURO';
        sslBadge.className = 'text-xs font-semibold px-2 py-1 rounded-full bg-green-600 text-white cursor-pointer hover:bg-green-700';
        sslBadge.title = `SSL activo con certificado "${status.certificate_name}"`;
    } else {
        // Self-signed
        sslBadge.textContent = '🟡 AUTO-FIRMADO';
        sslBadge.className = 'text-xs font-semibold px-2 py-1 rounded-full bg-yellow-600 text-white cursor-pointer hover:bg-yellow-700';
        sslBadge.title = 'SSL activo pero con certificado auto-firmado. Haz click para configurar.';
    }

    // Safety check - ensure hidden is gone (redundant but safe)
    sslBadge.classList.remove('hidden');
}

/**
 * Show the SSL configuration modal.
 */
export function showSslModal() {
    const { sslModal } = getSslElements();
    if (sslModal) {
        sslModal.classList.remove('hidden');
        sslModal.classList.add('flex');
        loadSslStatusInModal();
    }
}

/**
 * Hide the SSL configuration modal.
 */
export function hideSslModal() {
    const { sslModal } = getSslElements();
    if (sslModal) {
        sslModal.classList.add('hidden');
        sslModal.classList.remove('flex');
    }
}

/**
 * Load and display current SSL status in the modal.
 */
async function loadSslStatusInModal() {
    const { sslStatusInfo } = getSslElements();
    if (!sslStatusInfo) return;

    try {
        const status = await ApiClient.request(`/api/routers/${CONFIG.currentHost}/ssl/status`);

        let statusHtml = '';
        if (status.ssl_enabled) {
            if (status.is_trusted) {
                statusHtml = `<span class="text-green-400">✓</span> SSL está <strong>ACTIVO</strong> y <strong>SEGURO</strong><br>
                    <span class="text-text-secondary">Certificado: ${status.certificate_name}</span>`;
            } else {
                statusHtml = `<span class="text-yellow-400">⚠️</span> SSL está activo pero <strong>AUTO-FIRMADO</strong><br>
                    <span class="text-text-secondary">Re-provisiona para usar la CA interna.</span>`;
            }
        } else {
            statusHtml = `<span class="text-red-400">✗</span> SSL está <strong>DESHABILITADO</strong><br>
                <span class="text-text-secondary">Provisiona para habilitar conexiones seguras.</span>`;
        }

        sslStatusInfo.innerHTML = statusHtml;
        sslStatusInfo.classList.remove('hidden');
    } catch (e) {
        sslStatusInfo.innerHTML = '<span class="text-red-400">Error</span> al obtener estado SSL.';
        sslStatusInfo.classList.remove('hidden');
    }
}

/**
 * Provision SSL on the router.
 */
async function provisionSsl(method, installCa) {
    const btn = document.getElementById('provision-ssl-btn');
    const originalText = btn?.textContent;

    try {
        if (btn) {
            btn.disabled = true;
            btn.textContent = 'Provisionando...';
        }

        const result = await ApiClient.request(`/api/routers/${CONFIG.currentHost}/ssl/provision`, {
            method: 'POST',
            body: JSON.stringify({
                method: method,
                install_ca: installCa
            })
        });

        DomUtils.updateFeedback(`SSL provisionado correctamente: ${result.message}`, true);
        hideSslModal();

        // Re-check SSL status to update badge
        await loadSslStatus();

    } catch (e) {
        console.error('SSL provisioning failed:', e);
        DomUtils.updateFeedback(`Error al provisionar SSL: ${e.message || e}`, false);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.textContent = originalText;
        }
    }
}

/**
 * Initialize the SSL module (event listeners).
 */
export function initSslModule() {
    const { sslBadge, closeSslModalBtn, cancelSslBtn, sslModal, sslForm, sslMethodSelect, sslInstallCaCheckbox } = getSslElements();

    // Badge click opens modal
    if (sslBadge) {
        sslBadge.addEventListener('click', showSslModal);
    }

    // Modal close buttons
    if (closeSslModalBtn) {
        closeSslModalBtn.addEventListener('click', hideSslModal);
    }
    if (cancelSslBtn) {
        cancelSslBtn.addEventListener('click', hideSslModal);
    }

    // Close on background click
    if (sslModal) {
        sslModal.addEventListener('click', (e) => {
            if (e.target === sslModal) {
                hideSslModal();
            }
        });
    }

    // Form submission
    if (sslForm) {
        sslForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const method = sslMethodSelect?.value || 'router-side';
            const installCa = sslInstallCaCheckbox?.checked ?? true;
            await provisionSsl(method, installCa);
        });
    }

    // Initial status load - wrapped in try/catch to never break page
    try {
        // [MODIFIED] Force show badge immediately
        if (sslBadge) {
            sslBadge.classList.remove('hidden');
            // Show a neutral state while loading
            sslBadge.innerHTML = '<span class="animate-pulse">...</span>';
            sslBadge.className = 'text-xs font-semibold px-2 py-1 rounded-full bg-gray-600 text-white cursor-wait';
            sslBadge.title = 'Cargando estado SSL...';
        }

        loadSslStatus().catch(err => {
            console.warn('SSL status check failed (non-critical):', err);
            // Even on error, show the badge so user can retry
            if (sslBadge) {
                sslBadge.textContent = '❌ Error SSL';
                sslBadge.className = 'text-xs font-semibold px-2 py-1 rounded-full bg-red-600 text-white cursor-pointer hover:bg-red-700';
                sslBadge.classList.remove('hidden');
            }
        });
    } catch (e) {
        console.warn('SSL module init error (non-critical):', e);
    }
}

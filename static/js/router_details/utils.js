// static/js/router_details/utils.js
import { CONFIG, DOM_ELEMENTS, state } from './config.js';

/**
 * Clase unificada para todas las peticiones a la API.
 */
export class ApiClient {
    static async request(url, options = {}) {
        const fetchOptions = {
            ...options,
            headers: { 'Content-Type': 'application/json', ...options.headers },
        };
        if (!options.method || ['GET', 'DELETE'].includes(options.method?.toUpperCase())) {
            delete fetchOptions.headers['Content-Type'];
        }

        const response = await fetch(CONFIG.API_BASE_URL + url, fetchOptions);

        if (!response.ok) {
            if (response.status === 204) return null;

            const errorData = await response.json().catch(() => ({ detail: response.statusText }));
            let errorMessage = 'Error en la petición';

            if (errorData.detail) {
                if (Array.isArray(errorData.detail)) {
                    errorMessage = errorData.detail
                        .map(err => `${err.loc[err.loc.length - 1]}: ${err.msg}`)
                        .join('; ');
                } else {
                    errorMessage = errorData.detail;
                }
            } else if (response.statusText) {
                errorMessage = response.statusText;
            }
            throw new Error(errorMessage);
        }

        if (response.status === 204) return null;

        // --- Defensive JSON parsing ---
        const responseText = await response.text();
        if (!responseText) {
            return { status: 'success', message: 'Operación completada sin respuesta.' };
        }

        try {
            return JSON.parse(responseText);
        } catch (e) {
            console.warn("API response was not valid JSON. Treating as plain text.", responseText);
            // Return a valid object that looks like our other responses
            return { status: 'success_non_json', message: responseText };
        }
    }
}

/**
 * Clase de utilidades para manipular el DOM.
 */
export class DomUtils {
    static formatBytes(bytes) {
        if (!bytes || bytes === 0 || bytes === '0') return '0 Bytes';
        const k = 1024;
        const bytesNum = parseInt(bytes, 10);
        if (isNaN(bytesNum) || bytesNum === 0) return '0 Bytes'; // Extra safety for parsed 0

        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytesNum) / Math.log(k));
        return parseFloat((bytesNum / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }


    /**
     * Sanitize error messages by removing sensitive information
     */
    static sanitizeError(message) {
        if (!message) return 'An error occurred';

        let sanitized = String(message);

        // Remove IP addresses (IPv4)
        sanitized = sanitized.replace(/\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b/g, '[IP]');

        // Remove "failure:" prefix from MikroTik errors
        sanitized = sanitized.replace(/^failure:\s*/gi, '');

        // Remove technical stack traces
        sanitized = sanitized.replace(/\s+at\s+.+$/gm, '');

        // Truncate very long messages
        if (sanitized.length > 120) {
            sanitized = sanitized.substring(0, 120) + '...';
        }

        return sanitized;
    }

    /**
     * Show feedback message using Toast notifications
     * @param {string} message - The message to display
     * @param {boolean} isSuccess - Whether this is a success or error message
     * @param {Error|string} originalError - Optional original error for console logging
     */
    static updateFeedback(message, isSuccess = true, originalError = null) {
        const toastType = isSuccess ? 'success' : 'danger';

        if (isSuccess) {
            // Success messages are already user-friendly
            showToast(message, toastType);
        } else {
            // Sanitize error messages
            const sanitized = DomUtils.sanitizeError(message);
            showToast(sanitized, toastType);

            // Log full error details to console for debugging
            console.error('[Router Operation Error]', originalError || message);
        }
    }

    static updateBackupNameInput() {
        if (DOM_ELEMENTS.backupNameInput) {
            const now = new Date();
            const dateStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
            DOM_ELEMENTS.backupNameInput.value = `${state.currentRouterName}-${dateStr}`;
        }
    }

    /**
     * Muestra un modal de confirmación estilizado.
     * @param {Object} options - Opciones del modal
     * @param {string} options.title - Título del modal (default: 'Confirmar Acción')
     * @param {string} options.message - Mensaje a mostrar
     * @param {string} options.confirmText - Texto del botón confirmar (default: 'Confirmar')
     * @param {string} options.cancelText - Texto del botón cancelar (default: 'Cancelar')
     * @param {string} options.confirmIcon - Icono Material del botón confirmar (default: 'check')
     * @param {string} options.type - Tipo de modal: 'danger', 'warning', 'info' (default: 'danger')
     * @returns {Promise<boolean>} - true si confirmó, false si canceló
     */
    static showConfirmModal(options = {}) {
        return new Promise((resolve) => {
            const {
                title = 'Confirmar Acción',
                message = '¿Estás seguro?',
                confirmText = 'Confirmar',
                cancelText = 'Cancelar',
                confirmIcon = 'check',
                type = 'danger'
            } = options;

            // Remove existing modal if present
            const existingModal = document.getElementById('confirm-modal');
            if (existingModal) existingModal.remove();

            // Type-based styling
            const typeStyles = {
                danger: {
                    icon: 'warning',
                    iconColor: 'text-danger',
                    btnBg: 'bg-danger/10',
                    btnText: 'text-danger',
                    btnHoverBg: 'hover:bg-danger',
                    btnHoverText: 'hover:text-white'
                },
                warning: {
                    icon: 'warning',
                    iconColor: 'text-warning',
                    btnBg: 'bg-warning/10',
                    btnText: 'text-warning',
                    btnHoverBg: 'hover:bg-warning',
                    btnHoverText: 'hover:text-white'
                },
                info: {
                    icon: 'info',
                    iconColor: 'text-primary',
                    btnBg: 'bg-primary/10',
                    btnText: 'text-primary',
                    btnHoverBg: 'hover:bg-primary',
                    btnHoverText: 'hover:text-white'
                }
            };

            const style = typeStyles[type] || typeStyles.danger;

            const modalHtml = `
            <div id="confirm-modal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
                <div class="bg-surface-1 rounded-xl shadow-2xl max-w-md w-full border border-border overflow-hidden animate-in fade-in zoom-in duration-200">
                    <!-- Header -->
                    <div class="p-4 border-b border-border flex justify-between items-center bg-surface-2">
                        <h3 class="text-lg font-semibold text-text-primary flex items-center gap-2">
                            <span class="material-symbols-outlined ${style.iconColor}">${style.icon}</span>
                            ${title}
                        </h3>
                        <button id="confirm-modal-close-x" class="text-text-secondary hover:text-text-primary transition-colors">
                            <span class="material-symbols-outlined">close</span>
                        </button>
                    </div>
                    
                    <!-- Body -->
                    <div class="p-6">
                        <p class="text-text-secondary">${message}</p>
                    </div>
                    
                    <!-- Footer -->
                    <div class="p-4 border-t border-border bg-surface-2 flex justify-end gap-3">
                        <button id="confirm-modal-cancel" class="px-4 py-2 rounded-lg text-sm font-medium text-text-secondary hover:bg-surface-3 transition-colors">
                            ${cancelText}
                        </button>
                        <button id="confirm-modal-confirm" class="px-4 py-2 rounded-lg text-sm font-medium ${style.btnBg} ${style.btnText} ${style.btnHoverBg} ${style.btnHoverText} transition-colors flex items-center gap-1">
                            <span class="material-symbols-outlined text-sm">${confirmIcon}</span>
                            ${confirmText}
                        </button>
                    </div>
                </div>
            </div>
            `;

            document.body.insertAdjacentHTML('beforeend', modalHtml);

            const modal = document.getElementById('confirm-modal');

            const cleanup = (result) => {
                modal.remove();
                resolve(result);
            };

            // Event listeners
            document.getElementById('confirm-modal-cancel').onclick = () => cleanup(false);
            document.getElementById('confirm-modal-close-x').onclick = () => cleanup(false);
            document.getElementById('confirm-modal-confirm').onclick = () => cleanup(true);

            // Close on backdrop click
            modal.addEventListener('click', (e) => {
                if (e.target === modal) cleanup(false);
            });

            // Close on Escape key
            const handleEscape = (e) => {
                if (e.key === 'Escape') {
                    document.removeEventListener('keydown', handleEscape);
                    cleanup(false);
                }
            };
            document.addEventListener('keydown', handleEscape);

            // Focus confirm button for accessibility
            document.getElementById('confirm-modal-confirm').focus();
        });
    }

    /**
     * Muestra un modal de confirmación y ejecuta el callback si se confirma.
     * @param {string} message - Mensaje a mostrar
     * @param {Function} callback - Función a ejecutar si se confirma
     * @param {Object} options - Opciones adicionales del modal
     */
    static async confirmAndExecute(message, callback, options = {}) {
        const confirmed = await DomUtils.showConfirmModal({
            message,
            title: options.title || 'Confirmar Acción',
            confirmText: options.confirmText || 'Confirmar',
            confirmIcon: options.confirmIcon || 'delete',
            type: options.type || 'danger',
            ...options
        });

        if (confirmed) {
            callback();
        }
    }
}
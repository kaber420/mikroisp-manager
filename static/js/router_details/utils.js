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

    static confirmAndExecute(message, callback) {
        if (confirm(message)) {
            callback();
        }
    }
}
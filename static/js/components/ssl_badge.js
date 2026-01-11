// static/js/components/ssl_badge.js
/**
 * Reusable SSL Security Badge Component
 * 
 * Displays SSL status for any device type (router, ap, switch).
 * Shows: 🔴 INSEGURO, 🟡 AUTO-FIRMADO, 🟢 SEGURO
 */

export class SslBadge {
    /**
     * Create an SSL Badge instance.
     * @param {Object} config - Configuration object
     * @param {string} config.deviceType - API path: 'routers', 'aps', or 'switches'
     * @param {string} config.host - Device host/IP
     * @param {string} [config.elementId='ssl-security-badge'] - DOM element ID
     */
    constructor(config) {
        this.elementId = config.elementId || 'ssl-security-badge';
        this.deviceType = config.deviceType; // 'routers', 'aps', 'switches'
        this.host = config.host;
        this.element = document.getElementById(this.elementId);
    }

    /**
     * Initialize the badge - load status and render.
     */
    async init() {
        if (!this.element) {
            console.warn(`SslBadge: Element #${this.elementId} not found`);
            return;
        }
        this.setLoading();
        await this.fetchAndRender();
    }

    /**
     * Show loading state on the badge.
     */
    setLoading() {
        if (!this.element) return;
        this.element.classList.remove('hidden');
        this.element.innerHTML = '<span class="animate-pulse">...</span>';
        this.element.className = 'text-xs font-semibold px-2 py-1 rounded-full bg-gray-600 text-white cursor-wait';
        this.element.title = 'Cargando estado SSL...';
    }

    /**
     * Fetch SSL status from API and render the badge.
     */
    async fetchAndRender() {
        try {
            // Standard endpoint: /api/{deviceType}/{host}/ssl/status
            const response = await fetch(`/api/${this.deviceType}/${this.host}/ssl/status`);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const status = await response.json();
            this.render(status);
        } catch (e) {
            console.error('SslBadge: Error fetching SSL status:', e);
            this.renderError();
        }
    }

    /**
     * Render the badge based on SSL status.
     * @param {Object} status - SSL status from API
     */
    render(status) {
        if (!this.element) return;

        // Force visibility
        this.element.classList.remove('hidden');

        if (!status) {
            this.element.textContent = '❓ Estado SSL';
            this.element.className = 'text-xs font-semibold px-2 py-1 rounded-full bg-gray-500 text-white';
            this.element.title = 'No se pudo obtener estado SSL.';
            return;
        }

        if (!status.ssl_enabled) {
            // Insecure - Red
            this.element.textContent = '🔴 INSEGURO';
            this.element.className = 'text-xs font-semibold px-2 py-1 rounded-full bg-red-600 text-white';
            this.element.title = 'SSL no está habilitado.';
        } else if (status.is_trusted) {
            // Secure - Green
            this.element.textContent = '🟢 SEGURO';
            this.element.className = 'text-xs font-semibold px-2 py-1 rounded-full bg-green-600 text-white';
            this.element.title = `SSL activo con certificado "${status.certificate_name || 'N/A'}"`;
        } else {
            // Self-signed - Yellow
            this.element.textContent = '🟡 AUTO-FIRMADO';
            this.element.className = 'text-xs font-semibold px-2 py-1 rounded-full bg-yellow-600 text-white';
            this.element.title = 'SSL activo pero con certificado auto-firmado.';
        }
    }

    /**
     * Render error state.
     */
    renderError() {
        if (!this.element) return;
        this.element.classList.remove('hidden');
        this.element.textContent = '❌ Error SSL';
        this.element.className = 'text-xs font-semibold px-2 py-1 rounded-full bg-red-600 text-white';
        this.element.title = 'Error al obtener estado SSL.';
    }

    /**
     * Refresh the badge by re-fetching status.
     */
    async refresh() {
        await this.fetchAndRender();
    }
}

/**
 * Convenience function to initialize an SSL badge.
 * @param {Object} config - Same as SslBadge constructor
 * @returns {SslBadge} The initialized badge instance
 */
export function initSslBadge(config) {
    const badge = new SslBadge(config);
    badge.init();
    return badge;
}

/**
 * SSLActions - Shared utility for SSL repair actions across device types.
 *
 * Usage:
 *   import { SSLActions } from './utils/ssl_actions.js'; // If using ES modules
 *   // Or use window.SSLActions if loaded globally
 *
 *   await SSLActions.renew('router', '192.168.1.1');
 *   await SSLActions.unprovision('switch', '192.168.1.2');
 */

window.SSLActions = {
    /**
     * Get the API endpoint for a device type.
     * @param {string} deviceType - 'router', 'switch', or 'ap'
     * @param {string} host - Device IP/hostname
     * @returns {string} API endpoint URL
     */
    getEndpoint(deviceType, host) {
        const encodedHost = encodeURIComponent(host);
        switch (deviceType) {
            case 'router':
                return `/api/routers/${encodedHost}/repair`;
            case 'switch':
                return `/api/switches/${encodedHost}/ssl/repair`;
            case 'ap':
                return `/api/aps/${encodedHost}/repair`;
            default:
                throw new Error(`Unknown device type: ${deviceType}`);
        }
    },

    /**
     * Renew SSL certificates on a device without full re-provisioning.
     * @param {string} deviceType - 'router', 'switch', or 'ap'
     * @param {string} host - Device IP/hostname
     * @returns {Promise<{success: boolean, message: string}>}
     */
    async renew(deviceType, host) {
        const url = this.getEndpoint(deviceType, host);

        try {
            if (typeof showToast === 'function') {
                showToast('Renovando certificados SSL...', 'primary');
            }

            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'renew' })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Error al renovar SSL');
            }

            if (typeof showToast === 'function') {
                showToast('✅ Certificados SSL renovados exitosamente', 'success');
            }

            return { success: true, message: data.message };

        } catch (error) {
            console.error('SSLActions.renew error:', error);
            if (typeof showToast === 'function') {
                showToast(`❌ Error: ${error.message}`, 'danger');
            }
            return { success: false, message: error.message };
        }
    },

    /**
     * Mark a device as not provisioned (DB only), enabling full re-provisioning.
     * @param {string} deviceType - 'router', 'switch', or 'ap'
     * @param {string} host - Device IP/hostname
     * @returns {Promise<{success: boolean, message: string}>}
     */
    async unprovision(deviceType, host) {
        const url = this.getEndpoint(deviceType, host);

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'unprovision' })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Error al desvincular dispositivo');
            }

            if (typeof showToast === 'function') {
                showToast('Dispositivo desvinculado. Listo para re-aprovisionar.', 'success');
            }

            return { success: true, message: data.message };

        } catch (error) {
            console.error('SSLActions.unprovision error:', error);
            if (typeof showToast === 'function') {
                showToast(`❌ Error: ${error.message}`, 'danger');
            }
            return { success: false, message: error.message };
        }
    },

    /**
     * Show a confirmation modal and execute the selected action.
     * @param {string} deviceType - 'router', 'switch', or 'ap'
     * @param {string} host - Device IP/hostname
     * @param {string} hostname - Display name for the device
     * @param {Function} onComplete - Callback after action completes (e.g., reload data)
     */
    async showRepairModal(deviceType, host, hostname, onComplete) {
        const displayName = hostname || host;
        const deviceLabel = deviceType === 'ap' ? 'AP' : deviceType.charAt(0).toUpperCase() + deviceType.slice(1);

        // Use ModalUtils if available, otherwise basic confirm
        if (window.ModalUtils && window.ModalUtils.showConfirmModal) {
            const confirmed = await window.ModalUtils.showConfirmModal({
                title: `Reparar ${deviceLabel}`,
                message: `¿Qué acción desea realizar para "<strong>${displayName}</strong>"?<br><br>
                    <strong>Renovar SSL</strong>: Reinstala certificados sin cambiar usuario/contraseña.<br>
                    <strong>Desvincular</strong>: Marca como no aprovisionado para re-configurar.`,
                confirmText: 'Renovar SSL',
                cancelText: 'Desvincular',
                type: 'warning',
            });

            if (confirmed === true) {
                // User chose "Renovar SSL"
                const result = await this.renew(deviceType, host);
                if (result.success && typeof onComplete === 'function') {
                    onComplete();
                }
            } else if (confirmed === false) {
                // User chose "Desvincular" (cancel button was clicked)
                const result = await this.unprovision(deviceType, host);
                if (result.success && typeof onComplete === 'function') {
                    onComplete();
                }
            }
            // If confirmed === null/undefined, user closed the modal
        } else {
            // Fallback to simple confirm
            const action = confirm(`¿Desea RENOVAR SSL para ${displayName}?\n\nOK = Renovar SSL\nCancelar = Desvincular`);
            if (action) {
                await this.renew(deviceType, host);
            } else {
                await this.unprovision(deviceType, host);
            }
            if (typeof onComplete === 'function') {
                onComplete();
            }
        }
    }
};

console.log('[Utils] SSLActions loaded');

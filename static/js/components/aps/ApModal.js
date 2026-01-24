/**
 * AP Modal Component - Alpine.js Component
 *
 * Handles Add/Edit AP modal functionality.
 * Uses $store.aps for state.
 *
 * Usage:
 *   <div x-data="apModal()">...</div>
 */
document.addEventListener('alpine:init', () => {
    Alpine.data('apModal', () => ({
        // --- Computed bindings to store ---
        get isModalOpen() {
            return Alpine.store('aps').isModalOpen;
        },

        get isEditing() {
            return Alpine.store('aps').isEditing;
        },

        get currentAp() {
            return Alpine.store('aps').currentAp;
        },

        set currentAp(val) {
            Alpine.store('aps').currentAp = val;
        },

        get error() {
            return Alpine.store('aps').error;
        },

        get isTesting() {
            return Alpine.store('aps').isTesting;
        },

        get testMessage() {
            return Alpine.store('aps').testMessage;
        },

        get testStatus() {
            return Alpine.store('aps').testStatus;
        },

        get allZones() {
            return Alpine.store('aps').allZones;
        },

        // --- Helper Methods ---
        getDefaultPort() {
            return Alpine.store('aps').getDefaultPort(this.currentAp.vendor);
        },

        getPortHint() {
            return Alpine.store('aps').getPortHint(this.currentAp.vendor);
        },

        // --- Actions ---
        closeModal() {
            Alpine.store('aps').closeModal();
        },

        onVendorChange() {
            Alpine.store('aps').onVendorChange();
        },

        async testConnection() {
            await Alpine.store('aps').testConnection();
        },

        async saveAp() {
            await Alpine.store('aps').save();
        },

        async renewSSL() {
            if (!this.currentAp?.host) return;

            const hostname = this.currentAp.hostname || this.currentAp.host;
            const confirmed = await window.ModalUtils.showConfirmModal({
                title: 'Renovar Certificado SSL',
                message: `¿Renovar certificado SSL para "<strong>${hostname}</strong>"?<br><br>Esto reinstalará el certificado sin cambiar usuario/contraseña.`,
                confirmText: 'Renovar SSL',
                confirmIcon: 'sync_lock',
                type: 'primary',
            });

            if (confirmed) {
                const result = await window.SSLActions.renew('ap', this.currentAp.host);
                if (result.success) {
                    this.closeModal();
                    Alpine.store('aps').loadData();
                }
            }
        },

        async unlinkAp() {
            if (!this.currentAp?.host) return;

            const hostname = this.currentAp.hostname || this.currentAp.host;
            const confirmed = await window.ModalUtils.showConfirmModal({
                title: 'Desvincular AP',
                message: `¿Desvincular el AP "<strong>${hostname}</strong>"?<br><br>Esto lo marcará como no aprovisionado para re-configurar.`,
                confirmText: 'Desvincular',
                confirmIcon: 'link_off',
                type: 'warning',
            });

            if (confirmed) {
                const result = await window.SSLActions.unprovision('ap', this.currentAp.host);
                if (result.success) {
                    this.closeModal();
                    Alpine.store('aps').loadData();
                }
            }
        }
    }));

    console.log('[Component] ApModal initialized');
});

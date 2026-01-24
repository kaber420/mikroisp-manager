/**
 * Switch Modal Component - Alpine.js Component
 *
 * Handles the Add/Edit Switch modal form.
 * Uses $store.switches for state.
 *
 * Usage:
 *   <div x-data="switchModal()">...</div>
 */
document.addEventListener('alpine:init', () => {
    Alpine.data('switchModal', () => ({
        // --- Computed Helpers ---
        get isOpen() {
            return Alpine.store('switches').isModalOpen;
        },

        get isEditing() {
            return Alpine.store('switches').isEditing;
        },

        get currentSwitch() {
            return Alpine.store('switches').currentSwitch;
        },

        set currentSwitch(val) {
            Alpine.store('switches').currentSwitch = val;
        },

        get error() {
            return Alpine.store('switches').error;
        },

        get allZones() {
            return Alpine.store('switches').allZones;
        },

        // --- Actions ---
        close() {
            Alpine.store('switches').closeModal();
        },

        async save() {
            await Alpine.store('switches').save();
        },

        async renewSSL() {
            if (!this.currentSwitch?.host) return;

            const hostname = this.currentSwitch.hostname || this.currentSwitch.host;
            const confirmed = await window.ModalUtils.showConfirmModal({
                title: 'Renovar Certificado SSL',
                message: `¿Renovar certificado SSL para "<strong>${hostname}</strong>"?<br><br>Esto reinstalará el certificado sin cambiar usuario/contraseña.`,
                confirmText: 'Renovar SSL',
                confirmIcon: 'sync_lock',
                type: 'primary',
            });

            if (confirmed) {
                const result = await window.SSLActions.renew('switch', this.currentSwitch.host);
                if (result.success) {
                    this.close();
                    Alpine.store('switches').loadData();
                }
            }
        },

        async unlinkSwitch() {
            if (!this.currentSwitch?.host) return;

            const hostname = this.currentSwitch.hostname || this.currentSwitch.host;
            const confirmed = await window.ModalUtils.showConfirmModal({
                title: 'Desvincular Switch',
                message: `¿Desvincular el switch "<strong>${hostname}</strong>"?<br><br>Esto lo marcará como no aprovisionado para re-configurar.`,
                confirmText: 'Desvincular',
                confirmIcon: 'link_off',
                type: 'warning',
            });

            if (confirmed) {
                const result = await window.SSLActions.unprovision('switch', this.currentSwitch.host);
                if (result.success) {
                    this.close();
                    Alpine.store('switches').loadData();
                }
            }
        }
    }));

    console.log('[Component] SwitchModal initialized');
});

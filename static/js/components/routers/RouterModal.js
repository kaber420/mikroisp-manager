/**
 * Router Modal Component - Alpine.js Component
 *
 * Handles the Add/Edit Router modal form.
 * Uses $store.routers for state.
 *
 * Usage:
 *   <div x-data="routerModal()">...</div>
 */
document.addEventListener('alpine:init', () => {
    Alpine.data('routerModal', () => ({
        // --- Computed Helpers ---
        get isOpen() {
            return Alpine.store('routers').isModalOpen;
        },

        get isEditing() {
            return Alpine.store('routers').isEditing;
        },

        get currentRouter() {
            return Alpine.store('routers').currentRouter;
        },

        set currentRouter(val) {
            Alpine.store('routers').currentRouter = val;
        },

        get error() {
            return Alpine.store('routers').error;
        },

        get allZones() {
            return Alpine.store('routers').allZones;
        },

        // --- Actions ---
        close() {
            Alpine.store('routers').closeModal();
        },

        async save() {
            await Alpine.store('routers').save();
        },

        async renewSSL() {
            if (!this.currentRouter?.host) return;

            const hostname = this.currentRouter.hostname || this.currentRouter.host;
            const confirmed = await window.ModalUtils.showConfirmModal({
                title: 'Renovar Certificado SSL',
                message: `¿Renovar certificado SSL para "<strong>${hostname}</strong>"?<br><br>Esto reinstalará el certificado sin cambiar usuario/contraseña.`,
                confirmText: 'Renovar SSL',
                confirmIcon: 'sync_lock',
                type: 'primary',
            });

            if (confirmed) {
                const result = await window.SSLActions.renew('router', this.currentRouter.host);
                if (result.success) {
                    this.close();
                    Alpine.store('routers').loadData();
                }
            }
        },

        async unlinkRouter() {
            if (!this.currentRouter?.host) return;

            const hostname = this.currentRouter.hostname || this.currentRouter.host;
            const confirmed = await window.ModalUtils.showConfirmModal({
                title: 'Desvincular Router',
                message: `¿Desvincular el router "<strong>${hostname}</strong>"?<br><br>Esto lo marcará como no aprovisionado para re-configurar.`,
                confirmText: 'Desvincular',
                confirmIcon: 'link_off',
                type: 'warning',
            });

            if (confirmed) {
                const result = await window.SSLActions.unprovision('router', this.currentRouter.host);
                if (result.success) {
                    this.close();
                    Alpine.store('routers').loadData();
                }
            }
        }
    }));

    console.log('[Component] RouterModal initialized');
});

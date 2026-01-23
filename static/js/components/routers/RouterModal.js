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

        repairRouter(router) {
            Alpine.store('routers').repair(router);
        }
    }));

    console.log('[Component] RouterModal initialized');
});

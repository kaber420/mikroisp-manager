/**
 * Router List Component - Alpine.js Component
 *
 * Displays the main table of routers with actions.
 * Uses $store.routers for state.
 *
 * Usage:
 *   <div x-data="routerList()">...</div>
 */
document.addEventListener('alpine:init', () => {
    Alpine.data('routerList', () => ({
        // Spread the shared provisioning mixin
        ...window.provisionMixin,

        // --- Init ---
        async init() {
            await Alpine.store('routers').loadData();

            // Global reactivity event
            window.addEventListener('data-refresh-needed', () => {
                if (!Alpine.store('routers').isModalOpen && !this.isProvisionModalOpen) {
                    console.log("⚡ Routers: Recargando estado...");
                    Alpine.store('routers').loadData();
                }
            });
        },

        // Alias for the mixin's auto-refresh after provisioning
        async loadInitialData() {
            return Alpine.store('routers').loadData();
        },

        // --- Computed Helpers ---
        get routers() {
            return Alpine.store('routers').filteredList;
        },

        get isLoading() {
            return Alpine.store('routers').isLoading;
        },

        // Filter state bindings
        get statusFilter() {
            return Alpine.store('routers').statusFilter;
        },
        set statusFilter(val) {
            Alpine.store('routers').statusFilter = val;
        },

        get searchQuery() {
            return Alpine.store('routers').searchQuery;
        },
        set searchQuery(val) {
            Alpine.store('routers').searchQuery = val;
        },

        getZoneName(zoneId) {
            return Alpine.store('routers').getZoneName(zoneId);
        },

        isRouterProvisioned(router) {
            return Alpine.store('routers').isProvisioned(router);
        },

        // --- Actions ---
        openRouterModal(router = null) {
            Alpine.store('routers').openModal(router);
        },

        deleteRouter(host, hostname) {
            Alpine.store('routers').delete(host, hostname);
        },

        repairRouter(router) {
            Alpine.store('routers').repair(router);
        },

        // Override openProvisionModal to set Router-specific values
        openProvisionModal(router) {
            // Call base mixin method with router-specific config
            window.provisionMixin.openProvisionModal.call(this, router, 'Router', '/api/routers');
        },

        // Plans actions (delegates to PlanStore)
        openPlansModal() {
            Alpine.store('plans').openModal();
        }
    }));

    console.log('[Component] RouterList initialized');
});

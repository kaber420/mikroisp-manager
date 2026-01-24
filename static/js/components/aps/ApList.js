/**
 * AP List Component - Alpine.js Component
 *
 * Displays the main table of APs with actions.
 * Uses $store.aps for state.
 *
 * Usage:
 *   <div x-data="apList()">...</div>
 */
document.addEventListener('alpine:init', () => {
    Alpine.data('apList', () => ({
        // Spread the shared provisioning mixin
        ...window.provisionMixin,

        // --- Init ---
        async init() {
            await Alpine.store('aps').loadData();

            // Global reactivity event
            window.addEventListener('data-refresh-needed', () => {
                const store = Alpine.store('aps');
                if (!store.isModalOpen && !this.isProvisionModalOpen) {
                    console.log("⚡ APs: Recargando lista por actualización en vivo.");
                    store.loadData();
                } else {
                    console.log("⏳ APs: Actualización pausada (Usuario editando).");
                }
            });
        },

        // Alias for the mixin's auto-refresh after provisioning
        async loadInitialData() {
            return Alpine.store('aps').loadData();
        },

        // --- Computed Helpers ---
        get aps() {
            return Alpine.store('aps').filteredList;
        },

        get isLoading() {
            return Alpine.store('aps').isLoading;
        },

        get allZones() {
            return Alpine.store('aps').allZones;
        },

        // Filter state bindings
        get statusFilter() {
            return Alpine.store('aps').statusFilter;
        },
        set statusFilter(val) {
            Alpine.store('aps').statusFilter = val;
        },

        get searchQuery() {
            return Alpine.store('aps').searchQuery;
        },
        set searchQuery(val) {
            Alpine.store('aps').searchQuery = val;
        },

        get selectedZone() {
            return Alpine.store('aps').selectedZone;
        },
        set selectedZone(val) {
            Alpine.store('aps').selectedZone = val;
        },

        // --- Helper Methods ---
        getZoneName(zoneId) {
            return Alpine.store('aps').getZoneName(zoneId);
        },

        isApProvisioned(ap) {
            return Alpine.store('aps').isProvisioned(ap);
        },

        renderStatusBadge(status) {
            return Alpine.store('aps').renderStatusBadge(status);
        },

        renderVendorBadge(vendor) {
            return Alpine.store('aps').renderVendorBadge(vendor);
        },

        formatBytes(bytes) {
            if (bytes == null || bytes === 0) return '0 B';
            const units = ['B', 'KB', 'MB', 'GB', 'TB'];
            const i = Math.floor(Math.log(bytes) / Math.log(1024));
            return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
        },

        // --- Actions ---
        openApModal(ap = null) {
            Alpine.store('aps').openModal(ap);
        },

        deleteAp(ap) {
            Alpine.store('aps').delete(ap.host, ap.hostname);
        },

        repairAp(ap) {
            // Open the edit modal so users can access the 2 SSL action buttons
            Alpine.store('aps').openModal(ap);
        },

        // Override openProvisionModal to set AP-specific values
        openProvisionModal(ap) {
            window.provisionMixin.openProvisionModal.call(this, ap, 'AP', '/api/aps');
        }
    }));

    console.log('[Component] ApList initialized');
});

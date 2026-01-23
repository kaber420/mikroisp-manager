/**
 * Switch List Component - Alpine.js Component
 *
 * Displays the main table of switches with actions.
 * Uses $store.switches for state.
 *
 * Usage:
 *   <div x-data="switchList()">...</div>
 */
document.addEventListener('alpine:init', () => {
    Alpine.data('switchList', () => ({
        // --- Init ---
        async init() {
            await Alpine.store('switches').loadData();

            // Global reactivity event
            window.addEventListener('data-refresh-needed', () => {
                if (!Alpine.store('switches').isModalOpen) {
                    console.log("⚡ Switches: Reloading data...");
                    Alpine.store('switches').loadData();
                }
            });
        },

        // --- Computed Helpers ---
        get switches() {
            return Alpine.store('switches').filteredList;
        },

        get isLoading() {
            return Alpine.store('switches').isLoading;
        },

        // Filter state bindings
        get statusFilter() {
            return Alpine.store('switches').statusFilter;
        },
        set statusFilter(val) {
            Alpine.store('switches').statusFilter = val;
        },

        get searchQuery() {
            return Alpine.store('switches').searchQuery;
        },
        set searchQuery(val) {
            Alpine.store('switches').searchQuery = val;
        },

        getZoneName(zoneId) {
            return Alpine.store('switches').getZoneName(zoneId);
        },

        // --- Actions ---
        openSwitchModal(sw = null) {
            Alpine.store('switches').openModal(sw);
        },

        deleteSwitch(host, hostname) {
            Alpine.store('switches').delete(host, hostname);
        },

        testConnection(sw) {
            Alpine.store('switches').testConnection(sw);
        },

        // Navigation helper
        goToDetails(host) {
            window.location.href = '/switch/' + encodeURIComponent(host);
        }
    }));

    console.log('[Component] SwitchList initialized');
});

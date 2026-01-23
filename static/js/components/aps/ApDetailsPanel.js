/**
 * AP Details Panel Component - Alpine.js Component
 *
 * Displays AP device information reactively.
 * Uses $store.apDetails for state.
 *
 * Usage:
 *   <div x-data="apDetailsPanel()">...</div>
 */
document.addEventListener('alpine:init', () => {
    Alpine.data('apDetailsPanel', () => ({
        // --- Init ---
        async init() {
            await Alpine.store('apDetails').loadData();

            // Listen for data refresh events
            window.addEventListener('data-refresh-needed', () => {
                const store = Alpine.store('apDetails');
                if (!store.isDiagnosticActive && !store.isEditModalOpen) {
                    console.log("⚡ AP Details: Recargando datos por actualización en vivo.");
                    store.loadData();
                }
            });
        },

        // --- Computed Helpers ---
        get ap() {
            return Alpine.store('apDetails').ap;
        },

        get isLoading() {
            return Alpine.store('apDetails').isLoading;
        },

        get statusDisplay() {
            return Alpine.store('apDetails').statusDisplay;
        },

        get isDiagnosticActive() {
            return Alpine.store('apDetails').isDiagnosticActive;
        },

        get diagnosticTimerDisplay() {
            return Alpine.store('apDetails').diagnosticTimerDisplay;
        },

        // --- Formatters ---
        formatThroughput(kbps) {
            return Alpine.store('apDetails').formatThroughput(kbps);
        },

        formatBytes(bytes) {
            return Alpine.store('apDetails').formatBytes(bytes);
        },

        getZoneName(zoneId) {
            return Alpine.store('apDetails').getZoneName(zoneId);
        },

        // --- Actions ---
        openEditModal() {
            Alpine.store('apDetails').openEditModal();
        },

        deleteAp() {
            Alpine.store('apDetails').deleteAp();
        },

        toggleDiagnosticMode(checked) {
            const store = Alpine.store('apDetails');
            if (checked) {
                store.startDiagnosticMode();
            } else {
                store.stopDiagnosticMode(true);
            }
        }
    }));

    console.log('[Component] ApDetailsPanel initialized');
});

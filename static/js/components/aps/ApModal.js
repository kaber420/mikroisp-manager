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

        repairAp() {
            Alpine.store('aps').repair(this.currentAp);
        }
    }));

    console.log('[Component] ApModal initialized');
});

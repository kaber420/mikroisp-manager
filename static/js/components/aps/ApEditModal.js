/**
 * AP Edit Modal Component (Details Page) - Alpine.js Component
 *
 * Handles the Edit AP modal on the details page.
 * Uses $store.apDetails for state.
 *
 * Usage:
 *   <div x-data="apEditModal()">...</div>
 */
document.addEventListener('alpine:init', () => {
    Alpine.data('apEditModal', () => ({
        // --- Computed bindings to store ---
        get isOpen() {
            return Alpine.store('apDetails').isEditModalOpen;
        },

        get currentAp() {
            return Alpine.store('apDetails').editFormData;
        },

        get error() {
            return Alpine.store('apDetails').editError;
        },

        get allZones() {
            return Alpine.store('apDetails').allZones;
        },

        // --- Actions ---
        close() {
            Alpine.store('apDetails').closeEditModal();
        },

        async save() {
            await Alpine.store('apDetails').saveEdit();
        },

        // Helper for port placeholder
        getDefaultPort() {
            const vendor = Alpine.store('apDetails').currentVendor;
            return vendor === 'mikrotik' ? '8728' : '443';
        }
    }));

    console.log('[Component] ApEditModal initialized');
});

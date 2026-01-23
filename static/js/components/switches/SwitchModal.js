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
        }
    }));

    console.log('[Component] SwitchModal initialized');
});

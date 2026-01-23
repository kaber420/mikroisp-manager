/**
 * User Modal Component - Alpine.js Component
 *
 * Handles the Add/Edit User modal form.
 * Uses $store.users for state.
 *
 * Usage:
 *   <div x-data="userModal()">...</div>
 */
document.addEventListener('alpine:init', () => {
    Alpine.data('userModal', () => ({
        // --- Computed Helpers ---
        get isOpen() {
            return Alpine.store('users').isModalOpen;
        },

        get isEditing() {
            return Alpine.store('users').isEditing;
        },

        get currentUser() {
            return Alpine.store('users').currentUser;
        },

        set currentUser(val) {
            Alpine.store('users').currentUser = val;
        },

        get errors() {
            return Alpine.store('users').errors;
        },

        get error() {
            return Alpine.store('users').error;
        },

        // --- Actions ---
        close() {
            Alpine.store('users').closeModal();
        },

        async save() {
            await Alpine.store('users').save();
        }
    }));

    console.log('[Component] UserModal initialized');
});

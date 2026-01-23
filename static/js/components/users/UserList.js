/**
 * User List Component - Alpine.js Component
 *
 * Displays the main list/table of users with actions.
 * Uses $store.users for state.
 *
 * Usage:
 *   <div x-data="userList()">...</div>
 */
document.addEventListener('alpine:init', () => {
    Alpine.data('userList', () => ({
        // --- Init ---
        async init() {
            await Alpine.store('users').loadUsers();
        },

        // --- Computed Helpers ---
        get users() {
            return Alpine.store('users').list;
        },

        get isLoading() {
            return Alpine.store('users').isLoading;
        },

        get error() {
            return Alpine.store('users').error;
        },

        // --- Actions ---
        openAddModal() {
            Alpine.store('users').openModal();
        },

        openEditModal(user) {
            Alpine.store('users').openModal(user);
        },

        deleteUser(user) {
            Alpine.store('users').delete(user.username);
        }
    }));

    console.log('[Component] UserList initialized');
});

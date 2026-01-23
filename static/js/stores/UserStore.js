/**
 * User Store - Alpine.js Global Store
 *
 * Shared state for user-related components. Registered with Alpine.store().
 *
 * Usage in Alpine components:
 *   Alpine.store('users').list
 *   Alpine.store('users').loadUsers()
 */
document.addEventListener('alpine:init', () => {
    Alpine.store('users', {
        // --- State ---
        list: [],
        isLoading: true,

        // Modal state
        isModalOpen: false,
        isEditing: false,
        currentUser: {},
        errors: {},
        error: '',

        // --- Actions ---
        async loadUsers() {
            this.isLoading = true;
            this.error = '';
            try {
                const response = await fetch('/api/users');
                if (!response.ok) {
                    const err = await response.json().catch(() => ({}));
                    throw new Error(err.detail || 'Failed to load users');
                }
                this.list = await response.json();
            } catch (err) {
                console.error('Error loading users:', err);
                this.error = `Failed to load users: ${err.message}`;
            } finally {
                this.isLoading = false;
            }
        },

        _createEmptyUser() {
            return {
                username: '',
                email: '',
                password: '',
                role: 'admin',
                telegram_chat_id: '',
                receive_alerts: false,
                receive_announcements: false,
                disabled: false
            };
        },

        // --- Modal Actions ---
        openModal(user = null) {
            this.errors = {};
            this.error = '';
            if (user) {
                this.isEditing = true;
                this.currentUser = {
                    ...user,
                    email: user.email,
                    password: '', // Clear password for security
                    telegram_chat_id: user.telegram_chat_id || ''
                };
            } else {
                this.isEditing = false;
                this.currentUser = this._createEmptyUser();
            }
            this.isModalOpen = true;
        },

        closeModal() {
            this.isModalOpen = false;
            this.currentUser = {};
            this.errors = {};
            this.error = '';
        },

        _validate() {
            this.errors = {};
            const user = this.currentUser;

            if (this.isEditing === false) {
                // Add mode validation
                if (!validators.isRequired(user.username)) {
                    this.errors.username = 'Username is required.';
                } else if (user.username.length < 3) {
                    this.errors.username = 'Must be at least 3 characters.';
                }

                if (!validators.isRequired(user.password)) {
                    this.errors.password = 'Password is required.';
                } else if (user.password.length < 6) {
                    this.errors.password = 'Must be at least 6 characters.';
                }
            }

            // Edit mode password validation
            if (this.isEditing && user.password && user.password.length < 6) {
                this.errors.password = 'New password must be at least 6 characters.';
            }

            // Telegram ID validation
            if (user.telegram_chat_id && isNaN(parseInt(user.telegram_chat_id, 10))) {
                this.errors.telegram_chat_id = 'Must be a numeric ID.';
            }

            return !Object.values(this.errors).some(error => error);
        },

        async save() {
            if (!this._validate()) {
                return;
            }

            const url = this.isEditing
                ? `/api/users/${this.currentUser.username}`
                : '/api/users';
            const method = this.isEditing ? 'PUT' : 'POST';

            const data = {
                email: this.currentUser.email,
                role: this.currentUser.role,
                telegram_chat_id: this.currentUser.telegram_chat_id || null,
                receive_alerts: this.currentUser.receive_alerts,
                receive_announcements: this.currentUser.receive_announcements,
            };

            if (this.isEditing) {
                if (this.currentUser.password) {
                    data.password = this.currentUser.password;
                }
                data.disabled = this.currentUser.disabled;
            } else {
                data.username = this.currentUser.username;
                data.password = this.currentUser.password;
            }

            try {
                const response = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data),
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || 'Failed to save user');
                }

                await this.loadUsers();
                this.closeModal();
            } catch (err) {
                this.error = `Error: ${err.message}`;
            }
        },

        async delete(username) {
            window.ModalUtils.showConfirmModal({
                title: 'Delete User',
                message: `Are you sure you want to delete user "<strong>${username}</strong>"?`,
                confirmText: 'Delete',
                confirmIcon: 'delete',
                type: 'danger',
            }).then(async (confirmed) => {
                if (confirmed) {
                    try {
                        const response = await fetch(`/api/users/${username}`, { method: 'DELETE' });

                        if (!response.ok) {
                            const errorData = await response.json();
                            throw new Error(errorData.detail || 'Failed to delete user');
                        }

                        this.list = this.list.filter(u => u.username !== username);

                    } catch (err) {
                        showToast(`Error: ${err.message}`, 'danger');
                    }
                }
            });
        }
    });

    console.log('[Store] UserStore initialized');
});

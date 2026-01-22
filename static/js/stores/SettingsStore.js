/**
 * SettingsStore.js
 * Global Alpine.js store for managing settings state and API calls
 */

document.addEventListener('alpine:init', () => {
    Alpine.store('settings', {
        // State
        isLoading: false,
        activeTab: 'config',
        saveStatus: {
            message: '',
            type: 'success', // 'success' | 'danger'
            visible: false
        },

        // Actions
        setTab(tab) {
            this.activeTab = tab;
        },

        // Actions
        async fetchSettings() {
            this.isLoading = true;
            try {
                const response = await fetch(`${window.location.origin}/api/settings`);
                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}));
                    throw new Error(errorData.detail || 'Failed to load settings');
                }
                const settings = await response.json();
                this.isLoading = false;
                return settings;
            } catch (error) {
                console.error('Error loading settings:', error);
                window.showToast?.('Could not load settings. Please check the API connection.', 'danger');
                this.isLoading = false;
                throw error;
            }
        },

        async updateSettings(settingsData) {
            this.isLoading = true;
            this.saveStatus.visible = false;

            try {
                const response = await fetch(`${window.location.origin}/api/settings`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(settingsData)
                });

                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}));
                    throw new Error(errorData.detail || 'Failed to save settings');
                }

                this.saveStatus = {
                    message: 'Settings saved successfully!',
                    type: 'success',
                    visible: true
                };

                // Hide after 3 seconds
                setTimeout(() => {
                    this.saveStatus.visible = false;
                }, 3000);

            } catch (error) {
                console.error('Error saving settings:', error);
                this.saveStatus = {
                    message: `Error: ${error.message}`,
                    type: 'danger',
                    visible: true
                };
            } finally {
                this.isLoading = false;
            }
        },

        async triggerForceBilling() {
            const confirmed = await window.ModalUtils.showConfirmModal({
                title: 'Force Billing Check',
                message: 'Are you sure? This will update statuses (Active/Pending/Suspended) for <strong>ALL clients</strong> based on their payments.',
                confirmText: 'Process',
                confirmIcon: 'sync',
                type: 'warning',
            });

            if (!confirmed) return;

            try {
                const res = await fetch(`${window.location.origin}/api/settings/force-billing`, {
                    method: 'POST'
                });

                if (!res.ok) throw new Error('Request failed');

                const data = await res.json();
                window.showToast?.(
                    `Done! Processed: ${data.stats.processed}, Active: ${data.stats.active || 0}, Pending: ${data.stats.pendiente || 0}, Suspended: ${data.stats.suspended || 0}`,
                    'success',
                    5000
                );
            } catch (e) {
                window.showToast?.('Error updating statuses: ' + e.message, 'danger');
            }
        },

        async triggerManualBackup() {
            const confirmed = await window.ModalUtils.showConfirmModal({
                title: 'Manual Backup',
                message: 'This will create a manual backup of the database. Proceed?',
                confirmText: 'Create Backup',
                confirmIcon: 'save',
                type: 'primary',
            });

            if (!confirmed) return;

            try {
                const res = await fetch(`${window.location.origin}/api/settings/backup-now`, {
                    method: 'POST'
                });

                const data = await res.json();
                if (!res.ok) throw new Error(data.detail || 'Backup failed');

                window.showToast?.('Backup completed successfully!', 'success', 5000);
            } catch (e) {
                window.showToast?.('Backup error: ' + e.message, 'danger');
            }
        }
    });
});

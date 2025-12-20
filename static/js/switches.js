// static/js/switches.js

document.addEventListener('alpine:init', () => {
    Alpine.data('switchManager', () => ({
        // State
        switches: [],
        allZones: [],
        isLoading: true,
        isSwitchModalOpen: false,
        currentSwitch: {},
        switchError: '',
        isEditing: false,

        // Initialize
        async init() {
            this.isLoading = true;
            await this.loadData();
            this.isLoading = false;

            // Listen for data refresh events
            window.addEventListener('data-refresh-needed', () => {
                if (!this.isSwitchModalOpen) {
                    console.log("⚡ Switches: Reloading data...");
                    this.loadData();
                }
            });
        },

        // Load switches and zones data
        async loadData() {
            try {
                const [switchesRes, zonesRes] = await Promise.all([
                    fetch('/api/switches'),
                    fetch('/api/zonas')
                ]);
                if (!switchesRes.ok) throw new Error('Failed to load switches.');
                if (!zonesRes.ok) throw new Error('Failed to load zones.');
                this.switches = await switchesRes.json();
                this.allZones = await zonesRes.json();
            } catch (error) {
                console.error('Error loading data:', error);
                this.switchError = error.message;
            }
        },

        // Get zone name by ID
        getZoneName(zoneId) {
            if (!zoneId) return 'Unassigned';
            const zone = this.allZones.find(z => z.id === zoneId);
            return zone ? zone.nombre : 'Unassigned';
        },

        // Open modal for add/edit
        openSwitchModal(sw = null) {
            this.switchError = '';
            if (sw) {
                this.isEditing = true;
                this.currentSwitch = {
                    ...sw,
                    password: '', // Clear password for security
                };
            } else {
                this.isEditing = false;
                this.currentSwitch = {
                    host: '',
                    zona_id: '',
                    api_port: 8728,
                    username: 'admin',
                    password: '',
                    location: '',
                    notes: '',
                };
            }
            this.isSwitchModalOpen = true;
        },

        // Close modal
        closeSwitchModal() {
            this.isSwitchModalOpen = false;
            this.currentSwitch = {};
        },

        // Save switch (create or update)
        async saveSwitch() {
            this.switchError = '';

            // Validation
            if (!this.currentSwitch.host || !this.currentSwitch.username) {
                this.switchError = 'Please fill in all required fields (Host and Username).';
                return;
            }
            if (!this.isEditing && !this.currentSwitch.password) {
                this.switchError = 'Password is required for a new switch.';
                return;
            }

            const url = this.isEditing
                ? `/api/switches/${encodeURIComponent(this.currentSwitch.host)}`
                : '/api/switches';
            const method = this.isEditing ? 'PUT' : 'POST';

            // Don't send an empty password when editing
            const body = { ...this.currentSwitch };
            if (this.isEditing && !body.password) {
                delete body.password;
            }

            // Convert empty zona_id to null
            if (body.zona_id === '' || body.zona_id === undefined) {
                body.zona_id = null;
            }

            try {
                const response = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body)
                });
                if (!response.ok) {
                    const err = await response.json();
                    throw new Error(err.detail || 'Failed to save switch.');
                }

                // Show success toast
                if (typeof showToast === 'function') {
                    showToast(this.isEditing ? 'Switch updated successfully!' : 'Switch added successfully!', 'success');
                }

                await this.loadData();
                this.closeSwitchModal();
            } catch (error) {
                this.switchError = error.message;
            }
        },

        // Delete switch
        async deleteSwitch(host, hostname) {
            if (!confirm(`Are you sure you want to delete switch "${hostname || host}"?`)) return;

            try {
                const response = await fetch(`/api/switches/${encodeURIComponent(host)}`, { method: 'DELETE' });
                if (!response.ok) {
                    const err = await response.json();
                    throw new Error(err.detail || 'Failed to delete switch.');
                }
                this.switches = this.switches.filter(s => s.host !== host);

                if (typeof showToast === 'function') {
                    showToast('Switch deleted successfully!', 'success');
                }
            } catch (error) {
                if (typeof showToast === 'function') {
                    showToast(`Error: ${error.message}`, 'danger');
                } else {
                    console.error(error);
                }
            }
        },

        // Test connection to switch
        async testConnection(sw) {
            try {
                if (typeof showToast === 'function') {
                    showToast(`Testing connection to ${sw.hostname || sw.host}...`, 'primary');
                }

                const response = await fetch(`/api/switches/${encodeURIComponent(sw.host)}/status`);

                if (response.ok) {
                    const data = await response.json();
                    if (data.is_online) {
                        if (typeof showToast === 'function') {
                            showToast(`✅ ${sw.hostname || sw.host} is online! CPU: ${data.extra?.cpu_load || 'N/A'}%`, 'success');
                        }
                        // Reload to update status
                        await this.loadData();
                    } else {
                        if (typeof showToast === 'function') {
                            showToast(`❌ ${sw.hostname || sw.host} is offline: ${data.last_error || 'Unknown error'}`, 'danger');
                        }
                    }
                } else {
                    const err = await response.json();
                    throw new Error(err.detail || 'Connection failed');
                }
            } catch (error) {
                if (typeof showToast === 'function') {
                    showToast(`❌ Connection failed: ${error.message}`, 'danger');
                }
            }
        }
    }));
});

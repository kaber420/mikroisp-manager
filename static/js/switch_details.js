// static/js/switch_details.js
// JavaScript logic for the Switch Details page

function switchDetails(host) {
    return {
        // State
        host: host,
        switchData: {},
        liveData: {},
        interfaces: [],
        vlans: [],
        bridges: [],
        activeTab: 'overview',
        isOnline: false,
        isEditModalOpen: false,
        editForm: {},
        editError: '',
        ws: null,

        // Initialize
        async init() {
            await this.loadSwitchData();
            await this.loadInterfaces();
            await this.loadVlans();
            this.connectWebSocket();
            this.initSslBadge();
        },

        // Initialize SSL Badge
        initSslBadge() {
            const sslBadgeElement = document.getElementById('ssl-security-badge');
            if (sslBadgeElement) {
                // Load SSL Badge component dynamically
                import('/static/js/components/ssl_badge.js').then(({ SslBadge }) => {
                    const sslBadge = new SslBadge({
                        deviceType: 'switches',
                        host: this.host
                    });
                    sslBadge.init();
                }).catch(err => {
                    console.warn('Could not load SSL Badge component:', err);
                });
            }
        },

        // Load switch data from API
        async loadSwitchData() {
            try {
                const response = await fetch(`/api/switches/${encodeURIComponent(this.host)}`);
                if (!response.ok) throw new Error('Failed to load switch data');
                this.switchData = await response.json();
                this.isOnline = this.switchData.last_status === 'online';
            } catch (error) {
                console.error('Error loading switch data:', error);
                if (typeof showToast === 'function') {
                    showToast(`Error: ${error.message}`, 'danger');
                }
            }
        },

        // Load interfaces from API
        async loadInterfaces() {
            try {
                const response = await fetch(`/api/switches/${encodeURIComponent(this.host)}/interfaces`);
                if (!response.ok) throw new Error('Failed to load interfaces');
                this.interfaces = await response.json();
            } catch (error) {
                console.error('Error loading interfaces:', error);
            }
        },

        // Load VLANs from API
        async loadVlans() {
            try {
                const response = await fetch(`/api/switches/${encodeURIComponent(this.host)}/vlans`);
                if (!response.ok) throw new Error('Failed to load VLANs');
                this.vlans = await response.json();
            } catch (error) {
                console.error('Error loading VLANs:', error);
            }
        },

        // Connect to WebSocket for live data
        connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/api/ws/switch/${encodeURIComponent(this.host)}`;

            try {
                this.ws = new WebSocket(wsUrl);

                this.ws.onopen = () => {
                    console.log('✅ Switch WebSocket connected');
                    this.isOnline = true;
                };

                this.ws.onmessage = (event) => {
                    try {
                        const message = JSON.parse(event.data);
                        if (message.type === 'switch_status' && message.data) {
                            this.liveData = message.data;
                            this.isOnline = true;
                        } else if (message.type === 'error') {
                            console.error('WebSocket error:', message.message);
                            this.isOnline = false;
                        }
                    } catch (e) {
                        console.error('Error parsing WebSocket message:', e);
                    }
                };

                this.ws.onclose = () => {
                    console.log('❌ Switch WebSocket disconnected');
                    this.isOnline = false;
                    // Reconnect after 5 seconds
                    setTimeout(() => this.connectWebSocket(), 5000);
                };

                this.ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    this.isOnline = false;
                };
            } catch (error) {
                console.error('Error creating WebSocket:', error);
            }
        },

        // Format bytes to human readable
        formatBytes(bytes) {
            if (!bytes || bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        },

        // Open edit modal
        openEditModal() {
            this.editForm = {
                host: this.switchData.host,
                username: this.switchData.username,
                password: '',
                location: this.switchData.location || '',
                notes: this.switchData.notes || '',
            };
            this.editError = '';
            this.isEditModalOpen = true;
        },

        // Close edit modal
        closeEditModal() {
            this.isEditModalOpen = false;
            this.editForm = {};
        },

        // Save switch changes
        async saveSwitch() {
            this.editError = '';

            const updates = {
                username: this.editForm.username,
                location: this.editForm.location,
                notes: this.editForm.notes,
            };

            if (this.editForm.password) {
                updates.password = this.editForm.password;
            }

            try {
                const response = await fetch(`/api/switches/${encodeURIComponent(this.host)}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(updates)
                });

                if (!response.ok) {
                    const err = await response.json();
                    throw new Error(err.detail || 'Failed to update switch');
                }

                if (typeof showToast === 'function') {
                    showToast('Switch updated successfully!', 'success');
                }

                await this.loadSwitchData();
                this.closeEditModal();
            } catch (error) {
                this.editError = error.message;
            }
        },

        // Cleanup on destroy
        destroy() {
            if (this.ws) {
                this.ws.close();
            }
        }
    };
}

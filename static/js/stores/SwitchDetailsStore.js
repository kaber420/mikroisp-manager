document.addEventListener('alpine:init', () => {
    Alpine.store('switchDetails', {
        // --- State ---
        host: null,
        switchData: {},
        interfaces: [],
        vlans: [],
        liveData: {},
        activeTab: 'overview',
        isOnline: false,
        isLoading: true,
        error: '',

        // WebSocket
        ws: null,

        // Edit Modal
        isEditModalOpen: false,
        editForm: {},
        editError: '',

        // --- API Base URL ---
        get apiBaseUrl() {
            return window.location.origin;
        },

        get currentHost() {
            // Assuming URL is like /switches/<host>
            return window.location.pathname.split('/').pop();
        },


        // --- Actions ---

        async init() {
            this.host = this.currentHost;
            await this.loadData();
            this.connectWebSocket();
        },

        async loadData() {
            this.isLoading = true;
            try {
                await Promise.all([
                    this.loadSwitchData(),
                    this.loadInterfaces(),
                    this.loadVlans()
                ]);
            } catch (error) {
                console.error('Error loading switch data:', error);
                this.error = error.message;
            } finally {
                this.isLoading = false;
            }
        },

        async loadSwitchData() {
            try {
                const response = await fetch(`/api/switches/${encodeURIComponent(this.host)}`);
                if (!response.ok) throw new Error('Failed to load switch data');
                this.switchData = await response.json();
                this.isOnline = this.switchData.last_status === 'online';
                // Trigger SslBadge if needed, though typically components handle their own init
                this.initSslBadge();
            } catch (error) {
                console.error('Error loading switch details:', error);
                throw error;
            }
        },

        async loadInterfaces() {
            try {
                const response = await fetch(`/api/switches/${encodeURIComponent(this.host)}/interfaces`);
                if (!response.ok) throw new Error('Failed to load interfaces');
                this.interfaces = await response.json();
            } catch (error) {
                console.warn('Error loading interfaces:', error);
            }
        },

        async loadVlans() {
            try {
                const response = await fetch(`/api/switches/${encodeURIComponent(this.host)}/vlans`);
                if (!response.ok) throw new Error('Failed to load VLANs');
                this.vlans = await response.json();
            } catch (error) {
                console.warn('Error loading VLANs:', error);
            }
        },

        initSslBadge() {
            // Check if SslBadge component is loaded and initialize it
            // This logic was in the original file, adapting it here.
            // Ideally SslBadge should be an Alpine component itself or initialized in the HTML
            // For now, we mimic the original imperative call if it exists globally or dispatch an event
            const sslBadgeElement = document.getElementById('ssl-security-badge');
            if (sslBadgeElement) {
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

        // --- WebSocket ---
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
                    // Reconnect logic usually handled by simple retry
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


        // --- Helpers ---
        formatBytes(bytes) {
            if (!bytes || bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        },

        // --- Edit Modal ---
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

        closeEditModal() {
            this.isEditModalOpen = false;
            this.editForm = {};
        },

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

                await this.loadSwitchData(); // Reload details
                this.closeEditModal();
            } catch (error) {
                this.editError = error.message;
            }
        },

        destroy() {
            if (this.ws) this.ws.close();
        }

    });
});

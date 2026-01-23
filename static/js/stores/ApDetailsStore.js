/**
 * AP Details Store - Alpine.js Global Store
 *
 * Shared state for AP details page. Manages AP data, CPE list, and diagnostic mode.
 *
 * Usage in Alpine components:
 *   Alpine.store('apDetails').ap
 *   Alpine.store('apDetails').loadApDetails()
 */
document.addEventListener('alpine:init', () => {
    Alpine.store('apDetails', {
        // --- State ---
        ap: null,
        cpes: [],
        liveCpes: [],
        allZones: [],
        isLoading: true,
        error: '',
        currentPeriod: '24h',
        currentVendor: 'ubiquiti',

        // Diagnostic/Live mode state
        isDiagnosticActive: false,
        diagnosticTimeRemaining: 0,
        socket: null,
        countdownId: null,
        timeoutId: null,

        // Edit modal state
        isEditModalOpen: false,
        editFormData: {},
        editError: '',

        // Chart references (managed externally by ap_details_core.js)
        charts: {},

        // --- API Base URL ---
        get apiBaseUrl() {
            return window.location.origin;
        },

        get currentHost() {
            return window.location.pathname.split('/').pop();
        },

        // --- Formatters ---
        formatBytes(bytes) {
            if (bytes == null || bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        },

        formatThroughput(kbps) {
            if (kbps == null) return 'N/A';
            if (kbps < 1000) return `${kbps.toFixed(1)} kbps`;
            return `${(kbps / 1000).toFixed(1)} Mbps`;
        },

        // --- CPE Health Status ---
        getCPEHealthStatus(cpe) {
            if (cpe.eth_plugged === false) return { colorClass: 'border-danger', label: 'Cable Unplugged', icon: 'power_off' };
            if (cpe.eth_speed != null && cpe.eth_speed < 100) return { colorClass: 'border-orange', label: `${cpe.eth_speed} Mbps Link`, icon: 'warning' };
            if (cpe.signal == null) return { colorClass: 'border-text-secondary', label: 'No Signal Data', icon: 'signal_cellular_off' };
            if (cpe.signal < -75) return { colorClass: 'border-warning', label: 'Weak Signal', icon: 'signal_cellular_1_bar' };
            return { colorClass: 'border-success', label: 'Good Signal', icon: 'signal_cellular_4_bar' };
        },

        // --- Actions ---
        async loadData() {
            this.isLoading = true;
            try {
                await Promise.all([
                    this.loadApDetails(),
                    this.loadCPEData()
                ]);
            } catch (error) {
                console.error('Error loading AP data:', error);
                this.error = error.message;
            } finally {
                this.isLoading = false;
            }
        },

        async loadApDetails() {
            try {
                const response = await fetch(`${this.apiBaseUrl}/api/aps/${encodeURIComponent(this.currentHost)}`);
                if (!response.ok) throw new Error('AP not found');
                this.ap = await response.json();
                this.currentVendor = this.ap.vendor || 'ubiquiti';
                document.title = `${this.ap.hostname || this.ap.host} - AP Details`;
            } catch (error) {
                console.error('Error loading AP details:', error);
                throw error;
            }
        },

        async loadCPEData() {
            try {
                const [historyRes, liveRes] = await Promise.all([
                    fetch(`${this.apiBaseUrl}/api/aps/${encodeURIComponent(this.currentHost)}/cpes`),
                    fetch(`${this.apiBaseUrl}/api/aps/${encodeURIComponent(this.currentHost)}/live`)
                ]);

                if (historyRes.ok) {
                    this.cpes = await historyRes.json();
                }

                if (liveRes.ok) {
                    const liveData = await liveRes.json();
                    this.liveCpes = liveData.clients || [];
                    this.currentVendor = liveData.vendor || this.currentVendor;
                }
            } catch (error) {
                console.warn('Error loading CPE data:', error);
            }
        },

        async loadZones() {
            try {
                const response = await fetch(`${this.apiBaseUrl}/api/zonas`);
                if (response.ok) {
                    this.allZones = await response.json();
                }
            } catch (error) {
                console.warn('Could not load zones:', error);
            }
        },

        getZoneName(zoneId) {
            const zone = this.allZones.find(z => z.id === zoneId);
            return zone ? zone.nombre : 'N/A';
        },

        // --- Edit Modal Actions ---
        async openEditModal() {
            await this.loadZones();
            this.editFormData = {
                host: this.ap.host,
                username: this.ap.username,
                zona_id: this.ap.zona_id,
                monitor_interval: this.ap.monitor_interval || '',
                password: ''
            };
            this.editError = '';
            this.isEditModalOpen = true;
        },

        closeEditModal() {
            this.isEditModalOpen = false;
            this.editError = '';
        },

        async saveEdit() {
            this.editError = '';
            const data = {
                username: this.editFormData.username,
                zona_id: parseInt(this.editFormData.zona_id, 10),
                monitor_interval: this.editFormData.monitor_interval ? parseInt(this.editFormData.monitor_interval, 10) : null
            };
            if (this.editFormData.password) {
                data.password = this.editFormData.password;
            }

            try {
                const response = await fetch(`${this.apiBaseUrl}/api/aps/${encodeURIComponent(this.currentHost)}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                if (!response.ok) {
                    const err = await response.json();
                    throw new Error(err.detail || 'Failed to update AP');
                }
                this.closeEditModal();
                await this.loadApDetails();
            } catch (error) {
                this.editError = error.message;
            }
        },

        // --- Delete Action ---
        async deleteAp() {
            const hostname = this.ap?.hostname || this.currentHost;

            window.ModalUtils.showConfirmModal({
                title: 'Delete AP',
                message: `Are you sure you want to delete the AP "<strong>${hostname}</strong>" (${this.currentHost})?<br><br>This action cannot be undone.`,
                confirmText: 'Delete AP',
                confirmIcon: 'delete',
                type: 'danger',
            }).then(async (confirmed) => {
                if (!confirmed) return;

                try {
                    const response = await fetch(`${this.apiBaseUrl}/api/aps/${encodeURIComponent(this.currentHost)}`, { method: 'DELETE' });
                    if (!response.ok) throw new Error('Failed to delete AP');
                    showToast('AP deleted successfully.', 'success');
                    window.location.href = '/aps';
                } catch (error) {
                    showToast(`Error: ${error.message}`, 'danger');
                }
            });
        },

        // --- Diagnostic Mode ---
        startDiagnosticMode() {
            this.stopDiagnosticMode(false);
            const DURATION_MINUTES = 5;
            this.diagnosticTimeRemaining = DURATION_MINUTES * 60;

            try {
                const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${wsProtocol}//${window.location.host}/api/ws/aps/${encodeURIComponent(this.currentHost)}/resources`;

                this.socket = new WebSocket(wsUrl);
                this.isDiagnosticActive = true;

                this.socket.onopen = () => {
                    console.log(`✅ WS AP: Connected to ${this.currentHost}`);
                };

                this.socket.onmessage = (event) => {
                    const message = JSON.parse(event.data);
                    if (message.type === 'resources') {
                        this.updateWithLiveData(message.data);
                    } else if (message.type === 'error') {
                        console.error('WS AP Error:', message.data.message);
                    }
                };

                this.socket.onclose = () => {
                    console.log(`WS AP: Connection closed for ${this.currentHost}`);
                    if (this.isDiagnosticActive) {
                        this.stopDiagnosticMode(true);
                    }
                };

                this.socket.onerror = (error) => {
                    console.error('WS AP Error:', error);
                    showToast('WebSocket connection error', 'danger');
                    this.stopDiagnosticMode(true);
                };

                // Countdown timer
                const countdown = () => {
                    this.diagnosticTimeRemaining--;
                    if (this.diagnosticTimeRemaining <= 0) {
                        this.stopDiagnosticMode(true);
                    }
                };
                this.countdownId = setInterval(countdown, 1000);
                this.timeoutId = setTimeout(() => this.stopDiagnosticMode(true), DURATION_MINUTES * 60 * 1000);

            } catch (error) {
                showToast('Could not start diagnostic mode.', 'danger');
                this.isDiagnosticActive = false;
            }
        },

        stopDiagnosticMode(restoreHistory = true) {
            if (this.socket) {
                this.socket.close();
                this.socket = null;
            }
            if (this.timeoutId) clearTimeout(this.timeoutId);
            if (this.countdownId) clearInterval(this.countdownId);
            this.timeoutId = null;
            this.countdownId = null;
            this.isDiagnosticActive = false;
            this.diagnosticTimeRemaining = 0;

            if (restoreHistory) {
                console.log('Exiting Live Mode, restoring history view...');
                this.loadData();
            }
        },

        updateWithLiveData(data) {
            // Update AP data reactively
            this.ap = { ...this.ap, ...data };
            this.liveCpes = data.clients || [];
            this.currentVendor = data.vendor || this.currentVendor;

            // Dispatch event for charts
            window.dispatchEvent(new CustomEvent('ap-live-data', { detail: data }));
        },

        // --- Computed helpers for display ---
        get diagnosticTimerDisplay() {
            if (!this.isDiagnosticActive) return '';
            const minutes = Math.floor(this.diagnosticTimeRemaining / 60);
            const seconds = this.diagnosticTimeRemaining % 60;
            return `(${minutes}:${seconds.toString().padStart(2, '0')})`;
        },

        get statusDisplay() {
            if (this.isDiagnosticActive) {
                return { class: 'text-orange animate-pulse', label: 'Live', dotClass: 'bg-orange' };
            }
            if (!this.ap) {
                return { class: 'text-text-secondary', label: 'Loading...', dotClass: 'bg-text-secondary' };
            }
            if (this.ap.last_status === 'online') {
                return { class: 'text-success', label: 'Online', dotClass: 'bg-success' };
            }
            return { class: 'text-danger', label: 'Offline', dotClass: 'bg-danger' };
        }
    });

    console.log('[Store] ApDetailsStore initialized');
});

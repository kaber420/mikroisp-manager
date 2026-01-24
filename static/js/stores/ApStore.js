/**
 * AP Store - Alpine.js Global Store
 *
 * Shared state for AP-related components. Registered with Alpine.store().
 *
 * Usage in Alpine components:
 *   Alpine.store('aps').list
 *   Alpine.store('aps').loadData()
 */
document.addEventListener('alpine:init', () => {
    Alpine.store('aps', {
        // --- State ---
        list: [],
        allZones: [],
        isLoading: true,

        // Filter state
        statusFilter: 'all',
        searchQuery: '',
        selectedZone: '',

        // Modal state
        isModalOpen: false,
        isEditing: false,
        originalHost: null,
        currentAp: {},
        error: '',

        // Test Connection state
        isTesting: false,
        testMessage: '',
        testStatus: '',

        // --- Computed: Filtered List ---
        get filteredList() {
            let result = this.list;

            // Status filter
            if (this.statusFilter === 'online') {
                result = result.filter(ap => ap.last_status === 'online');
            } else if (this.statusFilter === 'offline') {
                result = result.filter(ap => ap.last_status === 'offline');
            } else if (this.statusFilter === 'pending') {
                result = result.filter(ap => !ap.is_provisioned);
            }

            // Zone filter
            if (this.selectedZone) {
                result = result.filter(ap => ap.zona_id === parseInt(this.selectedZone));
            }

            // Search filter
            if (this.searchQuery.trim()) {
                const q = this.searchQuery.toLowerCase();
                result = result.filter(ap =>
                    (ap.hostname || '').toLowerCase().includes(q) ||
                    (ap.host || '').toLowerCase().includes(q) ||
                    (ap.mac || '').toLowerCase().includes(q)
                );
            }

            return result;
        },

        // --- Actions ---
        async loadData() {
            this.isLoading = true;
            try {
                const [apsRes, zonesRes] = await Promise.all([
                    fetch('/api/aps'),
                    fetch('/api/zonas')
                ]);
                if (!apsRes.ok) throw new Error('Failed to load APs.');
                if (!zonesRes.ok) throw new Error('Failed to load zones.');
                this.list = await apsRes.json();
                this.allZones = await zonesRes.json();
            } catch (error) {
                console.error('Error loading AP data:', error);
                this.error = error.message;
            } finally {
                this.isLoading = false;
            }
        },

        getZoneName(zoneId) {
            const zone = this.allZones.find(z => z.id === zoneId);
            return zone ? zone.nombre : 'Unassigned';
        },

        isProvisioned(ap) {
            return ap.is_provisioned === true;
        },

        // --- Multi-vendor Helpers ---
        getDefaultPort(vendor) {
            return vendor === 'mikrotik' ? 8729 : 443;
        },

        getPortHint(vendor) {
            if (vendor === 'mikrotik') {
                return 'Default: 8729 (API-SSL). Requires API-SSL enabled on MikroTik.';
            }
            return 'Default: 443 (HTTPS). Standard AirOS port.';
        },

        renderVendorBadge(vendor) {
            if (vendor === 'mikrotik') {
                return `<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-500/20 text-blue-400 border border-blue-500/30">MikroTik</span>`;
            }
            return `<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-500/20 text-green-400 border border-green-500/30">Ubiquiti</span>`;
        },

        renderStatusBadge(status) {
            if (status === 'online') return `<div class="flex items-center gap-2"><div class="size-2 rounded-full bg-success"></div><span>Online</span></div>`;
            if (status === 'offline') return `<div class="flex items-center gap-2 text-danger"><div class="size-2 rounded-full bg-danger"></div><span>Offline</span></div>`;
            return `<div class="flex items-center gap-2 text-text-secondary"><div class="size-2 rounded-full bg-text-secondary"></div><span>Unknown</span></div>`;
        },

        // --- Modal Actions ---
        openModal(ap = null) {
            this.error = '';
            this.testMessage = '';
            this.testStatus = '';
            this.isTesting = false;

            if (ap) {
                this.isEditing = true;
                this.originalHost = ap.host;
                this.currentAp = {
                    ...ap,
                    password: '' // Clear for security
                };
            } else {
                this.isEditing = false;
                this.originalHost = null;
                this.currentAp = {
                    host: '',
                    zona_id: '',
                    username: 'ubnt',
                    password: '',
                    monitor_interval: '',
                    vendor: 'ubiquiti',
                    api_port: ''
                };
            }
            this.isModalOpen = true;
        },

        closeModal() {
            this.isModalOpen = false;
            this.error = '';
        },

        onVendorChange() {
            if (!this.isEditing) {
                this.currentAp.api_port = '';
                if (this.currentAp.vendor === 'mikrotik' && this.currentAp.username === 'ubnt') {
                    this.currentAp.username = 'admin';
                } else if (this.currentAp.vendor === 'ubiquiti' && this.currentAp.username === 'admin') {
                    this.currentAp.username = 'ubnt';
                }
            }
        },

        async testConnection() {
            this.testMessage = '';
            this.testStatus = '';
            this.error = '';

            if (!this.currentAp.host || !this.currentAp.username || !this.currentAp.password) {
                this.testMessage = 'Host, Username, and Password are required for testing.';
                this.testStatus = 'error';
                return;
            }

            this.isTesting = true;

            try {
                const payload = {
                    host: this.currentAp.host,
                    username: this.currentAp.username,
                    password: this.currentAp.password,
                    zona_id: this.currentAp.zona_id || 0,
                    is_enabled: true,
                    vendor: this.currentAp.vendor || 'ubiquiti',
                    api_port: parseInt(this.currentAp.api_port) || this.getDefaultPort(this.currentAp.vendor)
                };

                const response = await fetch('/api/aps/validate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                const data = await response.json();
                if (!response.ok) throw new Error(data.detail || 'Connection failed');

                this.testMessage = data.message;
                this.testStatus = 'success';

            } catch (error) {
                this.testMessage = error.message;
                this.testStatus = 'error';
            } finally {
                this.isTesting = false;
            }
        },

        async save() {
            this.error = '';

            if (!this.currentAp.host || !this.currentAp.zona_id || !this.currentAp.username) {
                this.error = 'Please fill out all required fields (Host, Zone, Username).';
                return;
            }

            if (!this.isEditing && !this.currentAp.password) {
                this.error = 'Password is required for new APs.';
                return;
            }

            const url = this.isEditing
                ? `/api/aps/${encodeURIComponent(this.originalHost)}`
                : '/api/aps';
            const method = this.isEditing ? 'PUT' : 'POST';

            const defaultPort = this.getDefaultPort(this.currentAp.vendor);
            const payload = {
                ...this.currentAp,
                zona_id: parseInt(this.currentAp.zona_id),
                monitor_interval: this.currentAp.monitor_interval ? parseInt(this.currentAp.monitor_interval) : null,
                api_port: this.currentAp.api_port ? parseInt(this.currentAp.api_port) : defaultPort,
                vendor: this.currentAp.vendor || 'ubiquiti'
            };

            if (this.isEditing) {
                delete payload.host;
                if (!payload.password) delete payload.password;
            }

            try {
                const response = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (!response.ok) {
                    const err = await response.json();
                    throw new Error(err.detail || 'Failed to save AP.');
                }

                await this.loadData();
                this.closeModal();
            } catch (error) {
                this.error = error.message;
            }
        },

        async delete(host, hostname) {
            window.ModalUtils.showConfirmModal({
                title: 'Delete AP',
                message: `Are you sure you want to delete AP "<strong>${hostname || host}</strong>"?`,
                confirmText: 'Delete',
                confirmIcon: 'delete',
                type: 'danger',
            }).then(async (confirmed) => {
                if (confirmed) {
                    try {
                        const response = await fetch(`/api/aps/${encodeURIComponent(host)}`, { method: 'DELETE' });
                        if (!response.ok) {
                            const err = await response.json();
                            throw new Error(err.detail || 'Failed to delete AP.');
                        }
                        this.list = this.list.filter(ap => ap.host !== host);
                    } catch (error) {
                        showToast(`Error: ${error.message}`, 'danger');
                    }
                }
            });
        },

        async repair(ap) {
            const hostname = ap.hostname || ap.host;

            window.ModalUtils.showConfirmModal({
                title: 'Reparar AP',
                message: `¿Desea desvincular el AP "<strong>${hostname}</strong>"?<br><br>Esto mostrará el botón "Provision" para configurar SSL nuevamente.`,
                confirmText: 'Desvincular',
                confirmIcon: 'build',
                type: 'warning',
            }).then(async (confirmed) => {
                if (confirmed) {
                    const result = await window.SSLActions.unprovision('ap', ap.host);
                    if (result.success) {
                        await this.loadData();
                    }
                }
            });
        },

        async renewSSL(ap) {
            const hostname = ap.hostname || ap.host;

            window.ModalUtils.showConfirmModal({
                title: 'Renovar Certificados SSL',
                message: `¿Desea renovar los certificados SSL para "<strong>${hostname}</strong>"?<br><br>Esto reinstalará los certificados sin cambiar usuario/contraseña.`,
                confirmText: 'Renovar SSL',
                confirmIcon: 'security',
                type: 'primary',
            }).then(async (confirmed) => {
                if (confirmed) {
                    const result = await window.SSLActions.renew('ap', ap.host);
                    if (result.success) {
                        await this.loadData();
                    }
                }
            });
        }
    });

    console.log('[Store] ApStore initialized');
});

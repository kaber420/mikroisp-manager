document.addEventListener('alpine:init', () => {
    Alpine.store('switches', {
        // --- State ---
        list: [],
        allZones: [],
        isLoading: true,

        // Filter state
        statusFilter: 'all', // 'all', 'online', 'offline'
        searchQuery: '',

        // Modal state
        isModalOpen: false,
        isEditing: false,
        currentSwitch: {},
        error: '',

        // --- Computed: Filtered List ---
        get filteredList() {
            let result = this.list;

            // Status filter
            if (this.statusFilter === 'online') {
                result = result.filter(s => s.last_status === 'online');
            } else if (this.statusFilter === 'offline') {
                result = result.filter(s => s.last_status === 'offline');
            }

            // Search filter
            if (this.searchQuery.trim()) {
                const q = this.searchQuery.toLowerCase();
                result = result.filter(s =>
                    (s.hostname || '').toLowerCase().includes(q) ||
                    (s.host || '').toLowerCase().includes(q) ||
                    this.getZoneName(s.zona_id).toLowerCase().includes(q)
                );
            }

            return result;
        },

        // --- Actions ---

        async loadData() {
            this.isLoading = true;
            try {
                const [switchesRes, zonesRes] = await Promise.all([
                    fetch('/api/switches'),
                    fetch('/api/zonas')
                ]);
                if (!switchesRes.ok) throw new Error('Failed to load switches.');
                if (!zonesRes.ok) throw new Error('Failed to load zones.');
                this.list = await switchesRes.json();
                this.allZones = await zonesRes.json();
            } catch (error) {
                console.error('Error loading switches data:', error);
                this.error = error.message;
            } finally {
                this.isLoading = false;
            }
        },

        getZoneName(zoneId) {
            if (!zoneId) return 'Unassigned';
            const zone = this.allZones.find(z => z.id === zoneId);
            return zone ? zone.nombre : 'Unassigned';
        },

        // --- Modal Actions ---

        openModal(sw = null) {
            this.error = '';
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
            this.isModalOpen = true;
        },

        closeModal() {
            this.isModalOpen = false;
            this.currentSwitch = {};
        },

        async save() {
            this.error = '';

            // Validation
            if (!this.currentSwitch.host || !this.currentSwitch.username) {
                this.error = 'Please fill in all required fields (Host and Username).';
                return;
            }
            if (!this.isEditing && !this.currentSwitch.password) {
                this.error = 'Password is required for a new switch.';
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

                const savedSwitch = await response.json();

                // For new switches, immediately check connection
                if (!this.isEditing) {
                    if (typeof showToast === 'function') {
                        showToast('Switch added! Checking connection...', 'primary');
                    }
                    this.testConnection(savedSwitch, true); // Auto-test after add
                } else {
                    if (typeof showToast === 'function') {
                        showToast('Switch updated successfully!', 'success');
                    }
                    await this.loadData();
                }

                this.closeModal();
            } catch (error) {
                this.error = error.message;
            }
        },

        async delete(host, hostname) {
            window.ModalUtils.showConfirmModal({
                title: 'Delete Switch',
                message: `Are you sure you want to delete switch "<strong>${hostname || host}</strong>"?`,
                confirmText: 'Delete',
                confirmIcon: 'delete',
                type: 'danger',
            }).then(async (confirmed) => {
                if (confirmed) {
                    try {
                        const response = await fetch(`/api/switches/${encodeURIComponent(host)}`, { method: 'DELETE' });
                        if (!response.ok) {
                            const err = await response.json();
                            throw new Error(err.detail || 'Failed to delete switch.');
                        }
                        this.list = this.list.filter(s => s.host !== host);

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
                }
            });
        },

        async testConnection(sw, isNew = false) {
            try {
                if (!isNew && typeof showToast === 'function') {
                    showToast(`Checking ${sw.hostname || sw.host}...`, 'primary');
                }

                // Use /check endpoint which updates the database
                const response = await fetch(`/api/switches/${encodeURIComponent(sw.host)}/check`, {
                    method: 'POST'
                });

                if (response.ok) {
                    const data = await response.json();
                    if (typeof showToast === 'function') {
                        const hostname = data.device_info?.hostname || sw.host;
                        const cpu = data.device_info?.cpu_load || 'N/A';
                        if (isNew) {
                            showToast('Switch added and connected successfully!', 'success');
                        } else {
                            showToast(`✅ ${hostname} is online! CPU: ${cpu}%`, 'success');
                        }
                    }
                    // Reload to update status and device info in table
                    await this.loadData();
                } else {
                    const err = await response.json();
                    if (typeof showToast === 'function') {
                        if (isNew) {
                            showToast('Switch added but connection check failed. Check credentials.', 'warning');
                        } else {
                            showToast(`❌ ${sw.hostname || sw.host}: ${err.detail || 'Connection failed'}`, 'danger');
                        }
                    }
                    // Still reload to show offline status
                    await this.loadData();
                }
            } catch (error) {
                if (typeof showToast === 'function') {
                    if (isNew) {
                        showToast('Switch added but connection check failed.', 'warning');
                    } else {
                        showToast(`❌ Connection failed: ${error.message}`, 'danger');
                    }
                }
                await this.loadData();
            }
        },

        async repairSSL(switchHost) {
            window.ModalUtils.showConfirmModal({
                title: 'Reparar SSL Switch',
                message: `¿Está seguro de que desea reparar SSL para el switch "<strong>${switchHost}</strong>"?<br><br>Esto instalará la CA de confianza y generará un nuevo certificado.`,
                confirmText: 'Reparar SSL',
                confirmIcon: 'build',
                type: 'warning',
            }).then(async (confirmed) => {
                if (confirmed) {
                    const result = await window.SSLActions.renew('switch', switchHost);
                    if (result.success) {
                        await this.loadData();
                    }
                }
            });
        },

        async unlinkSSL(switchHost) {
            window.ModalUtils.showConfirmModal({
                title: 'Desvincular Switch',
                message: `¿Desea desvincular el switch "<strong>${switchHost}</strong>"?<br><br>Esto mostrará el botón "Provision" para configurar SSL nuevamente.`,
                confirmText: 'Desvincular',
                confirmIcon: 'link_off',
                type: 'warning',
            }).then(async (confirmed) => {
                if (confirmed) {
                    const result = await window.SSLActions.unprovision('switch', switchHost);
                    if (result.success) {
                        await this.loadData();
                    }
                }
            });
        }
    });
});

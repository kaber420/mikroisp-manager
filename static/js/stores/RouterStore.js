/**
 * Router Store - Alpine.js Global Store
 *
 * Shared state for router-related components. Registered with Alpine.store().
 *
 * Usage in Alpine components:
 *   Alpine.store('routers').list
 *   Alpine.store('routers').loadRouters()
 */
document.addEventListener('alpine:init', () => {
    Alpine.store('routers', {
        // --- State ---
        list: [],
        allZones: [],
        isLoading: true,

        // Filter state
        statusFilter: 'all',
        searchQuery: '',

        // Modal state
        isModalOpen: false,
        isEditing: false,
        currentRouter: {},
        error: '',

        // --- Computed: Filtered List ---
        get filteredList() {
            let result = this.list;

            // Status filter
            if (this.statusFilter === 'online') {
                result = result.filter(r => r.is_provisioned && r.last_status === 'online');
            } else if (this.statusFilter === 'offline') {
                result = result.filter(r => r.is_provisioned && r.last_status === 'offline');
            } else if (this.statusFilter === 'pending') {
                result = result.filter(r => !r.is_provisioned);
            }

            // Search filter
            if (this.searchQuery.trim()) {
                const q = this.searchQuery.toLowerCase();
                result = result.filter(r =>
                    (r.hostname || '').toLowerCase().includes(q) ||
                    (r.host || '').toLowerCase().includes(q) ||
                    this.getZoneName(r.zona_id).toLowerCase().includes(q)
                );
            }

            return result;
        },

        // --- Actions ---
        async loadData() {
            this.isLoading = true;
            try {
                const [routersRes, zonesRes] = await Promise.all([
                    fetch('/api/routers'),
                    fetch('/api/zonas')
                ]);
                if (!routersRes.ok) throw new Error('Failed to load routers.');
                if (!zonesRes.ok) throw new Error('Failed to load zones.');
                this.list = await routersRes.json();
                this.allZones = await zonesRes.json();
            } catch (error) {
                console.error('Error loading router data:', error);
                this.error = error.message;
            } finally {
                this.isLoading = false;
            }
        },

        getZoneName(zoneId) {
            const zone = this.allZones.find(z => z.id === zoneId);
            return zone ? zone.nombre : 'Unassigned';
        },

        isProvisioned(router) {
            return router.is_provisioned === true;
        },

        // --- Modal Actions ---
        openModal(router = null) {
            this.error = '';
            if (router) {
                this.isEditing = true;
                this.currentRouter = {
                    ...router,
                    password: '', // Clear password for security
                };
            } else {
                this.isEditing = false;
                this.currentRouter = {
                    host: '',
                    zona_id: '',
                    api_port: 8728,
                    username: 'admin',
                    password: '',
                };
            }
            this.isModalOpen = true;
        },

        closeModal() {
            this.isModalOpen = false;
            this.currentRouter = {};
        },

        async save() {
            this.error = '';
            if (!this.currentRouter.host || !this.currentRouter.zona_id || !this.currentRouter.username) {
                this.error = 'Please fill in all required fields.';
                return;
            }
            if (!this.isEditing && !this.currentRouter.password) {
                this.error = 'Password is required for a new router.';
                return;
            }

            const url = this.isEditing
                ? `/api/routers/${encodeURIComponent(this.currentRouter.host)}`
                : '/api/routers';
            const method = this.isEditing ? 'PUT' : 'POST';

            // Don't send an empty password when editing
            const body = { ...this.currentRouter };
            if (this.isEditing && !body.password) {
                delete body.password;
            }

            try {
                const response = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body)
                });
                if (!response.ok) {
                    const err = await response.json();
                    throw new Error(err.detail || 'Failed to save router.');
                }
                await this.loadData();
                this.closeModal();
            } catch (error) {
                this.error = error.message;
            }
        },

        async delete(host, hostname) {
            window.ModalUtils.showConfirmModal({
                title: 'Delete Router',
                message: `Are you sure you want to delete router "<strong>${hostname || host}</strong>"?`,
                confirmText: 'Delete',
                confirmIcon: 'delete',
                type: 'danger',
            }).then(async (confirmed) => {
                if (confirmed) {
                    try {
                        const response = await fetch(`/api/routers/${encodeURIComponent(host)}`, { method: 'DELETE' });
                        if (!response.ok) {
                            const err = await response.json();
                            throw new Error(err.detail || 'Failed to delete router.');
                        }
                        this.list = this.list.filter(r => r.host !== host);
                    } catch (error) {
                        showToast(`Error: ${error.message}`, 'danger');
                    }
                }
            });
        },

        async repair(router) {
            const hostname = router.hostname || router.host;

            window.ModalUtils.showConfirmModal({
                title: 'Reparar Router',
                message: `¿Desea permitir re-aprovisionar el router "<strong>${hostname}</strong>"?<br><br>Esto mostrará el botón "Provision" para configurar SSL nuevamente.`,
                confirmText: 'Permitir',
                confirmIcon: 'build',
                type: 'warning',
            }).then(async (confirmed) => {
                if (confirmed) {
                    try {
                        const url = `/api/routers/${encodeURIComponent(router.host)}/repair?reset_provision=true`;
                        const response = await fetch(url, { method: 'POST' });
                        const data = await response.json();

                        if (!response.ok) {
                            throw new Error(data.detail || 'Error al reparar router');
                        }

                        showToast('Router listo para re-aprovisionar', 'success');
                        await this.loadData();

                    } catch (error) {
                        console.error('Repair error:', error);
                        showToast(`Error: ${error.message}`, 'danger');
                    }
                }
            });
        }
    });

    console.log('[Store] RouterStore initialized');
});

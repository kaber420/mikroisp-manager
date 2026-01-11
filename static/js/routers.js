// static/js/routers.js

document.addEventListener('alpine:init', () => {
    Alpine.data('routerManager', () => ({
        // Spread the shared provisioning mixin
        ...window.provisionMixin,

        // State
        routers: [],
        allZones: [],
        isLoading: true,
        isRouterModalOpen: false,
        currentRouter: {},
        routerError: '',
        isEditing: false,

        // --- INIT ---
        async init() {
            this.isLoading = true;
            await this.loadData();
            this.isLoading = false;

            // Reactividad global
            window.addEventListener('data-refresh-needed', () => {
                if (!this.isRouterModalOpen && !this.isProvisionModalOpen) {
                    console.log("⚡ Routers: Recargando estado...");
                    this.loadData();
                }
            });
        },

        // Alias for the mixin's auto-refresh after provisioning
        async loadInitialData() {
            return this.loadData();
        },

        // Methods
        async loadData() {
            try {
                const [routersRes, zonesRes] = await Promise.all([
                    fetch('/api/routers'),
                    fetch('/api/zonas')
                ]);
                if (!routersRes.ok) throw new Error('Failed to load routers.');
                if (!zonesRes.ok) throw new Error('Failed to load zones.');
                this.routers = await routersRes.json();
                this.allZones = await zonesRes.json();
            } catch (error) {
                console.error('Error loading data:', error);
                this.routerError = error.message;
            }
        },

        getZoneName(zoneId) {
            const zone = this.allZones.find(z => z.id === zoneId);
            return zone ? zone.nombre : 'Unassigned';
        },

        // Router Modal
        openRouterModal(router = null) {
            this.routerError = '';
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
            this.isRouterModalOpen = true;
        },

        closeRouterModal() {
            this.isRouterModalOpen = false;
            this.currentRouter = {};
        },

        async saveRouter() {
            this.routerError = '';
            if (!this.currentRouter.host || !this.currentRouter.zona_id || !this.currentRouter.username) {
                this.routerError = 'Please fill in all required fields.';
                return;
            }
            if (!this.isEditing && !this.currentRouter.password) {
                this.routerError = 'Password is required for a new router.';
                return;
            }

            const url = this.isEditing ? `/api/routers/${encodeURIComponent(this.currentRouter.host)}` : '/api/routers';
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
                this.closeRouterModal();
            } catch (error) {
                this.routerError = error.message;
            }
        },

        async deleteRouter(host, hostname) {
            if (!confirm(`Are you sure you want to delete router "${hostname || host}"?`)) return;

            try {
                const response = await fetch(`/api/routers/${encodeURIComponent(host)}`, { method: 'DELETE' });
                if (!response.ok) {
                    const err = await response.json();
                    throw new Error(err.detail || 'Failed to delete router.');
                }
                this.routers = this.routers.filter(r => r.host !== host);
            } catch (error) {
                showToast(`Error: ${error.message}`, 'danger');
            }
        },

        // Override openProvisionModal to set Router-specific values
        openProvisionModal(router) {
            // Call base mixin method with router-specific config
            window.provisionMixin.openProvisionModal.call(this, router, 'Router', '/api/routers');
        },

        // Repair router - allows re-provisioning
        async repairRouter(router) {
            const hostname = router.hostname || router.host;

            if (!confirm(`¿Desea permitir re-aprovisionar el router "${hostname}"?\n\nEsto mostrará el botón "Provision" para configurar SSL nuevamente.`)) {
                return;
            }

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
        },

        isRouterProvisioned(router) {
            return router.is_provisioned === true;
        }
    }));
});

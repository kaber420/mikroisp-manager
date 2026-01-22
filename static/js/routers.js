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

        // Plans State
        plans: [],
        isPlansModalOpen: false,
        showPlanForm: false,
        currentPlan: {},
        planError: '',
        editingPlan: false,

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
                        this.routers = this.routers.filter(r => r.host !== host);
                    } catch (error) {
                        showToast(`Error: ${error.message}`, 'danger');
                    }
                }
            });
        },

        // Override openProvisionModal to set Router-specific values
        openProvisionModal(router) {
            // Call base mixin method with router-specific config
            window.provisionMixin.openProvisionModal.call(this, router, 'Router', '/api/routers');
        },

        // Repair router - allows re-provisioning
        async repairRouter(router) {
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
        },

        isRouterProvisioned(router) {
            return router.is_provisioned === true;
        },

        // --- Plan Management ---
        async openPlansModal() {
            this.isPlansModalOpen = true;
            await this.loadPlans();
        },

        closePlansModal() {
            this.isPlansModalOpen = false;
            this.showPlanForm = false;
            this.currentPlan = {};
            this.planError = '';
        },

        async loadPlans() {
            try {
                const response = await fetch('/api/plans');
                if (!response.ok) throw new Error('Failed to load plans');
                this.plans = await response.json();
            } catch (error) {
                console.error('Error loading plans:', error);
                showToast(`Error: ${error.message}`, 'danger');
            }
        },

        openPlanForm(plan = null) {
            this.planError = '';
            if (plan) {
                this.editingPlan = true;
                this.currentPlan = { ...plan };
            } else {
                this.editingPlan = false;
                this.currentPlan = this.getDefaultPlan();
            }
            this.showPlanForm = true;
        },

        closePlanForm() {
            this.showPlanForm = false;
            this.currentPlan = {};
            this.planError = '';
            this.editingPlan = false;
        },

        getDefaultPlan() {
            return {
                name: '',
                max_limit: '',
                router_host: '',
                price: 0,
                plan_type: 'simple_queue',
                parent_queue: 'none',
                v6_queue_type: 'default-small',
                v7_queue_type: 'cake-default',
                profile_name: '',
            };
        },

        async savePlan() {
            this.planError = '';
            if (!this.currentPlan.name || !this.currentPlan.max_limit) {
                this.planError = 'Please fill in all required fields.';
                return;
            }

            // Convert empty router_host to null for Universal Plans
            const planData = { ...this.currentPlan };
            if (planData.router_host === '') {
                planData.router_host = null;
            }

            try {
                let response;
                if (this.editingPlan) {
                    // For now, delete and recreate (simple approach)
                    // TODO: Add PUT endpoint in API
                    await fetch(`/api/plans/${this.currentPlan.id}`, { method: 'DELETE' });
                    response = await fetch('/api/plans', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(planData)
                    });
                } else {
                    response = await fetch('/api/plans', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(planData)
                    });
                }

                if (!response.ok) {
                    const err = await response.json();
                    throw new Error(err.detail || 'Failed to save plan');
                }

                showToast(this.editingPlan ? 'Plan updated successfully!' : 'Plan created successfully!', 'success');
                await this.loadPlans();
                this.closePlanForm();
            } catch (error) {
                this.planError = error.message;
            }
        },

        editPlan(plan) {
            this.openPlanForm(plan);
        },

        async deletePlan(plan) {
            window.ModalUtils.showConfirmModal({
                title: 'Delete Plan',
                message: `Are you sure you want to delete the plan "<strong>${plan.name}</strong>"?`,
                confirmText: 'Delete',
                confirmIcon: 'delete',
                type: 'danger',
            }).then(async (confirmed) => {
                if (confirmed) {
                    try {
                        const response = await fetch(`/api/plans/${plan.id}`, { method: 'DELETE' });
                        if (!response.ok) {
                            const err = await response.json();
                            throw new Error(err.detail || 'Failed to delete plan');
                        }
                        showToast('Plan deleted successfully!', 'success');
                        this.plans = this.plans.filter(p => p.id !== plan.id);
                    } catch (error) {
                        showToast(`Error: ${error.message}`, 'danger');
                    }
                }
            });
        }
    }));
});

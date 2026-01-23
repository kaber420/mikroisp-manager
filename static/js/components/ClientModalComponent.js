/**
 * Client Modal Component - Alpine.js
 * 
 * Handles Client creation/editing and Service provisioning.
 * Extracted from the monolithic clients.js.
 * 
 * Usage: <div x-data="clientModal">...</div>
 */
document.addEventListener('alpine:init', () => {
    Alpine.data('clientModal', () => ({
        isModalOpen: false,
        isLoadingData: false,
        currentTab: 'info',
        isEditing: false,

        // Form Data
        client: {},
        service: {},

        // Errors
        errors: { client: '', service: '' },

        // Catalogs
        assignedCpes: [],
        unassignedCpes: [],
        routers: [],
        profiles: [],
        plans: [],
        selectedPlan: null,

        // UI toggles
        selectedCpeToAssign: '',
        pppoePasswordVisible: false,

        // --- Computed: Filter plans by type ---
        get pppoeePlansFiltered() {
            return this.plans.filter(p => p.plan_type === 'pppoe');
        },
        get simpleQueuePlansFiltered() {
            return this.plans.filter(p => p.plan_type === 'simple_queue' || !p.plan_type);
        },

        init() {
            window.addEventListener('open-client-modal', (e) => {
                this.openModal(e.detail?.client || null);
            });
        },

        async openModal(client = null) {
            this.reset();
            this.isModalOpen = true;
            this.isLoadingData = true;

            if (client) {
                this.isEditing = true;
                this.client = { ...client };
                await this.loadDependencies(client.id);
            } else {
                this.isEditing = false;
                this.client = { service_status: 'active' };
                await this.loadDependencies(null);
            }
            this.isLoadingData = false;
        },

        closeModal() {
            this.isModalOpen = false;
            this.reset();
            // Notify list to refresh
            Alpine.store('clientList').loadClients();
        },

        reset() {
            this.currentTab = 'info';
            this.isEditing = false;
            this.client = {};
            this.service = {};
            this.errors = { client: '', service: '' };
            this.assignedCpes = [];
            this.unassignedCpes = [];
            this.routers = [];
            this.profiles = [];
            this.plans = [];
            this.selectedPlan = null;
            this.pppoePasswordVisible = false;
        },

        switchTab(tab) {
            if (tab === 'service' && !this.isEditing) return;
            this.currentTab = tab;
        },

        // --- Data Loading ---
        async loadDependencies(clientId) {
            const reqs = [
                this.loadRouters(),
                this.loadPlans(),
                this.loadUnassignedCpes()
            ];

            if (clientId) {
                reqs.push(this.loadAssignedCpes(clientId));
                reqs.push(this.loadClientService(clientId));
            }

            await Promise.all(reqs);
        },

        async loadRouters() {
            try { this.routers = await (await fetch('/api/routers')).json(); } catch (e) { }
        },

        async loadPlans(routerHost = null) {
            try {
                const url = routerHost ? `/api/plans/router/${routerHost}` : '/api/plans';
                this.plans = await (await fetch(url)).json();
            } catch (e) { this.plans = []; }
        },

        async loadAssignedCpes(id) {
            try { this.assignedCpes = await (await fetch(`/api/clients/${id}/cpes`)).json(); } catch (e) { }
        },

        async loadUnassignedCpes() {
            try { this.unassignedCpes = await (await fetch('/api/cpes/unassigned')).json(); } catch (e) { }
        },

        async loadClientService(id) {
            try {
                const services = await (await fetch(`/api/clients/${id}/services`)).json();
                if (services && services.length) {
                    this.service = services[0];
                    if (this.service.service_type === 'pppoe' && this.service.router_host) {
                        await this.handleRouterChange();
                        this.service.profile_name = services[0].profile_name;
                    } else if (this.service.service_type === 'simple_queue') {
                        this.handlePlanChange();
                    }
                } else {
                    this.service = {
                        pppoe_username: this.client.name.trim().replace(/\s+/g, '.').toLowerCase()
                    };
                }
            } catch (e) { }
        },

        // --- Logic Handlers ---
        async handleRouterChange() {
            const host = this.service.router_host;
            this.profiles = [];
            if (!host) return;
            try {
                this.profiles = await (await fetch(`/api/routers/${host}/pppoe/profiles`)).json();
                await this.loadPlans(host);
            } catch (e) { console.error('Failed to load profiles'); }
        },

        handlePlanChange() {
            if (!Array.isArray(this.plans)) return;
            if (!this.service.plan_id) {
                this.selectedPlan = null;
                return;
            }
            const planIdInt = parseInt(this.service.plan_id, 10);
            this.selectedPlan = this.plans.find(p => p.id === planIdInt);
            console.log('handlePlanChange:', planIdInt, 'selectedPlan:', this.selectedPlan);
        },

        detectClientIp() {
            if (this.assignedCpes && this.assignedCpes.length > 0) {
                const cpe = this.assignedCpes.find(c => c.ip_address && c.ip_address !== '0.0.0.0');
                return cpe ? cpe.ip_address : null;
            }
            return null;
        },

        // --- Actions ---
        async saveClient() {
            this.errors.client = '';
            if (!this.client.name) { this.errors.client = 'Name is required.'; return; }

            const method = this.isEditing ? 'PUT' : 'POST';
            const url = this.isEditing ? `/api/clients/${this.client.id}` : '/api/clients';

            try {
                const res = await fetch(url, {
                    method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.client)
                });
                if (!res.ok) throw new Error((await res.json()).detail);

                const data = await res.json();
                Alpine.store('clientList').updateClient(data);

                if (!this.isEditing) {
                    this.isEditing = true;
                    this.client = data;
                    this.service.pppoe_username = data.name.trim().replace(/\s+/g, '.').toLowerCase();
                    await this.loadDependencies(data.id);
                    this.switchTab('service');
                    if (window.showToast) window.showToast('Client created. Now configure service.', 'success');
                } else {
                    this.closeModal();
                    if (window.showToast) window.showToast('Client updated.', 'success');
                }
            } catch (e) {
                this.errors.client = e.message;
            }
        },

        async saveService() {
            this.errors.service = '';
            const { router_host, service_type } = this.service;

            if (!router_host || !service_type) {
                this.errors.service = 'Router and Service Type are required.';
                return;
            }

            try {
                const isUpdate = !!this.service.id;

                let routerResourceId = this.service.router_secret_id;
                let profileNameOrPlan = this.service.profile_name || (this.selectedPlan ? this.selectedPlan.name : '');
                let targetIp = this.service.ip_address;

                // Only provision on router if this is a CREATE (not update)
                if (!isUpdate) {
                    if (service_type === 'simple_queue') {
                        if (!this.selectedPlan) {
                            this.errors.service = 'Please select a Service Plan.';
                            return;
                        }
                        targetIp = this.detectClientIp() || this.service.manual_ip;
                        if (!targetIp) {
                            this.errors.service = 'Please enter a manual IP address or assign a CPE with detected IP.';
                            return;
                        }

                        const queuePayload = {
                            name: this.client.name,
                            target: targetIp,
                            max_limit: this.selectedPlan.max_limit,
                            parent: this.selectedPlan.parent_queue || 'none',
                            comment: `Client-ID:${this.client.id} | Plan:${this.selectedPlan.name}`
                        };

                        const routerRes = await fetch(`/api/routers/${router_host}/write/add-simple-queue`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(queuePayload)
                        });

                        if (!routerRes.ok) throw new Error(`Router Error: ${(await routerRes.json()).detail}`);

                        const newQueue = await routerRes.json();
                        routerResourceId = newQueue.id || newQueue['.id'] || targetIp;
                        profileNameOrPlan = this.selectedPlan.name;

                    } else if (service_type === 'pppoe') {
                        const { pppoe_username, password } = this.service;

                        if (!this.selectedPlan) {
                            this.errors.service = 'Please select a PPPoE Plan.';
                            return;
                        }

                        if (!pppoe_username || !password) {
                            this.errors.service = 'PPPoE Username and Password are required.';
                            return;
                        }

                        const profileFromPlan = this.selectedPlan.profile_name || 'default';

                        const pppoePayload = {
                            username: pppoe_username,
                            password: password,
                            service: 'pppoe',
                            profile: profileFromPlan,
                            comment: `Client-ID: ${this.client.id} | Plan: ${this.selectedPlan.name}`
                        };

                        const routerRes = await fetch(`/api/routers/${router_host}/pppoe/secrets`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(pppoePayload)
                        });

                        if (!routerRes.ok) {
                            const err = await routerRes.json().catch(() => ({ detail: 'Unknown Router Error' }));
                            throw new Error(`Router Error: ${err.detail}`);
                        }

                        const newSecret = await routerRes.json();
                        routerResourceId = newSecret['.id'];
                        profileNameOrPlan = profileFromPlan;
                    }
                }

                const serviceData = {
                    router_host,
                    service_type,
                    pppoe_username: service_type === 'pppoe' ? this.service.pppoe_username : this.client.name,
                    router_secret_id: routerResourceId,
                    profile_name: profileNameOrPlan,
                    plan_id: this.service.plan_id || (this.selectedPlan ? this.selectedPlan.id : null),
                    ip_address: targetIp,
                    suspension_method: this.service.suspension_method || 'address_list',
                    address: this.service.address || null,
                    status: this.service.status || 'active',
                    billing_day: this.service.billing_day || null,
                    notes: this.service.notes || null
                };

                const url = isUpdate
                    ? `/api/services/${this.service.id}`
                    : `/api/clients/${this.client.id}/services`;

                const method = isUpdate ? 'PUT' : 'POST';

                console.log(`Saving Service: ${method} ${url}`, serviceData);

                const serviceRes = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(serviceData)
                });

                if (!serviceRes.ok) throw new Error(`API Error: ${(await serviceRes.json()).detail}`);

                if (window.showToast) showToast(isUpdate ? 'Service updated successfully!' : 'Service created successfully!', 'success');
                this.closeModal();

            } catch (error) {
                console.error(error);
                this.errors.service = error.message;
            }
        },

        // --- CPE Methods ---
        async assignCpe() {
            if (!this.selectedCpeToAssign) return;
            try {
                await fetch(`/api/cpes/${this.selectedCpeToAssign}/assign/${this.client.id}`, { method: 'POST' });
                this.selectedCpeToAssign = '';
                await this.loadAssignedCpes(this.client.id);
                await this.loadUnassignedCpes();
            } catch (e) { if (window.showToast) showToast(e.message, 'danger'); }
        },

        async unassignCpe(cpeMac) {
            const confirmed = await window.ModalUtils.showConfirmModal({
                title: 'Desasignar CPE',
                message: `¿Estás seguro de que deseas desasignar este CPE (${cpeMac}) del cliente?`,
                confirmText: 'Desasignar',
                cancelText: 'Cancelar',
                confirmIcon: 'link_off',
                type: 'warning'
            });

            if (!confirmed) return;

            try {
                const response = await fetch(`/api/cpes/${cpeMac}/unassign`, { method: 'POST' });
                if (!response.ok) {
                    const err = await response.json().catch(() => ({ detail: response.statusText }));
                    throw new Error(err.detail || 'Failed to unassign CPE');
                }
                if (window.showToast) showToast('CPE desasignado correctamente', 'success');
                await this.loadAssignedCpes(this.client.id);
                await this.loadUnassignedCpes();
            } catch (error) { if (window.showToast) showToast(`Error: ${error.message}`, 'danger'); }
        },

        getStatusBadgeClass(status) {
            return {
                'active': 'bg-success/20 text-success',
                'pendiente': 'bg-warning/20 text-warning',
                'suspended': 'bg-danger/20 text-danger',
                'cancelled': 'bg-surface-2 text-text-secondary'
            }[status] || 'bg-surface-2 text-text-secondary';
        }
    }));
});

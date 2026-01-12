document.addEventListener('alpine:init', () => {
    Alpine.data('clientManager', () => ({
        // --- STATE ---
        allClients: [],
        isLoading: true,
        isModalOpen: false,
        currentTab: 'info',

        // Filtering
        searchQuery: '',
        statusFilter: 'all',

        // Modal State
        isEditing: false,
        currentClient: {},
        currentService: {},
        clientError: '',
        serviceError: '',

        // CPE State
        assignedCpes: [],
        unassignedCpes: [],
        selectedCpeToAssign: '',

        // Service State
        routersForSelect: [],
        profilesForSelect: [],
        pppoePasswordVisible: false,
        servicePlans: [],
        selectedPlan: null,

        // --- COMPUTED: Filtrar planes por tipo ---
        get pppoeePlansFiltered() {
            return this.servicePlans.filter(p => p.plan_type === 'pppoe');
        },
        get simpleQueuePlansFiltered() {
            return this.servicePlans.filter(p => p.plan_type === 'simple_queue' || !p.plan_type);
        },

        // --- COMPUTED ---
        get filteredClients() {
            return this.allClients.filter(client => {
                const statusMatch = this.statusFilter === 'all' || client.service_status === this.statusFilter;
                const searchMatch = !this.searchQuery ||
                    client.name.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
                    (client.address && client.address.toLowerCase().includes(this.searchQuery.toLowerCase())) ||
                    (client.phone_number && client.phone_number.includes(this.searchQuery.toLowerCase()));
                return statusMatch && searchMatch;
            });
        },

        // --- METHODS ---
        // --- INIT ACTUALIZADO ---
        async init() {
            this.isLoading = true;
            await this.loadClients();
            this.isLoading = false;

            // NUEVO: Reactividad
            window.addEventListener('data-refresh-needed', () => {
                if (!this.isModalOpen) {
                    console.log("⚡ Clients: Recargando datos...");
                    this.loadClients();
                }
            });
        },

        async loadClients() {
            try {
                this.allClients = await (await fetch('/api/clients')).json();
            } catch (error) {
                console.error('Failed to load clients', error);
                showToast('Error: Could not load clients.', 'danger');
            }
        },

        // Modal Management
        async openClientModal(client = null) {
            this.resetModalState();
            if (client) {
                this.isEditing = true;
                this.currentClient = { ...client };
                await this.loadDataForModal(client.id);
            } else {
                this.isEditing = false;
                this.currentClient = { service_status: 'active' };
            }
            this.isModalOpen = true;
        },

        closeClientModal() {
            this.isModalOpen = false;
            this.resetModalState();
            this.loadClients();
        },

        resetModalState() {
            this.currentTab = 'info';
            this.isEditing = false;
            this.currentClient = {};
            this.currentService = {};
            this.clientError = '';
            this.serviceError = '';
            this.assignedCpes = [];
            this.unassignedCpes = [];
            this.routersForSelect = [];
            this.profilesForSelect = [];
            this.pppoePasswordVisible = false;
            this.servicePlans = [];
            this.selectedPlan = null;
        },

        async loadDataForModal(clientId) {
            const promises = [
                this.loadAssignedCpes(clientId),
                this.loadUnassignedCpes(),
                this.loadRoutersForSelect(),
                this.loadServicePlans(),
                this.loadClientService(clientId)
            ];
            await Promise.all(promises);
        },

        switchTab(tabName) {
            if (tabName === 'service' && !this.isEditing) return;
            this.currentTab = tabName;
        },

        // Client Form (Tab 1)
        async saveClient() {
            this.clientError = '';
            if (!this.currentClient.name) {
                this.clientError = 'Client name is required.';
                return;
            }

            const url = this.isEditing ? `/api/clients/${this.currentClient.id}` : '/api/clients';
            const method = this.isEditing ? 'PUT' : 'POST';

            try {
                const response = await fetch(url, {
                    method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.currentClient)
                });
                if (!response.ok) throw new Error((await response.json()).detail);

                const savedClient = await response.json();
                await this.loadClients();

                if (!this.isEditing) {
                    this.isEditing = true;
                    this.currentClient = savedClient;
                    this.currentService.pppoe_username = savedClient.name.trim().replace(/\s+/g, '.').toLowerCase();
                    await this.loadDataForModal(savedClient.id);
                    this.switchTab('service');
                } else {
                    this.closeClientModal();
                }
            } catch (error) {
                this.clientError = error.message;
            }
        },

        async deleteClient(clientId, clientName) {
            if (!confirm(`Are you sure you want to delete client "${clientName}"?`)) return;
            try {
                const response = await fetch(`/api/clients/${clientId}`, { method: 'DELETE' });
                if (!response.ok) throw new Error((await response.json()).detail);
                this.allClients = this.allClients.filter(c => c.id !== clientId);
            } catch (error) {
                showToast(`Error: ${error.message}`, 'danger');
            }
        },

        // CPE Management
        async loadAssignedCpes(clientId) {
            try {
                this.assignedCpes = await (await fetch(`/api/clients/${clientId}/cpes`)).json();
            } catch (e) { console.error('Failed to load assigned CPEs'); }
        },
        async loadUnassignedCpes() {
            try {
                this.unassignedCpes = await (await fetch('/api/cpes/unassigned')).json();
            } catch (e) { console.error('Failed to load unassigned CPEs'); }
        },
        async assignCpe() {
            if (!this.selectedCpeToAssign) return;
            try {
                await fetch(`/api/cpes/${this.selectedCpeToAssign}/assign/${this.currentClient.id}`, { method: 'POST' });
                await this.loadAssignedCpes(this.currentClient.id);
                await this.loadUnassignedCpes();
                await this.loadClients();
                this.selectedCpeToAssign = '';
            } catch (error) { showToast(`Error: ${error.message}`, 'danger'); }
        },
        async unassignCpe(cpeMac) {
            if (!confirm('Unassign this CPE?')) return;
            try {
                await fetch(`/api/cpes/${cpeMac}/unassign`, { method: 'POST' });
                await this.loadAssignedCpes(this.currentClient.id);
                await this.loadUnassignedCpes();
                await this.loadClients();
            } catch (error) { showToast(`Error: ${error.message}`, 'danger'); }
        },

        // Service Form (Tab 2)
        async loadClientService(clientId) {
            try {
                const services = await (await fetch(`/api/clients/${clientId}/services`)).json();
                if (services && services.length > 0) {
                    this.currentService = services[0];
                    if (this.currentService.service_type === 'pppoe') {
                        if (this.currentService.router_host) {
                            await this.handleRouterChange();
                            this.currentService.profile_name = services[0].profile_name;
                        }
                    } else if (this.currentService.service_type === 'simple_queue') {
                        this.handlePlanChange();
                    }
                } else {
                    this.currentService.pppoe_username = this.currentClient.name.trim().replace(/\s+/g, '.').toLowerCase();
                }
            } catch (e) { console.error('Failed to load client service', e); }
        },

        async loadRoutersForSelect() {
            try {
                const allRouters = await (await fetch('/api/routers')).json();
                this.routersForSelect = allRouters;
            } catch (e) { console.error('Failed to load routers'); }
        },

        async handleRouterChange() {
            const host = this.currentService.router_host;
            this.profilesForSelect = [];
            if (!host) return;
            try {
                // Load PPPoE profiles from router (for reference)
                this.profilesForSelect = await (await fetch(`/api/routers/${host}/pppoe/profiles`)).json();
                // Reload plans filtered by this router
                await this.loadServicePlans(host);
            } catch (e) { console.error('Failed to load profiles'); }
        },

        async loadServicePlans(routerHost = null) {
            try {
                // If router specified, load only plans for that router
                const url = routerHost ? `/api/plans/router/${routerHost}` : '/api/plans';
                const response = await fetch(url);
                if (response.ok) {
                    this.servicePlans = await response.json();
                } else {
                    console.error('API endpoint failed with status:', response.status);
                    this.servicePlans = [];
                }
            } catch (e) {
                console.error('Failed to load service plans', e);
                this.servicePlans = [];
            }
        },

        detectClientIp() {
            if (this.assignedCpes && this.assignedCpes.length > 0) {
                const cpe = this.assignedCpes.find(c => c.ip_address && c.ip_address !== '0.0.0.0');
                return cpe ? cpe.ip_address : null;
            }
            return null;
        },

        handlePlanChange() {
            if (!Array.isArray(this.servicePlans)) return;
            if (!this.currentService.plan_id) {
                this.selectedPlan = null;
                return;
            }
            // Parse plan_id as integer for comparison (dropdown returns string)
            const planIdInt = parseInt(this.currentService.plan_id, 10);
            this.selectedPlan = this.servicePlans.find(p => p.id === planIdInt);
            console.log('handlePlanChange:', planIdInt, 'selectedPlan:', this.selectedPlan);
        },

        async saveService() {
            this.serviceError = '';
            const { router_host, service_type } = this.currentService;

            if (!router_host || !service_type) {
                this.serviceError = 'Router and Service Type are required.';
                return;
            }

            try {
                // DETECTAR SI ES EDICIÓN (UPDATE) O CREACIÓN (CREATE)
                const isUpdate = !!this.currentService.id;

                let routerResourceId = this.currentService.router_secret_id;
                let profileNameOrPlan = this.currentService.profile_name || (this.selectedPlan ? this.selectedPlan.name : '');
                let targetIp = this.currentService.ip_address;

                // SOLO PROVISIONAR EN ROUTER SI ES CREACIÓN (O si se implementa lógica de re-provisioning)
                // En modo edición, asumimos que el router ya tiene la config o se usa "Change Plan" para cambios de red.
                if (!isUpdate) {
                    // LÓGICA SIMPLE QUEUE (Usa BD Plans)
                    if (service_type === 'simple_queue') {
                        if (!this.selectedPlan) {
                            this.serviceError = 'Please select a Service Plan.';
                            return;
                        }
                        // Try detected IP first, then manual IP
                        targetIp = this.detectClientIp() || this.currentService.manual_ip;
                        if (!targetIp) {
                            this.serviceError = 'Please enter a manual IP address or assign a CPE with detected IP.';
                            return;
                        }

                        const queuePayload = {
                            name: this.currentClient.name,
                            target: targetIp,
                            max_limit: this.selectedPlan.max_limit,
                            parent: this.selectedPlan.parent_queue || 'none',
                            comment: `Client-ID:${this.currentClient.id} | Plan:${this.selectedPlan.name}`
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

                        // LÓGICA PPPoE (Usa Plan con profile_name)
                    } else if (service_type === 'pppoe') {
                        const { pppoe_username, password } = this.currentService;

                        // Validar que se haya seleccionado un plan
                        if (!this.selectedPlan) {
                            this.serviceError = 'Please select a PPPoE Plan.';
                            return;
                        }

                        if (!pppoe_username || !password) {
                            this.serviceError = 'PPPoE Username and Password are required.';
                            return;
                        }

                        // Obtener el profile_name del plan seleccionado
                        const profileFromPlan = this.selectedPlan.profile_name || 'default';

                        const pppoePayload = {
                            username: pppoe_username,
                            password: password,
                            service: 'pppoe',
                            profile: profileFromPlan,
                            comment: `Client-ID: ${this.currentClient.id} | Plan: ${this.selectedPlan.name}`
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
                } // FIN if (!isUpdate)

                const serviceData = {
                    router_host,
                    service_type,
                    pppoe_username: service_type === 'pppoe' ? this.currentService.pppoe_username : this.currentClient.name,
                    router_secret_id: routerResourceId,
                    profile_name: profileNameOrPlan,
                    plan_id: this.currentService.plan_id || (this.selectedPlan ? this.selectedPlan.id : null),
                    ip_address: targetIp,
                    suspension_method: this.currentService.suspension_method || 'address_list',
                    // New service-specific fields
                    address: this.currentService.address || null,
                    status: this.currentService.status || 'active',
                    billing_day: this.currentService.billing_day || null,
                    notes: this.currentService.notes || null
                };

                // URL y Método dinámicos
                const url = isUpdate
                    ? `/api/services/${this.currentService.id}`
                    : `/api/clients/${this.currentClient.id}/services`;

                const method = isUpdate ? 'PUT' : 'POST';

                console.log(`Saving Service: ${method} ${url}`, serviceData);

                const serviceRes = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(serviceData)
                });

                if (!serviceRes.ok) throw new Error(`API Error: ${(await serviceRes.json()).detail}`);

                showToast(isUpdate ? 'Service updated successfully!' : 'Service created successfully!', 'success');
                this.closeClientModal();

            } catch (error) {
                console.error(error);
                this.serviceError = error.message;
            }
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
/**
 * Client Details Component - Alpine.js
 * 
 * Main component for the Client Details page.
 * Handles: client info, service status, services list, and modals.
 * 
 * Dependencies: ClientStore.js (must be loaded first)
 * 
 * Usage: <main x-data="clientDetails">...</main>
 */
document.addEventListener('alpine:init', () => {
    Alpine.data('clientDetails', () => ({
        // --- Local State ---
        loading: true,
        error: null,
        currentServiceForPlanChange: null,
        currentServiceForEdit: null,
        showPlanChangeModal: false,
        showEditServiceModal: false,

        // --- Lifecycle ---
        async init() {
            try {
                // Tab switching logic
                this.setupTabSwitching();

                // Form event listeners
                this.setupFormListeners();

                // Load data
                await this.loadClientData();
                await Promise.all([
                    this.loadServiceStatus(),
                    this.loadClientServices()
                ]);
                this.loading = false;
            } catch (e) {
                this.error = e.message;
                this.loading = false;
                showToast(`Failed to initialize page: ${e.message}`, 'danger');
            }
        },

        setupTabSwitching() {
            const tabButtons = document.querySelectorAll('.tab-button');
            const tabPanels = document.querySelectorAll('.tab-panel');
            tabButtons.forEach(button => {
                button.addEventListener('click', () => {
                    tabButtons.forEach(btn => btn.classList.remove('active'));
                    button.classList.add('active');
                    const tabName = button.getAttribute('data-tab');
                    tabPanels.forEach(panel => {
                        panel.classList.toggle('active', panel.id === `tab-${tabName}`);
                    });
                });
            });
        },

        setupFormListeners() {
            // Plan change form
            const planChangeForm = document.getElementById('plan-change-form');
            if (planChangeForm) {
                planChangeForm.addEventListener('submit', (e) => this.handlePlanChangeSubmit(e));
            }

            // Edit service form
            const editServiceForm = document.getElementById('edit-service-form');
            if (editServiceForm) {
                editServiceForm.addEventListener('submit', (e) => this.handleEditServiceSubmit(e));
            }

            // Listen for payment registered event (cross-component communication)
            document.addEventListener('payment:registered', () => {
                this.loadServiceStatus();
            });
        },

        // --- Store Access ---
        get store() {
            return Alpine.store('client');
        },

        get clientId() {
            return this.store.clientId;
        },

        get allServices() {
            return this.store.allServices;
        },

        // --- API Helper (uses global ApiService) ---
        async fetchJSON(url, options = {}) {
            return ApiService.fetchJSON(url, options);
        },

        // --- Utility ---
        formatBytes(bytes) {
            if (!bytes || bytes === 0) return '0 Bytes';
            const bytesNum = parseInt(bytes, 10);
            if (isNaN(bytesNum)) return 'N/A';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
            const i = Math.floor(Math.log(bytesNum) / Math.log(k));
            return parseFloat((bytesNum / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        },

        // --- Data Loading ---
        async loadClientData() {
            const clientData = await this.fetchJSON(`/api/clients/${this.clientId}`);
            if (!clientData) throw new Error("Client not found.");

            this.store.setClient(clientData);
            document.title = `${clientData.name} - Client Details`;
            document.getElementById('main-clientname').textContent = clientData.name;
            this.renderClientInfo(clientData);
        },

        renderClientInfo(client) {
            const container = document.getElementById('client-info-container');
            const coordsLink = client.coordinates
                ? `<a href="http://maps.google.com/maps?q=${client.coordinates}" target="_blank" class="font-semibold text-primary hover:underline">${client.coordinates}</a>`
                : '<span class="font-semibold">N/A</span>';

            container.innerHTML = `
                <div class="flex justify-between"><span>Phone:</span> <span class="font-semibold">${client.phone_number || 'N/A'}</span></div>
                <div class="flex justify-between"><span>WhatsApp:</span> <span class="font-semibold">${client.whatsapp_number || 'N/A'}</span></div>
                <div class="flex justify-between"><span>Email:</span> <span class="font-semibold">${client.email || 'N/A'}</span></div>
                <div class="flex justify-between"><span>Telegram:</span> <span class="font-semibold">${client.telegram_contact || 'N/A'}</span></div>
                <div class="flex justify-between"><span>Coordinates:</span> ${coordsLink}</div>
            `;
        },

        // --- Service Status (Live from Router) ---
        async loadServiceStatus() {
            const container = document.getElementById('service-status-container');
            container.innerHTML = '<p class="text-text-secondary text-center">Loading service status...</p>';

            try {
                const services = await this.fetchJSON(`/api/clients/${this.clientId}/services`);
                if (!services || services.length === 0) {
                    container.innerHTML = '<p class="text-text-secondary text-center font-semibold">This client has no network services configured.</p>';
                    return;
                }

                let statusHtml = '<div class="space-y-4">';
                for (const service of services) {
                    const planLabel = service.plan_name || service.profile_name || 'N/A';
                    const routerHost = service.router_host;

                    if (service.service_type === 'pppoe') {
                        statusHtml += await this.renderPPPoEStatus(service, planLabel, routerHost);
                    } else if (service.service_type === 'simple_queue') {
                        statusHtml += await this.renderSimpleQueueStatus(service, planLabel, routerHost);
                    }
                }
                statusHtml += '</div>';
                container.innerHTML = statusHtml;
            } catch (e) {
                container.innerHTML = `<p class="text-danger text-center">Error loading live status: ${e.message}</p>`;
            }
        },

        async renderPPPoEStatus(service, planLabel, routerHost) {
            const username = service.pppoe_username;
            const typeClass = 'bg-blue-500/20 text-blue-400 border-blue-500/30';

            try {
                const secretData = await this.fetchJSON(`/api/routers/${routerHost}/pppoe/secrets?name=${encodeURIComponent(username)}`);

                if (!secretData || secretData.length === 0) {
                    return `
                        <div class="p-4 rounded-lg border ${typeClass}">
                            <div class="flex items-center gap-2 mb-3">
                                <span class="text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400">PPPoE</span>
                                <span class="font-mono text-sm">${username}</span>
                            </div>
                            <div class="flex justify-between"><span>Status:</span> <span class="font-semibold text-danger">User Not Found on Router</span></div>
                            <div class="flex justify-between"><span>Router:</span> <span class="font-mono">${routerHost}</span></div>
                        </div>`;
                }

                const secret = secretData[0];
                const isDisabled = secret.disabled === 'true';
                const statusClass = isDisabled ? 'text-danger' : 'text-success';
                const statusText = isDisabled ? 'Suspended' : 'Active';

                const activeConnections = await this.fetchJSON(`/api/routers/${routerHost}/pppoe/active?name=${encodeURIComponent(username)}`);
                const isOnline = activeConnections && activeConnections.length > 0;
                const onlineText = isOnline ? `Online (<span class="text-success">${activeConnections[0].address}</span>)` : 'Offline';

                return `
                    <div class="p-4 rounded-lg border ${typeClass}">
                        <div class="flex items-center gap-2 mb-3">
                            <span class="text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400">PPPoE</span>
                            <span class="font-mono text-sm font-semibold">${secret.name}</span>
                        </div>
                        <div class="grid grid-cols-2 gap-2 text-sm">
                            <div class="flex justify-between"><span>Account:</span> <span class="font-semibold ${statusClass}">${statusText}</span></div>
                            <div class="flex justify-between"><span>Network:</span> <span class="font-semibold">${onlineText}</span></div>
                            <div class="flex justify-between"><span>Router:</span> <span class="font-mono">${routerHost}</span></div>
                            <div class="flex justify-between"><span>Uptime:</span> <span>${isOnline ? activeConnections[0].uptime : 'N/A'}</span></div>
                            <div class="flex justify-between"><span>Plan:</span> <span class="font-semibold text-primary">${planLabel}</span></div>
                            <div class="flex justify-between"><span>Profile:</span> <span class="font-mono text-text-secondary">${secret.profile || 'N/A'}</span></div>
                            <div class="flex justify-between col-span-2"><span>Usage (Up/Down):</span> 
                                <span class="font-semibold">${this.formatBytes(secret['bytes-out'])} / ${this.formatBytes(secret['bytes-in'])}</span>
                            </div>
                        </div>
                    </div>`;
            } catch (e) {
                return `
                    <div class="p-4 rounded-lg border ${typeClass}">
                        <div class="flex items-center gap-2 mb-3">
                            <span class="text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400">PPPoE</span>
                            <span class="font-mono text-sm">${username}</span>
                        </div>
                        <p class="text-danger">Error: ${e.message}</p>
                    </div>`;
            }
        },

        async renderSimpleQueueStatus(service, planLabel, routerHost) {
            const ipAddress = service.ip_address;
            const typeClass = 'bg-purple-500/20 text-purple-400 border-purple-500/30';

            try {
                const queueData = await this.fetchJSON(`/api/routers/${routerHost}/queue/stats?target=${encodeURIComponent(ipAddress)}`);

                if (!queueData || queueData.status === 'not_found') {
                    return `
                        <div class="p-4 rounded-lg border ${typeClass}">
                            <div class="flex items-center gap-2 mb-3">
                                <span class="text-xs font-semibold px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-400">Simple Queue</span>
                                <span class="font-mono text-sm">${ipAddress}</span>
                            </div>
                            <div class="flex justify-between"><span>Status:</span> <span class="font-semibold text-warning">Queue Not Found on Router</span></div>
                            <div class="flex justify-between"><span>Router:</span> <span class="font-mono">${routerHost}</span></div>
                        </div>`;
                }

                const bytesStr = queueData.bytes || '0/0';
                const [bytesUp, bytesDown] = bytesStr.split('/').map(b => parseInt(b, 10) || 0);

                return `
                    <div class="p-4 rounded-lg border ${typeClass}">
                        <div class="flex items-center gap-2 mb-3">
                            <span class="text-xs font-semibold px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-400">Simple Queue</span>
                            <span class="font-mono text-sm font-semibold">${queueData.name || ipAddress}</span>
                        </div>
                        <div class="grid grid-cols-2 gap-2 text-sm">
                            <div class="flex justify-between"><span>Target:</span> <span class="font-mono">${queueData.target || ipAddress}</span></div>
                            <div class="flex justify-between"><span>Max Limit:</span> <span class="font-semibold">${queueData['max-limit'] || 'N/A'}</span></div>
                            <div class="flex justify-between"><span>Router:</span> <span class="font-mono">${routerHost}</span></div>
                            <div class="flex justify-between"><span>Plan:</span> <span class="font-semibold text-primary">${planLabel}</span></div>
                            <div class="flex justify-between col-span-2"><span>Usage (Up/Down):</span> 
                                <span class="font-semibold">${this.formatBytes(bytesUp)} / ${this.formatBytes(bytesDown)}</span>
                            </div>
                        </div>
                    </div>`;
            } catch (e) {
                return `
                    <div class="p-4 rounded-lg border ${typeClass}">
                        <div class="flex items-center gap-2 mb-3">
                            <span class="text-xs font-semibold px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-400">Simple Queue</span>
                            <span class="font-mono text-sm">${ipAddress}</span>
                        </div>
                        <p class="text-danger">Error: ${e.message}</p>
                    </div>`;
            }
        },

        // --- Services List ---
        // --- Services List ---
        async loadClientServices() {
            try {
                this.loading = true;
                const services = await this.fetchJSON(`/api/clients/${this.clientId}/services`);
                this.store.setServices(services || []);

                // Notify other components that services are loaded
                document.dispatchEvent(new CustomEvent('services:loaded'));
            } catch (e) {
                console.error("Error loading services:", e);
                // In a real app, you might want to show an error message in the UI
                this.store.setServices([]);
            } finally {
                this.loading = false;
            }
        },

        // --- Plan Change Modal ---
        async openPlanChangeModal(serviceId, serviceName) {
            this.currentServiceForPlanChange = this.allServices.find(s => s.id === serviceId);

            if (!this.currentServiceForPlanChange) {
                showToast('Service not found', 'danger');
                return;
            }

            document.getElementById('plan-change-service-id').value = serviceId;
            document.getElementById('plan-change-service-name').textContent = serviceName;
            document.getElementById('plan-change-error').classList.add('hidden');
            document.getElementById('new-plan-select').value = '';

            await this.loadPlansForSelect(this.currentServiceForPlanChange.service_type, this.currentServiceForPlanChange.router_host);
            this.showPlanChangeModal = true;
            document.getElementById('plan-change-modal').classList.remove('hidden');
        },

        closePlanChangeModal() {
            this.showPlanChangeModal = false;
            document.getElementById('plan-change-modal').classList.add('hidden');
        },

        async loadPlansForSelect(serviceType, routerHost) {
            const select = document.getElementById('new-plan-select');
            select.innerHTML = '<option value="">Loading...</option>';

            try {
                const plans = await this.fetchJSON(`/api/plans/for-service/${routerHost}`);
                const filteredPlans = plans.filter(p => p.plan_type === serviceType);
                this.store.setPlans(filteredPlans);

                select.innerHTML = '<option value="">Select a plan...</option>';
                for (const plan of filteredPlans) {
                    const speedDisplay = plan.max_limit || 'N/A';
                    const priceDisplay = plan.price ? `$${plan.price}` : '$0.00';
                    select.innerHTML += `<option value="${plan.id}">${plan.name} - ${priceDisplay} (${speedDisplay})</option>`;
                }

                if (filteredPlans.length === 0) {
                    select.innerHTML = '<option value="">No plans available for this service type</option>';
                }
            } catch (e) {
                console.error('Error loading plans:', e);
                select.innerHTML = '<option value="">Error loading options</option>';
            }
        },

        async handlePlanChangeSubmit(event) {
            event.preventDefault();
            const errorEl = document.getElementById('plan-change-error');
            errorEl.classList.add('hidden');

            const serviceId = document.getElementById('plan-change-service-id').value;
            const newPlanId = document.getElementById('new-plan-select').value;

            if (!newPlanId) {
                errorEl.textContent = 'Please select a plan.';
                errorEl.classList.remove('hidden');
                return;
            }

            try {
                const url = `/api/services/${serviceId}/plan?new_plan_id=${newPlanId}`;
                await this.fetchJSON(url, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' }
                });

                showToast('Plan changed successfully!', 'success');
                this.closePlanChangeModal();
                await this.loadClientServices();
                await this.loadServiceStatus();
            } catch (error) {
                errorEl.textContent = `Error: ${error.message}`;
                errorEl.classList.remove('hidden');
            }
        },

        // --- Edit Service Modal ---
        openEditServiceModal(serviceId) {
            this.currentServiceForEdit = this.allServices.find(s => s.id === serviceId);
            if (!this.currentServiceForEdit) {
                showToast('Service not found', 'danger');
                return;
            }

            document.getElementById('edit-service-id').value = serviceId;
            const identifier = this.currentServiceForEdit.pppoe_username || this.currentServiceForEdit.ip_address || 'N/A';
            document.getElementById('edit-service-identifier').value = identifier;
            document.getElementById('edit-service-notes').value = this.currentServiceForEdit.notes || '';
            document.getElementById('edit-service-error').classList.add('hidden');

            // Populate Billing Day Select
            const billingSelect = document.getElementById('edit-service-billing-day');
            billingSelect.innerHTML = '<option value="">Select Day...</option>';
            for (let i = 1; i <= 28; i++) {
                const option = document.createElement('option');
                option.value = i;
                option.textContent = i;
                if (this.currentServiceForEdit.billing_day === i) {
                    option.selected = true;
                }
                billingSelect.appendChild(option);
            }

            this.showEditServiceModal = true;
            document.getElementById('edit-service-modal').classList.remove('hidden');
        },

        closeEditServiceModal() {
            this.showEditServiceModal = false;
            document.getElementById('edit-service-modal').classList.add('hidden');
        },

        async handleEditServiceSubmit(event) {
            event.preventDefault();
            const errorEl = document.getElementById('edit-service-error');
            errorEl.classList.add('hidden');

            const serviceId = document.getElementById('edit-service-id').value;
            const billingDay = document.getElementById('edit-service-billing-day').value;
            const notes = document.getElementById('edit-service-notes').value;

            if (!billingDay) {
                errorEl.textContent = 'Please select a billing day.';
                errorEl.classList.remove('hidden');
                return;
            }

            try {
                await this.fetchJSON(`/api/services/${serviceId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        billing_day: parseInt(billingDay, 10),
                        notes: notes
                    })
                });

                showToast('Service updated successfully!', 'success');
                this.closeEditServiceModal();
                await this.loadClientServices();
            } catch (error) {
                errorEl.textContent = `Error updating service: ${error.message}`;
                errorEl.classList.remove('hidden');
            }
        },

        // --- Delete Service ---
        // --- Delete Service ---
        async deleteService(serviceId, serviceName) {
            window.ModalUtils.showConfirmModal({
                title: 'Delete Service',
                message: `Are you sure you want to delete the service "<strong>${serviceName}</strong>"?<br><br>This will also remove the configuration from the router if applicable.`,
                confirmText: 'Delete Service',
                confirmIcon: 'delete',
                type: 'danger',
            }).then(async (confirmed) => {
                if (confirmed) {
                    try {
                        await this.fetchJSON(`/api/services/${serviceId}`, { method: 'DELETE' });
                        showToast('Service deleted successfully!', 'success');
                        await this.loadClientServices();
                        await this.loadServiceStatus();
                    } catch (error) {
                        showToast(`Error deleting service: ${error.message}`, 'danger');
                    }
                }
            });
        },

        // --- Sync Service to Router ---
        async syncService(serviceId, serviceName) {
            window.ModalUtils.showConfirmModal({
                title: 'Sync to Router',
                message: `This will re-apply the configuration for service "<strong>${serviceName}</strong>" to the router.<br><br>Use this if the queue or PPPoE secret was not created correctly.`,
                confirmText: 'Sync Now',
                confirmIcon: 'sync',
                type: 'warning',
            }).then(async (confirmed) => {
                if (confirmed) {
                    try {
                        showToast('Syncing service to router...', 'info');
                        const result = await this.fetchJSON(`/api/services/${serviceId}/sync`, { method: 'POST' });

                        if (result.status === 'success') {
                            showToast('Service synced to router successfully!', 'success');
                            console.log('Sync result:', result);
                        } else {
                            showToast(`Sync completed with warnings: ${result.message}`, 'warning');
                        }
                        await this.loadServiceStatus();
                    } catch (error) {
                        showToast(`Error syncing service: ${error.message}`, 'danger');
                    }
                }
            });
        }
    }));

    console.log('[Component] ClientDetails initialized');
});

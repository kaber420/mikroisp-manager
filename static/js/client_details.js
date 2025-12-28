document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = window.location.origin;
    const clientId = window.location.pathname.split('/').pop();
    let clientData = null;

    // Variables de estado para el calendario
    let currentYear = new Date().getFullYear();
    let paidMonthsSet = new Set(); // Guardará "2025-01", "2025-02", etc.

    // --- Lógica de Pestañas ---
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

    // --- Funciones de Utilidad ---
    async function fetchJSON(url, options = {}) {
        const getUrl = new URL(url, API_BASE_URL);
        if (!options.method || options.method === 'GET') {
            getUrl.searchParams.append('_', new Date().getTime());
        }
        const response = await fetch(getUrl.toString(), options);
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(errorData.detail || 'API Request Failed');
        }
        return response.status === 204 ? null : response.json();
    }

    function formatBytes(bytes) {
        if (!bytes || bytes === 0) return '0 Bytes';
        const bytesNum = parseInt(bytes, 10);
        if (isNaN(bytesNum)) return 'N/A';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytesNum) / Math.log(k));
        return parseFloat((bytesNum / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // --- LÓGICA DE UI: RENDERIZAR MESES ---
    function renderMonthSelector(billingDay) {
        const grid = document.getElementById('months-grid');
        const yearDisplay = document.getElementById('current-year-display');
        const hiddenInput = document.getElementById('payment-month');

        if (!grid || !yearDisplay) return;

        yearDisplay.textContent = currentYear;
        grid.innerHTML = '';

        const months = [
            "Ene", "Feb", "Mar", "Abr", "May", "Jun",
            "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"
        ];

        months.forEach((name, index) => {
            const monthNum = String(index + 1).padStart(2, '0');
            const value = `${currentYear}-${monthNum}`;
            const isPaid = paidMonthsSet.has(value);

            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = `
                py-2 px-1 rounded-md text-sm font-semibold border transition-all relative overflow-hidden
                ${isPaid
                    ? 'bg-success/20 border-success text-success cursor-not-allowed opacity-60'
                    : 'bg-surface-2 border-border-color hover:border-primary hover:text-primary'
                }
            `;

            // Contenido del botón
            if (isPaid) {
                btn.innerHTML = `${name} <span class="block text-[10px] uppercase">Pagado</span>`;
                btn.disabled = true;
            } else {
                btn.textContent = name;
                btn.onclick = () => {
                    // Deseleccionar anteriores
                    grid.querySelectorAll('.selected-month').forEach(b => {
                        b.classList.remove('ring-2', 'ring-primary', 'bg-primary/20', 'selected-month');
                    });

                    // Seleccionar actual
                    btn.classList.add('ring-2', 'ring-primary', 'bg-primary/20', 'selected-month');
                    hiddenInput.value = value;

                    // Calcular y mostrar ciclo
                    calculateCycleDates(value, billingDay);
                };
            }
            grid.appendChild(btn);
        });
    }

    // --- LÓGICA DE NEGOCIO: CALCULAR FECHAS ---
    function calculateCycleDates(yearMonth, billingDay) {
        if (!billingDay) billingDay = 1; // Default día 1

        // Parsear "2025-11"
        const [year, month] = yearMonth.split('-').map(Number);

        // Fecha Inicio: El día de corte del mes seleccionado
        // Nota: En Javascript los meses son 0-index (Enero=0)
        const startDate = new Date(year, month - 1, billingDay);

        // Fecha Fin: El día de corte del mes siguiente
        const endDate = new Date(year, month, billingDay);

        // Formatear bonito
        const options = { day: 'numeric', month: 'long', year: 'numeric' };
        const startStr = startDate.toLocaleDateString('es-ES', options);
        const endStr = endDate.toLocaleDateString('es-ES', options);

        const cycleDatesEl = document.getElementById('cycle-dates');
        const cycleInfoEl = document.getElementById('cycle-info');

        if (cycleDatesEl) cycleDatesEl.textContent = `${startStr} al ${endStr}`;
        if (cycleInfoEl) cycleInfoEl.classList.remove('hidden');
    }

    // --- Funciones de Carga y Renderizado ---
    function renderClientInfo(client) {
        const container = document.getElementById('client-info-container');
        const coordsLink = client.coordinates ? `<a href="http://maps.google.com/maps?q=${client.coordinates}" target="_blank" class="font-semibold text-primary hover:underline">${client.coordinates}</a>` : '<span class="font-semibold">N/A</span>';
        container.innerHTML = `
            <div class="flex justify-between"><span>Phone:</span> <span class="font-semibold">${client.phone_number || 'N/A'}</span></div>
            <div class="flex justify-between"><span>WhatsApp:</span> <span class="font-semibold">${client.whatsapp_number || 'N/A'}</span></div>
            <div class="flex justify-between"><span>Email:</span> <span class="font-semibold">${client.email || 'N/A'}</span></div>
            <div class="flex justify-between"><span>Telegram:</span> <span class="font-semibold">${client.telegram_contact || 'N/A'}</span></div>
            <div class="flex justify-between"><span>Coordinates:</span> ${coordsLink}</div>
        `;
    }

    async function loadServiceStatus() {
        const container = document.getElementById('service-status-container');
        container.innerHTML = '<p class="text-text-secondary text-center">Loading service status...</p>';
        try {
            const services = await fetchJSON(`/api/clients/${clientId}/services`);
            if (!services || services.length === 0) {
                container.innerHTML = '<p class="text-text-secondary text-center font-semibold">This client has no network services configured.</p>';
                return;
            }

            let statusHtml = '<div class="space-y-4">';

            for (const service of services) {
                const planLabel = service.plan_name || service.profile_name || 'N/A';
                const routerHost = service.router_host;

                if (service.service_type === 'pppoe') {
                    // PPPoE Service
                    statusHtml += await renderPPPoEStatus(service, planLabel, routerHost);
                } else if (service.service_type === 'simple_queue') {
                    // Simple Queue Service
                    statusHtml += await renderSimpleQueueStatus(service, planLabel, routerHost);
                }
            }

            statusHtml += '</div>';
            container.innerHTML = statusHtml;

        } catch (e) {
            container.innerHTML = `<p class="text-danger text-center">Error loading live status: ${e.message}</p>`;
        }
    }

    async function renderPPPoEStatus(service, planLabel, routerHost) {
        const username = service.pppoe_username;
        const typeClass = 'bg-blue-500/20 text-blue-400 border-blue-500/30';

        try {
            const secretData = await fetchJSON(`/api/routers/${routerHost}/pppoe/secrets?name=${encodeURIComponent(username)}`);

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

            const activeConnections = await fetchJSON(`/api/routers/${routerHost}/pppoe/active?name=${encodeURIComponent(username)}`);
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
                            <span class="font-semibold">${formatBytes(secret['bytes-out'])} / ${formatBytes(secret['bytes-in'])}</span>
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
    }

    async function renderSimpleQueueStatus(service, planLabel, routerHost) {
        const ipAddress = service.ip_address;
        const typeClass = 'bg-purple-500/20 text-purple-400 border-purple-500/30';

        try {
            const queueData = await fetchJSON(`/api/routers/${routerHost}/queue/stats?target=${encodeURIComponent(ipAddress)}`);

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

            // Parse bytes (format: "upload/download")
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
                            <span class="font-semibold">${formatBytes(bytesUp)} / ${formatBytes(bytesDown)}</span>
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
    }

    // --- Services List Management ---
    let allServices = [];
    let allPlans = [];

    async function loadClientServices() {
        const container = document.getElementById('services-list-container');
        container.innerHTML = '<p class="text-text-secondary text-center">Loading services...</p>';

        try {
            allServices = await fetchJSON(`/api/clients/${clientId}/services`);
            renderServicesList();
        } catch (e) {
            container.innerHTML = `<p class="text-danger text-center">Error loading services: ${e.message}</p>`;
        }
    }

    function renderServicesList() {
        const container = document.getElementById('services-list-container');

        if (!allServices || allServices.length === 0) {
            container.innerHTML = '<p class="text-text-secondary text-center">No network services configured for this client.</p>';
            return;
        }

        // Helper function for status badge
        const getStatusBadgeClass = (status) => {
            const classes = {
                'active': 'bg-success/20 text-success',
                'pendiente': 'bg-warning/20 text-warning',
                'suspended': 'bg-danger/20 text-danger',
                'cancelled': 'bg-surface-2 text-text-secondary'
            };
            return classes[status] || 'bg-surface-2 text-text-secondary';
        };

        let html = '<div class="space-y-3">';
        for (const service of allServices) {
            const serviceIdentifier = service.pppoe_username || service.ip_address || 'N/A';
            const serviceTypeLabel = service.service_type === 'pppoe' ? 'PPPoE' : 'Simple Queue';
            const typeClass = service.service_type === 'pppoe' ? 'bg-blue-500/20 text-blue-400' : 'bg-purple-500/20 text-purple-400';
            const planDisplay = service.plan_name || service.profile_name || 'No Plan';
            const statusLabel = service.status ? (service.status.charAt(0).toUpperCase() + service.status.slice(1)) : 'Active';
            const statusClass = getStatusBadgeClass(service.status || 'active');

            html += `
            <div class="flex flex-col p-4 bg-surface-2 rounded-lg gap-3">
                <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div class="flex-1">
                        <div class="flex items-center gap-2 mb-1">
                            <span class="text-xs font-semibold px-2 py-0.5 rounded-full ${typeClass}">${serviceTypeLabel}</span>
                            <span class="text-xs font-semibold px-2 py-0.5 rounded-full ${statusClass}">${statusLabel}</span>
                            <span class="font-mono text-sm font-semibold">${serviceIdentifier}</span>
                        </div>
                        <div class="text-xs text-text-secondary space-x-4">
                            <span>Router: <span class="font-mono">${service.router_host || 'N/A'}</span></span>
                            <span>Plan: <span class="font-semibold text-primary">${planDisplay}</span></span>
                        </div>
                    </div>
                    <div class="flex gap-2">
                        <button onclick="openPlanChangeModal(${service.id}, '${serviceIdentifier}')" 
                                class="px-3 py-1.5 text-xs font-semibold rounded-md bg-primary/20 text-primary hover:bg-primary/30 flex items-center gap-1">
                            <span class="material-symbols-outlined text-sm">swap_horiz</span>
                            Change Plan
                        </button>
                        <button onclick="deleteService(${service.id}, '${serviceIdentifier}')" 
                                class="px-3 py-1.5 text-xs font-semibold rounded-md bg-danger/20 text-danger hover:bg-danger/30 flex items-center gap-1">
                            <span class="material-symbols-outlined text-sm">delete</span>
                            Delete
                        </button>
                    </div>
                </div>
                <div class="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs text-text-secondary border-t border-border-color pt-3">
                    <div><span class="font-medium">Address:</span> ${service.address || 'N/A'}</div>
                    <div><span class="font-medium">Billing Day:</span> ${service.billing_day || 'N/A'}</div>
                    <div><span class="font-medium">Notes:</span> ${service.notes || 'N/A'}</div>
                </div>
            </div>`;
        }
        html += '</div>';
        container.innerHTML = html;
    }

    // --- Plan Change Modal Functions ---
    let currentServiceForPlanChange = null;

    async function loadPlansForSelect(serviceType, routerHost) {
        const select = document.getElementById('new-plan-select');
        select.innerHTML = '<option value="">Loading...</option>';

        try {
            // Load plans from database for ALL service types (PPPoE and Simple Queue)
            // Filter by plan_type matching the service type
            const plans = await fetchJSON(`/api/plans/router/${routerHost}`);
            const filteredPlans = plans.filter(p => p.plan_type === serviceType);
            allPlans = filteredPlans; // Store for later use

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
    }

    // Global functions for modal (must be accessible from onclick)
    window.openPlanChangeModal = async function (serviceId, serviceName) {
        // Find the service details from allServices array
        currentServiceForPlanChange = allServices.find(s => s.id === serviceId);

        if (!currentServiceForPlanChange) {
            showToast('Service not found', 'danger');
            return;
        }

        document.getElementById('plan-change-service-id').value = serviceId;
        document.getElementById('plan-change-service-name').textContent = serviceName;
        document.getElementById('plan-change-error').classList.add('hidden');
        document.getElementById('new-plan-select').value = '';

        await loadPlansForSelect(currentServiceForPlanChange.service_type, currentServiceForPlanChange.router_host);
        document.getElementById('plan-change-modal').classList.remove('hidden');
    };

    window.closePlanChangeModal = function () {
        document.getElementById('plan-change-modal').classList.add('hidden');
    };

    async function handlePlanChangeSubmit(e) {
        e.preventDefault();
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
            // Always use the /plan endpoint which handles both PPPoE and Simple Queue
            const url = `/api/services/${serviceId}/plan?new_plan_id=${newPlanId}`;

            await fetchJSON(url, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' }
            });

            showToast('Plan changed successfully!', 'success');
            closePlanChangeModal();
            loadClientServices();
            loadServiceStatus();
        } catch (error) {
            errorEl.textContent = `Error: ${error.message}`;
            errorEl.classList.remove('hidden');
        }
    }

    // --- Delete Service ---
    window.deleteService = async function (serviceId, serviceName) {
        if (!confirm(`Are you sure you want to delete the service "${serviceName}"?\n\nThis will also remove the PPPoE secret from the router if applicable.`)) {
            return;
        }

        try {
            await fetchJSON(`/api/services/${serviceId}`, { method: 'DELETE' });
            showToast('Service deleted successfully!', 'success');
            loadClientServices();
            loadServiceStatus();
        } catch (error) {
            showToast(`Error deleting service: ${error.message}`, 'danger');
        }
    };

    async function loadPaymentHistory() {
        const container = document.getElementById('payment-history-list');
        container.innerHTML = '<p class="text-text-secondary">Loading history...</p>';
        try {
            const payments = await fetchJSON(`/api/clients/${clientId}/payments`);

            // LIMPIAR Y LLENAR EL SET
            paidMonthsSet.clear();
            if (payments) {
                payments.forEach(p => {
                    if (p.mes_correspondiente) {
                        paidMonthsSet.add(p.mes_correspondiente);
                    }
                });
            }

            // Renderizar selector de meses - get billing_day from first service if available
            const billingDay = (allServices && allServices.length > 0)
                ? (allServices[0].billing_day || 1)
                : 1;
            renderMonthSelector(billingDay);

            if (!payments || payments.length === 0) {
                container.innerHTML = '<p class="text-text-secondary">No payments registered for this client.</p>';
                return;
            }

            container.innerHTML = '';
            payments.forEach(payment => {
                const paymentEl = document.createElement('div');
                paymentEl.className = 'flex justify-between items-center bg-surface-2 p-3 rounded-md';
                const paymentDate = new Date(payment.fecha_pago).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
                paymentEl.innerHTML = `
                    <div class="flex-grow">
                        <p class="font-semibold text-text-primary">$${payment.monto.toFixed(2)} - <span class="font-medium text-text-secondary">For: ${payment.mes_correspondiente}</span></p>
                        <p class="text-xs text-text-secondary">${paymentDate} (${payment.metodo_pago || 'N/A'})</p>
                        ${payment.notas ? `<p class="text-xs text-warning mt-1">${payment.notas}</p>` : ''}
                    </div>
                    <div>
                        <button onclick="window.open('/payment/${payment.id}/receipt', '_blank')" class="p-2 rounded-md hover:bg-surface-3" title="Print Receipt">
                            <span class="material-symbols-outlined">print</span>
                        </button>
                    </div>
                `;
                container.appendChild(paymentEl);
            });

        } catch (e) {
            container.innerHTML = `<p class="text-danger">Error loading history: ${e.message}</p>`;
        }
    }

    async function handleRegisterPayment(e) {
        e.preventDefault();
        const errorEl = document.getElementById('payment-form-error');
        errorEl.classList.add('hidden');

        const data = {
            monto: parseFloat(document.getElementById('payment-amount').value),
            mes_correspondiente: document.getElementById('payment-month').value,
            metodo_pago: document.getElementById('payment-method').value,
            notas: document.getElementById('payment-notes').value,
        };

        if (!data.monto || data.monto <= 0) {
            errorEl.textContent = 'Amount must be a valid number.';
            errorEl.classList.remove('hidden');
            return;
        }
        if (!validators.isRequired(data.mes_correspondiente) || !/^\d{4}-\d{2}$/.test(data.mes_correspondiente)) {
            errorEl.textContent = 'Please select a month to pay.';
            errorEl.classList.remove('hidden');
            return;
        }

        try {
            await fetchJSON(`/api/clients/${clientId}/payments`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            showToast('Payment registered and service reactivated successfully!', 'success');
            document.getElementById('register-payment-form').reset();
            // Resetear selección visual
            document.getElementById('payment-month').value = '';
            document.getElementById('cycle-info').classList.add('hidden');

            // Reload both dynamic parts of the page
            loadServiceStatus();
            loadPaymentHistory();

        } catch (error) {
            errorEl.textContent = `Error: ${error.message}`;
            errorEl.classList.remove('hidden');
        }
    }

    // Listeners para cambio de año
    const prevYearBtn = document.getElementById('prev-year-btn');
    const nextYearBtn = document.getElementById('next-year-btn');

    // Helper to get billing day from services
    const getServiceBillingDay = () => (allServices && allServices.length > 0)
        ? (allServices[0].billing_day || 1)
        : 1;

    if (prevYearBtn) {
        prevYearBtn.addEventListener('click', () => {
            currentYear--;
            renderMonthSelector(getServiceBillingDay());
        });
    }

    if (nextYearBtn) {
        nextYearBtn.addEventListener('click', () => {
            currentYear++;
            renderMonthSelector(getServiceBillingDay());
        });
    }

    // --- Auto-fill Payment Amount based on Client's Plan ---
    async function autoFillPaymentAmount() {
        try {
            // Get client's services to find their plan
            const services = await fetchJSON(`/api/clients/${clientId}/services`);
            if (!services || services.length === 0) return;

            // Get the first service's plan (primary service)
            const primaryService = services[0];
            if (!primaryService.plan_id || !primaryService.router_host) return;

            // Fetch plans for the router
            const plans = await fetchJSON(`/api/plans/router/${primaryService.router_host}`);
            if (!plans || plans.length === 0) return;

            // Find the plan that matches the service
            const clientPlan = plans.find(p => p.id === primaryService.plan_id);
            if (!clientPlan || !clientPlan.price) return;

            // Auto-fill the payment amount input
            const amountInput = document.getElementById('payment-amount');
            if (amountInput) {
                amountInput.value = clientPlan.price.toFixed(2);
                amountInput.placeholder = `Plan: ${clientPlan.name} - $${clientPlan.price.toFixed(2)}`;
            }

            console.log(`✅ Auto-filled payment amount: $${clientPlan.price} from plan "${clientPlan.name}"`);
        } catch (e) {
            console.warn('Could not auto-fill payment amount:', e.message);
        }
    }

    // --- Carga Inicial de la Página ---
    async function initializePage() {
        try {
            // --- CÓDIGO OPTIMIZADO ---
            // Solicitamos directamente el cliente por ID a la API
            clientData = await fetchJSON(`/api/clients/${clientId}`);

            if (!clientData) throw new Error("Client not found.");

            document.title = `${clientData.name} - Client Details`;
            document.getElementById('main-clientname').textContent = clientData.name;

            // Renderizar info básica
            renderClientInfo(clientData);

            // Las otras cargas siguen igual, ya que dependen del ID
            loadServiceStatus();
            loadClientServices();
            loadPaymentHistory();

            // Auto-fill payment amount based on client's plan
            await autoFillPaymentAmount();

            const paymentForm = document.getElementById('register-payment-form');
            if (paymentForm) {
                paymentForm.addEventListener('submit', handleRegisterPayment);
            }

            const planChangeForm = document.getElementById('plan-change-form');
            if (planChangeForm) {
                planChangeForm.addEventListener('submit', handlePlanChangeSubmit);
            }

        } catch (error) {
            console.error(error);
            const nameEl = document.getElementById('main-clientname');
            if (nameEl) nameEl.textContent = 'Error Loading Client';
            showToast(`Failed to initialize page: ${error.message}`, 'danger');
        }
    }

    initializePage();
});
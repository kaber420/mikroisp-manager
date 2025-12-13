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
            <div class="flex justify-between"><span>Address:</span> <span class="font-semibold text-right">${client.address || 'N/A'}</span></div>
            <div class="flex justify-between"><span>Billing Day:</span> <span class="font-semibold">${client.billing_day || '1'}</span></div>
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

            const pppoeService = services.find(s => s.service_type === 'pppoe');
            if (!pppoeService) {
                container.innerHTML = '<p class="text-text-secondary text-center font-semibold">Service is not PPPoE.</p>';
                return;
            }

            const username = pppoeService.pppoe_username;
            const routerHost = pppoeService.router_host;

            const secretData = await fetchJSON(`/api/routers/${routerHost}/pppoe/secrets?name=${encodeURIComponent(username)}`);

            let statusHtml = '';
            if (!secretData || secretData.length === 0) {
                statusHtml = `
                    <div class="flex justify-between"><span class="text-text-secondary">Status:</span> <span class="font-semibold text-danger">User Not Found on Router</span></div>
                    <div class="flex justify-between"><span class="text-text-secondary">PPPoE User:</span> <span class="font-mono">${username}</span></div>
                    <div class="flex justify-between"><span class="text-text-secondary">Router:</span> <span class="font-mono">${routerHost}</span></div>
                `;
            } else {
                const secret = secretData[0];
                const isDisabled = secret.disabled === 'true';
                const statusClass = isDisabled ? 'text-danger' : 'text-success';
                const statusText = isDisabled ? 'Suspended' : 'Active';

                const activeConnections = await fetchJSON(`/api/routers/${routerHost}/pppoe/active?name=${encodeURIComponent(username)}`);
                const isOnline = activeConnections && activeConnections.length > 0;
                const onlineText = isOnline ? `Online (<span class="text-success">${activeConnections[0].address}</span>)` : 'Offline';

                statusHtml = `
                    <div class="flex justify-between"><span>Account Status:</span> <span class="font-semibold ${statusClass}">${statusText}</span></div>
                    <div class="flex justify-between"><span>Network Status:</span> <span class="font-semibold">${onlineText}</span></div>
                    <div class="flex justify-between"><span>PPPoE User:</span> <span class="font-mono">${secret.name}</span></div>
                    <div class="flex justify-between"><span>Router:</span> <span class="font-mono">${routerHost}</span></div>
                    <div class="flex justify-between"><span>Uptime:</span> <span>${isOnline ? activeConnections[0].uptime : 'N/A'}</span></div>
                    <div class="flex justify-between"><span>Plan:</span> <span>${secret.profile || 'N/A'}</span></div>
                    <div class="flex justify-between"><span>Usage (Up/Down):</span> 
                        <span class="font-semibold">${formatBytes(secret['bytes-out'])} / ${formatBytes(secret['bytes-in'])}</span>
                    </div>
                `;
            }
            container.innerHTML = statusHtml;

        } catch (e) {
            container.innerHTML = `<p class="text-danger text-center">Error loading live status: ${e.message}</p>`;
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

        let html = '<div class="space-y-3">';
        for (const service of allServices) {
            const serviceIdentifier = service.pppoe_username || service.ip_address || 'N/A';
            const serviceTypeLabel = service.service_type === 'pppoe' ? 'PPPoE' : 'Simple Queue';
            const typeClass = service.service_type === 'pppoe' ? 'bg-blue-500/20 text-blue-400' : 'bg-purple-500/20 text-purple-400';

            html += `
            <div class="flex flex-col sm:flex-row sm:items-center justify-between p-4 bg-surface-2 rounded-lg gap-4">
                <div class="flex-1">
                    <div class="flex items-center gap-2 mb-1">
                        <span class="text-xs font-semibold px-2 py-0.5 rounded-full ${typeClass}">${serviceTypeLabel}</span>
                        <span class="font-mono text-sm font-semibold">${serviceIdentifier}</span>
                    </div>
                    <div class="text-xs text-text-secondary space-x-4">
                        <span>Router: <span class="font-mono">${service.router_host || 'N/A'}</span></span>
                        ${service.profile_name ? `<span>Profile: <span class="font-mono">${service.profile_name}</span></span>` : ''}
                        <span>Method: <span class="font-mono">${service.suspension_method || 'N/A'}</span></span>
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
            if (serviceType === 'pppoe' && routerHost) {
                // For PPPoE: Load profiles from the router
                const profiles = await fetchJSON(`/api/routers/${routerHost}/pppoe/profiles`);
                select.innerHTML = '<option value="">Select a profile...</option>';
                for (const profile of profiles) {
                    const rateLimit = profile['rate-limit'] || 'Unlimited';
                    select.innerHTML += `<option value="${profile.name}">${profile.name} (${rateLimit})</option>`;
                }
            } else {
                // For Simple Queue: Load plans from database (filtered by router)
                const plans = await fetchJSON(`/api/plans/router/${routerHost}`);
                select.innerHTML = '<option value="">Select a plan...</option>';
                for (const plan of plans) {
                    select.innerHTML += `<option value="${plan.id}">${plan.name} (${plan.max_limit || 'N/A'})</option>`;
                }
            }
        } catch (e) {
            console.error('Error loading plans/profiles:', e);
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
        const newValue = document.getElementById('new-plan-select').value;

        if (!newValue) {
            errorEl.textContent = 'Please select a plan/profile.';
            errorEl.classList.remove('hidden');
            return;
        }

        try {
            let url;
            if (currentServiceForPlanChange && currentServiceForPlanChange.service_type === 'pppoe') {
                // For PPPoE: Use pppoe-profile endpoint with profile name
                url = `/api/services/${serviceId}/pppoe-profile?new_profile=${encodeURIComponent(newValue)}`;
            } else {
                // For Simple Queue: Use plan endpoint with plan ID
                url = `/api/services/${serviceId}/plan?new_plan_id=${newValue}`;
            }

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

            // Renderizar selector de meses si tenemos datos del cliente
            if (clientData) {
                renderMonthSelector(clientData.billing_day);
            }

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

    if (prevYearBtn) {
        prevYearBtn.addEventListener('click', () => {
            currentYear--;
            renderMonthSelector(clientData?.billing_day);
        });
    }

    if (nextYearBtn) {
        nextYearBtn.addEventListener('click', () => {
            currentYear++;
            renderMonthSelector(clientData?.billing_day);
        });
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
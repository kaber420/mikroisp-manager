/**
 * Billing Panel Component - Alpine.js
 * 
 * Component for payment registration and history.
 * Uses ClientStore for shared state (billingDay, paidMonthsSet, etc.)
 * 
 * Dependencies: ClientStore.js (must be loaded first)
 * 
 * Usage: <div id="tab-billing" x-data="billingPanel">...</div>
 */
document.addEventListener('alpine:init', () => {
    Alpine.data('billingPanel', () => ({
        // --- Local State ---
        loading: true,
        payments: [],
        selectedMonth: '',

        // --- Lifecycle ---
        async init() {
            await this.loadPaymentHistory();
            await this.autoFillPaymentAmount();
            this.setupFormListeners();
            this.loading = false;
        },

        // --- Print Modal ---
        openPrintModal(paymentId) {
            const iframeContent = `
                <div class="flex-1 bg-white p-0 overflow-hidden relative">
                    <iframe src="/payment/${paymentId}/receipt" class="w-full h-[60vh] border-0"></iframe>
                </div>
            `;

            ModalUtils.showCustomModal({
                title: 'Print Receipt',
                content: iframeContent,
                size: 'md',
                modalId: 'print-receipt-modal',
                actions: [
                    {
                        text: 'Close',
                        className: 'px-4 py-2 rounded-md text-sm font-semibold border border-border-color hover:bg-surface-3'
                    },
                    {
                        text: 'Print',
                        icon: 'print',
                        primary: true,
                        closeOnClick: false,
                        handler: () => {
                            const iframe = document.querySelector('#print-receipt-modal iframe');
                            if (iframe && iframe.contentWindow) {
                                iframe.contentWindow.focus();
                                iframe.contentWindow.print();
                            }
                        }
                    }
                ]
            });
        },

        // --- Store Access ---
        get store() {
            return Alpine.store('client');
        },

        get clientId() {
            return this.store.clientId;
        },

        get currentYear() {
            return this.store.currentYear;
        },

        get billingDay() {
            return this.store.billingDay;
        },

        // --- API Helper ---
        async fetchJSON(url, options = {}) {
            const API_BASE_URL = window.location.origin;
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
        },

        // --- Month Selector ---
        get months() {
            return [
                "Ene", "Feb", "Mar", "Abr", "May", "Jun",
                "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"
            ];
        },

        renderMonthSelector() {
            const grid = document.getElementById('months-grid');
            const yearDisplay = document.getElementById('current-year-display');
            const hiddenInput = document.getElementById('payment-month');

            if (!grid || !yearDisplay) return;

            yearDisplay.textContent = this.currentYear;
            grid.innerHTML = '';

            this.months.forEach((name, index) => {
                const monthNum = String(index + 1).padStart(2, '0');
                const value = `${this.currentYear}-${monthNum}`;
                const isPaid = this.store.isMonthPaid(value);

                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = `
                    py-2 px-1 rounded-md text-sm font-semibold border transition-all relative overflow-hidden
                    ${isPaid
                        ? 'bg-success/20 border-success text-success cursor-not-allowed opacity-60'
                        : 'bg-surface-2 border-border-color hover:border-primary hover:text-primary'
                    }
                `;

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
                        this.selectedMonth = value;

                        // Calcular y mostrar ciclo
                        this.calculateCycleDates(value);
                    };
                }
                grid.appendChild(btn);
            });
        },

        calculateCycleDates(yearMonth) {
            const billingDay = this.billingDay || 1;
            const [year, month] = yearMonth.split('-').map(Number);

            const startDate = new Date(year, month - 1, billingDay);
            const endDate = new Date(year, month, billingDay);

            const options = { day: 'numeric', month: 'long', year: 'numeric' };
            const startStr = startDate.toLocaleDateString('es-ES', options);
            const endStr = endDate.toLocaleDateString('es-ES', options);

            const cycleDatesEl = document.getElementById('cycle-dates');
            const cycleInfoEl = document.getElementById('cycle-info');

            if (cycleDatesEl) cycleDatesEl.textContent = `${startStr} al ${endStr}`;
            if (cycleInfoEl) cycleInfoEl.classList.remove('hidden');
        },

        // --- Year Navigation ---
        prevYear() {
            this.store.prevYear();
            this.renderMonthSelector();
        },

        nextYear() {
            this.store.nextYear();
            this.renderMonthSelector();
        },

        // --- Payment History ---
        async loadPaymentHistory() {
            try {
                this.loading = true;
                const payments = await this.fetchJSON(`/api/clients/${this.clientId}/payments`);
                this.payments = payments || [];

                // Update store with paid months
                this.store.clearPaidMonths();
                this.payments.forEach(p => {
                    if (p.mes_correspondiente) {
                        this.store.addPaidMonth(p.mes_correspondiente);
                    }
                });

                // Render month selector (needs paid months data)
                this.renderMonthSelector();
            } catch (e) {
                console.error("Error loading history:", e);
                // In a real app, you might want to show an error message in the UI
                this.payments = [];
            } finally {
                this.loading = false;
            }
        },

        // --- Register Payment ---
        setupFormListeners() {
            const paymentForm = document.getElementById('register-payment-form');
            if (paymentForm) {
                paymentForm.addEventListener('submit', (e) => this.handleRegisterPayment(e));
            }

            const prevYearBtn = document.getElementById('prev-year-btn');
            const nextYearBtn = document.getElementById('next-year-btn');

            if (prevYearBtn) {
                prevYearBtn.addEventListener('click', () => this.prevYear());
            }
            if (nextYearBtn) {
                nextYearBtn.addEventListener('click', () => this.nextYear());
            }
        },

        async handleRegisterPayment(e) {
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
            if (!data.mes_correspondiente || !/^\d{4}-\d{2}$/.test(data.mes_correspondiente)) {
                errorEl.textContent = 'Please select a month to pay.';
                errorEl.classList.remove('hidden');
                return;
            }

            try {
                await this.fetchJSON(`/api/clients/${this.clientId}/payments`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                showToast('Payment registered and service reactivated successfully!', 'success');
                document.getElementById('register-payment-form').reset();
                document.getElementById('payment-month').value = '';
                document.getElementById('cycle-info').classList.add('hidden');
                this.selectedMonth = '';

                // Reload data
                await this.loadPaymentHistory();

                // Trigger service status reload in parent component (if available)
                // Use custom event for cross-component communication
                document.dispatchEvent(new CustomEvent('payment:registered'));

            } catch (error) {
                errorEl.textContent = `Error: ${error.message}`;
                errorEl.classList.remove('hidden');
            }
        },

        // --- Auto-fill Payment Amount ---
        async autoFillPaymentAmount() {
            try {
                const services = this.store.allServices;
                if (!services || services.length === 0) return;

                const primaryService = services[0];
                if (!primaryService.plan_id || !primaryService.router_host) return;

                const plans = await this.fetchJSON(`/api/plans/router/${primaryService.router_host}`);
                if (!plans || plans.length === 0) return;

                const clientPlan = plans.find(p => p.id === primaryService.plan_id);
                if (!clientPlan || !clientPlan.price) return;

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
    }));

    console.log('[Component] BillingPanel initialized');
});

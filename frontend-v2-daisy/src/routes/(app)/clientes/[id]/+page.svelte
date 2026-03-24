<script lang="ts">
    import { goto } from '$app/navigation';
    import type { PageData } from './$types';
    import type { ClientService, Payment, PaymentCreate } from '$lib/types/client';
    import {
        getClientServices,
        getPaymentHistory,
        registerPayment,
        changeServicePlan,
        syncServiceToRouter,
        deleteClientService,
        getPlansForService,
        getPPPoESecrets,
        getPPPoEActive,
        getQueueStats,
        generateClientAccess,
        getUsers,
    } from '$lib/api';
import type { User, UserCreate } from '$lib/types/user';

    let { data }: { data: PageData } = $props();
    let client = $derived(data.client);

    // --- Tab state ---
    let activeTab = $state<'info' | 'servicios' | 'pagos' | 'acceso'>('info');

    // --- Services tab state ---
    let services = $state<ClientService[]>([]);
    let servicesLoading = $state(false);
    let servicesError = $state('');
    let liveStatus = $state<Record<number, any>>({});
    let liveStatusLoading = $state<Record<number, boolean>>({});

    // --- Payments tab state ---
    let payments = $state<Payment[]>([]);
    let paymentsLoading = $state(false);
    let paymentError = $state('');
    let paymentSuccess = $state('');
    let paidMonths = $state<Set<string>>(new Set());
    let selectedMonth = $state('');
    let currentYear = $state(new Date().getFullYear());
    let paymentAmount = $state('');
    let paymentMethod = $state('Efectivo');
    let paymentNotes = $state('');
    let submittingPayment = $state(false);

    // --- Plan change modal state ---
    let showPlanModal = $state(false);
    let planModalService = $state<ClientService | null>(null);
    let availablePlans = $state<any[]>([]);
    let selectedPlanId = $state('');
    let planModalLoading = $state(false);
    let planModalError = $state('');

    // --- Access tab state ---
    let clientUser = $state<User | null>(null);
    let accessLoading = $state(false);
    let accessError = $state('');
    let showAccessModal = $state(false);
    let accessForm = $state({
        username: '',
        password: '',
        telegram_chat_id: '',
    });
    let creatingAccess = $state(false);

    // --- Utility functions ---
    function formatBytes(bytes: number | undefined | null): string {
        if (!bytes || bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    function statusLabel(status: string): string {
        const map: Record<string, string> = {
            active: 'Activo', suspended: 'Suspendido', inactive: 'Inactivo',
        };
        return map[status] ?? status;
    }

    function statusBadgeClass(status: string): string {
        if (status === 'active') return 'badge-success';
        if (status === 'suspended') return 'badge-warning';
        return 'badge-neutral';
    }

    // --- Load service data ---
    async function loadServices() {
        servicesLoading = true;
        servicesError = '';
        try {
            services = await getClientServices(client.id);
            // Load live status for each service in parallel
            for (const svc of services) {
                loadLiveStatus(svc);
            }
        } catch (e: any) {
            servicesError = e?.response?.data?.detail ?? e?.message ?? 'Error al cargar servicios';
        } finally {
            servicesLoading = false;
        }
    }

    async function loadLiveStatus(svc: ClientService) {
        liveStatusLoading = { ...liveStatusLoading, [svc.id]: true };
        try {
            if (svc.service_type === 'pppoe' && svc.pppoe_username) {
                const secrets = await getPPPoESecrets(svc.router_host, svc.pppoe_username);
                const activeConns = await getPPPoEActive(svc.router_host, svc.pppoe_username);
                const secret = secrets?.[0];
                liveStatus = {
                    ...liveStatus,
                    [svc.id]: {
                        found: !!secret,
                        account_status: secret ? (secret.disabled === 'true' ? 'Suspendido' : 'Activo') : null,
                        is_online: activeConns && activeConns.length > 0,
                        uptime: activeConns?.[0]?.uptime,
                        online_ip: activeConns?.[0]?.address,
                        bytes_in: parseInt(secret?.['bytes-in'] || '0', 10),
                        bytes_out: parseInt(secret?.['bytes-out'] || '0', 10),
                        profile: secret?.profile,
                    }
                };
            } else if (svc.service_type === 'simple_queue' && svc.ip_address) {
                const queueData = await getQueueStats(svc.router_host, svc.ip_address);
                const bytesStr = queueData?.bytes || '0/0';
                const [bytesUp, bytesDown] = bytesStr.split('/').map((b: string) => parseInt(b, 10) || 0);
                liveStatus = {
                    ...liveStatus,
                    [svc.id]: {
                        found: !!(queueData && queueData.status !== 'not_found'),
                        name: queueData?.name,
                        target: queueData?.target,
                        max_limit: queueData?.['max-limit'],
                        bytes_up: bytesUp,
                        bytes_down: bytesDown,
                    }
                };
            }
        } catch {
            liveStatus = { ...liveStatus, [svc.id]: { error: true } };
        } finally {
            liveStatusLoading = { ...liveStatusLoading, [svc.id]: false };
        }
    }

    // --- Sync service ---
    async function handleSync(svc: ClientService) {
        if (!confirm(`¿Sincronizar servicio "${svc.pppoe_username || svc.ip_address}" al router?`)) return;
        try {
            await syncServiceToRouter(svc.id);
            await loadLiveStatus(svc);
        } catch (e: any) {
            alert('Error al sincronizar: ' + (e?.response?.data?.detail ?? e?.message));
        }
    }

    // --- Delete service ---
    async function handleDeleteService(svc: ClientService) {
        const label = svc.pppoe_username || svc.ip_address || String(svc.id);
        if (!confirm(`¿Eliminar el servicio "${label}"? Esto lo eliminará del router también.`)) return;
        try {
            await deleteClientService(svc.id);
            await loadServices();
        } catch (e: any) {
            alert('Error al eliminar: ' + (e?.response?.data?.detail ?? e?.message));
        }
    }

    // --- Plan change modal ---
    async function openPlanModal(svc: ClientService) {
        planModalService = svc;
        showPlanModal = true;
        planModalLoading = true;
        planModalError = '';
        selectedPlanId = '';
        try {
            const plans = await getPlansForService(svc.router_host);
            availablePlans = plans.filter((p: any) => p.plan_type === svc.service_type);
        } catch (e: any) {
            planModalError = 'No se pudieron cargar los planes.';
        } finally {
            planModalLoading = false;
        }
    }

    async function handlePlanChange() {
        if (!planModalService || !selectedPlanId) return;
        planModalLoading = true;
        planModalError = '';
        try {
            await changeServicePlan(planModalService.id, parseInt(selectedPlanId));
            showPlanModal = false;
            await loadServices();
        } catch (e: any) {
            planModalError = e?.response?.data?.detail ?? e?.message ?? 'Error al cambiar el plan.';
        } finally {
            planModalLoading = false;
        }
    }

    // --- Load payments ---
    async function loadPayments() {
        paymentsLoading = true;
        paymentError = '';
        try {
            payments = await getPaymentHistory(client.id);
            paidMonths = new Set(payments.map((p) => p.mes_correspondiente));
            // Auto-fill amount with plan price from first service
            if (services.length > 0 && services[0].plan_price && !paymentAmount) {
                paymentAmount = services[0].plan_price.toFixed(2);
            }
        } catch (e: any) {
            paymentError = e?.response?.data?.detail ?? e?.message ?? 'Error al cargar pagos';
        } finally {
            paymentsLoading = false;
        }
    }

    // --- Register payment ---
    async function handleRegisterPayment(e: SubmitEvent) {
        e.preventDefault();
        paymentError = '';
        paymentSuccess = '';
        if (!selectedMonth) {
            paymentError = 'Por favor selecciona el mes a pagar.';
            return;
        }
        if (!paymentAmount || parseFloat(paymentAmount) <= 0) {
            paymentError = 'El monto debe ser un número válido.';
            return;
        }
        submittingPayment = true;
        try {
            const payload: PaymentCreate = {
                monto: parseFloat(paymentAmount),
                mes_correspondiente: selectedMonth,
                metodo_pago: paymentMethod,
                notas: paymentNotes || undefined,
            };
            await registerPayment(client.id, payload);
            paymentSuccess = '¡Pago registrado y servicio reactivado correctamente!';
            selectedMonth = '';
            paymentNotes = '';
            await loadPayments();
        } catch (e: any) {
            paymentError = e?.response?.data?.detail ?? e?.message ?? 'Error al registrar el pago';
        } finally {
            submittingPayment = false;
        }
    }

    function selectMonth(yearMonth: string) {
        if (paidMonths.has(yearMonth)) return;
        selectedMonth = yearMonth;
        // auto fill amount from service plan
        if (services.length > 0 && services[0].plan_price) {
            paymentAmount = services[0].plan_price.toFixed(2);
        }
    }

    // --- Access management ---
    async function loadAccessInfo() {
        accessLoading = true;
        accessError = '';
        try {
            // Buscamos un usuario que tenga este client_id
            const allUsers = await getUsers();
            clientUser = allUsers.find(u => u.client_id === client.id) || null;
            
            // Pre-llenar el formulario con datos existentes o sugerencias
            if (clientUser) {
                accessForm.username = clientUser.username;
                accessForm.telegram_chat_id = clientUser.telegram_chat_id || '';
                // La contraseña se deja vacía por seguridad al editar
                accessForm.password = '';
            } else {
                // Sugerir username basado en email o nombre si es nuevo
                accessForm.username = client.email?.split('@')[0] || client.name.toLowerCase().replace(/\s+/g, '.');
                accessForm.telegram_chat_id = client.telegram_contact || '';
                accessForm.password = '';
            }
        } catch (e: any) {
            accessError = 'No se pudo cargar la información de acceso.';
        } finally {
            accessLoading = false;
        }
    }

    async function handleCreateAccess(e: SubmitEvent) {
        e.preventDefault();
        creatingAccess = true;
        accessError = '';
        try {
            const payload = {
                username: accessForm.username,
                email: client.email || `${accessForm.username}@mikroisp.local`,
                password: accessForm.password || undefined,
                role: 'client',
                client_id: client.id,
                telegram_chat_id: accessForm.telegram_chat_id || null,
            };
            await generateClientAccess(client.id, payload);
            showAccessModal = false;
            await loadAccessInfo();
            // Limpiar password para seguridad
            accessForm.password = '';
        } catch (e: any) {
            accessError = e?.response?.data?.detail ?? e?.message ?? 'Error al procesar el acceso';
        } finally {
            creatingAccess = false;
        }
    }

    // --- Tab switching (load data lazily) ---
    function switchTab(tab: 'info' | 'servicios' | 'pagos' | 'acceso') {
        activeTab = tab;
        if (tab === 'servicios' && services.length === 0 && !servicesLoading) {
            loadServices();
        }
        if (tab === 'pagos') {
            if (payments.length === 0 && !paymentsLoading) loadPayments();
            if (services.length === 0 && !servicesLoading) loadServices();
        }
        if (tab === 'acceso' && !clientUser && !accessLoading) {
            loadAccessInfo();
        }
    }

    const MONTHS = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];

    function getBillingDay(): number {
        return services[0]?.billing_day ?? client.billing_day ?? 1;
    }

    function getCycleDates(yearMonth: string): string {
        const [year, month] = yearMonth.split('-').map(Number);
        const bd = getBillingDay();
        const start = new Date(year, month - 1, bd);
        const end = new Date(year, month, bd);
        const opts: Intl.DateTimeFormatOptions = { day: 'numeric', month: 'long', year: 'numeric' };
        return `${start.toLocaleDateString('es-MX', opts)} al ${end.toLocaleDateString('es-MX', opts)}`;
    }
</script>

<div style="display:flex;flex-direction:column;gap:1.5rem;">
    <!-- ── HEADER ──────────────────────────────────────────────────────── -->
    <div class="glass-card-flat" style="border-radius:1rem;overflow:hidden;">
        <div style="padding:1.25rem 1.5rem;display:flex;align-items:center;gap:1rem;flex-wrap:wrap;justify-content:space-between;">
            <div style="display:flex;align-items:center;gap:0.75rem;">
                <button
                    class="btn btn-ghost btn-sm btn-square"
                    onclick={() => goto('/clientes')}
                    title="Volver a clientes"
                >
                    <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
                    </svg>
                </button>
                <div>
                    <h1 style="margin:0;font-size:1.5rem;font-weight:800;">{client.name}</h1>
                    <span class="badge {statusBadgeClass(client.service_status)} badge-sm" style="margin-top:4px;">
                        {statusLabel(client.service_status)}
                    </span>
                </div>
            </div>
            <div style="font-size:0.8rem;opacity:0.5;">
                Alta: {new Date(client.created_at).toLocaleDateString('es-MX')}
            </div>
        </div>

        <!-- Tabs -->
        <div class="tabs tabs-border" style="padding:0 1rem;border-top:1px solid color-mix(in oklch, currentColor 10%, transparent);">
            <button
                class="tab {activeTab === 'info' ? 'tab-active' : ''}"
                onclick={() => switchTab('info')}
            >
                <svg class="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
                Información
            </button>
            <button
                class="tab {activeTab === 'servicios' ? 'tab-active' : ''}"
                onclick={() => switchTab('servicios')}
            >
                <svg class="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.14 0" />
                </svg>
                Servicios · <span class="ml-1 badge badge-sm {client.cpe_count > 0 ? 'badge-info' : 'badge-neutral'}">{client.cpe_count}</span>
            </button>
            <button
                class="tab {activeTab === 'pagos' ? 'tab-active' : ''}"
                onclick={() => switchTab('pagos')}
            >
                <svg class="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2z" />
                </svg>
                Facturación
            </button>
            <button
                class="tab {activeTab === 'acceso' ? 'tab-active' : ''}"
                onclick={() => switchTab('acceso')}
            >
                <svg class="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                </svg>
                Acceso Portal
            </button>
        </div>
    </div>

    <!-- ── TAB: INFORMACIÓN ────────────────────────────────────────────── -->
    {#if activeTab === 'info'}
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:1.5rem;">
            <!-- Datos de contacto -->
            <div class="glass-card-flat" style="border-radius:1rem;overflow:hidden;">
                <div style="padding:1rem 1.25rem;font-weight:700;font-size:1rem;border-bottom:1px solid color-mix(in oklch,currentColor 10%,transparent);">
                    Datos de Contacto
                </div>
                <div style="padding:1.25rem;display:flex;flex-direction:column;gap:0.75rem;font-size:0.875rem;">
                    {#each [
                        { label: 'Dirección', val: client.address },
                        { label: 'Teléfono', val: client.phone_number },
                        { label: 'WhatsApp', val: client.whatsapp_number },
                        { label: 'Email', val: client.email },
                        { label: 'Telegram', val: client.telegram_contact },
                        { label: 'Día de facturación', val: client.billing_day ? `Día ${client.billing_day}` : null },
                    ] as field}
                        <div style="display:flex;justify-content:space-between;gap:1rem;align-items:flex-start;">
                            <span style="opacity:0.55;min-width:120px;">{field.label}</span>
                            <span style="font-weight:600;text-align:right;">{field.val ?? '—'}</span>
                        </div>
                    {/each}
                    {#if client.coordinates}
                        <div style="display:flex;justify-content:space-between;gap:1rem;align-items:flex-start;">
                            <span style="opacity:0.55;min-width:120px;">Coordenadas</span>
                            <a
                                href="https://maps.google.com/maps?q={client.coordinates}"
                                target="_blank"
                                rel="noopener noreferrer"
                                class="link link-primary"
                                style="font-weight:600;text-align:right;"
                            >{client.coordinates}</a>
                        </div>
                    {/if}
                </div>
            </div>
            <!-- Notas -->
            {#if client.notes}
                <div class="glass-card-flat" style="border-radius:1rem;overflow:hidden;">
                    <div style="padding:1rem 1.25rem;font-weight:700;font-size:1rem;border-bottom:1px solid color-mix(in oklch,currentColor 10%,transparent);">
                        Notas
                    </div>
                    <div style="padding:1.25rem;font-size:0.875rem;white-space:pre-wrap;opacity:0.8;">
                        {client.notes}
                    </div>
                </div>
            {/if}
        </div>
    {/if}

    <!-- ── TAB: SERVICIOS ──────────────────────────────────────────────── -->
    {#if activeTab === 'servicios'}
        <div class="glass-card-flat" style="border-radius:1rem;overflow:hidden;">
            <div style="padding:1rem 1.25rem;border-bottom:1px solid color-mix(in oklch,currentColor 10%,transparent);display:flex;align-items:center;justify-content:space-between;">
                <span style="font-weight:700;font-size:1rem;">Servicios de Red</span>
            </div>
            <div style="padding:1.25rem;display:flex;flex-direction:column;gap:1rem;">
                {#if servicesLoading}
                    <div style="text-align:center;padding:2rem;opacity:0.5;">
                        <span class="loading loading-spinner loading-md"></span>
                        <p style="margin-top:0.5rem;">Cargando servicios...</p>
                    </div>
                {:else if servicesError}
                    <div class="alert alert-error"><span>{servicesError}</span></div>
                {:else if services.length === 0}
                    <p style="text-align:center;opacity:0.5;padding:2rem;">Sin servicios configurados para este cliente.</p>
                {:else}
                    {#each services as svc (svc.id)}
                        {@const live = liveStatus[svc.id]}
                        {@const liveLoading = liveStatusLoading[svc.id]}
                        {@const isPPPoE = svc.service_type === 'pppoe'}
                        <div style="border-radius:0.75rem;border:1px solid {isPPPoE ? 'color-mix(in oklch,oklch(60% 0.15 240) 40%,transparent)' : 'color-mix(in oklch,oklch(60% 0.15 280) 40%,transparent)'};padding:1rem;background:color-mix(in oklch,{isPPPoE ? 'oklch(60% 0.15 240)' : 'oklch(60% 0.15 280)'} 5%,transparent);">
                            <!-- Service header -->
                            <div style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:0.5rem;margin-bottom:0.75rem;">
                                <div style="display:flex;align-items:center;gap:0.5rem;flex-wrap:wrap;">
                                    <span class="badge badge-sm" style="background:color-mix(in oklch,{isPPPoE ? 'oklch(60% 0.15 240)' : 'oklch(60% 0.15 280)'} 30%,transparent);">
                                        {isPPPoE ? 'PPPoE' : 'Simple Queue'}
                                    </span>
                                    <span class="badge {statusBadgeClass(svc.status)} badge-sm">{statusLabel(svc.status)}</span>
                                    <code style="font-size:0.85rem;font-weight:600;">{svc.pppoe_username || svc.ip_address || '—'}</code>
                                </div>
                                <!-- Actions -->
                                <div style="display:flex;gap:0.5rem;flex-shrink:0;">
                                    <button class="btn btn-xs btn-warning" onclick={() => handleSync(svc)} title="Sincronizar al router">
                                        <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                                        </svg>
                                        Sync
                                    </button>
                                    <button class="btn btn-xs btn-info" onclick={() => openPlanModal(svc)} title="Cambiar plan">
                                        <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                                        </svg>
                                        Plan
                                    </button>
                                    <button class="btn btn-xs btn-error" onclick={() => handleDeleteService(svc)} title="Eliminar servicio">
                                        <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                        </svg>
                                    </button>
                                </div>
                            </div>

                            <!-- Service meta info -->
                            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:0.5rem;font-size:0.8rem;margin-bottom:0.75rem;opacity:0.7;">
                                <span>Router: <code>{svc.router_host}</code></span>
                                {#if svc.plan_name}
                                    <span>Plan: <strong style="color:var(--color-primary,oklch(60% 0.15 240))">{svc.plan_name} {svc.plan_price != null ? `($${svc.plan_price.toFixed(2)})` : ''}</strong></span>
                                {/if}
                                {#if svc.billing_day}
                                    <span>Día facturación: <strong>{svc.billing_day}</strong></span>
                                {/if}
                                {#if svc.notes}
                                    <span>Notas: {svc.notes}</span>
                                {/if}
                            </div>

                            <!-- Live status -->
                            <div style="border-top:1px solid color-mix(in oklch,currentColor 10%,transparent);padding-top:0.75rem;">
                                {#if liveLoading}
                                    <div style="display:flex;align-items:center;gap:0.5rem;opacity:0.5;font-size:0.8rem;">
                                        <span class="loading loading-spinner loading-xs"></span>
                                        Consultando router...
                                    </div>
                                {:else if !live}
                                    <p style="font-size:0.8rem;opacity:0.5;">Estado no disponible.</p>
                                {:else if live.error}
                                    <p class="text-error" style="font-size:0.8rem;">Error al consultar el router.</p>
                                {:else if !live.found}
                                    <p class="text-warning" style="font-size:0.8rem;">⚠ No encontrado en el router. Usa Sync para recrearlo.</p>
                                {:else if isPPPoE}
                                    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:0.5rem;font-size:0.82rem;">
                                        <div style="display:flex;justify-content:space-between;">
                                            <span style="opacity:0.6;">Cuenta:</span>
                                            <strong class="{live.account_status === 'Activo' ? 'text-success' : 'text-warning'}">{live.account_status ?? '—'}</strong>
                                        </div>
                                        <div style="display:flex;justify-content:space-between;">
                                            <span style="opacity:0.6;">Red:</span>
                                            <strong class="{live.is_online ? 'text-success' : 'text-error'}">{live.is_online ? `Online (${live.online_ip ?? ''})` : 'Offline'}</strong>
                                        </div>
                                        {#if live.is_online && live.uptime}
                                            <div style="display:flex;justify-content:space-between;">
                                                <span style="opacity:0.6;">Uptime:</span>
                                                <strong>{live.uptime}</strong>
                                            </div>
                                        {/if}
                                        {#if live.profile}
                                            <div style="display:flex;justify-content:space-between;">
                                                <span style="opacity:0.6;">Perfil:</span>
                                                <code>{live.profile}</code>
                                            </div>
                                        {/if}
                                        <div style="display:flex;justify-content:space-between;grid-column:1/-1;">
                                            <span style="opacity:0.6;">Uso (↑ / ↓):</span>
                                            <strong>{formatBytes(live.bytes_out)} / {formatBytes(live.bytes_in)}</strong>
                                        </div>
                                    </div>
                                {:else}
                                    <!-- Simple Queue live -->
                                    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:0.5rem;font-size:0.82rem;">
                                        <div style="display:flex;justify-content:space-between;">
                                            <span style="opacity:0.6;">Nombre Queue:</span>
                                            <code>{live.name ?? '—'}</code>
                                        </div>
                                        <div style="display:flex;justify-content:space-between;">
                                            <span style="opacity:0.6;">Target:</span>
                                            <code>{live.target ?? svc.ip_address ?? '—'}</code>
                                        </div>
                                        <div style="display:flex;justify-content:space-between;">
                                            <span style="opacity:0.6;">Límite:</span>
                                            <strong>{live.max_limit ?? '—'}</strong>
                                        </div>
                                        <div style="display:flex;justify-content:space-between;grid-column:1/-1;">
                                            <span style="opacity:0.6;">Uso (↑ / ↓):</span>
                                            <strong>{formatBytes(live.bytes_up)} / {formatBytes(live.bytes_down)}</strong>
                                        </div>
                                    </div>
                                {/if}
                            </div>
                        </div>
                    {/each}
                {/if}
            </div>
        </div>
    {/if}

    <!-- ── TAB: PAGOS ──────────────────────────────────────────────────── -->
    {#if activeTab === 'pagos'}
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:1.5rem;">
            <!-- Registrar Pago -->
            <div class="glass-card-flat" style="border-radius:1rem;overflow:hidden;">
                <div style="padding:1rem 1.25rem;font-weight:700;font-size:1rem;border-bottom:1px solid color-mix(in oklch,currentColor 10%,transparent);">
                    Registrar Pago
                </div>
                <!-- Plan info banner -->
                {#if services.length > 0 && services[0].plan_name}
                    <div style="margin:1rem 1.25rem 0;padding:0.75rem 1rem;border-radius:0.75rem;background:color-mix(in oklch,var(--color-primary,oklch(60% 0.15 240)) 12%,transparent);border:1px solid color-mix(in oklch,var(--color-primary,oklch(60% 0.15 240)) 30%,transparent);display:flex;justify-content:space-between;align-items:center;">
                        <div>
                            <p style="font-size:0.7rem;text-transform:uppercase;letter-spacing:0.05em;opacity:0.55;margin:0;">Plan del Cliente</p>
                            <p style="font-weight:700;font-size:1rem;margin:0;color:var(--color-primary,oklch(60% 0.15 240));">{services[0].plan_name}</p>
                        </div>
                        <div style="text-align:right;">
                            <p style="font-size:0.7rem;text-transform:uppercase;opacity:0.55;margin:0;">Precio Mensual</p>
                            <p style="font-size:1.4rem;font-weight:800;margin:0;color:oklch(75% 0.15 145);">${services[0].plan_price?.toFixed(2) ?? '—'}</p>
                        </div>
                    </div>
                {/if}

                <form onsubmit={handleRegisterPayment} style="padding:1.25rem;display:flex;flex-direction:column;gap:1rem;">
                    <!-- Month selector -->
                    <div>
                        <label style="display:block;font-size:0.85rem;font-weight:600;margin-bottom:0.75rem;text-align:center;">Seleccionar Mes a Pagar</label>
                        <div style="border:1px solid color-mix(in oklch,currentColor 15%,transparent);border-radius:0.75rem;padding:1rem;background:color-mix(in oklch,currentColor 3%,transparent);">
                            <!-- Year navigator -->
                            <div style="display:flex;align-items:center;justify-content:center;gap:1.5rem;margin-bottom:0.75rem;">
                                <button type="button" class="btn btn-ghost btn-xs btn-circle" onclick={() => currentYear--}>
                                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg>
                                </button>
                                <span style="font-weight:700;font-size:1.1rem;min-width:50px;text-align:center;">{currentYear}</span>
                                <button type="button" class="btn btn-ghost btn-xs btn-circle" onclick={() => currentYear++}>
                                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
                                </button>
                            </div>
                            <!-- Month grid -->
                            <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:0.5rem;">
                                {#each MONTHS as monthName, idx}
                                    {@const monthNum = String(idx + 1).padStart(2, '0')}
                                    {@const ym = `${currentYear}-${monthNum}`}
                                    {@const isPaid = paidMonths.has(ym)}
                                    {@const isSelected = selectedMonth === ym}
                                    <button
                                        type="button"
                                        disabled={isPaid}
                                        onclick={() => selectMonth(ym)}
                                        class="btn btn-xs"
                                        style="height:2.5rem;position:relative;{isPaid ? 'background:color-mix(in oklch,oklch(75% 0.15 145) 20%,transparent);border-color:oklch(75% 0.15 145);color:oklch(75% 0.15 145);cursor:not-allowed;' : isSelected ? 'background:color-mix(in oklch,var(--color-primary,oklch(60% 0.15 240)) 25%,transparent);border-color:var(--color-primary,oklch(60% 0.15 240));outline:2px solid var(--color-primary,oklch(60% 0.15 240));outline-offset:1px;' : ''}"
                                    >
                                        {monthName}
                                        {#if isPaid}
                                            <span style="position:absolute;top:2px;right:2px;width:10px;height:10px;border-radius:50%;background:oklch(75% 0.15 145);display:flex;align-items:center;justify-content:center;font-size:6px;">✓</span>
                                        {/if}
                                    </button>
                                {/each}
                            </div>
                        </div>
                        {#if selectedMonth}
                            <div style="margin-top:0.5rem;padding:0.5rem 0.75rem;border-radius:0.5rem;background:color-mix(in oklch,var(--color-primary,oklch(60% 0.15 240)) 10%,transparent);font-size:0.8rem;color:var(--color-primary,oklch(60% 0.15 240));font-weight:600;">
                                📅 Ciclo: {getCycleDates(selectedMonth)}
                            </div>
                        {/if}
                    </div>

                    <!-- Amount & Method -->
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;">
                        <div>
                            <label class="label" style="font-size:0.8rem;">Monto</label>
                            <input type="number" step="0.01" min="0" bind:value={paymentAmount} required class="input input-sm input-bordered w-full" placeholder="0.00" style="font-size:1rem;font-weight:700;" />
                        </div>
                        <div>
                            <label class="label" style="font-size:0.8rem;">Método de Pago</label>
                            <select bind:value={paymentMethod} class="select select-sm select-bordered w-full">
                                <option>Efectivo</option>
                                <option>Transferencia</option>
                                <option>Otro</option>
                            </select>
                        </div>
                    </div>
                    <div>
                        <label class="label" style="font-size:0.8rem;">Notas (Opcional)</label>
                        <input type="text" bind:value={paymentNotes} class="input input-sm input-bordered w-full" placeholder="Referencia, comentario..." />
                    </div>

                    {#if paymentError}
                        <div class="alert alert-error p-2 text-sm"><span>{paymentError}</span></div>
                    {/if}
                    {#if paymentSuccess}
                        <div class="alert alert-success p-2 text-sm"><span>{paymentSuccess}</span></div>
                    {/if}

                    <div style="text-align:right;">
                        <button type="submit" class="btn btn-primary btn-sm" disabled={submittingPayment}>
                            {#if submittingPayment}<span class="loading loading-spinner loading-xs"></span>{/if}
                            Registrar Pago &amp; Reactivar
                        </button>
                    </div>
                </form>
            </div>

            <!-- Historial de pagos -->
            <div class="glass-card-flat" style="border-radius:1rem;overflow:hidden;">
                <div style="padding:1rem 1.25rem;font-weight:700;font-size:1rem;border-bottom:1px solid color-mix(in oklch,currentColor 10%,transparent);display:flex;justify-content:space-between;align-items:center;">
                    <span>Historial de Pagos</span>
                    {#if payments.length > 0}
                        <span class="badge badge-neutral badge-sm">{payments.length}</span>
                    {/if}
                </div>
                <div style="padding:1rem;max-height:520px;overflow-y:auto;display:flex;flex-direction:column;gap:0.5rem;">
                    {#if paymentsLoading}
                        <div style="text-align:center;padding:2rem;opacity:0.5;">
                            <span class="loading loading-spinner loading-md"></span>
                        </div>
                    {:else if payments.length === 0}
                        <p style="text-align:center;opacity:0.5;padding:2rem;">Sin pagos registrados.</p>
                    {:else}
                        {#each payments as payment (payment.id)}
                            <div style="display:flex;justify-content:space-between;align-items:center;padding:0.75rem;border-radius:0.5rem;background:color-mix(in oklch,currentColor 4%,transparent);border:1px solid color-mix(in oklch,currentColor 8%,transparent);">
                                <div>
                                    <p style="margin:0;font-weight:700;font-size:0.9rem;">
                                        ${payment.monto.toFixed(2)}
                                        <span style="font-weight:500;opacity:0.6;font-size:0.8rem;"> · {payment.mes_correspondiente}</span>
                                    </p>
                                    <p style="margin:0.2rem 0 0;font-size:0.75rem;opacity:0.55;">
                                        {new Date(payment.fecha_pago).toLocaleString('es-MX', { dateStyle: 'medium', timeStyle: 'short' })}
                                        {#if payment.metodo_pago} · {payment.metodo_pago}{/if}
                                    </p>
                                    {#if payment.notas}
                                        <p style="margin:0.2rem 0 0;font-size:0.73rem;color:oklch(70% 0.12 60);">{payment.notas}</p>
                                    {/if}
                                </div>
                                <a
                                    href="/payment/{payment.id}/receipt"
                                    target="_blank"
                                    rel="noopener"
                                    class="btn btn-ghost btn-xs"
                                    title="Ver recibo"
                                >
                                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
                                    </svg>
                                </a>
                            </div>
                        {/each}
                    {/if}
                </div>
            </div>
        </div>
    {/if}

    <!-- ── TAB: ACCESO PORTAL ────────────────────────────────────────── -->
    {#if activeTab === 'acceso'}
        <div class="glass-card-flat" style="border-radius:1rem;overflow:hidden;">
            <div style="padding:1rem 1.25rem;font-weight:700;font-size:1rem;border-bottom:1px solid color-mix(in oklch,currentColor 10%,transparent);">
                Gestión de Acceso al Portal
            </div>
            <div style="padding:2rem;display:flex;flex-direction:column;align-items:center;text-align:center;gap:1.5rem;">
                {#if accessLoading}
                    <span class="loading loading-spinner loading-lg"></span>
                {:else if clientUser}
                    <div class="avatar placeholder">
                        <div class="bg-neutral text-neutral-content rounded-full w-24">
                            <span class="text-3xl">{clientUser.username[0].toUpperCase()}</span>
                        </div>
                    </div>
                    <div>
                        <h3 style="font-size:1.25rem;font-weight:700;margin:0;">{clientUser.username}</h3>
                        <p style="opacity:0.6;margin:0.25rem 0;">{clientUser.email}</p>
                        <div style="margin-top:0.5rem;display:flex;gap:0.5rem;justify-content:center;">
                            <span class="badge badge-success">Acceso Activo</span>
                            <span class="badge badge-outline">{clientUser.role}</span>
                        </div>
                    </div>
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 w-full max-w-md mt-2">
                        <div class="stats shadow bg-base-200/50">
                            <div class="stat p-3">
                                <div class="stat-title text-xs">Telegram ID</div>
                                <div class="stat-value text-sm">{clientUser.telegram_chat_id || 'No vinculado'}</div>
                            </div>
                        </div>
                        <div class="stats shadow bg-base-200/50">
                            <div class="stat p-3">
                                <div class="stat-title text-xs">Último Acceso</div>
                                <div class="stat-value text-sm">Próximamente</div>
                            </div>
                        </div>
                    </div>
                    <button class="btn btn-outline btn-sm mt-4" onclick={() => showAccessModal = true}>
                        Actualizar Credenciales / Telegram
                    </button>
                {:else}
                    <div style="background:color-mix(in oklch,var(--color-primary,oklch(60% 0.15 240)) 10%,transparent);padding:2rem;border-radius:50%;margin-bottom:0.5rem;">
                        <svg class="w-16 h-16 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                        </svg>
                    </div>
                    <div>
                        <h3 style="font-size:1.25rem;font-weight:700;">Sin Acceso al Portal</h3>
                        <p style="opacity:0.6;max-width:400px;margin:0.5rem auto;">
                            Este cliente aún no tiene credenciales vinculadas para acceder al portal de autogestión.
                        </p>
                    </div>
                    <button class="btn btn-primary" onclick={() => showAccessModal = true}>
                        Crear Credenciales de Acceso
                    </button>
                {/if}
            </div>
        </div>
    {/if}
</div>

<!-- ── MODAL: Crear Acceso ─────────────────────────────────────────── -->
{#if showAccessModal}
    <div style="position:fixed;inset:0;z-index:1000;display:flex;align-items:center;justify-content:center;padding:1rem;background:rgba(0,0,0,0.6);">
        <div class="glass-card-flat" style="border-radius:1rem;width:100%;max-width:460px;overflow:hidden;">
            <div style="padding:1.25rem 1.5rem;font-weight:700;font-size:1.1rem;border-bottom:1px solid color-mix(in oklch,currentColor 10%,transparent);display:flex;justify-content:space-between;align-items:center;">
                <span>{clientUser ? 'Gestionar' : 'Crear'} Acceso al Portal</span>
                <button class="btn btn-ghost btn-xs btn-circle" onclick={() => { showAccessModal = false; }}>✕</button>
            </div>
            <form onsubmit={handleCreateAccess} style="padding:1.5rem;display:flex;flex-direction:column;gap:1rem;">
                <div class="form-control">
                    <label class="label"><span class="label-text">Nombre de Usuario</span></label>
                    <input type="text" bind:value={accessForm.username} required class="input input-bordered" placeholder="Ej: pablo.perez" />
                </div>
                <div class="form-control">
                    <label class="label">
                        <span class="label-text">Contraseña</span>
                        {#if clientUser}
                            <span class="label-text-alt text-warning">Dejar vacío para no cambiar</span>
                        {/if}
                    </label>
                    <input type="password" bind:value={accessForm.password} required={!clientUser} class="input input-bordered" placeholder="••••••••" />
                </div>
                <div class="form-control">
                    <label class="label">
                        <span class="label-text">Telegram Chat ID</span>
                        <span class="label-text-alt text-info">Para comandos /password</span>
                    </label>
                    <input type="text" bind:value={accessForm.telegram_chat_id} class="input input-bordered" placeholder="Ej: 123456789" />
                </div>

                {#if accessError}
                    <div class="alert alert-error p-2 text-sm"><span>{accessError}</span></div>
                {/if}

                <div style="display:flex;justify-content:flex-end;gap:0.75rem;padding-top:1rem;">
                    <button type="button" class="btn btn-ghost" onclick={() => { showAccessModal = false; }}>Cancelar</button>
                    <button type="submit" class="btn btn-primary" disabled={creatingAccess}>
                        {#if creatingAccess}<span class="loading loading-spinner loading-xs"></span>{/if}
                        {clientUser ? 'Guardar Cambios' : 'Habilitar Acceso'}
                    </button>
                </div>
            </form>
        </div>
    </div>
{/if}

<!-- ── MODAL: Cambiar Plan ─────────────────────────────────────────── -->
{#if showPlanModal}
    <div style="position:fixed;inset:0;z-index:1000;display:flex;align-items:center;justify-content:center;padding:1rem;background:rgba(0,0,0,0.6);">
        <div class="glass-card-flat" style="border-radius:1rem;width:100%;max-width:460px;overflow:hidden;">
            <div style="padding:1.25rem 1.5rem;font-weight:700;font-size:1.1rem;border-bottom:1px solid color-mix(in oklch,currentColor 10%,transparent);display:flex;justify-content:space-between;align-items:center;">
                <span>Cambiar Plan del Servicio</span>
                <button class="btn btn-ghost btn-xs btn-circle" onclick={() => { showPlanModal = false; }}>✕</button>
            </div>
            <div style="padding:1.5rem;display:flex;flex-direction:column;gap:1rem;">
                {#if planModalService}
                    <p style="font-size:0.85rem;opacity:0.7;">
                        Servicio: <code>{planModalService.pppoe_username || planModalService.ip_address}</code>
                        · Router: <code>{planModalService.router_host}</code>
                    </p>
                {/if}
                {#if planModalLoading}
                    <div style="text-align:center;padding:1.5rem;"><span class="loading loading-spinner loading-md"></span></div>
                {:else}
                    <div>
                        <label class="label" style="font-size:0.85rem;">Nuevo Plan</label>
                        <select bind:value={selectedPlanId} class="select select-bordered w-full">
                            <option value="">Selecciona un plan...</option>
                            {#each availablePlans as plan (plan.id)}
                                <option value={String(plan.id)}>{plan.name} — ${plan.price ?? '0.00'} ({plan.max_limit ?? 'N/A'})</option>
                            {/each}
                        </select>
                        {#if availablePlans.length === 0}
                            <p style="font-size:0.8rem;opacity:0.5;margin-top:0.5rem;">No hay planes disponibles para este tipo de servicio.</p>
                        {/if}
                    </div>
                    {#if planModalError}
                        <div class="alert alert-error p-2 text-sm"><span>{planModalError}</span></div>
                    {/if}
                    <div style="display:flex;justify-content:flex-end;gap:0.75rem;padding-top:0.5rem;">
                        <button class="btn btn-ghost btn-sm" onclick={() => { showPlanModal = false; }}>Cancelar</button>
                        <button class="btn btn-primary btn-sm" onclick={handlePlanChange} disabled={!selectedPlanId || planModalLoading}>
                            {#if planModalLoading}<span class="loading loading-spinner loading-xs"></span>{/if}
                            Cambiar Plan
                        </button>
                    </div>
                {/if}
            </div>
        </div>
    </div>
{/if}

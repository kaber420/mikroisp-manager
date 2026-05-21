<script lang="ts">
    import { goto } from '$app/navigation';
    import type { PageData } from './$types';
    import type { ClientService, PaymentCreate } from '$lib/types/client';
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
    import type { User } from '$lib/types/user';

    import ClienteInfoTab      from '$lib/components/clientes/ClienteInfoTab.svelte';
    import ClienteServiciosTab from '$lib/components/clientes/ClienteServiciosTab.svelte';
    import ClientePagosTab     from '$lib/components/clientes/ClientePagosTab.svelte';
    import ClienteAccesoTab    from '$lib/components/clientes/ClienteAccesoTab.svelte';
    import ClientePlanModal    from '$lib/components/clientes/ClientePlanModal.svelte';
    import ClienteAccesoModal  from '$lib/components/clientes/ClienteAccesoModal.svelte';

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
    let payments = $state<any[]>([]);
    let paymentsLoading = $state(false);
    let paymentError = $state('');
    let paymentSuccess = $state('');
    let submittingPayment = $state(false);

    // --- Plan change modal state ---
    let showPlanModal = $state(false);
    let planModalService = $state<ClientService | null>(null);
    let availablePlans = $state<any[]>([]);
    let planModalLoading = $state(false);
    let planModalError = $state('');

    // --- Access tab state ---
    let clientUser = $state<User | null>(null);
    let accessLoading = $state(false);
    let accessError = $state('');
    let showAccessModal = $state(false);
    let creatingAccess = $state(false);

    // --- Helpers ---
    function statusLabel(status: string): string {
        const map: Record<string, string> = { active: 'Activo', suspended: 'Suspendido', inactive: 'Inactivo' };
        return map[status] ?? status;
    }
    function statusBadgeClass(status: string): string {
        if (status === 'active') return 'badge-success';
        if (status === 'suspended') return 'badge-warning';
        return 'badge-neutral';
    }

    // --- Load services ---
    async function loadServices() {
        servicesLoading = true; servicesError = '';
        try {
            services = await getClientServices(client.id);
            for (const svc of services) loadLiveStatus(svc);
        } catch (e: any) {
            servicesError = e?.response?.data?.detail ?? e?.message ?? 'Error al cargar servicios';
        } finally { servicesLoading = false; }
    }

    async function loadLiveStatus(svc: ClientService) {
        liveStatusLoading = { ...liveStatusLoading, [svc.id]: true };
        try {
            if (svc.service_type === 'pppoe' && svc.pppoe_username) {
                const secrets = await getPPPoESecrets(svc.router_host, svc.pppoe_username);
                const activeConns = await getPPPoEActive(svc.router_host, svc.pppoe_username);
                const secret = secrets?.[0];
                liveStatus = { ...liveStatus, [svc.id]: {
                    found: !!secret,
                    account_status: secret ? (secret.disabled === 'true' ? 'Suspendido' : 'Activo') : null,
                    is_online: activeConns && activeConns.length > 0,
                    uptime: activeConns?.[0]?.uptime,
                    online_ip: activeConns?.[0]?.address,
                    bytes_in: parseInt(secret?.['bytes-in'] || '0', 10),
                    bytes_out: parseInt(secret?.['bytes-out'] || '0', 10),
                    profile: secret?.profile,
                }};
            } else if (svc.service_type === 'simple_queue' && svc.ip_address) {
                const queueData = await getQueueStats(svc.router_host, svc.ip_address);
                const [bytesUp, bytesDown] = (queueData?.bytes || '0/0').split('/').map((b: string) => parseInt(b, 10) || 0);
                liveStatus = { ...liveStatus, [svc.id]: {
                    found: !!(queueData && queueData.status !== 'not_found'),
                    name: queueData?.name, target: queueData?.target,
                    max_limit: queueData?.['max-limit'], bytes_up: bytesUp, bytes_down: bytesDown,
                }};
            }
        } catch {
            liveStatus = { ...liveStatus, [svc.id]: { error: true } };
        } finally {
            liveStatusLoading = { ...liveStatusLoading, [svc.id]: false };
        }
    }

    // --- Service actions ---
    async function handleSync(svc: ClientService) {
        if (!confirm(`¿Sincronizar servicio "${svc.pppoe_username || svc.ip_address}" al router?`)) return;
        try { await syncServiceToRouter(svc.id); await loadLiveStatus(svc); }
        catch (e: any) { alert('Error al sincronizar: ' + (e?.response?.data?.detail ?? e?.message)); }
    }

    async function handleDeleteService(svc: ClientService) {
        const label = svc.pppoe_username || svc.ip_address || String(svc.id);
        if (!confirm(`¿Eliminar el servicio "${label}"? Esto lo eliminará del router también.`)) return;
        try { await deleteClientService(svc.id); await loadServices(); }
        catch (e: any) { alert('Error al eliminar: ' + (e?.response?.data?.detail ?? e?.message)); }
    }

    // --- Plan modal ---
    async function openPlanModal(svc: ClientService) {
        planModalService = svc; showPlanModal = true;
        planModalLoading = true; planModalError = '';
        try {
            const plans = await getPlansForService(svc.router_host);
            availablePlans = plans.filter((p: any) => p.plan_type === svc.service_type);
        } catch { planModalError = 'No se pudieron cargar los planes.'; }
        finally { planModalLoading = false; }
    }

    async function handlePlanChange(planId: number) {
        if (!planModalService) return;
        planModalLoading = true; planModalError = '';
        try {
            await changeServicePlan(planModalService.id, planId);
            showPlanModal = false; await loadServices();
        } catch (e: any) {
            planModalError = e?.response?.data?.detail ?? e?.message ?? 'Error al cambiar el plan.';
        } finally { planModalLoading = false; }
    }

    // --- Payments ---
    async function loadPayments() {
        paymentsLoading = true; paymentError = '';
        try { payments = await getPaymentHistory(client.id); }
        catch (e: any) { paymentError = e?.response?.data?.detail ?? e?.message ?? 'Error al cargar pagos'; }
        finally { paymentsLoading = false; }
    }

    async function handleRegisterPayment(payload: PaymentCreate) {
        paymentError = ''; paymentSuccess = '';
        submittingPayment = true;
        try {
            await registerPayment(client.id, payload);
            paymentSuccess = '¡Pago registrado y servicio reactivado correctamente!';
            await loadPayments();
        } catch (e: any) {
            paymentError = e?.response?.data?.detail ?? e?.message ?? 'Error al registrar el pago';
        } finally { submittingPayment = false; }
    }

    // --- Access ---
    async function loadAccessInfo() {
        accessLoading = true; accessError = '';
        try {
            const allUsers = await getUsers();
            clientUser = allUsers.find((u: User) => u.client_id === client.id) || null;
        } catch { accessError = 'No se pudo cargar la información de acceso.'; }
        finally { accessLoading = false; }
    }

    async function handleCreateAccess(payload: { username: string; password: string | undefined; telegram_chat_id: string | null }) {
        creatingAccess = true; accessError = '';
        try {
            await generateClientAccess(client.id, {
                username: payload.username,
                email: client.email || `${payload.username}@mikroisp.local`,
                password: payload.password,
                role: 'client',
                client_id: client.id,
                telegram_chat_id: payload.telegram_chat_id,
            });
            showAccessModal = false;
            await loadAccessInfo();
        } catch (e: any) {
            accessError = e?.response?.data?.detail ?? e?.message ?? 'Error al procesar el acceso';
        } finally { creatingAccess = false; }
    }

    // --- Tab switching (lazy load) ---
    function switchTab(tab: 'info' | 'servicios' | 'pagos' | 'acceso') {
        activeTab = tab;
        if (tab === 'servicios' && services.length === 0 && !servicesLoading) loadServices();
        if (tab === 'pagos') {
            if (payments.length === 0 && !paymentsLoading) loadPayments();
            if (services.length === 0 && !servicesLoading) loadServices();
        }
        if (tab === 'acceso' && !clientUser && !accessLoading) loadAccessInfo();
    }

    let billingDay = $derived(services[0]?.billing_day ?? client.billing_day ?? 1);
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
            <button class="tab {activeTab === 'info' ? 'tab-active' : ''}" onclick={() => switchTab('info')}>
                <svg class="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
                Información
            </button>
            <button class="tab {activeTab === 'servicios' ? 'tab-active' : ''}" onclick={() => switchTab('servicios')}>
                <svg class="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.14 0" />
                </svg>
                Servicios · <span class="ml-1 badge badge-sm {client.cpe_count > 0 ? 'badge-info' : 'badge-neutral'}">{client.cpe_count}</span>
            </button>
            <button class="tab {activeTab === 'pagos' ? 'tab-active' : ''}" onclick={() => switchTab('pagos')}>
                <svg class="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2z" />
                </svg>
                Facturación
            </button>
            <button class="tab {activeTab === 'acceso' ? 'tab-active' : ''}" onclick={() => switchTab('acceso')}>
                <svg class="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                </svg>
                Acceso Portal
            </button>
        </div>
    </div>

    <!-- ── TAB CONTENT ──────────────────────────────────────────────────── -->
    {#if activeTab === 'info'}
        <ClienteInfoTab {client} />
    {/if}

    {#if activeTab === 'servicios'}
        <ClienteServiciosTab
            {services} {servicesLoading} {servicesError}
            {liveStatus} {liveStatusLoading}
            onsync={handleSync}
            ondelete={handleDeleteService}
            onopenplan={openPlanModal}
        />
    {/if}

    {#if activeTab === 'pagos'}
        <ClientePagosTab
            {services} {payments} {paymentsLoading}
            {paymentError} {paymentSuccess} {submittingPayment}
            {billingDay}
            onregister={handleRegisterPayment}
        />
    {/if}

    {#if activeTab === 'acceso'}
        <ClienteAccesoTab
            {clientUser} {accessLoading}
            onopenmodal={() => (showAccessModal = true)}
        />
    {/if}
</div>

<!-- ── MODALS ──────────────────────────────────────────────────────────── -->
<ClientePlanModal
    open={showPlanModal}
    service={planModalService}
    {availablePlans}
    loading={planModalLoading}
    error={planModalError}
    onconfirm={handlePlanChange}
    onclose={() => (showPlanModal = false)}
/>

<ClienteAccesoModal
    open={showAccessModal}
    {clientUser}
    clientEmail={client.email ?? ''}
    clientName={client.name}
    clientTelegram={client.telegram_contact ?? ''}
    {creatingAccess}
    {accessError}
    onsubmit={handleCreateAccess}
    onclose={() => (showAccessModal = false)}
/>

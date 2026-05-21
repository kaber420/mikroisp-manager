<script lang="ts">
    import type { PageData } from "./$types";
    import TopMetricsCard from "$lib/components/dashboard/TopMetricsCard.svelte";
    import MobileSetupModal from "$lib/components/dashboard/MobileSetupModal.svelte";

    // Subcomponentes refactorizados
    import CriticalInfraGrid from "$lib/components/dashboard/CriticalInfraGrid.svelte";
    import TicketsFeedCard from "$lib/components/dashboard/TicketsFeedCard.svelte";
    import EventsLogCard from "$lib/components/dashboard/EventsLogCard.svelte";

    let { data }: { data: PageData } = $props();
    let showMobileModal = $state(false);
</script>

<div class="space-y-6 pb-12">
    <!-- ── HEADER ─────────────────────────────────────────────────────────── -->
    <div
        class="glass-card-flat"
        style="border-radius:1rem;display:flex;flex-direction:column;overflow:hidden;"
    >
        <div
            style="padding:1.25rem 1.5rem;display:flex;flex-direction:column;gap:0.75rem;"
        >
            <div
                style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:0.75rem;"
            >
                <div>
                    <h1 style="margin:0;font-size:1.5rem;font-weight:800;">
                        Dashboard
                    </h1>
                </div>
                <div
                    style="display:flex;align-items:center;gap:0.75rem;flex-wrap:wrap;"
                >
                    <!-- Unified Setup Button -->
                    <button 
                        onclick={() => showMobileModal = true}
                        class="btn btn-sm bg-base-100 hover:bg-base-200 border-base-content/10 rounded-xl gap-2 shadow-sm normal-case flex items-center"
                        title="Configurar App Móvil y Certificado CA"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="opacity-70"><rect width="5" height="5" x="3" y="3" rx="1"/><rect width="5" height="5" x="16" y="3" rx="1"/><rect width="5" height="5" x="3" y="16" rx="1"/><path d="M21 16h-3a2 2 0 0 0-2 2v3"/><path d="M21 21v.01"/><path d="M12 7v3a2 2 0 0 1-2 2H7"/><path d="M3 12h.01"/><path d="M12 3h.01"/><path d="M12 16v.01"/><path d="M16 12h1"/><path d="M21 12v.01"/><path d="M12 21v.01"/></svg>
                        <span class="font-bold tracking-tight">Certificado</span>
                    </button>
                </div>
            </div>
        </div>
    </div>

    <!-- ==========================================
         FILA 1: TOP CARDS (Critical Infrastructure)
         ========================================== -->
    <CriticalInfraGrid stats={data.stats} />

    <!-- ==========================================
         FILA 2: TICKETS (Feed) + TIMELINE DE RED
         ========================================== -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- === TICKETS FEED === -->
        <TicketsFeedCard ticketStats={data.stats.tickets} recentTickets={data.recentTickets} />

        <!-- === TOPS INTERACTIVOS (Metrics Carousel) === -->
        <TopMetricsCard {data} />
    </div>

    <!-- ==========================================
         FILA 3: Placeholder Tráfico Core (PENDIENTE BACKEND) 
         ========================================== -->
    <div class="glass-card p-6 relative overflow-hidden">
        <div class="flex justify-between items-center mb-2">
            <div>
                <h3 class="font-semibold flex items-center gap-2">
                    📈 Tráfico Global Core
                </h3>
                <p class="text-xs opacity-40 mt-0.5">
                    Descarga / Subida agregado de interfaces WAN primarias.
                </p>
            </div>
            <span
                class="text-[10px] px-2 py-1 rounded bg-amber-500/10 text-amber-500 border border-amber-500/20 font-bold uppercase"
                >Pendiente API</span
            >
        </div>
        <div class="flex items-center justify-center py-12 opacity-20">
            <p class="text-sm text-center">
                Este componente se habilitará cuando el endpoint de tráfico
                histórico esté disponible en el backend.
            </p>
        </div>
    </div>

    <!-- ==========================================
         FILA 4: BITÁCORA DE EVENTOS
         ========================================== -->
    <EventsLogCard routers={data.routersList} />
</div>

<MobileSetupModal bind:show={showMobileModal} />

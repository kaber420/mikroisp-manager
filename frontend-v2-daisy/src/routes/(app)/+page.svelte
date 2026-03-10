<script lang="ts">
    import type { PageData } from "./$types";
    import TopMetricsCard from "$lib/components/dashboard/TopMetricsCard.svelte";
    import { onMount, tick } from "svelte";
    import { securityApi } from "$lib/api";
    import MobileSetupModal from "$lib/components/dashboard/MobileSetupModal.svelte";

    let { data }: { data: PageData } = $props();
    let showMobileModal = $state(false);

    // --- Infraestructura Crítica (Grid Superior - 4 cards) ---
    let infraStats = $derived([
        {
            label: "CPEs",
            value: data.stats.cpes.total_cpes ?? 0,
            active: data.stats.cpes.active ?? 0,
            offline:
                (data.stats.cpes.total_cpes ?? 0) -
                (data.stats.cpes.active ?? 0),
            percent:
                (data.stats.cpes.total_cpes ?? 0) > 0
                    ? Math.round(
                          ((data.stats.cpes.active ?? 0) /
                              (data.stats.cpes.total_cpes ?? 1)) *
                              100,
                      )
                    : 0,
            icon: "📡",
            color: "blue",
        },
        {
            label: "Routers",
            value: data.stats.routers.total_routers ?? 0,
            active: data.stats.routers.online ?? 0,
            offline:
                (data.stats.routers.total_routers ?? 0) -
                (data.stats.routers.online ?? 0),
            percent:
                (data.stats.routers.total_routers ?? 0) > 0
                    ? Math.round(
                          ((data.stats.routers.online ?? 0) /
                              (data.stats.routers.total_routers ?? 1)) *
                              100,
                      )
                    : 0,
            icon: "🔀",
            color: "violet",
        },
        {
            label: "Access Points",
            value: data.stats.aps.total_aps ?? 0,
            active: data.stats.aps.online ?? 0,
            offline:
                (data.stats.aps.total_aps ?? 0) - (data.stats.aps.online ?? 0),
            percent:
                (data.stats.aps.total_aps ?? 0) > 0
                    ? Math.round(
                          ((data.stats.aps.online ?? 0) /
                              (data.stats.aps.total_aps ?? 1)) *
                              100,
                      )
                    : 0,
            icon: "📶",
            color: "sky",
        },
        {
            label: "Switches",
            value: data.stats.switches.total_switches ?? 0,
            active: data.stats.switches.online ?? 0,
            offline:
                (data.stats.switches.total_switches ?? 0) -
                (data.stats.switches.online ?? 0),
            percent:
                (data.stats.switches.total_switches ?? 0) > 0
                    ? Math.round(
                          ((data.stats.switches.online ?? 0) /
                              (data.stats.switches.total_switches ?? 1)) *
                              100,
                      )
                    : 0,
            icon: "🔌",
            color: "emerald",
        },
    ]);

    // --- Tickets Contadores ---
    let tickets = $derived({
        open: data.stats.tickets.open_tickets ?? 0,
        resolved: data.stats.tickets.resolved_tickets ?? 0,
        pending: data.stats.tickets.pending_tickets ?? 0,
        total: data.stats.tickets.total_tickets ?? 0,
    });

    // --- Tickets Recientes (Feed) ---
    let recentTickets = $derived((data.recentTickets ?? []) as any[]);

    // --- Scroller de Tickets ---
    let ticketsFeed: HTMLElement | undefined = $state();
    let canScrollUp = $state(false);
    let canScrollDown = $state(false);

    function handleTicketsScroll() {
        if (!ticketsFeed) return;
        canScrollUp = ticketsFeed.scrollTop > 5;
        // Permite un margen de error de unos pocos píxeles para el cálculo inferior
        canScrollDown =
            ticketsFeed.scrollTop + ticketsFeed.clientHeight <
            ticketsFeed.scrollHeight - 5;
    }

    $effect(() => {
        // En cada cambio de la cantidad de tickets o al renderizar el DOM
        if (recentTickets.length > 0 && ticketsFeed) {
            handleTicketsScroll();
        }
    });

    function scrollTickets(direction: "up" | "down") {
        if (!ticketsFeed) return;
        const scrollAmount = Math.max(ticketsFeed.clientHeight - 60, 200);
        ticketsFeed.scrollBy({
            top: direction === "down" ? scrollAmount : -scrollAmount,
            behavior: "smooth",
        });
    }

    // Clases mapeadas 1:1 desde el mockup
    const colorMap: Record<string, any> = {
        blue: {
            text: "text-blue-400",
            bgLight: "bg-blue-500/10",
            borderLight: "border-blue-500/20",
            glow: "drop-shadow-[0_0_8px_rgba(59,130,246,0.3)]",
            blob: "bg-blue-500/10 group-hover:bg-blue-500/15",
        },
        violet: {
            text: "text-purple-400",
            bgLight: "bg-purple-500/10",
            borderLight: "border-purple-500/20",
            glow: "drop-shadow-[0_0_8px_rgba(168,85,247,0.3)]",
            blob: "bg-purple-500/10 group-hover:bg-purple-500/15",
        },
        sky: {
            text: "text-sky-400",
            bgLight: "bg-sky-500/10",
            borderLight: "border-sky-500/20",
            glow: "drop-shadow-[0_0_8px_rgba(14,165,233,0.3)]",
            blob: "bg-sky-500/10 group-hover:bg-sky-500/15",
        },
        emerald: {
            text: "text-emerald-400",
            bgLight: "bg-emerald-500/10",
            borderLight: "border-emerald-500/20",
            glow: "drop-shadow-[0_0_8px_rgba(16,185,129,0.3)]",
            blob: "bg-emerald-500/10 group-hover:bg-emerald-500/15",
        },
    };

    // --- Helpers para Tickets Feed ---
    const ticketStatusConfig: Record<
        string,
        { label: string; badgeCss: string; iconSvg: string }
    > = {
        open: {
            label: "Abierto",
            badgeCss: "bg-blue-500/15 text-blue-400 border-blue-500/25",
            iconSvg: `<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>`,
        },
        pending: {
            label: "En Proceso",
            badgeCss: "bg-amber-500/15 text-amber-400 border-amber-500/25",
            iconSvg: `<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><polyline points="16 11 18 13 22 9"/>`,
        },
        resolved: {
            label: "Resuelto",
            badgeCss:
                "bg-emerald-500/15 text-emerald-400 border-emerald-500/25",
            iconSvg: `<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>`,
        },
    };

    const priorityColor: Record<string, string> = {
        high: "text-rose-400",
        urgent: "text-rose-400",
        normal: "text-slate-400",
        low: "text-slate-500",
    };

    function formatTimeAgo(dateStr: string): string {
        const date = new Date(dateStr);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);
        if (diffMins < 1) return "Ahora";
        if (diffMins < 60) return `Hace ${diffMins} min`;
        const diffHrs = Math.floor(diffMins / 60);
        if (diffHrs < 24) return `Hace ${diffHrs}h`;
        const diffDays = Math.floor(diffHrs / 24);
        return `Hace ${diffDays}d`;
    }

    // --- Bitácora de Eventos ---
    let events = $state<{
        items: any[];
        page: number;
        pageSize: number;
        totalPages: number;
        total: number;
        hostFilter: string;
        loading: boolean;
    }>({
        items: [],
        page: 1,
        pageSize: 10,
        totalPages: 1,
        total: 0,
        hostFilter: "all",
        loading: false,
    });

    let routerOptions = $derived([
        { value: "all", label: "Todos los Dispositivos" },
        ...(data.routersList?.map((r: any) => ({
            value: r.host,
            label: r.hostname || r.host,
        })) || []),
    ]);

    async function loadEvents() {
        events.loading = true;
        try {
            const url = `/api/stats/events?host=${encodeURIComponent(
                events.hostFilter,
            )}&page=${events.page}&page_size=${events.pageSize}`;
            const res = await fetch(url);
            if (res.ok) {
                const json = await res.json();
                events.items = json.items || [];
                events.totalPages = json.total_pages || 1;
                events.total = json.total || 0;
            }
        } catch (error) {
            console.error("Error loading events:", error);
        } finally {
            events.loading = false;
        }
    }

    function changePage(direction: number) {
        const newPage = events.page + direction;
        if (newPage > 0 && newPage <= events.totalPages) {
            events.page = newPage;
            loadEvents();
        }
    }

    function changePageSize(e: Event) {
        const target = e.target as HTMLSelectElement;
        events.pageSize = parseInt(target.value);
        events.page = 1;
        loadEvents();
    }

    function changeFilter(e: Event) {
        const target = e.target as HTMLSelectElement;
        events.hostFilter = target.value;
        events.page = 1;
        loadEvents();
    }

    function formatEventDate(timestamp: string) {
        const dateObj = new Date(timestamp + "Z");
        const timeStr = dateObj.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
        });
        const dateStr = dateObj.toLocaleDateString();
        return { timeStr, dateStr };
    }

    function getEventIconAndClass(eventType: string) {
        let icon = "❓";
        let colorClass = "text-info bg-info/10 border-info/20"; // Info en daisyUI

        if (eventType === "danger") {
            icon = "❌";
            colorClass = "text-error bg-error/10 border-error/20";
        } else if (eventType === "success") {
            icon = "✅";
            colorClass = "text-success bg-success/10 border-success/20";
        }

        return { icon, colorClass };
    }

    let paginationInfo = $derived(
        (() => {
            const start = (events.page - 1) * events.pageSize + 1;
            const end = Math.min(start + events.pageSize - 1, events.total);
            return events.total > 0
                ? `Mostrando ${start}-${end} de ${events.total}`
                : "Sin resultados";
        })(),
    );

    onMount(() => {
        loadEvents();
    });
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
                    <!-- Mobile Setup Button -->
                    <button 
                        onclick={() => showMobileModal = true}
                        class="btn btn-sm bg-base-100 hover:bg-base-200 border-base-content/10 rounded-xl gap-2 shadow-sm normal-case"
                    >
                        <span class="text-base">📱</span>
                        <span class="hidden sm:inline">Móvil</span>
                    </button>

                    <!-- CA Download Button -->
                    <button 
                        onclick={() => window.open(securityApi.getCaCertificateUrl(), "_blank")}
                        class="btn btn-sm bg-base-100 hover:bg-base-200 border-base-content/10 rounded-xl gap-2 shadow-sm normal-case"
                        title="Descargar Certificado CA"
                    >
                        <span class="text-base">🛡️</span>
                        <span class="hidden sm:inline">Certificado CA</span>
                    </button>
                </div>
            </div>
        </div>
    </div>

    <!-- ==========================================
         FILA 1: TOP CARDS (Glassmorphism + Donas Radial)
         ========================================== -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {#each infraStats as stat}
            {@const theme = colorMap[stat.color] || colorMap.blue}
            <div
                class="glass-panel-dona p-5 flex items-center justify-between group relative overflow-hidden"
            >
                <!-- Columna izquierda: Datos -->
                <div class="flex flex-col z-10">
                    <span
                        class="text-[11px] font-bold tracking-[0.15em] text-slate-400 uppercase mb-1"
                    >
                        {stat.label}
                    </span>
                    <span
                        class="text-3xl font-extrabold text-white leading-none"
                    >
                        {stat.value}
                    </span>
                    <!-- Badges de Up / Down -->
                    <div class="mt-3 flex gap-2 text-xs">
                        <span
                            class="bg-emerald-500/10 text-emerald-400 border-emerald-500/20 px-2 py-0.5 rounded border font-medium"
                        >
                            {stat.active}
                        </span>
                        <span
                            class="bg-rose-500/10 text-rose-400 border-rose-500/20 px-2 py-0.5 rounded border font-medium"
                        >
                            {stat.offline}
                        </span>
                    </div>
                </div>

                <!-- Columna derecha: Dona (Radial Progress) -->
                <div
                    class="z-10 {theme.text} radial-progress donut-sm {theme.glow}"
                    style="--value:{stat.percent};"
                    role="progressbar"
                >
                    <span class="text-white text-xs font-bold"
                        >{stat.percent}%</span
                    >
                </div>

                <!-- Fondo mancha -->
                <div
                    class="absolute right-0 top-0 w-32 h-32 blur-[40px] rounded-full pointer-events-none transition-colors {theme.blob}"
                ></div>
            </div>
        {/each}
    </div>

    <!-- ==========================================
         FILA 2: TICKETS (Feed) + TIMELINE DE RED
         ========================================== -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- === TICKETS === -->
        <div class="glass-card p-5 flex flex-col gap-4">
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                    <span class="text-lg">🎫</span>
                    <h3 class="font-semibold">Tickets</h3>
                </div>
                <a
                    href="/tickets"
                    class="text-xs text-blue-500 hover:underline font-medium"
                    data-sveltekit-preload-data="hover">Ver todos →</a
                >
            </div>

            <!-- Métricas Rápidas de Tickets (3 contadores) -->
            <div class="grid grid-cols-3 gap-3">
                <div
                    class="rounded-xl p-3 text-center border border-error/20 bg-error/5"
                >
                    <p class="text-2xl font-bold text-error">{tickets.open}</p>
                    <p class="text-xs text-error/70 mt-1 font-medium">
                        Abiertos
                    </p>
                </div>
                <div
                    class="rounded-xl p-3 text-center border border-warning/20 bg-warning/5"
                >
                    <p class="text-2xl font-bold text-warning">
                        {tickets.pending}
                    </p>
                    <p class="text-xs text-warning/70 mt-1 font-medium">
                        En Proceso
                    </p>
                </div>
                <div
                    class="rounded-xl p-3 text-center border border-success/20 bg-success/5"
                >
                    <p class="text-2xl font-bold text-success">
                        {tickets.resolved}
                    </p>
                    <p class="text-xs text-success/70 mt-1 font-medium">
                        Resueltos
                    </p>
                </div>
            </div>

            <!-- Barra de progreso visual -->
            {#if tickets.total > 0}
                <div>
                    <div class="flex justify-between text-xs opacity-50 mb-1">
                        <span>Resolución</span>
                        <span
                            >{Math.round(
                                (tickets.resolved / tickets.total) * 100,
                            )}%</span
                        >
                    </div>
                    <div class="h-2 bg-base-300 rounded-full overflow-hidden">
                        <div
                            class="h-full bg-success rounded-full transition-all duration-500"
                            style="width: {Math.round(
                                (tickets.resolved / tickets.total) * 100,
                            )}%"
                        ></div>
                    </div>
                </div>
            {/if}

            <!-- Feed de Tickets Recientes -->
            <div class="relative flex-1 flex flex-col min-h-0 pt-2">
                <!-- Gradiente y Flecha Arriba -->
                {#if canScrollUp}
                    <div
                        class="absolute top-0 left-0 right-0 h-6 bg-gradient-to-b from-base-200 to-transparent z-10 pointer-events-none rounded-t-xl"
                    ></div>
                    <button
                        class="absolute top-0 left-1/2 -translate-x-1/2 z-20 hover:scale-110 active:scale-95 transition-transform bg-base-100 hover:bg-base-content/10 border border-base-content/10 text-base-content/70 rounded-full w-8 h-8 flex items-center justify-center shadow-lg cursor-pointer -mt-3"
                        onclick={() => scrollTickets("up")}
                        aria-label="Subir"
                    >
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            width="16"
                            height="16"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            stroke-width="2.5"
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            ><path d="m18 15-6-6-6 6" /></svg
                        >
                    </button>
                {/if}

                <div
                    bind:this={ticketsFeed}
                    onscroll={handleTicketsScroll}
                    class="flex-1 overflow-y-auto max-h-[380px] space-y-2 dashboard-scrollbar px-1 pb-1"
                >
                    {#if recentTickets.length > 0}
                        {#each recentTickets as ticket}
                            {@const cfg =
                                ticketStatusConfig[ticket.status] ||
                                ticketStatusConfig.open}
                            <a
                                href="/tickets"
                                class="block p-3 rounded-xl bg-base-200/50 border border-base-300/50 hover:bg-base-200/80 transition-colors cursor-pointer group hover:-translate-y-0.5"
                                data-sveltekit-preload-data="hover"
                            >
                                <div class="flex justify-between items-start">
                                    <div class="flex gap-3 min-w-0">
                                        <div
                                            class="w-7 h-7 rounded-full {cfg.badgeCss} flex items-center justify-center shrink-0 border"
                                        >
                                            <svg
                                                xmlns="http://www.w3.org/2000/svg"
                                                width="12"
                                                height="12"
                                                viewBox="0 0 24 24"
                                                fill="none"
                                                stroke="currentColor"
                                                stroke-width="2"
                                                stroke-linecap="round"
                                                stroke-linejoin="round"
                                            >
                                                {@html cfg.iconSvg}
                                            </svg>
                                        </div>
                                        <div class="min-w-0">
                                            <h4
                                                class="text-sm font-semibold truncate group-hover:opacity-100 opacity-90 transition-opacity"
                                            >
                                                #{ticket.ticket_id}
                                                <span
                                                    class="font-normal opacity-60 ml-1"
                                                    >{ticket.client_name}</span
                                                >
                                            </h4>
                                            <p
                                                class="text-xs opacity-50 mt-0.5 truncate"
                                            >
                                                {ticket.subject}
                                            </p>
                                            {#if ticket.assigned_tech_username}
                                                <p
                                                    class="text-[10px] bg-base-300 text-base-content/60 inline-flex px-1.5 py-0.5 rounded mt-1.5 font-medium"
                                                >
                                                    @{ticket.assigned_tech_username}
                                                </p>
                                            {/if}
                                        </div>
                                    </div>
                                    <div
                                        class="flex flex-col items-end shrink-0 ml-2"
                                    >
                                        <span
                                            class="text-[9px] px-1.5 py-0.5 rounded font-semibold border {cfg.badgeCss}"
                                            >{cfg.label}</span
                                        >
                                        <span
                                            class="text-[10px] opacity-40 mt-1 whitespace-nowrap"
                                            >{formatTimeAgo(
                                                ticket.updated_at,
                                            )}</span
                                        >
                                    </div>
                                </div>
                            </a>
                        {/each}
                    {:else}
                        <p class="text-sm opacity-30 text-center py-6">
                            No hay tickets recientes
                        </p>
                    {/if}
                </div>

                <!-- Gradiente y Flecha Abajo -->
                {#if canScrollDown}
                    <div
                        class="absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-base-200 to-transparent z-10 pointer-events-none rounded-b-xl"
                    ></div>
                    <button
                        class="absolute bottom-0 left-1/2 -translate-x-1/2 z-20 hover:scale-110 active:scale-95 transition-transform bg-base-100 hover:bg-base-content/10 border border-base-content/10 text-base-content/70 rounded-full w-8 h-8 flex items-center justify-center shadow-lg cursor-pointer -mb-3"
                        onclick={() => scrollTickets("down")}
                        aria-label="Bajar"
                    >
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            width="16"
                            height="16"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            stroke-width="2.5"
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            ><path d="m6 9 6 6 6-6" /></svg
                        >
                    </button>
                {/if}
            </div>
        </div>

        <!-- === TOPS INTERACTIVOS (componente configurable y auto-rotante) === -->
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
    <div class="glass-card p-6 flex flex-col gap-4">
        <!-- Encabezado de la bitácora -->
        <div
            class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-base-content/10 pb-4"
        >
            <h3 class="text-lg font-semibold flex items-center gap-2">
                <span class="text-xl">📜</span>
                Bitácora de Eventos
            </h3>

            <!-- Controles de filtrado -->
            <div class="flex items-center gap-2">
                <label
                    for="log-filter"
                    class="text-xs uppercase font-bold opacity-60"
                    >Filtrar:</label
                >
                <select
                    id="log-filter"
                    class="select select-bordered select-sm w-48 transition-colors bg-base-200/50"
                    value={events.hostFilter}
                    onchange={changeFilter}
                >
                    {#each routerOptions as opt}
                        <option value={opt.value}>{opt.label}</option>
                    {/each}
                </select>
            </div>
        </div>

        <!-- Tabla -->
        <div class="overflow-x-auto">
            <table class="table w-full text-sm text-left">
                <thead>
                    <tr class="border-b border-base-content/10">
                        <th class="font-semibold bg-transparent">Fecha/Hora</th>
                        <th class="font-semibold bg-transparent">Host</th>
                        <th class="font-semibold bg-transparent">Mensaje</th>
                        <th class="font-semibold bg-transparent">Tipo</th>
                    </tr>
                </thead>
                <tbody>
                    {#if events.loading}
                        <tr>
                            <td colspan="4" class="text-center py-8">
                                <span
                                    class="loading loading-spinner text-primary"
                                ></span>
                            </td>
                        </tr>
                    {:else if events.items.length === 0}
                        <tr>
                            <td
                                colspan="4"
                                class="text-center py-8 opacity-40 italic"
                            >
                                No hay eventos registrados.
                            </td>
                        </tr>
                    {:else}
                        {#each events.items as evt (evt.id)}
                            {@const styling = getEventIconAndClass(
                                evt.event_type,
                            )}
                            <tr
                                class="border-b border-base-content/5 hover:bg-base-200/50 transition-colors"
                            >
                                <td class="whitespace-nowrap">
                                    <span class="block font-medium">
                                        {formatEventDate(evt.timestamp).timeStr}
                                    </span>
                                    <span class="text-xs opacity-60">
                                        {formatEventDate(evt.timestamp).dateStr}
                                    </span>
                                </td>
                                <td class="font-medium">{evt.device_host}</td>
                                <td>{evt.message}</td>
                                <td>
                                    <span
                                        class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold border {styling.colorClass}"
                                    >
                                        <span>{styling.icon}</span>
                                        <span
                                            >{evt.event_type.toUpperCase()}</span
                                        >
                                    </span>
                                </td>
                            </tr>
                        {/each}
                    {/if}
                </tbody>
            </table>
        </div>

        <!-- Paginación -->
        <div
            class="flex flex-col sm:flex-row items-center justify-between gap-4 mt-2 pt-4 border-t border-base-content/10"
        >
            <!-- Selector de tamaño de página -->
            <div class="flex items-center gap-2 text-xs opacity-70">
                <span>Mostrar</span>
                <select
                    id="logs-page-size"
                    class="select select-bordered select-xs bg-base-200/50"
                    value={events.pageSize}
                    onchange={changePageSize}
                >
                    <option value="10">10</option>
                    <option value="20">20</option>
                    <option value="50">50</option>
                </select>
                <span>por pág.</span>
            </div>

            <!-- Información (Mostrando 1-10 de 50) -->
            <span class="text-xs opacity-70 font-medium">
                {paginationInfo}
            </span>

            <!-- Botones anterior / siguiente -->
            <div class="join">
                <button
                    class="join-item btn btn-sm bg-base-200/50 hover:bg-base-300 border-base-content/10"
                    disabled={events.page <= 1}
                    onclick={() => changePage(-1)}
                >
                    « Ant
                </button>
                <button
                    class="join-item btn btn-sm bg-base-200/50 hover:bg-base-300 border-base-content/10"
                    disabled={events.page >= events.totalPages}
                    onclick={() => changePage(1)}
                >
                    Sig »
                </button>
            </div>
        </div>
    </div>
</div>

<MobileSetupModal bind:show={showMobileModal} />

<style>
    .dashboard-scrollbar::-webkit-scrollbar {
        width: 3px;
    }
    .dashboard-scrollbar::-webkit-scrollbar-track {
        background: transparent;
    }
    .dashboard-scrollbar::-webkit-scrollbar-thumb {
        background-color: oklch(from var(--color-base-content) l c h / 0.1);
        border-radius: 20px;
    }
</style>

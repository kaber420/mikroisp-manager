<script lang="ts">
    import type { PageData } from "./$types";
    import { onMount, tick } from "svelte";

    let { data }: { data: PageData } = $props();

    // --- Infraestructura Crítica (Grid Superior - 4 cards) ---
    let infraStats = $derived([
        {
            label: "Clientes (CPEs)",
            value: data.stats.cpes.total_cpes ?? 0,
            sub: `${data.stats.cpes.active ?? 0} activos`,
            offline:
                (data.stats.cpes.total_cpes ?? 0) -
                (data.stats.cpes.active ?? 0),
            icon: "📡",
            color: "blue",
        },
        {
            label: "Routers",
            value: data.stats.routers.total_routers ?? 0,
            sub: `${data.stats.routers.online ?? 0} online`,
            offline:
                (data.stats.routers.total_routers ?? 0) -
                (data.stats.routers.online ?? 0),
            icon: "🔀",
            color: "violet",
        },
        {
            label: "Access Points",
            value: data.stats.aps.total_aps ?? 0,
            sub: `${data.stats.aps.online ?? 0} online`,
            offline:
                (data.stats.aps.total_aps ?? 0) - (data.stats.aps.online ?? 0),
            icon: "📶",
            color: "sky",
        },
        {
            label: "Switches",
            value: data.stats.switches.total_switches ?? 0,
            sub: `${data.stats.switches.online ?? 0} online`,
            offline:
                (data.stats.switches.total_switches ?? 0) -
                (data.stats.switches.online ?? 0),
            icon: "🔌",
            color: "emerald",
        },
    ]);

    // --- Tickets ---
    let tickets = $derived({
        open: data.stats.tickets.open_tickets ?? 0,
        resolved: data.stats.tickets.resolved_tickets ?? 0,
        pending: data.stats.tickets.pending_tickets ?? 0,
        total: data.stats.tickets.total_tickets ?? 0,
    });

    // --- Tops Reales (Alimentados desde la API) ---
    type TopItem = { name: string; value: string; badge?: string };

    // Función de ayuda para formatear a Mbps
    function formatBpsToMbps(bps: number | undefined | null): string {
        if (!bps && bps !== 0) return "0 Mbps";
        return (bps / 1000000).toFixed(2) + " Mbps";
    }

    // Función de ayuda para formatear bytes en GB o MB según magnitud
    function formatBytes(bytes: number | undefined | null): string {
        if (!bytes) return "0 B";
        const gb = bytes / 1024 ** 3;
        if (gb >= 1) return gb.toFixed(2) + " GB";
        const mb = bytes / 1024 ** 2;
        if (mb >= 1) return mb.toFixed(2) + " MB";
        return (bytes / 1024).toFixed(1) + " KB";
    }

    let TOPS = $derived<
        Record<
            string,
            { label: string; icon: string; unit: string; items: TopItem[] }
        >
    >({
        signal: {
            label: "Top Señal Débil",
            icon: "📡",
            unit: "dBm",
            items: (data.tops?.signal || []).slice(0, 5).map((cpe: any) => {
                let badge = "";
                if (cpe.signal < -80) badge = "Crítico";
                else if (cpe.signal < -75) badge = "Bajo";

                return {
                    name: `${cpe.cpe_hostname || cpe.cpe_mac} (${cpe.ap_host})`,
                    value: `${cpe.signal} dBm`,
                    badge: badge || undefined,
                };
            }),
        },
        airtime: {
            label: "Top Airtime",
            icon: "📊",
            unit: "%",
            items: (data.tops?.airtime || []).slice(0, 5).map((ap: any) => {
                let badge = "";
                if (ap.airtime_total_usage > 80) badge = "Saturado";
                else if (ap.airtime_total_usage > 60) badge = "Alto";
                else if (ap.airtime_total_usage > 40) badge = "Moderado";

                return {
                    name: `${ap.hostname || ap.host}`,
                    value: `${ap.airtime_total_usage ?? 0}%`,
                    badge: badge || undefined,
                };
            }),
        },
        consumption: {
            label: "Top Consumo (Routers)",
            icon: "🔥",
            unit: "",
            items: (data.tops?.consumption || []).slice(0, 5).map((r: any) => {
                // Formatting RX and TX separately
                const hasBytes = (r.total_bytes || 0) > 0;

                let displayValue = "";
                if (hasBytes) {
                    const rx = formatBytes(r.wan_rx_bytes);
                    const tx = formatBytes(r.wan_tx_bytes);
                    displayValue = `${rx} ↓ · ${tx} ↑`;
                } else {
                    const rxBps = formatBpsToMbps(r.wan_rx_bps);
                    const txBps = formatBpsToMbps(r.wan_tx_bps);
                    displayValue = `${rxBps} ↓ · ${txBps} ↑`;
                }

                // Quitamos el badge porque 100GB no necesariamente es crítico para todos
                let badge = undefined;

                return {
                    name: `${r.hostname || r.host}`,
                    value: displayValue,
                    badge: badge,
                };
            }),
        },
        offline: {
            label: "Top Offline",
            icon: "⚠️",
            unit: "",
            items: (data.tops?.offline || []).slice(0, 5).map((dev: any) => {
                return {
                    name: `${dev.device_type}: ${dev.hostname || dev.host}`,
                    value: dev.last_checked || "Desconocido",
                    badge: dev.device_type === "Router" ? "Crítico" : "Alto",
                };
            }),
        },
    });

    let activeTop = $state("signal");

    const badgeClass: Record<string, string> = {
        Crítico: "bg-red-100 text-red-700",
        Saturado: "bg-red-100 text-red-700",
        Bajo: "bg-amber-100 text-amber-700",
        Alto: "bg-amber-100 text-amber-700",
        Moderado: "bg-yellow-100 text-yellow-700",
    };

    function colorClass(color: string, type: "border" | "text" | "bg") {
        const map: Record<string, Record<string, string>> = {
            blue: {
                border: "border-blue-200",
                text: "text-blue-600",
                bg: "bg-blue-50",
            },
            violet: {
                border: "border-violet-200",
                text: "text-violet-600",
                bg: "bg-violet-50",
            },
            sky: {
                border: "border-sky-200",
                text: "text-sky-600",
                bg: "bg-sky-50",
            },
            emerald: {
                border: "border-emerald-200",
                text: "text-emerald-600",
                bg: "bg-emerald-50",
            },
        };
        return map[color]?.[type] ?? "";
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
        let colorClass = "text-blue-600 bg-blue-100 border border-blue-200";

        if (eventType === "danger") {
            icon = "❌";
            colorClass = "text-red-600 bg-red-100 border border-red-200";
        } else if (eventType === "success") {
            icon = "✅";
            colorClass =
                "text-emerald-600 bg-emerald-100 border border-emerald-200";
        }

        return { icon, colorClass };
    }

    let paginationInfo = $derived(() => {
        const start = (events.page - 1) * events.pageSize + 1;
        const end = Math.min(start + events.pageSize - 1, events.total);
        return events.total > 0
            ? `Mostrando ${start}-${end} de ${events.total}`
            : "Sin resultados";
    });

    onMount(() => {
        loadEvents();
    });
</script>

<div class="space-y-6">
    <!-- Encabezado -->
    <div>
        <h2 class="text-2xl font-bold text-gray-900">Dashboard</h2>
        <p class="text-gray-500 mt-1">Resumen del estado actual del ISP</p>
    </div>

    <!-- Grid de Infraestructura Crítica (4 cards) -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {#each infraStats as stat}
            <div
                class="card p-5 flex flex-col gap-3 hover:-translate-y-1 transition-transform duration-200 border-l-4 {colorClass(
                    stat.color,
                    'border',
                )}"
            >
                <!-- Cabecera de la card -->
                <div class="flex items-center justify-between">
                    <span class="text-sm font-medium text-gray-500"
                        >{stat.label}</span
                    >
                    <span class="text-xl">{stat.icon}</span>
                </div>
                <!-- Número principal -->
                <p class="text-4xl font-bold text-gray-900">{stat.value}</p>
                <!-- Sub-métricas -->
                <div class="flex items-center gap-3 text-sm">
                    <span class="font-medium {colorClass(stat.color, 'text')}"
                        >{stat.sub}</span
                    >
                    {#if stat.offline > 0}
                        <span class="text-red-500 font-medium"
                            >{stat.offline} offline</span
                        >
                    {/if}
                </div>
            </div>
        {/each}
    </div>

    <!-- Área de Mosaicos -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <!-- === MOSAICO 1: Tickets === -->
        <div class="card p-5 flex flex-col gap-4">
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                    <span class="text-lg">🎫</span>
                    <h3 class="font-semibold text-gray-800">
                        Gestión de Tickets
                    </h3>
                </div>
                <a
                    href="/tickets"
                    class="text-xs text-blue-600 hover:underline font-medium"
                    >Ver todos →</a
                >
            </div>

            <!-- Métricas de Tickets -->
            <div class="grid grid-cols-3 gap-3">
                <div
                    class="rounded-xl bg-red-50 border border-red-100 p-3 text-center"
                >
                    <p class="text-2xl font-bold text-red-600">
                        {tickets.open}
                    </p>
                    <p class="text-xs text-red-500 mt-1 font-medium">
                        Abiertos
                    </p>
                </div>
                <div
                    class="rounded-xl bg-amber-50 border border-amber-100 p-3 text-center"
                >
                    <p class="text-2xl font-bold text-amber-600">
                        {tickets.pending}
                    </p>
                    <p class="text-xs text-amber-500 mt-1 font-medium">
                        En Proceso
                    </p>
                </div>
                <div
                    class="rounded-xl bg-emerald-50 border border-emerald-100 p-3 text-center"
                >
                    <p class="text-2xl font-bold text-emerald-600">
                        {tickets.resolved}
                    </p>
                    <p class="text-xs text-emerald-500 mt-1 font-medium">
                        Resueltos
                    </p>
                </div>
            </div>

            <!-- Barra de progreso visual -->
            {#if tickets.total > 0}
                <div>
                    <div
                        class="flex justify-between text-xs text-gray-400 mb-1"
                    >
                        <span>Resolución</span>
                        <span
                            >{Math.round(
                                (tickets.resolved / tickets.total) * 100,
                            )}%</span
                        >
                    </div>
                    <div class="h-2 bg-gray-100 rounded-full overflow-hidden">
                        <div
                            class="h-full bg-emerald-500 rounded-full transition-all duration-500"
                            style="width: {Math.round(
                                (tickets.resolved / tickets.total) * 100,
                            )}%"
                        ></div>
                    </div>
                </div>
            {:else}
                <p class="text-sm text-gray-400 text-center py-2">
                    No hay tickets registrados
                </p>
            {/if}
        </div>

        <!-- === MOSAICO 2: Tops Interactivos === -->
        <div class="card p-5 flex flex-col gap-4">
            <!-- Selector de Tops (Tabs tipo pill) -->
            <div class="flex items-center gap-2 flex-wrap">
                {#each Object.entries(TOPS) as [key, top]}
                    <button
                        onclick={() => (activeTop = key)}
                        class="px-3 py-1.5 rounded-full text-xs font-semibold transition-all duration-150
                            {activeTop === key
                            ? 'bg-gray-900 text-white shadow-sm'
                            : 'bg-gray-100 text-gray-500 hover:bg-gray-200'}"
                    >
                        {top.icon}
                        {top.label}
                    </button>
                {/each}
            </div>

            <!-- Lista del Top activo -->
            <div class="flex flex-col gap-1.5">
                {#each TOPS[activeTop].items as item, i}
                    <div
                        class="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-50 transition-colors group"
                    >
                        <!-- Posición -->
                        <span
                            class="text-xs font-bold text-gray-300 w-4 shrink-0"
                            >#{i + 1}</span
                        >
                        <!-- Nombre -->
                        <span class="text-sm text-gray-700 flex-1 truncate"
                            >{item.name}</span
                        >
                        <!-- Badge opcional -->
                        {#if item.badge}
                            <span
                                class="text-xs px-2 py-0.5 rounded-full font-medium {badgeClass[
                                    item.badge
                                ] ?? 'bg-gray-100 text-gray-600'}"
                            >
                                {item.badge}
                            </span>
                        {/if}
                        <!-- Valor -->
                        <span class="text-sm font-bold text-gray-800 shrink-0"
                            >{item.value}</span
                        >
                    </div>
                {/each}
            </div>

            <!-- Nota de datos mock -->
            <p class="text-xs text-gray-300 text-right font-mono">
                ⚡ datos de muestra · v2-beta
            </p>
        </div>
    </div>

    <!-- === BITÁCORA DE EVENTOS === -->
    <div class="card p-5 flex flex-col gap-4">
        <!-- Encabezado de la bitácora -->
        <div
            class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gray-100 pb-4"
        >
            <h3
                class="text-lg font-semibold text-gray-800 flex items-center gap-2"
            >
                <span class="text-xl">📜</span>
                Bitácora de Eventos
            </h3>

            <!-- Controles de filtrado -->
            <div class="flex items-center gap-2">
                <label
                    for="log-filter"
                    class="text-xs text-gray-500 uppercase font-bold"
                    >Filtrar:</label
                >
                <select
                    id="log-filter"
                    class="select select-bordered select-sm w-48 transition-colors"
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
            <table class="table w-full text-sm text-left text-gray-600">
                <thead>
                    <tr class="text-gray-500 border-b border-gray-100">
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
                                class="text-center py-8 text-gray-400 italic"
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
                                class="border-b border-gray-50 hover:bg-gray-50 transition-colors"
                            >
                                <td class="whitespace-nowrap">
                                    <span
                                        class="block text-gray-800 font-medium"
                                    >
                                        {formatEventDate(evt.timestamp).timeStr}
                                    </span>
                                    <span class="text-xs text-gray-500">
                                        {formatEventDate(evt.timestamp).dateStr}
                                    </span>
                                </td>
                                <td class="text-gray-800 font-medium"
                                    >{evt.device_host}</td
                                >
                                <td>{evt.message}</td>
                                <td>
                                    <span
                                        class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold {styling.colorClass}"
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
            class="flex flex-col sm:flex-row items-center justify-between gap-4 mt-2 pt-4 border-t border-gray-100"
        >
            <!-- Selector de tamaño de página -->
            <div class="flex items-center gap-2 text-xs text-gray-500">
                <span>Mostrar</span>
                <select
                    id="logs-page-size"
                    class="select select-bordered select-xs"
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
            <span class="text-xs text-gray-500 font-medium">
                {paginationInfo}
            </span>

            <!-- Botones anterior / siguiente -->
            <div class="join">
                <button
                    class="join-item btn btn-sm btn-ghost"
                    disabled={events.page <= 1}
                    onclick={() => changePage(-1)}
                >
                    « Ant
                </button>
                <button
                    class="join-item btn btn-sm btn-ghost"
                    disabled={events.page >= events.totalPages}
                    onclick={() => changePage(1)}
                >
                    Sig »
                </button>
            </div>
        </div>
    </div>
</div>

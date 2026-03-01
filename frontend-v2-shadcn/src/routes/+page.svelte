<script lang="ts">
    import type { PageData } from "./$types";
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
</div>

<script lang="ts">
    import type { PageData } from "./$types";
    let { data }: { data: PageData } = $props();

    // Format data from the real API
    // Nombres de campo tal como los devuelve el backend:
    // cpes: { total_cpes, active, offline, disabled }
    // switches: { total_switches, online, offline }
    // tickets: { total_tickets, open_tickets, resolved_tickets, pending_tickets, ... }
    // routers: { total_routers, online, offline }
    // aps: { total_aps, online, offline }
    let stats = $derived([
        {
            label: "Clientes (CPEs)",
            value: data.stats.cpes.total_cpes ?? "0",
            change: `${data.stats.cpes.active ?? 0} activos`,
            positive: true,
        },
        {
            label: "Routers",
            value: data.stats.routers.total_routers ?? "0",
            change: `${data.stats.routers.online ?? 0} online`,
            positive: true,
        },
        {
            label: "Access Points",
            value: data.stats.aps.total_aps ?? "0",
            change: `${data.stats.aps.online ?? 0} online`,
            positive: true,
        },
        {
            label: "Switches",
            value: data.stats.switches.total_switches ?? "0",
            change: `${data.stats.switches.online ?? 0} online`,
            positive: true,
        },
        {
            label: "Tickets Abiertos",
            value: data.stats.tickets.open_tickets ?? "0",
            change: `${data.stats.tickets.resolved_tickets ?? 0} resueltos`,
            positive: true,
        },
    ]);
</script>

<div class="space-y-6">
    <!-- Page Header -->
    <div>
        <h2 class="text-2xl font-bold text-gray-900">Dashboard</h2>
        <p class="text-gray-500 mt-1">Resumen del estado actual del ISP</p>
    </div>

    <!-- Stats Grid -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-6">
        {#each stats as stat}
            <div
                class="card p-6 flex flex-col justify-between hover:-translate-y-1 transition-transform duration-200"
            >
                <p class="text-sm font-medium text-gray-500">{stat.label}</p>
                <div class="flex items-baseline gap-2 mt-2">
                    <p class="text-3xl font-bold text-gray-900">{stat.value}</p>
                    <span
                        class="text-sm font-medium {typeof stat.change ===
                            'string' &&
                        (stat.change.includes('online') ||
                            stat.change.includes('activos'))
                            ? 'text-green-600'
                            : 'text-blue-600'}"
                    >
                        {stat.change}
                    </span>
                </div>
            </div>
        {/each}
    </div>

    <!-- Content Area -->
    <div class="card p-8 mt-8 text-center ring-1 ring-gray-900/5">
        <h3 class="text-lg font-semibold text-gray-900">
            Nueva Interfaz Moderna ⚡
        </h3>
        <p class="text-gray-500 mt-2 max-w-md mx-auto">
            SvelteKit proporciona una experiencia de usuario rápida y fluida sin
            parpadeos. Hemos configurado nuestra paleta, tipografía y utilidad
            base.
        </p>
        <button class="btn-primary mt-6"> Acción Principal </button>
    </div>
</div>

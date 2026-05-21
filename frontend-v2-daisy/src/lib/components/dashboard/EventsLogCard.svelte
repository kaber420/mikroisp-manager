<script lang="ts">
    import { onMount } from "svelte";
    import { request } from "$lib/api";

    let { routers = [] } = $props<{
        routers: Array<{ host: string; hostname?: string }>;
    }>();

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
        ...(routers?.map((r: any) => ({
            value: r.host,
            label: r.hostname || r.host,
        })) || []),
    ]);

    async function loadEvents() {
        events.loading = true;
        try {
            const url = `/stats/events?host=${encodeURIComponent(
                events.hostFilter,
            )}&page=${events.page}&page_size=${events.pageSize}`;
            const json = await request(url);
            events.items = json.items || [];
            events.totalPages = json.total_pages || 1;
            events.total = json.total || 0;
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

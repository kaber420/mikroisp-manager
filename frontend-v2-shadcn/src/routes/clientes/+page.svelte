<script lang="ts">
    import type { PageData } from "./$types";
    import { getClients } from "$lib/api";
    import type { Client } from "$lib/types/client";

    let { data }: { data: PageData } = $props();

    // Estado reactivo de paginación
    let page = $state(data.clients.page);
    let clients = $state(data.clients.items);
    let total = $state(data.clients.total);
    let totalPages = $state(data.clients.total_pages);
    let loading = $state(false);
    let error = $state<string | null>(null);

    const PAGE_SIZE = 10;

    async function loadPage(newPage: number) {
        loading = true;
        error = null;
        try {
            const res = await getClients(newPage, PAGE_SIZE);
            clients = res.items;
            page = res.page;
            total = res.total;
            totalPages = res.total_pages;
        } catch (e: any) {
            error = e?.response?.data?.detail ?? "Error al cargar clientes";
        } finally {
            loading = false;
        }
    }

    function statusLabel(status: string) {
        const map: Record<string, string> = {
            active: "Activo",
            suspended: "Suspendido",
            inactive: "Inactivo",
        };
        return map[status] ?? status;
    }

    function statusClass(status: string) {
        if (status === "active") return "badge-green";
        if (status === "suspended") return "badge-yellow";
        return "badge-gray";
    }
</script>

<div class="space-y-6">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
        <div>
            <h2 class="text-2xl font-bold text-gray-900">
                Gestión de Clientes
            </h2>
            <p class="text-gray-500 mt-1">
                {total} cliente{total !== 1 ? "s" : ""} registrados
            </p>
        </div>
        <button class="btn-primary">+ Nuevo Cliente</button>
    </div>

    <!-- Error State -->
    {#if error}
        <div
            class="card p-4 border border-red-200 bg-red-50 text-red-700 text-sm rounded-lg"
        >
            ⚠️ {error}
        </div>
    {/if}

    <!-- Table Card -->
    <div class="card overflow-hidden">
        <div class="overflow-x-auto">
            <table class="w-full text-sm text-left">
                <thead class="bg-gray-50 border-b border-gray-200">
                    <tr>
                        <th class="px-4 py-3 font-semibold text-gray-600"
                            >Nombre</th
                        >
                        <th class="px-4 py-3 font-semibold text-gray-600"
                            >Dirección</th
                        >
                        <th class="px-4 py-3 font-semibold text-gray-600"
                            >Teléfono</th
                        >
                        <th class="px-4 py-3 font-semibold text-gray-600"
                            >Estado</th
                        >
                        <th
                            class="px-4 py-3 font-semibold text-gray-600 text-center"
                            >CPEs</th
                        >
                        <th class="px-4 py-3 font-semibold text-gray-600"
                            >Alta</th
                        >
                    </tr>
                </thead>
                <tbody class="divide-y divide-gray-100">
                    {#if loading}
                        {#each Array(PAGE_SIZE) as _}
                            <tr class="animate-pulse">
                                <td class="px-4 py-3" colspan="6">
                                    <div
                                        class="h-4 bg-gray-200 rounded w-full"
                                    ></div>
                                </td>
                            </tr>
                        {/each}
                    {:else if clients.length === 0}
                        <tr>
                            <td
                                colspan="6"
                                class="px-4 py-12 text-center text-gray-400"
                            >
                                Sin clientes registrados
                            </td>
                        </tr>
                    {:else}
                        {#each clients as client (client.id)}
                            <tr class="hover:bg-gray-50 transition-colors">
                                <td class="px-4 py-3 font-medium text-gray-900"
                                    >{client.name}</td
                                >
                                <td class="px-4 py-3 text-gray-500"
                                    >{client.address ?? "—"}</td
                                >
                                <td class="px-4 py-3 text-gray-500"
                                    >{client.phone_number ?? "—"}</td
                                >
                                <td class="px-4 py-3">
                                    <span
                                        class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                                        {client.service_status === 'active'
                                            ? 'bg-green-100 text-green-800'
                                            : client.service_status ===
                                                'suspended'
                                              ? 'bg-yellow-100 text-yellow-800'
                                              : 'bg-gray-100 text-gray-600'}"
                                    >
                                        {statusLabel(client.service_status)}
                                    </span>
                                </td>
                                <td
                                    class="px-4 py-3 text-center text-gray-700 font-mono"
                                    >{client.cpe_count}</td
                                >
                                <td class="px-4 py-3 text-gray-400 text-xs">
                                    {new Date(
                                        client.created_at,
                                    ).toLocaleDateString("es-MX")}
                                </td>
                            </tr>
                        {/each}
                    {/if}
                </tbody>
            </table>
        </div>

        <!-- Paginación -->
        {#if totalPages > 1}
            <div
                class="flex items-center justify-between px-4 py-3 border-t border-gray-100 bg-gray-50 text-sm text-gray-600"
            >
                <span>Página {page} de {totalPages}</span>
                <div class="flex gap-2">
                    <button
                        class="px-3 py-1 rounded border border-gray-300 hover:bg-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                        disabled={page <= 1 || loading}
                        onclick={() => loadPage(page - 1)}
                    >
                        ← Anterior
                    </button>
                    <button
                        class="px-3 py-1 rounded border border-gray-300 hover:bg-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                        disabled={page >= totalPages || loading}
                        onclick={() => loadPage(page + 1)}
                    >
                        Siguiente →
                    </button>
                </div>
            </div>
        {/if}
    </div>
</div>

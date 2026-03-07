<script lang="ts">
    import type { PageData } from "./$types";
    import { getClients } from "$lib/api";
    import DataTable from "$lib/components/DataTable.svelte";
    import type { Client } from "$lib/types/client";
    import { goto } from "$app/navigation";

    let { data }: { data: PageData } = $props();

    async function loadClients(page: number, pageSize: number, search: string) {
        const res = await getClients(page, pageSize, search);
        return {
            items: res.items,
            total: res.total,
            total_pages: res.total_pages,
        };
    }

    function statusLabel(status: string) {
        const map: Record<string, string> = {
            active: "Activo",
            suspended: "Suspendido",
            inactive: "Inactivo",
        };
        return map[status] ?? status;
    }

    function statusStyle(status: string) {
        if (status === "active")
            return "background:#dcfce7;color:#166534;border:1px solid #bbf7d0;";
        if (status === "suspended")
            return "background:#fef9c3;color:#854d0e;border:1px solid #fef08a;";
        return "background:#f3f4f6;color:#374151;border:1px solid #e5e7eb;";
    }
</script>

<div style="display:flex;flex-direction:column;gap:1.5rem;">
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
                        Gestión de Clientes
                    </h1>
                    <p
                        style="margin:0.25rem 0 0;font-size:0.85rem;opacity:0.5;"
                    >
                        {data.clients.total} cliente{data.clients.total !== 1
                            ? "s"
                            : ""} registrados
                    </p>
                </div>
                <div
                    style="display:flex;align-items:center;gap:0.75rem;flex-wrap:wrap;"
                >
                    <button class="btn btn-primary btn-sm gap-2">
                        <svg
                            class="w-4 h-4"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                stroke-width="2"
                                d="M12 4v16m8-8H4"
                            />
                        </svg>
                        Nuevo Cliente
                    </button>
                </div>
            </div>
        </div>
    </div>

    <!-- DataTable modo servidor -->
    <DataTable
        loadData={loadClients}
        initialItems={data.clients.items}
        initialTotal={data.clients.total}
        initialPage={data.clients.page}
        initialTotalPages={data.clients.total_pages}
    >
        {#snippet header()}
            <tr>
                <th class="dt-th">Nombre</th>
                <th class="dt-th">Dirección</th>
                <th class="dt-th">Teléfono</th>
                <th class="dt-th">Estado</th>
                <th class="dt-th" style="text-align:center;">CPEs</th>
                <th class="dt-th">Alta</th>
                <th class="dt-th" style="text-align:center;">Acciones</th>
            </tr>
        {/snippet}

        {#snippet row(client: Client)}
            <tr style="cursor:pointer;" onclick={() => goto(`/clientes/${client.id}`)}>
                <td class="dt-td" style="font-weight:500;">
                    <a
                        href="/clientes/{client.id}"
                        onclick={(e) => e.stopPropagation()}
                        style="color:inherit;text-decoration:none;hover:text-decoration:underline;"
                    >{client.name}</a>
                </td>
                <td class="dt-td" style="opacity:0.6;"
                    >{client.address ?? "—"}</td
                >
                <td class="dt-td" style="opacity:0.6;"
                    >{client.phone_number ?? "—"}</td
                >
                <td class="dt-td">
                    <span
                        style="
                        display:inline-block;
                        padding:0.15rem 0.55rem;
                        border-radius:999px;
                        font-size:0.7rem;
                        font-weight:600;
                        {statusStyle(client.service_status)}
                    ">{statusLabel(client.service_status)}</span
                    >
                </td>
                <td
                    class="dt-td"
                    style="text-align:center;font-family:monospace;"
                    >{client.cpe_count}</td
                >
                <td class="dt-td" style="font-size:0.75rem;opacity:0.45;">
                    {new Date(client.created_at).toLocaleDateString("es-MX")}
                </td>
                <td class="dt-td" style="text-align:center;">
                    <a
                        href="/clientes/{client.id}"
                        onclick={(e) => e.stopPropagation()}
                        class="btn btn-xs btn-ghost"
                        title="Ver detalle"
                    >
                        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                        </svg>
                    </a>
                </td>
            </tr>
        {/snippet}
    </DataTable>
</div>

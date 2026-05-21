<script lang="ts">
    import type { PageData } from "./$types";
    import { getTickets } from "$lib/api";
    import DataTable from "$lib/components/DataTable.svelte";
    import TicketsHeader from "$lib/components/tickets/TicketsHeader.svelte";
    import TicketCreateModal from "$lib/components/tickets/TicketCreateModal.svelte";
    import { statusLabel, statusClass, priorityLabel, priorityClass, getDisplayId, fmtDate } from "$lib/components/tickets/ticketHelpers";
    import type { Ticket, TicketStatus, TicketType } from "$lib/types/ticket";

    let { data }: { data: PageData } = $props();

    // ── Filtros ──────────────────────────────────────────────────────────
    let filterType = $state<TicketType | "all">("all");
    let filterStatus = $state<TicketStatus | "todos">("todos");

    // ── Modal de creación ────────────────────────────────────────────────
    let showModal = $state(false);

    // ── Referencia a la tabla dinámica ───────────────────────────────────
    let tableComponent: any = $state();
    function applyFilter() {
        tableComponent?.refresh();
    }

    // ── Carga de datos paginados ─────────────────────────────────────────
    async function loadTickets(page: number, pageSize: number, search: string) {
        const offset = (page - 1) * pageSize;
        const params: Record<string, any> = { limit: pageSize, offset };
        if (filterStatus !== "todos") params.status_filter = filterStatus;
        if (filterType !== "all") params.ticket_type = filterType;
        if (search) params.search = search;
        const res = await getTickets(params);
        return {
            items: res.items,
            total: res.total,
            total_pages: Math.max(1, Math.ceil(res.total / pageSize)),
        };
    }
</script>

<div style="display:flex;flex-direction:column;gap:1.5rem;">
    <!-- Header + Tabs -->
    <TicketsHeader
        total={data.tickets.total}
        {filterType}
        onOpenModal={() => (showModal = true)}
        onFilterChange={(t) => { filterType = t; applyFilter(); }}
    />

    <!-- Tabla dinámica -->
    <DataTable
        bind:this={tableComponent}
        loadData={loadTickets}
        initialItems={data.tickets.items}
        initialTotal={data.tickets.total}
        initialPage={1}
        initialTotalPages={Math.max(1, Math.ceil(data.tickets.total / 10))}
    >
        {#snippet filters()}
            <select
                class="select select-bordered select-sm"
                bind:value={filterStatus}
                onchange={applyFilter}
                style="border-radius:0.5rem;font-size:0.875rem;"
            >
                <option value="todos">Todos los Estados</option>
                <option value="open">Abiertos</option>
                <option value="pending">Pendientes</option>
                <option value="resolved">Resueltos</option>
                <option value="closed">Cerrados</option>
            </select>
        {/snippet}

        {#snippet header()}
            <tr>
                <th class="dt-th">Estado</th>
                <th class="dt-th">Asunto</th>
                <th class="dt-th">Cliente</th>
                <th class="dt-th">Asignado</th>
                <th class="dt-th">Prioridad</th>
                <th class="dt-th">Fecha</th>
                <th class="dt-th" style="text-align:center;width:60px;"></th>
            </tr>
        {/snippet}

        {#snippet row(ticket: Ticket)}
            <tr
                onclick={() => (window.location.href = `/tickets/${ticket.id}`)}
                style="cursor:pointer;"
            >
                <td class="dt-td">
                    <span class="badge badge-sm {statusClass(ticket.status)}">
                        {statusLabel(ticket.status)}
                    </span>
                </td>
                <td class="dt-td">
                    <p style="font-family:monospace;font-size:0.7rem;opacity:0.5;margin:0;">{getDisplayId(ticket)}</p>
                    <p style="font-weight:500;margin:0;">{ticket.subject}</p>
                    <p style="font-size:0.75rem;opacity:0.5;margin:0;max-width:240px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{ticket.description}</p>
                </td>
                <td class="dt-td" style="opacity:0.7;">{ticket.client_name}</td>
                <td class="dt-td">
                    {#if ticket.assigned_tech_username}
                        <span style="font-size:0.8rem;font-weight:500;">{ticket.assigned_tech_username}</span>
                    {:else}
                        <span style="opacity:0.35;font-size:0.8rem;">—</span>
                    {/if}
                </td>
                <td class="dt-td">
                    <span class="badge badge-xs {priorityClass(ticket.priority)}">{priorityLabel(ticket.priority)}</span>
                </td>
                <td class="dt-td" style="font-size:0.75rem;opacity:0.5;">{fmtDate(ticket.created_at)}</td>
                <td class="dt-td" style="text-align:center;">
                    <span style="opacity:0.4;">›</span>
                </td>
            </tr>
        {/snippet}
    </DataTable>
</div>

<!-- Modal de creación -->
<TicketCreateModal
    bind:showModal
    onClose={() => (showModal = false)}
    onCreated={applyFilter}
/>

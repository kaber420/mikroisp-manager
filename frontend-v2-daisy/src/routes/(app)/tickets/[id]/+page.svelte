<script lang="ts">
    import type { PageData } from "./$types";
    import { updateTicketStatus, getTicket } from "$lib/api";
    import type { Ticket, TicketStatus } from "$lib/types/ticket";
    import { statusLabel, statusClass, getDisplayId, fmtDate } from "$lib/components/tickets/ticketHelpers";
    import TicketInfoCard from "$lib/components/tickets/TicketInfoCard.svelte";
    import TicketStatusDropdown from "$lib/components/tickets/TicketStatusDropdown.svelte";
    import TicketChatPanel from "$lib/components/tickets/TicketChatPanel.svelte";

    let { data }: { data: PageData } = $props();

    let ticket = $state<Ticket>(data.ticket);
    let updatingStatus = $state(false);
    let error = $state<string | null>(null);

    async function refreshTicket() {
        try {
            ticket = await getTicket(ticket.id);
        } catch (_) {}
    }

    async function changeStatus(newStatus: TicketStatus) {
        updatingStatus = true;
        error = null;
        try {
            await updateTicketStatus(ticket.id, { status: newStatus });
            await refreshTicket();
        } catch (e: any) {
            error = e?.response?.data?.detail ?? "Error al cambiar el estado.";
        } finally {
            updatingStatus = false;
        }
    }
</script>

<div style="display:flex;flex-direction:column;gap:1.25rem;max-width:900px;margin:0 auto;">
    <!-- Breadcrumb -->
    <div style="display:flex;align-items:center;gap:0.75rem;flex-wrap:wrap;">
        <a href="/tickets" class="btn btn-ghost btn-sm gap-1">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
            </svg>
            Tickets
        </a>
        <span style="opacity:0.3;">/</span>
        <span style="font-family:monospace;font-size:0.85rem;opacity:0.6;">{getDisplayId(ticket)}</span>
        <span class="badge {statusClass(ticket.status)}">{statusLabel(ticket.status)}</span>
    </div>

    <!-- Título -->
    <div>
        <h2 style="font-size:1.25rem;font-weight:700;margin:0;">{ticket.subject}</h2>
        <p style="margin:0.25rem 0 0;font-size:0.82rem;opacity:0.45;">
            {ticket.ticket_type === "installation" ? "📦 Instalación" : "🛠 Soporte"} · Creado {fmtDate(ticket.created_at, true)}
        </p>
    </div>

    <!-- Info card + Dropdown de estado -->
    <div style="display:grid;grid-template-columns:1fr auto;gap:1rem;align-items:start;flex-wrap:wrap;">
        <TicketInfoCard {ticket} />
        <TicketStatusDropdown
            {updatingStatus}
            onChangeStatus={changeStatus}
        />
    </div>

    {#if error}
        <div class="alert alert-error py-2 text-sm">{error}</div>
    {/if}

    <!-- Panel de chat -->
    <TicketChatPanel {ticket} onRefresh={refreshTicket} bind:error />
</div>

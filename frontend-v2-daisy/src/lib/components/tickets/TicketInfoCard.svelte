<script lang="ts">
    import type { Ticket } from "$lib/types/ticket";
    import { priorityClass, priorityLabel, fmtDate } from "./ticketHelpers";

    interface Props {
        ticket: Ticket;
    }

    let { ticket }: Props = $props();
</script>

<div
    class="bg-base-200 rounded-xl p-4"
    style="display:flex;flex-wrap:wrap;gap:1rem;"
>
    <!-- Cliente -->
    <div>
        <p style="font-size:0.7rem;font-weight:700;opacity:0.5;text-transform:uppercase;margin:0;">
            Cliente
        </p>
        <p style="font-size:0.9rem;font-weight:600;margin:0;">{ticket.client_name}</p>
    </div>

    <!-- Técnico -->
    <div>
        <p style="font-size:0.7rem;font-weight:700;opacity:0.5;text-transform:uppercase;margin:0;">
            Técnico
        </p>
        <p style="font-size:0.9rem;margin:0;">
            {#if ticket.assigned_tech_username}
                {ticket.assigned_tech_username}
            {:else}
                <span style="opacity:0.4;">Sin asignar</span>
            {/if}
        </p>
    </div>

    <!-- Prioridad -->
    <div>
        <p style="font-size:0.7rem;font-weight:700;opacity:0.5;text-transform:uppercase;margin:0;">
            Prioridad
        </p>
        <span class="badge badge-sm {priorityClass(ticket.priority)}">{priorityLabel(ticket.priority)}</span>
    </div>

    <!-- Campos de instalación -->
    {#if ticket.ticket_type === "installation"}
        {#if ticket.scheduled_at}
            <div>
                <p style="font-size:0.7rem;font-weight:700;opacity:0.5;text-transform:uppercase;margin:0;">
                    Fecha Prog.
                </p>
                <p style="font-size:0.85rem;margin:0;">{fmtDate(ticket.scheduled_at, true)}</p>
            </div>
        {/if}
        {#if ticket.coordinates}
            <div>
                <p style="font-size:0.7rem;font-weight:700;opacity:0.5;text-transform:uppercase;margin:0;">
                    Ubicación
                </p>
                <a
                    href="https://www.google.com/maps/search/?api=1&query={encodeURIComponent(ticket.coordinates)}"
                    target="_blank"
                    class="link link-primary text-sm"
                >📍 Ver en mapa</a>
            </div>
        {/if}
        {#if ticket.address_notes}
            <div style="flex: 0 0 100%;">
                <p style="font-size:0.7rem;font-weight:700;opacity:0.5;text-transform:uppercase;margin:0;">
                    Notas
                </p>
                <p style="font-size:0.85rem;margin:0;opacity:0.75;">{ticket.address_notes}</p>
            </div>
        {/if}
    {/if}
</div>

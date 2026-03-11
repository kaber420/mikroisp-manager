<script lang="ts">
    import type { PageData } from "./$types";
    import { replyTicket, updateTicketStatus, getTicket } from "$lib/api";
    import type { Ticket, TicketStatus } from "$lib/types/ticket";

    let { data }: { data: PageData } = $props();

    let ticket = $state<Ticket>(data.ticket);
    let replyContent = $state("");
    let sending = $state(false);
    let updatingStatus = $state(false);
    let error = $state<string | null>(null);

    // Scroll al bottom del chat al cargar
    let chatContainer: HTMLDivElement;
    $effect(() => {
        if (chatContainer && ticket.messages) {
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    });

    async function refreshTicket() {
        try {
            ticket = await getTicket(ticket.id);
        } catch (_) {}
    }

    async function sendReply() {
        if (!replyContent.trim()) return;
        sending = true;
        error = null;
        try {
            await replyTicket(ticket.id, { content: replyContent });
            replyContent = "";
            await refreshTicket();
            // Scroll al fondo
            setTimeout(() => {
                if (chatContainer)
                    chatContainer.scrollTop = chatContainer.scrollHeight;
            }, 50);
        } catch (e: any) {
            error =
                e?.response?.data?.detail ?? "Error al enviar la respuesta.";
        } finally {
            sending = false;
        }
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

    function onKeydown(e: KeyboardEvent) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendReply();
        }
    }

    // --- Helpers ---
    function statusLabel(s: string) {
        return (
            {
                open: "Abierto",
                pending: "Pendiente",
                resolved: "Resuelto",
                closed: "Cerrado",
            }[s] ?? s
        );
    }
    function statusClass(s: string) {
        return (
            {
                open: "badge-success",
                pending: "badge-warning",
                resolved: "badge-primary",
                closed: "badge-ghost",
            }[s] ?? "badge-ghost"
        );
    }
    function priorityLabel(p: string) {
        return (
            { urgent: "Urgente", high: "Alta", normal: "Normal", low: "Baja" }[
                p
            ] ?? p
        );
    }
    function priorityClass(p: string) {
        return (
            {
                urgent: "badge-error",
                high: "badge-warning",
                normal: "badge-info",
                low: "badge-ghost",
            }[p] ?? "badge-ghost"
        );
    }
    function getDisplayId(t: Ticket) {
        if (t.ticket_id && t.ticket_id > 0) return "#" + t.ticket_id;
        return "#" + t.id.slice(-6);
    }
    function fmtDate(s: string) {
        if (!s) return "—";
        return new Date(s).toLocaleString("es-MX", {
            dateStyle: "medium",
            timeStyle: "short",
        });
    }
</script>

<div
    style="display:flex;flex-direction:column;gap:1.25rem;max-width:900px;margin:0 auto;"
>
    <!-- Breadcrumb / Header -->
    <div style="display:flex;align-items:center;gap:0.75rem;flex-wrap:wrap;">
        <a href="/tickets" class="btn btn-ghost btn-sm gap-1">
            <svg
                xmlns="http://www.w3.org/2000/svg"
                width="16"
                height="16"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2"
            >
                <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M15 19l-7-7 7-7"
                />
            </svg>
            Tickets
        </a>
        <span style="opacity:0.3;">/</span>
        <span style="font-family:monospace;font-size:0.85rem;opacity:0.6;"
            >{getDisplayId(ticket)}</span
        >
        <span class="badge {statusClass(ticket.status)}"
            >{statusLabel(ticket.status)}</span
        >
    </div>

    <!-- Título -->
    <div>
        <h2 style="font-size:1.25rem;font-weight:700;margin:0;">
            {ticket.subject}
        </h2>
        <p style="margin:0.25rem 0 0;font-size:0.82rem;opacity:0.45;">
            {ticket.ticket_type === "installation"
                ? "📦 Instalación"
                : "🛠 Soporte"} · Creado {fmtDate(ticket.created_at)}
        </p>
    </div>

    <!-- Info card y acciones -->
    <div
        style="display:grid;grid-template-columns:1fr auto;gap:1rem;align-items:start;flex-wrap:wrap;"
    >
        <div
            class="bg-base-200 rounded-xl p-4"
            style="display:flex;flex-wrap:wrap;gap:1rem;"
        >
            <div>
                <p
                    style="font-size:0.7rem;font-weight:700;opacity:0.5;text-transform:uppercase;margin:0;"
                >
                    Cliente
                </p>
                <p style="font-size:0.9rem;font-weight:600;margin:0;">
                    {ticket.client_name}
                </p>
            </div>
            <div>
                <p
                    style="font-size:0.7rem;font-weight:700;opacity:0.5;text-transform:uppercase;margin:0;"
                >
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
            <div>
                <p
                    style="font-size:0.7rem;font-weight:700;opacity:0.5;text-transform:uppercase;margin:0;"
                >
                    Prioridad
                </p>
                <span class="badge badge-sm {priorityClass(ticket.priority)}"
                    >{priorityLabel(ticket.priority)}</span
                >
            </div>
            {#if ticket.ticket_type === "installation"}
                {#if ticket.scheduled_at}
                    <div>
                        <p
                            style="font-size:0.7rem;font-weight:700;opacity:0.5;text-transform:uppercase;margin:0;"
                        >
                            Fecha Prog.
                        </p>
                        <p style="font-size:0.85rem;margin:0;">
                            {fmtDate(ticket.scheduled_at)}
                        </p>
                    </div>
                {/if}
                {#if ticket.coordinates}
                    <div>
                        <p
                            style="font-size:0.7rem;font-weight:700;opacity:0.5;text-transform:uppercase;margin:0;"
                        >
                            Ubicación
                        </p>
                        <a
                            href="https://www.google.com/maps/search/?api=1&query={encodeURIComponent(
                                ticket.coordinates,
                            )}"
                            target="_blank"
                            class="link link-primary text-sm">📍 Ver en mapa</a
                        >
                    </div>
                {/if}
                {#if ticket.address_notes}
                    <div style="flex: 0 0 100%;">
                        <p
                            style="font-size:0.7rem;font-weight:700;opacity:0.5;text-transform:uppercase;margin:0;"
                        >
                            Notas
                        </p>
                        <p style="font-size:0.85rem;margin:0;opacity:0.75;">
                            {ticket.address_notes}
                        </p>
                    </div>
                {/if}
            {/if}
        </div>

        <!-- Dropdown de cambio de estado -->
        <div class="dropdown dropdown-end">
            <div
                tabindex="0"
                role="button"
                class="btn btn-sm btn-ghost border border-base-300"
                class:loading={updatingStatus}
            >
                {updatingStatus ? "" : "Cambiar estado"}
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="14"
                    height="14"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    stroke-width="2"
                    ><path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M19 9l-7 7-7-7"
                    /></svg
                >
            </div>
            <ul
                class="dropdown-content z-[50] menu p-2 shadow-xl bg-base-200 rounded-box w-48 border border-base-300"
            >
                <li>
                    <button onclick={() => changeStatus("open")}>
                        <span class="badge badge-success badge-xs"></span> Abierto
                    </button>
                </li>
                <li>
                    <button onclick={() => changeStatus("pending")}>
                        <span class="badge badge-warning badge-xs"></span> Pendiente
                    </button>
                </li>
                <li>
                    <button onclick={() => changeStatus("resolved")}>
                        <span class="badge badge-primary badge-xs"></span> Resuelto
                    </button>
                </li>
                <li class="divider my-0.5"></li>
                <li>
                    <button
                        onclick={() => changeStatus("closed")}
                        class="text-error"
                    >
                        <span class="badge badge-error badge-xs"></span> Cerrado
                    </button>
                </li>
            </ul>
        </div>
    </div>

    {#if error}
        <div class="alert alert-error py-2 text-sm">{error}</div>
    {/if}

    <!-- Área de chat -->
    <div
        class="bg-base-100 border border-base-200 rounded-2xl"
        style="display:flex;flex-direction:column;min-height:420px;max-height:65vh;"
    >
        <!-- Chat header -->
        <div
            class="border-b border-base-200 px-4 py-3"
            style="display:flex;align-items:center;gap:0.5rem;"
        >
            <span style="font-size:0.8rem;font-weight:700;opacity:0.5;"
                >CONVERSACIÓN</span
            >
            <span class="badge badge-ghost badge-xs"
                >{ticket.messages.length} mensajes</span
            >
        </div>

        <!-- Mensajes -->
        <div
            bind:this={chatContainer}
            style="flex:1;overflow-y:auto;padding:1.25rem;display:flex;flex-direction:column;gap:0.875rem;"
        >
            <!-- Descripción inicial como primer mensaje del cliente -->
            <div style="display:flex;justify-content:flex-start;">
                <div
                    style="max-width:75%;background:oklch(from var(--color-base-200) l c h);border-radius:1rem;border-top-left-radius:0.25rem;padding:0.875rem 1rem;"
                >
                    <p
                        style="font-size:0.7rem;font-weight:700;opacity:0.5;margin:0 0 0.25rem;"
                    >
                        {ticket.client_name}
                    </p>
                    <p
                        style="font-size:0.875rem;margin:0;white-space:pre-wrap;"
                    >
                        {ticket.description}
                    </p>
                    <p
                        style="font-size:0.68rem;opacity:0.4;margin:0.375rem 0 0;text-align:right;"
                    >
                        {fmtDate(ticket.created_at)}
                    </p>
                </div>
            </div>

            <!-- Mensajes del hilo -->
            {#each ticket.messages as msg (msg.id)}
                {@const isTech = msg.sender_type === "tech"}
                <div
                    style="display:flex;justify-content:{isTech
                        ? 'flex-end'
                        : 'flex-start'};"
                >
                    <div
                        style="max-width:75%;padding:0.875rem 1rem;border-radius:1rem;{isTech
                            ? 'border-top-right-radius:0.25rem;background:oklch(from var(--color-primary) l c h / 0.12);border:1px solid oklch(from var(--color-primary) l c h / 0.2);'
                            : 'border-top-left-radius:0.25rem;background:oklch(from var(--color-base-200) l c h);'}"
                    >
                        <p
                            style="font-size:0.7rem;font-weight:700;opacity:0.6;margin:0 0 0.25rem;color:{isTech
                                ? 'var(--color-primary)'
                                : 'inherit'};"
                        >
                            {isTech ? "Técnico" : ticket.client_name}
                        </p>
                        <p
                            style="font-size:0.875rem;margin:0;white-space:pre-wrap;"
                        >
                            {msg.content}
                        </p>
                        {#if msg.media_url}
                            <a
                                href={msg.media_url}
                                target="_blank"
                                class="link link-primary text-xs">📎 Adjunto</a
                            >
                        {/if}
                        <p
                            style="font-size:0.68rem;opacity:0.4;margin:0.375rem 0 0;text-align:{isTech
                                ? 'right'
                                : 'left'};"
                        >
                            {fmtDate(msg.created_at)}
                        </p>
                    </div>
                </div>
            {/each}

            {#if ticket.messages.length === 0}
                <div
                    style="flex:1;display:flex;align-items:center;justify-content:center;opacity:0.3;"
                >
                    <p style="font-size:0.85rem;">Sin mensajes adicionales</p>
                </div>
            {/if}
        </div>

        <!-- Input de respuesta -->
        <div
            class="border-t border-base-200"
            style="padding:0.875rem 1rem;background:oklch(from var(--color-base-200) l c h / 0.3);"
        >
            {#if ticket.status === "closed"}
                <p
                    style="text-align:center;opacity:0.4;font-size:0.85rem;margin:0.25rem 0;"
                >
                    Este ticket está cerrado. Cambia el estado para responder.
                </p>
            {:else}
                <div style="display:flex;gap:0.5rem;align-items:flex-end;">
                    <textarea
                        class="textarea textarea-bordered flex-1 textarea-sm"
                        rows="2"
                        placeholder="Escribe tu respuesta... (Enter para enviar, Shift+Enter para nueva línea)"
                        bind:value={replyContent}
                        onkeydown={onKeydown}
                        disabled={sending}
                        style="resize:none;"
                    ></textarea>
                    <button
                        class="btn btn-primary btn-sm"
                        onclick={sendReply}
                        disabled={sending || !replyContent.trim()}
                        style="align-self:flex-end;height:2.5rem;"
                    >
                        {#if sending}
                            <span class="loading loading-spinner loading-xs"
                            ></span>
                        {:else}
                            <svg
                                xmlns="http://www.w3.org/2000/svg"
                                width="16"
                                height="16"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                                stroke-width="2"
                            >
                                <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"
                                />
                            </svg>
                        {/if}
                    </button>
                </div>
            {/if}
        </div>
    </div>
</div>

<script lang="ts">
    import { replyTicket } from "$lib/api";
    import type { Ticket } from "$lib/types/ticket";
    import { fmtDate } from "./ticketHelpers";

    interface Props {
        ticket: Ticket;
        onRefresh: () => Promise<void>;
        error: string | null;
    }

    let { ticket, onRefresh, error = $bindable() }: Props = $props();

    let replyContent = $state("");
    let sending = $state(false);
    let chatContainer: HTMLDivElement;

    // Scroll al fondo cuando cambian los mensajes
    $effect(() => {
        if (chatContainer && ticket.messages) {
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    });

    async function sendReply() {
        if (!replyContent.trim()) return;
        sending = true;
        error = null;
        try {
            await replyTicket(ticket.id, { content: replyContent });
            replyContent = "";
            await onRefresh();
            setTimeout(() => {
                if (chatContainer) chatContainer.scrollTop = chatContainer.scrollHeight;
            }, 50);
        } catch (e: any) {
            error = e?.response?.data?.detail ?? "Error al enviar la respuesta.";
        } finally {
            sending = false;
        }
    }

    function onKeydown(e: KeyboardEvent) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendReply();
        }
    }
</script>

<div
    class="bg-base-100 border border-base-200 rounded-2xl"
    style="display:flex;flex-direction:column;min-height:420px;max-height:65vh;"
>
    <!-- Chat header -->
    <div
        class="border-b border-base-200 px-4 py-3"
        style="display:flex;align-items:center;gap:0.5rem;"
    >
        <span style="font-size:0.8rem;font-weight:700;opacity:0.5;">CONVERSACIÓN</span>
        <span class="badge badge-ghost badge-xs">{ticket.messages.length} mensajes</span>
    </div>

    <!-- Mensajes -->
    <div
        bind:this={chatContainer}
        style="flex:1;overflow-y:auto;padding:1.25rem;display:flex;flex-direction:column;gap:0.875rem;"
    >
        <!-- Descripción inicial como primer mensaje del cliente -->
        <div style="display:flex;justify-content:flex-start;">
            <div style="max-width:75%;background:oklch(from var(--color-base-200) l c h);border-radius:1rem;border-top-left-radius:0.25rem;padding:0.875rem 1rem;">
                <p style="font-size:0.7rem;font-weight:700;opacity:0.5;margin:0 0 0.25rem;">{ticket.client_name}</p>
                <p style="font-size:0.875rem;margin:0;white-space:pre-wrap;">{ticket.description}</p>
                <p style="font-size:0.68rem;opacity:0.4;margin:0.375rem 0 0;text-align:right;">{fmtDate(ticket.created_at, true)}</p>
            </div>
        </div>

        <!-- Mensajes del hilo -->
        {#each ticket.messages as msg (msg.id)}
            {@const isTech = msg.sender_type === "tech"}
            <div style="display:flex;justify-content:{isTech ? 'flex-end' : 'flex-start'};">
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
                    <p style="font-size:0.875rem;margin:0;white-space:pre-wrap;">{msg.content}</p>
                    {#if msg.media_url}
                        <a href={msg.media_url} target="_blank" class="link link-primary text-xs">📎 Adjunto</a>
                    {/if}
                    <p
                        style="font-size:0.68rem;opacity:0.4;margin:0.375rem 0 0;text-align:{isTech ? 'right' : 'left'};"
                    >
                        {fmtDate(msg.created_at, true)}
                    </p>
                </div>
            </div>
        {/each}

        {#if ticket.messages.length === 0}
            <div style="flex:1;display:flex;align-items:center;justify-content:center;opacity:0.3;">
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
            <p style="text-align:center;opacity:0.4;font-size:0.85rem;margin:0.25rem 0;">
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
                        <span class="loading loading-spinner loading-xs"></span>
                    {:else}
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />
                        </svg>
                    {/if}
                </button>
            </div>
        {/if}
    </div>
</div>

<script lang="ts">
    import { searchClientsForTicket, createTicket } from "$lib/api";
    import type { TicketCreate, TicketType } from "$lib/types/ticket";

    interface Props {
        showModal: boolean;
        onClose: () => void;
        onCreated: () => void;
    }

    let { showModal = $bindable(), onClose, onCreated }: Props = $props();

    // ── Estado del formulario ────────────────────────────────────────────
    const emptyForm: TicketCreate & { client_name_display: string } = {
        client_id: "",
        client_name_display: "",
        subject: "",
        description: "",
        priority: "normal",
        ticket_type: "support",
        scheduled_at: null,
        coordinates: null,
        address_notes: null,
    };

    let form = $state({ ...emptyForm });
    let creating = $state(false);
    let createError = $state<string | null>(null);

    // ── Búsqueda de clientes ─────────────────────────────────────────────
    let clientSearch = $state("");
    let clientResults = $state<{ id: string; name: string }[]>([]);
    let searchingClients = $state(false);
    let clientSearchTimeout: ReturnType<typeof setTimeout>;

    function onClientSearch(e: Event) {
        clientSearch = (e.target as HTMLInputElement).value;
        clearTimeout(clientSearchTimeout);
        if (clientSearch.length < 2) {
            clientResults = [];
            return;
        }
        clientSearchTimeout = setTimeout(async () => {
            searchingClients = true;
            try {
                const res = await searchClientsForTicket(clientSearch);
                clientResults = res.items;
            } finally {
                searchingClients = false;
            }
        }, 300);
    }

    function selectClient(c: { id: string; name: string }) {
        form.client_id = c.id;
        form.client_name_display = c.name;
        clientSearch = c.name;
        clientResults = [];
    }

    // ── Abrir / cerrar ───────────────────────────────────────────────────
    function reset() {
        form = { ...emptyForm };
        clientSearch = "";
        clientResults = [];
        createError = null;
    }

    $effect(() => {
        if (showModal) reset();
    });

    // ── Submit ───────────────────────────────────────────────────────────
    async function submitCreate() {
        if (!form.client_id || !form.subject.trim() || !form.description.trim()) {
            createError =
                "Por favor completa los campos requeridos (cliente, asunto, descripción).";
            return;
        }
        creating = true;
        createError = null;
        try {
            const payload: TicketCreate = {
                client_id: form.client_id,
                subject: form.subject,
                description: form.description,
                priority: form.priority,
                ticket_type: form.ticket_type,
                scheduled_at: form.scheduled_at || null,
                coordinates: form.coordinates || null,
                address_notes: form.address_notes || null,
            };
            await createTicket(payload);
            showModal = false;
            onCreated();
        } catch (e: any) {
            createError =
                e?.response?.data?.detail ?? "Error al crear el ticket.";
        } finally {
            creating = false;
        }
    }
</script>

{#if showModal}
    <!-- Overlay -->
    <div
        role="dialog"
        aria-modal="true"
        style="position:fixed;inset:0;z-index:100;display:flex;align-items:center;justify-content:center;padding:1rem;background:rgba(0,0,0,0.5);backdrop-filter:blur(4px);"
        onclick={(e) => { if (e.target === e.currentTarget) onClose(); }}
        onkeydown={(e) => { if (e.key === "Escape") onClose(); }}
    >
        <div class="bg-base-100 rounded-2xl shadow-2xl border border-base-300 w-full max-w-lg">
            <!-- Header -->
            <div class="flex items-center justify-between p-5 border-b border-base-200">
                <h3 class="text-lg font-bold">Nuevo Ticket</h3>
                <button class="btn btn-ghost btn-sm btn-circle" onclick={onClose}>✕</button>
            </div>

            <!-- Body -->
            <div
                class="p-5"
                style="display:flex;flex-direction:column;gap:1rem;max-height:70vh;overflow-y:auto;"
            >
                {#if createError}
                    <div class="alert alert-error py-2 text-sm">{createError}</div>
                {/if}

                <!-- Búsqueda de cliente -->
                <div style="position:relative;">
                    <label class="label pb-1" for="client-search">
                        <span class="label-text text-xs font-bold uppercase opacity-60">Cliente *</span>
                    </label>
                    <input
                        id="client-search"
                        type="text"
                        class="input input-bordered w-full input-sm"
                        placeholder="Buscar cliente por nombre..."
                        value={clientSearch}
                        oninput={onClientSearch}
                    />
                    {#if searchingClients}
                        <p class="text-xs opacity-50 mt-1">Buscando...</p>
                    {/if}
                    {#if clientResults.length > 0}
                        <div
                            class="bg-base-200 border border-base-300 rounded-xl mt-1 shadow-lg"
                            style="position:absolute;z-index:10;width:100%;max-height:180px;overflow-y:auto;"
                        >
                            {#each clientResults as c}
                                <button
                                    class="w-full text-left px-4 py-2 hover:bg-base-300 text-sm transition-colors"
                                    onclick={() => selectClient(c)}
                                >{c.name}</button>
                            {/each}
                        </div>
                    {/if}
                </div>

                <!-- Tipo y Prioridad -->
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;">
                    <div>
                        <label class="label pb-1" for="ticket-type">
                            <span class="label-text text-xs font-bold uppercase opacity-60">Tipo *</span>
                        </label>
                        <select id="ticket-type" class="select select-bordered select-sm w-full" bind:value={form.ticket_type}>
                            <option value="support">Soporte</option>
                            <option value="installation">Instalación</option>
                        </select>
                    </div>
                    <div>
                        <label class="label pb-1" for="ticket-priority">
                            <span class="label-text text-xs font-bold uppercase opacity-60">Prioridad</span>
                        </label>
                        <select id="ticket-priority" class="select select-bordered select-sm w-full" bind:value={form.priority}>
                            <option value="low">Baja</option>
                            <option value="normal">Normal</option>
                            <option value="high">Alta</option>
                            <option value="urgent">Urgente</option>
                        </select>
                    </div>
                </div>

                <!-- Campos exclusivos de instalación -->
                {#if form.ticket_type === "installation"}
                    <div class="bg-base-200 rounded-xl p-3" style="display:flex;flex-direction:column;gap:0.75rem;">
                        <p class="text-xs font-bold uppercase opacity-60 m-0">Datos de Instalación</p>
                        <div>
                            <label class="label pb-1" for="scheduled-at">
                                <span class="label-text text-xs">Fecha programada</span>
                            </label>
                            <input
                                id="scheduled-at"
                                type="datetime-local"
                                class="input input-bordered input-sm w-full"
                                bind:value={form.scheduled_at}
                            />
                        </div>
                        <div>
                            <label class="label pb-1" for="coordinates">
                                <span class="label-text text-xs">Coordenadas (Lat, Lon)</span>
                            </label>
                            <input
                                id="coordinates"
                                type="text"
                                class="input input-bordered input-sm w-full"
                                placeholder="-20.1234, -98.5678"
                                bind:value={form.coordinates}
                            />
                        </div>
                        <div>
                            <label class="label pb-1" for="address-notes">
                                <span class="label-text text-xs">Notas de acceso</span>
                            </label>
                            <input
                                id="address-notes"
                                type="text"
                                class="input input-bordered input-sm w-full"
                                placeholder="Ej: Portón azul, llamar al llegar"
                                bind:value={form.address_notes}
                            />
                        </div>
                    </div>
                {/if}

                <!-- Asunto -->
                <div>
                    <label class="label pb-1" for="ticket-subject">
                        <span class="label-text text-xs font-bold uppercase opacity-60">Asunto *</span>
                    </label>
                    <input
                        id="ticket-subject"
                        type="text"
                        class="input input-bordered input-sm w-full"
                        placeholder="Resumen breve..."
                        bind:value={form.subject}
                    />
                </div>

                <!-- Descripción -->
                <div>
                    <label class="label pb-1" for="ticket-description">
                        <span class="label-text text-xs font-bold uppercase opacity-60">Descripción *</span>
                    </label>
                    <textarea
                        id="ticket-description"
                        class="textarea textarea-bordered w-full textarea-sm"
                        rows="3"
                        placeholder="Descripción detallada..."
                        bind:value={form.description}
                    ></textarea>
                </div>
            </div>

            <!-- Footer -->
            <div class="flex justify-end gap-2 p-5 border-t border-base-200">
                <button class="btn btn-ghost btn-sm" onclick={onClose}>Cancelar</button>
                <button
                    class="btn btn-primary btn-sm"
                    onclick={submitCreate}
                    disabled={creating}
                >
                    {#if creating}<span class="loading loading-spinner loading-xs"></span>{/if}
                    Crear Ticket
                </button>
            </div>
        </div>
    </div>
{/if}

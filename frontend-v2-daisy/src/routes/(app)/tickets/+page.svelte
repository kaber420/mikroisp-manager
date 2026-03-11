<script lang="ts">
    import type { PageData } from "./$types";
    import { getTickets, createTicket, searchClientsForTicket } from "$lib/api";
    import DataTable from "$lib/components/DataTable.svelte";
    import type {
        Ticket,
        TicketCreate,
        TicketStatus,
        TicketType,
    } from "$lib/types/ticket";

    let { data }: { data: PageData } = $props();

    // --- Estados de filtro ---
    let filterType = $state<TicketType | "all">("all");
    let filterStatus = $state<TicketStatus | "todos">("todos");

    // --- Modal de creación ---
    let showModal = $state(false);
    let creating = $state(false);
    let createError = $state<string | null>(null);
    let clientSearch = $state("");
    let clientResults = $state<{ id: string; name: string }[]>([]);
    let searchingClients = $state(false);

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

    // --- Tabla dinámica ---
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

    // Disparar recarga cuando cambian los filtros
    let tableComponent: any = $state();
    function applyFilter() {
        tableComponent?.refresh();
    }

    // --- Búsqueda de clientes ---
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

    function openModal() {
        form = { ...emptyForm };
        clientSearch = "";
        clientResults = [];
        createError = null;
        showModal = true;
    }

    async function submitCreate() {
        if (
            !form.client_id ||
            !form.subject.trim() ||
            !form.description.trim()
        ) {
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
            applyFilter();
        } catch (e: any) {
            createError =
                e?.response?.data?.detail ?? "Error al crear el ticket.";
        } finally {
            creating = false;
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
    function priorityLabel(p: string) {
        return (
            { urgent: "Urgente", high: "Alta", normal: "Normal", low: "Baja" }[
                p
            ] ?? p
        );
    }
    function getDisplayId(t: Ticket) {
        if (t.ticket_id && t.ticket_id > 0) return "#" + t.ticket_id;
        return "#" + t.id.slice(-6);
    }
    function fmtDate(s: string) {
        return new Date(s).toLocaleDateString("es-MX", {
            year: "numeric",
            month: "short",
            day: "numeric",
        });
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
                        Tickets de Soporte
                    </h1>
                    <p
                        style="margin:0.25rem 0 0;font-size:0.85rem;opacity:0.5;"
                    >
                        {data.tickets.total} ticket{data.tickets.total !== 1
                            ? "s"
                            : ""} registrados
                    </p>
                </div>
                <div
                    style="display:flex;align-items:center;gap:0.75rem;flex-wrap:wrap;"
                >
                    <button
                        class="btn btn-primary btn-sm gap-2"
                        onclick={openModal}
                    >
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
                        Nuevo Ticket
                    </button>
                </div>
            </div>
        </div>
        <!-- Pestañas Integradas (Tipos de Ticket) -->
        <div
            style="background:oklch(from var(--color-base-content) l c h / 0.02);border-top:1px solid oklch(from var(--color-base-content) l c h / 0.08);padding:0 1.5rem;display:flex;gap:1.5rem;"
            role="tablist"
        >
            {#each [["all", "📋 Todos"], ["support", "🛠️ Soporte"], ["installation", "🔧 Instalación"]] as [val, label]}
                <button
                    role="tab"
                    aria-selected={filterType === val}
                    onclick={() => {
                        filterType = val as any;
                        applyFilter();
                    }}
                    style="padding:0.85rem 0;font-size:0.85rem;font-weight:{filterType ===
                    val
                        ? '800'
                        : '600'};color:{filterType === val
                        ? 'oklch(from var(--color-primary) l c h)'
                        : 'inherit'};opacity:{filterType === val
                        ? '1'
                        : '0.5'};border-bottom:3px solid {filterType === val
                        ? 'oklch(from var(--color-primary) l c h)'
                        : 'transparent'};background:none;cursor:pointer;transition:all 0.2s;"
                >
                    {label}
                </button>
            {/each}
        </div>
    </div>

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
                    <p
                        style="font-family:monospace;font-size:0.7rem;opacity:0.5;margin:0;"
                    >
                        {getDisplayId(ticket)}
                    </p>
                    <p style="font-weight:500;margin:0;">
                        {ticket.subject}
                    </p>
                    <p
                        style="font-size:0.75rem;opacity:0.5;margin:0;max-width:240px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"
                    >
                        {ticket.description}
                    </p>
                </td>
                <td class="dt-td" style="opacity:0.7;">{ticket.client_name}</td>
                <td class="dt-td">
                    {#if ticket.assigned_tech_username}
                        <span style="font-size:0.8rem;font-weight:500;"
                            >{ticket.assigned_tech_username}</span
                        >
                    {:else}
                        <span style="opacity:0.35;font-size:0.8rem;">—</span>
                    {/if}
                </td>
                <td class="dt-td">
                    <span
                        class="badge badge-xs {priorityClass(ticket.priority)}"
                    >
                        {priorityLabel(ticket.priority)}
                    </span>
                </td>
                <td class="dt-td" style="font-size:0.75rem;opacity:0.5;"
                    >{fmtDate(ticket.created_at)}</td
                >
                <td class="dt-td" style="text-align:center;">
                    <span style="opacity:0.4;">›</span>
                </td>
            </tr>
        {/snippet}
    </DataTable>
</div>

<!-- Modal crear ticket -->
{#if showModal}
    <div
        style="position:fixed;inset:0;z-index:100;display:flex;align-items:center;justify-content:center;padding:1rem;background:rgba(0,0,0,0.5);backdrop-filter:blur(4px);"
        onclick={(e) => {
            if (e.target === e.currentTarget) showModal = false;
        }}
    >
        <div
            class="bg-base-100 rounded-2xl shadow-2xl border border-base-300 w-full max-w-lg"
        >
            <!-- Header modal -->
            <div
                class="flex items-center justify-between p-5 border-b border-base-200"
            >
                <h3 class="text-lg font-bold">Nuevo Ticket</h3>
                <button
                    class="btn btn-ghost btn-sm btn-circle"
                    onclick={() => (showModal = false)}>✕</button
                >
            </div>

            <!-- Body -->
            <div
                class="p-5"
                style="display:flex;flex-direction:column;gap:1rem;max-height:70vh;overflow-y:auto;"
            >
                {#if createError}
                    <div class="alert alert-error py-2 text-sm">
                        {createError}
                    </div>
                {/if}

                <!-- Búsqueda de cliente -->
                <div style="position:relative;">
                    <label class="label pb-1"
                        ><span
                            class="label-text text-xs font-bold uppercase opacity-60"
                            >Cliente *</span
                        ></label
                    >
                    <input
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
                                    >{c.name}</button
                                >
                            {/each}
                        </div>
                    {/if}
                </div>

                <!-- Tipo y Prioridad -->
                <div
                    style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;"
                >
                    <div>
                        <label class="label pb-1"
                            ><span
                                class="label-text text-xs font-bold uppercase opacity-60"
                                >Tipo *</span
                            ></label
                        >
                        <select
                            class="select select-bordered select-sm w-full"
                            bind:value={form.ticket_type}
                        >
                            <option value="support">Soporte</option>
                            <option value="installation">Instalación</option>
                        </select>
                    </div>
                    <div>
                        <label class="label pb-1"
                            ><span
                                class="label-text text-xs font-bold uppercase opacity-60"
                                >Prioridad</span
                            ></label
                        >
                        <select
                            class="select select-bordered select-sm w-full"
                            bind:value={form.priority}
                        >
                            <option value="low">Baja</option>
                            <option value="normal">Normal</option>
                            <option value="high">Alta</option>
                            <option value="urgent">Urgente</option>
                        </select>
                    </div>
                </div>

                <!-- Campos exclusivos de instalación -->
                {#if form.ticket_type === "installation"}
                    <div
                        class="bg-base-200 rounded-xl p-3"
                        style="display:flex;flex-direction:column;gap:0.75rem;"
                    >
                        <p class="text-xs font-bold uppercase opacity-60 m-0">
                            Datos de Instalación
                        </p>
                        <div>
                            <label class="label pb-1"
                                ><span class="label-text text-xs"
                                    >Fecha programada</span
                                ></label
                            >
                            <input
                                type="datetime-local"
                                class="input input-bordered input-sm w-full"
                                bind:value={form.scheduled_at}
                            />
                        </div>
                        <div>
                            <label class="label pb-1"
                                ><span class="label-text text-xs"
                                    >Coordenadas (Lat, Lon)</span
                                ></label
                            >
                            <input
                                type="text"
                                class="input input-bordered input-sm w-full"
                                placeholder="-20.1234, -98.5678"
                                bind:value={form.coordinates}
                            />
                        </div>
                        <div>
                            <label class="label pb-1"
                                ><span class="label-text text-xs"
                                    >Notas de acceso</span
                                ></label
                            >
                            <input
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
                    <label class="label pb-1"
                        ><span
                            class="label-text text-xs font-bold uppercase opacity-60"
                            >Asunto *</span
                        ></label
                    >
                    <input
                        type="text"
                        class="input input-bordered input-sm w-full"
                        placeholder="Resumen breve..."
                        bind:value={form.subject}
                    />
                </div>

                <!-- Descripción -->
                <div>
                    <label class="label pb-1"
                        ><span
                            class="label-text text-xs font-bold uppercase opacity-60"
                            >Descripción *</span
                        ></label
                    >
                    <textarea
                        class="textarea textarea-bordered w-full textarea-sm"
                        rows="3"
                        placeholder="Descripción detallada..."
                        bind:value={form.description}
                    ></textarea>
                </div>
            </div>

            <!-- Footer -->
            <div class="flex justify-end gap-2 p-5 border-t border-base-200">
                <button
                    class="btn btn-ghost btn-sm"
                    onclick={() => (showModal = false)}>Cancelar</button
                >
                <button
                    class="btn btn-primary btn-sm"
                    onclick={submitCreate}
                    disabled={creating}
                >
                    {#if creating}<span
                            class="loading loading-spinner loading-xs"
                        ></span>{/if}
                    Crear Ticket
                </button>
            </div>
        </div>
    </div>
{/if}

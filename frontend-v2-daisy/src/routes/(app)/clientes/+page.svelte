<script lang="ts">
    import type { PageData } from "./$types";
    import { getClients, createClient, getZonas } from "$lib/api";
    import DataTable from "$lib/components/DataTable.svelte";
    import AdminToolbar from "$lib/components/AdminToolbar.svelte";
    import type { Client, ClientCreate } from "$lib/types/client";
    import type { Zona } from "$lib/types/zona";
    import { goto } from "$app/navigation";
    import { notify } from "$lib/stores/notifications";
    import { onMount } from "svelte";

    let { data }: { data: PageData } = $props();

    // ── Modal Crear ──────────────────────────────────────────────────────
    let showModal = $state(false);
    let modalLoading = $state(false);

    // Campos del formulario
    let fName = $state("");
    let fAddress = $state("");
    let fPhoneNumber = $state("");
    let fWhatsappNumber = $state("");
    let fEmail = $state("");
    let fBillingDay = $state<number | null>(null);
    let fNotes = $state("");
    let fTelegramContact = $state("");
    let fZonaId = $state<number | null>(null);
    
    let zonas = $state<Zona[]>([]);

    async function loadZonas() {
        try {
            zonas = await getZonas();
        } catch (e: any) {
            console.error("Error cargando zonas:", e);
        }
    }

    onMount(() => {
        loadZonas();
    });

    function resetForm() {
        fName = "";
        fAddress = "";
        fPhoneNumber = "";
        fWhatsappNumber = "";
        fEmail = "";
        fBillingDay = null;
        fNotes = "";
        fTelegramContact = "";
        fZonaId = null;
    }

    function openCreate() {
        resetForm();
        showModal = true;
    }

    async function saveClient() {
        if (!fName.trim()) {
            notify.error("El nombre es obligatorio");
            return;
        }

        modalLoading = true;
        try {
            const payload: ClientCreate = {
                name: fName.trim(),
                address: fAddress.trim() || undefined,
                phone_number: fPhoneNumber.trim() || undefined,
                whatsapp_number: fWhatsappNumber.trim() || undefined,
                email: fEmail.trim() || undefined,
                billing_day: fBillingDay || undefined,
                notes: fNotes.trim() || undefined,
                telegram_contact: fTelegramContact.trim() || undefined,
                service_status: "active",
                zona_id: fZonaId || undefined
            };

            await createClient(payload);
            notify.success("Cliente creado exitosamente");
            showModal = false;
            // Refrescar la página para ver el nuevo cliente
            goto("/clientes", { invalidateAll: true });
        } catch (e: any) {
            notify.error(e?.response?.data?.detail ?? "Error al crear el cliente");
        } finally {
            modalLoading = false;
        }
    }

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
    <AdminToolbar
        title="Gestión de Clientes"
        subtitle="{data.clients.total} cliente{data.clients.total !== 1 ? 's' : ''} registrados"
    >
        {#snippet actions()}
            <button class="btn btn-primary btn-sm gap-2" onclick={openCreate}>
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
        {/snippet}
    </AdminToolbar>

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

{#if showModal}
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
    <div
        style="position:fixed;inset:0;z-index:200;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;padding:1rem;overflow-y:auto;"
        role="dialog"
        aria-modal="true"
        tabindex="-1"
        onclick={() => (showModal = false)}
    >
        <div
            style="background:var(--color-base-100);border-radius:1rem;width:100%;max-width:520px;box-shadow:0 25px 50px -12px rgba(0,0,0,0.4);overflow:hidden;margin:auto;"
            role="document"
            onclick={(e) => e.stopPropagation()}
        >
            <!-- Header del modal -->
            <div
                style="padding:1.25rem 1.5rem;border-bottom:1px solid oklch(from var(--color-base-content) l c h / 0.12);display:flex;align-items:center;justify-content:space-between;"
            >
                <h3 style="margin:0;font-size:1.1rem;font-weight:700;">
                    ➕ Nuevo Cliente
                </h3>
                <button
                    class="btn btn-ghost btn-sm btn-circle"
                    onclick={() => (showModal = false)}>✕</button
                >
            </div>

            <!-- Cuerpo del formulario -->
            <form
                onsubmit={(e) => {
                    e.preventDefault();
                    saveClient();
                }}
                style="padding:1.5rem;display:flex;flex-direction:column;gap:1rem;"
            >
                <!-- Nombre -->
                <label class="form-control w-full">
                    <div class="label">
                        <span class="label-text font-semibold">Nombre Completo *</span>
                    </div>
                    <input
                        class="input input-bordered input-sm w-full"
                        type="text"
                        bind:value={fName}
                        placeholder="ej: Juan Pérez"
                        required
                    />
                </label>

                <!-- Dirección -->
                <label class="form-control w-full">
                    <div class="label">
                        <span class="label-text font-semibold">Dirección</span>
                    </div>
                    <input
                        class="input input-bordered input-sm w-full"
                        type="text"
                        bind:value={fAddress}
                        placeholder="ej: Calle Falsa 123"
                    />
                </label>

                <!-- Teléfono + WhatsApp -->
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;">
                    <label class="form-control w-full">
                        <div class="label">
                            <span class="label-text font-semibold">Teléfono</span>
                        </div>
                        <input
                            class="input input-bordered input-sm w-full"
                            type="text"
                            bind:value={fPhoneNumber}
                            placeholder="5512345678"
                        />
                    </label>
                    <label class="form-control w-full">
                        <div class="label">
                            <span class="label-text font-semibold">WhatsApp</span>
                        </div>
                        <input
                            class="input input-bordered input-sm w-full"
                            type="text"
                            bind:value={fWhatsappNumber}
                            placeholder="5512345678"
                        />
                    </label>
                </div>

                <!-- Email + Día Billing -->
                <div style="display:grid;grid-template-columns:1.5fr 1fr;gap:0.75rem;">
                    <label class="form-control w-full">
                        <div class="label">
                            <span class="label-text font-semibold">Email</span>
                        </div>
                        <input
                            class="input input-bordered input-sm w-full"
                            type="email"
                            bind:value={fEmail}
                            placeholder="juan@ejemplo.com"
                        />
                    </label>
                    <label class="form-control w-full">
                        <div class="label">
                            <span class="label-text font-semibold">Día de Pago</span>
                        </div>
                        <input
                            class="input input-bordered input-sm w-full"
                            type="number"
                            min="1"
                            max="31"
                            bind:value={fBillingDay}
                            placeholder="5"
                        />
                    </label>
                </div>

                <!-- Telegram -->
                <label class="form-control w-full">
                    <div class="label">
                        <span class="label-text font-semibold">ID Telegram (opcional)</span>
                    </div>
                    <input
                        class="input input-bordered input-sm w-full"
                        type="text"
                        bind:value={fTelegramContact}
                        placeholder="ej: 123456789"
                    />
                </label>

                <!-- Zona -->
                <label class="form-control w-full">
                    <div class="label">
                        <span class="label-text font-semibold">Zona (Opcional)</span>
                    </div>
                    <select class="select select-bordered select-sm w-full" bind:value={fZonaId}>
                        <option value={null}>-- Sin asignar --</option>
                        {#each zonas as z}
                            <option value={z.id}>{z.nombre}</option>
                        {/each}
                    </select>
                </label>

                <!-- Notas -->
                <label class="form-control w-full">
                    <div class="label">
                        <span class="label-text font-semibold">Notas</span>
                    </div>
                    <textarea
                        class="textarea textarea-bordered textarea-sm w-full h-20"
                        bind:value={fNotes}
                        placeholder="Ocurrencias o datos adicionales..."
                    ></textarea>
                </label>

                <!-- Botones -->
                <div
                    style="display:flex;gap:0.5rem;justify-content:flex-end;padding-top:0.5rem;border-top:1px solid oklch(from var(--color-base-content) l c h / 0.08);"
                >
                    <button
                        type="button"
                        class="btn btn-ghost btn-sm"
                        onclick={() => (showModal = false)}>Cancelar</button
                    >
                    <button
                        type="submit"
                        class="btn btn-primary btn-sm"
                        disabled={modalLoading}
                    >
                        {#if modalLoading}
                            <span class="loading loading-spinner loading-xs"></span>
                        {/if}
                        Guardar Cliente
                    </button>
                </div>
            </form>
        </div>
    </div>
{/if}

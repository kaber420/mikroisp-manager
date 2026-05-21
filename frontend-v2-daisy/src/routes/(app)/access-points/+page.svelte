<script lang="ts">
    import { onMount } from "svelte";
    import { getAPs, getZonas } from "$lib/api";
    import DataTable from "$lib/components/DataTable.svelte";
    import type { AP } from "$lib/types/ap";
    import type { Zona } from "$lib/types/zona";
    import APFormModal from "$lib/components/access-points/APFormModal.svelte";
    import APDeleteModal from "$lib/components/access-points/APDeleteModal.svelte";

    // ── Estado principal ──────────────────────────────────────────────────
    let aps = $state<AP[]>([]);
    let zonas = $state<Zona[]>([]);
    let loading = $state(true);
    let pageError = $state<string | null>(null);

    // ── Control de Modales ────────────────────────────────────────────────
    let showModal = $state(false);
    let modalMode = $state<"create" | "edit">("create");
    let editTarget = $state<AP | null>(null);

    let showDeleteModal = $state(false);
    let deleteTarget = $state<AP | null>(null);

    // ── Estadísticas ──────────────────────────────────────────────────────
    let totalAPs = $derived(aps.length);
    let onlineAPs = $derived(
        aps.filter((a) => a.last_status === "online").length,
    );
    let offlineAPs = $derived(
        aps.filter((a) => a.last_status === "offline").length,
    );
    let percentAPs = $derived(
        totalAPs > 0 ? Math.round((onlineAPs / totalAPs) * 100) : 0
    );

    // ── Filtrado por Fabricante ──────────────────────────────────────────
    let selectedVendor = $state("all");
    let filteredAPs = $derived(
        aps.filter((a) => selectedVendor === "all" || a.vendor === selectedVendor)
    );

    // ── Carga inicial ─────────────────────────────────────────────────────
    async function loadAPs() {
        loading = true;
        pageError = null;
        try {
            const [apsRes, zonasRes] = await Promise.all([
                getAPs(),
                getZonas(),
            ]);
            aps = apsRes;
            zonas = zonasRes;
        } catch (e: any) {
            pageError =
                e?.response?.data?.detail ??
                "Error al cargar los Access Points.";
        } finally {
            loading = false;
        }
    }

    onMount(loadAPs);

    // ── Abrir Modales ──────────────────────────────────────────────────────
    function openCreate() {
        modalMode = "create";
        editTarget = null;
        showModal = true;
    }

    function openEdit(a: AP) {
        modalMode = "edit";
        editTarget = a;
        showModal = true;
    }

    function openDelete(a: AP) {
        deleteTarget = a;
        showDeleteModal = true;
    }

    // ── Helpers de estado ──────────────────────────────────────────────────
    function statusBadge(status: string | null | undefined) {
        if (!status) return { cls: "badge-ghost", label: "Sin datos" };
        if (status === "online")
            return { cls: "badge-success", label: "Online" };
        if (status === "offline")
            return { cls: "badge-error", label: "Offline" };
        return { cls: "badge-warning", label: status };
    }
</script>

<svelte:head>
    <title>Access Points — OmniWISP</title>
</svelte:head>

<!-- ── CONTENEDOR PRINCIPAL ───────────────────────────────────────────── -->
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
                <div style="display:flex;align-items:center;gap:1.25rem;flex-wrap:wrap;">
                    <div>
                        <h1 style="margin:0;font-size:1.5rem;font-weight:800;letter-spacing:-0.025em;">
                            Access Points
                        </h1>
                    </div>
                    
                    {#if !loading}
                        <div style="display:flex;align-items:center;gap:0.6rem;background:oklch(from var(--color-base-content) l c h / 0.03);padding:0.35rem 0.75rem;border-radius:0.75rem;border:1px solid oklch(from var(--color-base-content) l c h / 0.05);">
                            <!-- Total -->
                            <span class="text-xs font-semibold text-slate-400" style="padding-right:0.25rem;">
                                Total: <span class="text-white font-extrabold">{totalAPs}</span>
                            </span>
                            
                            <div style="width:1px;height:12px;background:oklch(from var(--color-base-content) l c h / 0.12);"></div>
                            
                            <!-- Online -->
                            <span class="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-400">
                                <span class="relative flex h-2 w-2">
                                    <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                                    <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                                </span>
                                {onlineAPs} <span class="font-medium text-slate-400">Online</span>
                            </span>
                            
                            <div style="width:1px;height:12px;background:oklch(from var(--color-base-content) l c h / 0.12);"></div>
                            
                            <!-- Offline -->
                            <span class="inline-flex items-center gap-1.5 text-xs font-bold text-rose-400">
                                <span class="h-2 w-2 rounded-full bg-rose-500"></span>
                                {offlineAPs} <span class="font-medium text-slate-400">Offline</span>
                            </span>

                            {#if totalAPs > 0}
                                <div style="width:1px;height:12px;background:oklch(from var(--color-base-content) l c h / 0.12);"></div>
                                <!-- Salud -->
                                <span class="badge badge-sm badge-primary font-bold text-[10px]">
                                    {percentAPs}% OK
                                </span>
                            {/if}
                        </div>
                    {:else}
                        <div style="height:1.75rem;width:120px;border-radius:0.5rem;background:oklch(from var(--color-base-content) l c h / 0.08);animation:pulseSkel 1.5s infinite;"></div>
                    {/if}
                </div>
                <div
                    style="display:flex;align-items:center;gap:0.75rem;flex-wrap:wrap;"
                >
                    <button
                        class="btn btn-primary btn-sm gap-2"
                        onclick={openCreate}
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
                        Nuevo AP
                    </button>
                </div>
            </div>
        </div>
    </div>

    <!-- Error de página -->
    {#if pageError}
        <div class="alert alert-error shadow-sm">
            <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-5 w-5 shrink-0"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
            >
                <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
            </svg>
            <span>{pageError}</span>
            <button
                class="btn btn-xs btn-ghost"
                onclick={() => (pageError = null)}>✕</button
            >
        </div>
    {/if}

    <!-- DataTable -->
    {#if !loading}
        <DataTable items={filteredAPs}>
            {#snippet filters()}
                <select 
                    class="select select-bordered select-xs rounded-lg font-semibold text-xs bg-base-100/50 backdrop-blur-sm"
                    bind:value={selectedVendor}
                >
                    <option value="all">Todos los fabricantes</option>
                    <option value="ubiquiti">Ubiquiti</option>
                    <option value="mikrotik">MikroTik</option>
                </select>
            {/snippet}
            {#snippet header()}
                <tr>
                    <th class="dt-th">Host / IP</th>
                    <th class="dt-th">Nombre (hostname)</th>
                    <th class="dt-th">Modelo</th>
                    <th class="dt-th">Vendor</th>
                    <th class="dt-th">Zona</th>
                    <th class="dt-th" style="text-align:center;">Estado</th>
                    <th class="dt-th" style="text-align:center;">Activo</th>
                    <th class="dt-th" style="text-align:center;">Acciones</th>
                </tr>
            {/snippet}

            {#snippet row(a: AP)}
                {@const badge = statusBadge(a.last_status)}
                <tr>
                    <!-- Host / IP (con link a detalles) -->
                    <td class="dt-td">
                        <a
                            href="/access-points/{a.host}"
                            style="font-family:monospace;font-weight:600;font-size:0.9rem;color:oklch(from var(--color-primary) l c h);text-decoration:none;"
                            class="hover:underline"
                        >
                            {a.host}
                        </a>
                    </td>

                    <!-- Hostname -->
                    <td class="dt-td">
                        {#if a.hostname}
                            <span style="font-weight:500;">{a.hostname}</span>
                        {:else}
                            <span style="opacity:0.35;">—</span>
                        {/if}
                    </td>

                    <!-- Modelo -->
                    <td class="dt-td">
                        {#if a.model}
                            <span style="opacity:0.8;">{a.model}</span>
                        {:else}
                            <span style="opacity:0.35;">—</span>
                        {/if}
                    </td>

                    <!-- Vendor -->
                    <td class="dt-td">
                        {#if a.vendor}
                            <span
                                class="badge badge-sm badge-outline"
                                style="text-transform:uppercase;font-weight:bold;font-size:0.7rem;"
                            >
                                {a.vendor}
                            </span>
                        {:else}
                            <span style="opacity:0.35;">—</span>
                        {/if}
                    </td>

                    <!-- Zona -->
                    <td class="dt-td">
                        {#if a.zona_nombre}
                            <span style="opacity:0.8;">{a.zona_nombre}</span>
                        {:else}
                            <span style="opacity:0.35;">—</span>
                        {/if}
                    </td>

                    <!-- Estado -->
                    <td class="dt-td" style="text-align:center;">
                        <span class="badge badge-sm {badge.cls}"
                            >{badge.label}</span
                        >
                    </td>

                    <!-- Habilitado -->
                    <td class="dt-td" style="text-align:center;">
                        {#if a.is_enabled}
                            <span
                                class="badge badge-sm badge-success badge-outline"
                                >Sí</span
                            >
                        {:else}
                            <span class="badge badge-sm badge-ghost">No</span>
                        {/if}
                    </td>

                    <!-- Acciones -->
                    <td class="dt-td" style="text-align:center;">
                        <div
                            style="display:flex;gap:0.375rem;justify-content:center;"
                        >
                            <a
                                href="/access-points/{a.host}"
                                class="btn btn-xs btn-ghost text-info"
                                title="Ver información del AP"
                            >
                                👁️
                            </a>
                            <button
                                class="btn btn-xs btn-ghost"
                                title="Editar AP"
                                onclick={() => openEdit(a)}>✏️</button
                            >
                            <button
                                class="btn btn-xs btn-ghost text-error"
                                title="Eliminar AP"
                                onclick={() => openDelete(a)}>🗑️</button
                            >
                        </div>
                    </td>
                </tr>
            {/snippet}
        </DataTable>
    {:else}
        <!-- Skeleton -->
        <div class="glass-card-flat" style="padding:2rem;border-radius:1rem;">
            {#each Array(5) as _}
                <div
                    style="height:1.2rem;border-radius:0.3rem;background:oklch(from var(--color-base-content) l c h / 0.08);margin-bottom:0.75rem;animation:pulseSkel 1.5s infinite;"
                ></div>
            {/each}
        </div>
    {/if}
</div>

<!-- Modales modularizados -->
<APFormModal
    bind:show={showModal}
    mode={modalMode}
    target={editTarget}
    {zonas}
    onsave={loadAPs}
/>

<APDeleteModal
    bind:show={showDeleteModal}
    target={deleteTarget}
    onconfirm={loadAPs}
/>

<style>
    @keyframes pulseSkel {
        0%,
        100% {
            opacity: 1;
        }
        50% {
            opacity: 0.4;
        }
    }
</style>

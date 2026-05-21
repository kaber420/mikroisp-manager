<script lang="ts">
    import { onMount } from "svelte";
    import {
        getRouters,
        provisionRouter,
        getZonas,
    } from "$lib/api";
    import DataTable from "$lib/components/DataTable.svelte";
    import ProvisionModal from "$lib/components/ProvisionModal.svelte";
    import type { Router } from "$lib/types/router";
    import type { Zona } from "$lib/types/zona";
    import { notify } from "$lib/stores/notifications";
    import { goto } from "$app/navigation";

    // Subcomponentes refactorizados
    import RouterFormModal from "$lib/components/routers/RouterFormModal.svelte";
    import RouterDeleteModal from "$lib/components/routers/RouterDeleteModal.svelte";
    import RouterPostCreateModal from "$lib/components/routers/RouterPostCreateModal.svelte";

    // ── Estado principal ──────────────────────────────────────────────────
    let routers = $state<Router[]>([]);
    let zonas = $state<Zona[]>([]);
    let loading = $state(true);

    // ── Modal Crear/Editar ────────────────────────────────────────────────
    let showModal = $state(false);
    let modalMode = $state<"create" | "edit">("create");
    let editTarget = $state<Router | null>(null);

    // ── Modal Confirmar Eliminar ─────────────────────────────────────────
    let showDeleteModal = $state(false);
    let deleteTarget = $state<Router | null>(null);

    // ── Aprovisionamiento desde la lista ──────────────────────────────────
    let showProvisionModal = $state(false);
    let provisionTarget = $state<Router | null>(null);
    let isProvisioning = $state(false);

    // ── Modal Post-Creación (sugerir aprovisionar) ────────────────────────
    let showPostCreateModal = $state(false);
    let postCreateRouter = $state<Router | null>(null);

    // ── Estadísticas ──────────────────────────────────────────────────────
    let totalRouters = $derived(routers.length);
    let onlineRouters = $derived(
        routers.filter((r) => r.last_status === "online").length,
    );
    let offlineRouters = $derived(
        routers.filter((r) => r.last_status === "offline").length,
    );
    let percentRouters = $derived(
        totalRouters > 0 ? Math.round((onlineRouters / totalRouters) * 100) : 0
    );

    // ── Carga inicial ─────────────────────────────────────────────────────
    async function loadRouters() {
        loading = true;
        try {
            const [fetchedRouters, fetchedZonas] = await Promise.all([
                getRouters(),
                getZonas()
            ]);
            routers = fetchedRouters;
            zonas = fetchedZonas;
        } catch (e: any) {
            notify.error(e?.response?.data?.detail ?? "Error al cargar datos.");
        } finally {
            loading = false;
        }
    }

    onMount(loadRouters);

    // ── Abrir Modales ──────────────────────────────────────────────────────
    function openCreate() {
        modalMode = "create";
        editTarget = null;
        showModal = true;
    }

    function openEdit(r: Router) {
        modalMode = "edit";
        editTarget = r;
        showModal = true;
    }

    function openDelete(r: Router) {
        deleteTarget = r;
        showDeleteModal = true;
    }

    // ── Callbacks de los modales ───────────────────────────────────────────
    async function handleSave(host: string, isCreated: boolean, vendor: string, isProvisioned: boolean) {
        await loadRouters();
        if (isCreated && vendor === 'mikrotik' && !isProvisioned) {
            const created = routers.find(r => r.host === host);
            if (created) {
                postCreateRouter = created;
                showPostCreateModal = true;
            }
        }
    }

    async function handleDeleteConfirm() {
        notify.success("Router eliminado correctamente.");
        await loadRouters();
    }

    function handleRequestProvision(r: Router) {
        provisionTarget = r;
        showProvisionModal = true;
    }

    function handlePostCreateProvision() {
        if (postCreateRouter) {
            provisionTarget = postCreateRouter;
            showProvisionModal = true;
        }
    }

    // ── Aprovisionamiento desde la lista ──────────────────────────────────
    async function handleProvision(provisionData: any) {
        if (!provisionTarget) return;
        isProvisioning = true;
        try {
            await provisionRouter(
                provisionTarget.host, 
                provisionData.newApiUser, 
                provisionData.newApiPassword, 
                provisionData.method
            );
            notify.success(`Router ${provisionTarget.host} aprovisionado exitosamente.`);
            showProvisionModal = false;
            showPostCreateModal = false;
            showModal = false;
            await loadRouters();
        } catch (e: any) {
            notify.error(e?.response?.data?.detail ?? "Error al aprovisionar.");
        } finally {
            isProvisioning = false;
            provisionTarget = null;
        }
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
    <title>Routers — OmniWISP</title>
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
                            Routers
                        </h1>
                    </div>
                    
                    {#if !loading}
                        <div style="display:flex;align-items:center;gap:0.6rem;background:oklch(from var(--color-base-content) l c h / 0.03);padding:0.35rem 0.75rem;border-radius:0.75rem;border:1px solid oklch(from var(--color-base-content) l c h / 0.05);">
                            <!-- Total -->
                            <span class="text-xs font-semibold text-slate-400" style="padding-right:0.25rem;">
                                Total: <span class="text-white font-extrabold">{totalRouters}</span>
                            </span>
                            
                            <div style="width:1px;height:12px;background:oklch(from var(--color-base-content) l c h / 0.12);"></div>
                            
                            <!-- Online -->
                            <span class="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-400">
                                <span class="relative flex h-2 w-2">
                                    <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                                    <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                                </span>
                                {onlineRouters} <span class="font-medium text-slate-400">Online</span>
                            </span>
                            
                            <div style="width:1px;height:12px;background:oklch(from var(--color-base-content) l c h / 0.12);"></div>
                            
                            <!-- Offline -->
                            <span class="inline-flex items-center gap-1.5 text-xs font-bold text-rose-400">
                                <span class="h-2 w-2 rounded-full bg-rose-500"></span>
                                {offlineRouters} <span class="font-medium text-slate-400">Offline</span>
                            </span>

                            {#if totalRouters > 0}
                                <div style="width:1px;height:12px;background:oklch(from var(--color-base-content) l c h / 0.12);"></div>
                                <!-- Salud -->
                                <span class="badge badge-sm badge-primary font-bold text-[10px]">
                                    {percentRouters}% OK
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
                        Nuevo Router
                    </button>
                </div>
            </div>
        </div>
    </div>

    <!-- DataTable -->
    {#if !loading}
        <DataTable items={routers}>
            {#snippet header()}
                <tr>
                    <th class="dt-th">Host / IP</th>
                    <th class="dt-th">Nombre (hostname)</th>
                    <th class="dt-th">Modelo</th>
                    <th class="dt-th">Zona</th>
                    <th class="dt-th" style="text-align:center;">Estado</th>
                    <th class="dt-th" style="text-align:center;">Acciones</th>
                </tr>
            {/snippet}

            {#snippet row(r: Router)}
                {@const badge = statusBadge(r.last_status)}
                <tr style="cursor: pointer;" onclick={() => goto(`/routers/${r.host}`)}>
                    <!-- Host / IP -->
                    <td class="dt-td">
                        <span
                            style="font-family:monospace;font-weight:600;font-size:0.9rem;"
                            >{r.host}</span
                        >
                    </td>

                    <!-- Hostname -->
                    <td class="dt-td">
                        {#if r.hostname}
                            {r.hostname}
                        {:else}
                            <span style="opacity:0.35;">—</span>
                        {/if}
                    </td>

                    <!-- Modelo / Marca -->
                    <td class="dt-td">
                        {#if r.vendor}
                            <span class="badge badge-sm badge-outline badge-primary" style="margin-right: 0.25rem;">
                                {r.vendor}
                            </span>
                        {/if}
                        {#if r.model}
                            {r.model}
                        {:else}
                            <span style="opacity:0.35;">—</span>
                        {/if}
                    </td>

                    <!-- Zona -->
                    <td class="dt-td">
                        {#if r.zona_nombre}
                            <span class="badge badge-sm badge-outline"
                                >{r.zona_nombre}</span
                            >
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

                    <!-- Acciones -->
                    <td class="dt-td" style="text-align:center;" onclick={(e) => e.stopPropagation()}>
                        <div
                            style="display:flex;gap:0.375rem;justify-content:center;"
                        >
                            <a
                                class="btn btn-xs btn-ghost"
                                href="/routers/{r.host}"
                                title="Ver detalle del router">📊</a
                            >
                            <button
                                class="btn btn-xs btn-ghost"
                                title="Editar router"
                                onclick={() => openEdit(r)}>✏️</button
                            >
                            <button
                                class="btn btn-xs btn-ghost text-error"
                                title="Eliminar router"
                                onclick={() => openDelete(r)}>🗑️</button
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

<!-- Modales Refactorizados -->
<RouterFormModal
    bind:show={showModal}
    mode={modalMode}
    target={editTarget}
    {zonas}
    onsave={handleSave}
    onrequestprovision={handleRequestProvision}
/>

<RouterDeleteModal
    bind:show={showDeleteModal}
    target={deleteTarget}
    onconfirm={handleDeleteConfirm}
/>

<RouterPostCreateModal
    bind:show={showPostCreateModal}
    target={postCreateRouter}
    onprovision={handlePostCreateProvision}
/>

<!-- Reusable ProvisionModal -->
<ProvisionModal
    bind:show={showProvisionModal}
    {isProvisioning}
    onprovision={handleProvision}
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

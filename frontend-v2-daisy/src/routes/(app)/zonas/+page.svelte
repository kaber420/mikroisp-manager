<script lang="ts">
    import { onMount } from "svelte";
    import { getZonas } from "$lib/api";
    import { notify } from "$lib/stores/notifications";
    import DataTable from "$lib/components/DataTable.svelte";
    import AdminToolbar from "$lib/components/AdminToolbar.svelte";
    import type { Zona } from "$lib/types/zona";
    import { user } from "$lib/stores/auth";
    import ZonaFormModal from "./ZonaFormModal.svelte";
    import ZonaDeleteModal from "./ZonaDeleteModal.svelte";

    // ── Estado principal ───────────────────────────────────────────────────
    let zonas = $state<Zona[]>([]);
    let loading = $state(true);

    // ── Permisos ───────────────────────────────────────────────────────────
    let canEdit = $derived($user?.role === "admin" || $user?.role === "tecnico");

    // ── Modal Crear ────────────────────────────────────────────────────────
    let showModal = $state(false);

    // ── Modal Confirmar Eliminar ───────────────────────────────────────────
    let showDeleteModal = $state(false);
    let deleteTarget = $state<Zona | null>(null);

    // ── Carga inicial ──────────────────────────────────────────────────────
    async function loadZonas() {
        loading = true;
        try {
            zonas = await getZonas();
        } catch (e: any) {
            notify.error(e?.response?.data?.detail ?? "Error al cargar las zonas.");
        } finally {
            loading = false;
        }
    }

    onMount(loadZonas);

    function openDelete(z: Zona) {
        deleteTarget = z;
        showDeleteModal = true;
    }
</script>

<!-- ── CONTENEDOR PRINCIPAL ──────────────────────────────────────────── -->
<div style="display:flex;flex-direction:column;gap:1.5rem;">
    <!-- ── HEADER ──────────────────────────────────────────────────────── -->
    <AdminToolbar
        title="Gestión — Zonas de Cobertura"
        subtitle={loading ? "Cargando..." : `${zonas.length} zona${zonas.length !== 1 ? "s" : ""} registrada${zonas.length !== 1 ? "s" : ""}`}
    >
        {#snippet actions()}
            {#if canEdit}
                <button class="btn btn-primary btn-sm" onclick={() => (showModal = true)}>
                    + Nueva Zona
                </button>
            {/if}
        {/snippet}
    </AdminToolbar>

    <!-- DataTable -->
    {#if !loading}
        <DataTable items={zonas}>
            {#snippet header()}
                <tr>
                    <th class="dt-th">Nombre</th>
                    <th class="dt-th" style="text-align:center;">Acciones</th>
                </tr>
            {/snippet}

            {#snippet row(z: Zona)}
                <tr>
                    <td class="dt-td">
                        <a
                            href="/zonas/{z.id}"
                            style="display:flex;align-items:center;gap:0.5rem;font-weight:600;color:inherit;text-decoration:none;"
                            class="hover:underline"
                        >
                            <span style="font-size:1.1rem;opacity:0.65;flex-shrink:0;">🗺️</span>
                            {z.nombre}
                        </a>
                    </td>
                    <td class="dt-td" style="text-align:center;">
                        <div style="display:flex;gap:0.375rem;justify-content:center;align-items:center;">
                            {#if canEdit}
                                <a
                                    class="btn btn-xs btn-ghost"
                                    href="/zonas/{z.id}"
                                    title="Editar zona">✏️</a
                                >
                                <button
                                    class="btn btn-xs btn-ghost text-error"
                                    title="Eliminar zona"
                                    onclick={() => openDelete(z)}>🗑️</button
                                >
                            {:else}
                                <span class="badge badge-ghost badge-sm opacity-60">Solo lectura</span>
                            {/if}
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

<!-- ── MODALES ──────────────────────────────────────────────────────────── -->
<ZonaFormModal bind:show={showModal} onsave={loadZonas} />
<ZonaDeleteModal bind:show={showDeleteModal} target={deleteTarget} onconfirm={loadZonas} />

<style>
    @keyframes pulseSkel {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
    }
</style>

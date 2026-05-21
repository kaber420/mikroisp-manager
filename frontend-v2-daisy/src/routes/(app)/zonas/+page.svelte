<script lang="ts">
    import { onMount } from "svelte";
    import { getZonas } from "$lib/api";
    import { notify } from "$lib/stores/notifications";
    import DataTable from "$lib/components/DataTable.svelte";
    import type { Zona } from "$lib/types/zona";
    import ZonaFormModal from "./ZonaFormModal.svelte";
    import ZonaDeleteModal from "./ZonaDeleteModal.svelte";

    // ── Estado principal ───────────────────────────────────────────────────
    let zonas = $state<Zona[]>([]);
    let loading = $state(true);

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
    <div class="glass-card-flat" style="border-radius:1rem;display:flex;flex-direction:column;overflow:hidden;">
        <div style="padding:1.25rem 1.5rem;display:flex;flex-direction:column;gap:0.75rem;">
            <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:0.75rem;">
                <div>
                    <h1 style="margin:0;font-size:1.5rem;font-weight:800;">
                        Gestión — Zonas de Cobertura
                    </h1>
                    <p style="margin:0.25rem 0 0;font-size:0.85rem;opacity:0.5;">
                        {loading
                            ? "Cargando..."
                            : `${zonas.length} zona${zonas.length !== 1 ? "s" : ""} registrada${zonas.length !== 1 ? "s" : ""}`}
                    </p>
                </div>
                <div style="display:flex;align-items:center;gap:0.75rem;flex-wrap:wrap;">
                    <button class="btn btn-primary btn-sm" onclick={() => (showModal = true)}>
                        + Nueva Zona
                    </button>
                </div>
            </div>
        </div>
    </div>

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
                        <div style="display:flex;gap:0.375rem;justify-content:center;">
                            <a
                                class="btn btn-xs btn-ghost"
                                href="/zonas/{z.id}/editar"
                                title="Editar zona">✏️</a
                            >
                            <button
                                class="btn btn-xs btn-ghost text-error"
                                title="Eliminar zona"
                                onclick={() => openDelete(z)}>🗑️</button
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

<!-- ── MODALES ──────────────────────────────────────────────────────────── -->
<ZonaFormModal bind:show={showModal} onsave={loadZonas} />
<ZonaDeleteModal bind:show={showDeleteModal} target={deleteTarget} onconfirm={loadZonas} />

<style>
    @keyframes pulseSkel {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
    }
</style>

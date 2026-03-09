<script lang="ts">
    import { onMount } from "svelte";
    import { api, createZona, updateZona, deleteZona } from "$lib/api";
    import DataTable from "$lib/components/DataTable.svelte";
    import { notify } from "$lib/stores/notifications";
    import type { Zona, ZonaCreate, ZonaUpdate } from "$lib/types/zona";

    // ── Estado principal ──────────────────────────────────────────────────
    let zonas = $state<Zona[]>([]);
    let loading = $state(true);
    let pageError = $state<string | null>(null);

    // ── Modal Crear/Editar ────────────────────────────────────────────────
    let showModal = $state(false);
    let modalMode = $state<"create" | "edit">("create");
    let editTarget = $state<Zona | null>(null);
    let modalError = $state<string | null>(null);
    let modalLoading = $state(false);

    // Campos del formulario
    let fNombre = $state("");

    // ── Modal Confirmar Eliminar ─────────────────────────────────────────
    let showDeleteModal = $state(false);
    let deleteTarget = $state<Zona | null>(null);
    let deleteLoading = $state(false);

    // ── Carga inicial ─────────────────────────────────────────────────────
    async function loadZonas() {
        loading = true;
        pageError = null;
        try {
            const res = await api.get<Zona[]>("/zonas");
            zonas = res.data;
        } catch (e: any) {
            notify.error(e?.response?.data?.detail ?? "Error al cargar las zonas.");
        } finally {
            loading = false;
        }
    }

    onMount(loadZonas);

    // ── Abrir Modales ──────────────────────────────────────────────────────
    function openCreate() {
        modalMode = "create";
        editTarget = null;
        fNombre = "";
        modalError = null;
        showModal = true;
    }

    function openEdit(z: Zona) {
        // La edición completa se hace en la ruta dedicada
        window.location.href = `/zonas/${z.id}/editar`;
    }

    function openDelete(z: Zona) {
        deleteTarget = z;
        showDeleteModal = true;
    }

    // ── Guardar Zona ────────────────────────────────────────────────────────
    async function saveZona() {
        modalLoading = true;
        modalError = null;
        try {
            const payload: ZonaCreate = { nombre: fNombre.trim() };
            await createZona(payload);
            showModal = false;
            notify.success("Zona creada correctamente.");
            await loadZonas();
        } catch (e: any) {
            notify.error(e?.response?.data?.detail ?? "Error al guardar la zona.");
        } finally {
            modalLoading = false;
        }
    }

    // ── Eliminar Zona ───────────────────────────────────────────────────────
    async function confirmDelete() {
        if (!deleteTarget) return;
        deleteLoading = true;
        try {
            await deleteZona(deleteTarget.id);
            showModal = false;
            showDeleteModal = false;
            deleteTarget = null;
            notify.success("Zona eliminada correctamente.");
            await loadZonas();
        } catch (e: any) {
            notify.error(e?.response?.data?.detail ?? "Error al eliminar la zona.");
            showDeleteModal = false;
        } finally {
            deleteLoading = false;
        }
    }
</script>

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
                <div>
                    <h1 style="margin:0;font-size:1.5rem;font-weight:800;">
                        Gestión — Zonas de Cobertura
                    </h1>
                    <p
                        style="margin:0.25rem 0 0;font-size:0.85rem;opacity:0.5;"
                    >
                        {loading
                            ? "Cargando..."
                            : `${zonas.length} zona${zonas.length !== 1 ? "s" : ""} registrada${zonas.length !== 1 ? "s" : ""}`}
                    </p>
                </div>
                <div
                    style="display:flex;align-items:center;gap:0.75rem;flex-wrap:wrap;"
                >
                    <button class="btn btn-primary btn-sm" onclick={openCreate}>
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
                    <!-- Nombre (enlace a detalle) -->
                    <td class="dt-td">
                        <a
                            href="/zonas/{z.id}"
                            style="display:flex;align-items:center;gap:0.5rem;font-weight:600;color:inherit;text-decoration:none;"
                            class="hover:underline"
                        >
                            <span
                                style="font-size:1.1rem;opacity:0.65;flex-shrink:0;"
                                >🗺️</span
                            >
                            {z.nombre}
                        </a>
                    </td>

                    <!-- Acciones -->
                    <td class="dt-td" style="text-align:center;">
                        <div
                            style="display:flex;gap:0.375rem;justify-content:center;"
                        >
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

        <!-- DataTable maneja su propio estado vacío internamente -->
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

<!-- ═══════════════════════════════════════════════════
     MODAL — Crear / Editar Zona
═══════════════════════════════════════════════════ -->
{#if showModal}
    <div
        style="position:fixed;inset:0;z-index:200;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;padding:1rem;"
        role="dialog"
        aria-modal="true"
    >
        <div
            style="background:var(--color-base-100);border-radius:1rem;width:100%;max-width:440px;box-shadow:0 25px 50px -12px rgba(0,0,0,0.4);overflow:hidden;"
        >
            <!-- Header del modal -->
            <div
                style="padding:1.25rem 1.5rem;border-bottom:1px solid oklch(from var(--color-base-content) l c h / 0.12);display:flex;align-items:center;justify-content:space-between;"
            >
                <h3 style="margin:0;font-size:1.1rem;font-weight:700;">
                    {modalMode === "create"
                        ? "➕ Nueva Zona"
                        : "✏️ Editar Zona"}
                </h3>
                <button
                    class="btn btn-ghost btn-sm btn-circle"
                    onclick={() => (showModal = false)}>✕</button
                >
            </div>

            <!-- Cuerpo -->
            <form
                onsubmit={(e) => {
                    e.preventDefault();
                    saveZona();
                }}
                style="padding:1.5rem;display:flex;flex-direction:column;gap:1rem;"
            >
                <!-- Nombre -->
                <label class="form-control w-full">
                    <div class="label">
                        <span class="label-text font-semibold">Nombre *</span>
                    </div>
                    <input
                        class="input input-bordered input-sm w-full"
                        type="text"
                        bind:value={fNombre}
                        placeholder="ej: Zona Norte, Centro..."
                        required
                    />
                </label>

                <!-- Botones -->
                <div
                    style="display:flex;gap:0.5rem;justify-content:flex-end;padding-top:0.25rem;"
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
                            <span class="loading loading-spinner loading-xs"
                            ></span>
                        {/if}
                        {modalMode === "create"
                            ? "Crear Zona"
                            : "Guardar Cambios"}
                    </button>
                </div>
            </form>
        </div>
    </div>
{/if}

<!-- ═══════════════════════════════════════════════════
     MODAL — Confirmar Eliminación
═══════════════════════════════════════════════════ -->
{#if showDeleteModal && deleteTarget}
    <div
        style="position:fixed;inset:0;z-index:200;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;padding:1rem;"
        role="dialog"
        aria-modal="true"
    >
        <div
            style="background:var(--color-base-100);border-radius:1rem;width:100%;max-width:380px;box-shadow:0 25px 50px -12px rgba(0,0,0,0.4);padding:1.5rem;display:flex;flex-direction:column;gap:1rem;"
        >
            <h3
                style="margin:0;font-size:1.1rem;font-weight:700;color:var(--color-error);"
            >
                🗑️ Eliminar Zona
            </h3>
            <p style="margin:0;font-size:0.9rem;opacity:0.8;">
                ¿Estás seguro de que quieres eliminar la zona
                <strong>{deleteTarget.nombre}</strong>? Esta acción no se puede
                deshacer.
            </p>
            <div style="display:flex;gap:0.5rem;justify-content:flex-end;">
                <button
                    class="btn btn-ghost btn-sm"
                    onclick={() => (showDeleteModal = false)}>Cancelar</button
                >
                <button
                    class="btn btn-error btn-sm"
                    onclick={confirmDelete}
                    disabled={deleteLoading}
                >
                    {#if deleteLoading}
                        <span class="loading loading-spinner loading-xs"></span>
                    {/if}
                    Eliminar
                </button>
            </div>
        </div>
    </div>
{/if}

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

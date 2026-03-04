<script lang="ts">
    import { onMount } from "svelte";
    import {
        getRouters,
        createRouter,
        updateRouter,
        deleteRouter,
    } from "$lib/api";
    import DataTable from "$lib/components/DataTable.svelte";
    import type { Router, RouterCreate, RouterUpdate } from "$lib/types/router";

    // ── Estado principal ──────────────────────────────────────────────────
    let routers = $state<Router[]>([]);
    let loading = $state(true);
    let pageError = $state<string | null>(null);

    // ── Modal Crear/Editar ────────────────────────────────────────────────
    let showModal = $state(false);
    let modalMode = $state<"create" | "edit">("create");
    let editTarget = $state<Router | null>(null);
    let modalError = $state<string | null>(null);
    let modalLoading = $state(false);

    // Campos del formulario
    let fHost = $state("");
    let fUsername = $state("");
    let fPassword = $state("");
    let fSshPort = $state(22);
    let fApiPort = $state(8728);
    let fIsEnabled = $state(true);
    let fWanInterface = $state("");

    // ── Modal Confirmar Eliminar ─────────────────────────────────────────
    let showDeleteModal = $state(false);
    let deleteTarget = $state<Router | null>(null);
    let deleteLoading = $state(false);

    // ── Estadísticas ──────────────────────────────────────────────────────
    let totalRouters = $derived(routers.length);
    let onlineRouters = $derived(
        routers.filter((r) => r.last_status === "online").length,
    );
    let offlineRouters = $derived(
        routers.filter((r) => r.last_status === "offline").length,
    );
    let provisionedRouters = $derived(
        routers.filter((r) => r.is_provisioned).length,
    );

    // ── Carga inicial ─────────────────────────────────────────────────────
    async function loadRouters() {
        loading = true;
        pageError = null;
        try {
            routers = await getRouters();
        } catch (e: any) {
            pageError =
                e?.response?.data?.detail ?? "Error al cargar los routers.";
        } finally {
            loading = false;
        }
    }

    onMount(loadRouters);

    // ── Helpers de Formulario ─────────────────────────────────────────────
    function resetForm() {
        fHost = "";
        fUsername = "";
        fPassword = "";
        fSshPort = 22;
        fApiPort = 8728;
        fIsEnabled = true;
        fWanInterface = "";
        modalError = null;
    }

    // ── Abrir Modales ──────────────────────────────────────────────────────
    function openCreate() {
        modalMode = "create";
        editTarget = null;
        resetForm();
        showModal = true;
    }

    function openEdit(r: Router) {
        modalMode = "edit";
        editTarget = r;
        fHost = r.host;
        fUsername = r.username;
        fPassword = "";
        fSshPort = r.ssh_port;
        fApiPort = r.api_port;
        fIsEnabled = r.is_enabled;
        fWanInterface = r.wan_interface ?? "";
        modalError = null;
        showModal = true;
    }

    function openDelete(r: Router) {
        deleteTarget = r;
        showDeleteModal = true;
    }

    // ── Guardar Router ────────────────────────────────────────────────────
    async function saveRouter() {
        modalLoading = true;
        modalError = null;
        try {
            if (modalMode === "create") {
                const payload: RouterCreate = {
                    host: fHost.trim(),
                    username: fUsername.trim(),
                    password: fPassword,
                    ssh_port: fSshPort,
                    api_port: fApiPort,
                    is_enabled: fIsEnabled,
                };
                await createRouter(payload);
            } else if (editTarget) {
                const payload: RouterUpdate = {
                    username: fUsername.trim(),
                    ssh_port: fSshPort,
                    api_port: fApiPort,
                    is_enabled: fIsEnabled,
                    wan_interface: fWanInterface.trim() || null,
                };
                if (fPassword.trim()) {
                    payload.password = fPassword;
                }
                await updateRouter(editTarget.host, payload);
            }
            showModal = false;
            await loadRouters();
        } catch (e: any) {
            modalError =
                e?.response?.data?.detail ?? "Error al guardar el router.";
        } finally {
            modalLoading = false;
        }
    }

    // ── Eliminar Router ────────────────────────────────────────────────────
    async function confirmDelete() {
        if (!deleteTarget) return;
        deleteLoading = true;
        try {
            await deleteRouter(deleteTarget.host);
            showDeleteModal = false;
            deleteTarget = null;
            await loadRouters();
        } catch (e: any) {
            pageError =
                e?.response?.data?.detail ?? "Error al eliminar el router.";
            showDeleteModal = false;
        } finally {
            deleteLoading = false;
        }
    }

    // ── Helpers de estado ──────────────────────────────────────────────────
    function statusBadge(status: string | null) {
        if (!status) return { cls: "badge-ghost", label: "Sin datos" };
        if (status === "online")
            return { cls: "badge-success", label: "Online" };
        if (status === "offline")
            return { cls: "badge-error", label: "Offline" };
        return { cls: "badge-warning", label: status };
    }
</script>

<svelte:head>
    <title>Routers — UManager</title>
</svelte:head>

<!-- ── CONTENEDOR PRINCIPAL ───────────────────────────────────────────── -->
<div style="display:flex;flex-direction:column;gap:1.5rem;">
    <!-- Encabezado -->
    <div
        style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:0.5rem;"
    >
        <div>
            <h2 style="font-size:1.375rem;font-weight:700;margin:0;">
                Infraestructura — Routers MikroTik
            </h2>
            <p style="margin:0.25rem 0 0;font-size:0.85rem;opacity:0.5;">
                {loading
                    ? "Cargando..."
                    : `${totalRouters} router${totalRouters !== 1 ? "s" : ""} registrado${totalRouters !== 1 ? "s" : ""}`}
            </p>
        </div>
        <button class="btn btn-primary btn-sm" onclick={openCreate}>
            + Nuevo Router
        </button>
    </div>

    <!-- KPI Cards -->
    {#if !loading}
        <div
            style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1rem;"
        >
            <div
                class="glass-card-flat"
                style="padding:1rem;border-radius:0.875rem;display:flex;align-items:center;gap:0.875rem;"
            >
                <div
                    style="font-size:1.75rem;width:2.5rem;height:2.5rem;display:flex;align-items:center;justify-content:center;background:oklch(from var(--color-primary) l c h / 0.12);border-radius:0.625rem;"
                >
                    🖧
                </div>
                <div>
                    <p
                        style="margin:0;font-size:0.7rem;opacity:0.5;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;"
                    >
                        Total
                    </p>
                    <p style="margin:0;font-size:1.5rem;font-weight:700;">
                        {totalRouters}
                    </p>
                </div>
            </div>
            <div
                class="glass-card-flat"
                style="padding:1rem;border-radius:0.875rem;display:flex;align-items:center;gap:0.875rem;"
            >
                <div
                    style="font-size:1.75rem;width:2.5rem;height:2.5rem;display:flex;align-items:center;justify-content:center;background:oklch(from var(--color-success) l c h / 0.12);border-radius:0.625rem;"
                >
                    ✅
                </div>
                <div>
                    <p
                        style="margin:0;font-size:0.7rem;opacity:0.5;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;"
                    >
                        Online
                    </p>
                    <p
                        style="margin:0;font-size:1.5rem;font-weight:700;color:oklch(from var(--color-success) l c h);"
                    >
                        {onlineRouters}
                    </p>
                </div>
            </div>
            <div
                class="glass-card-flat"
                style="padding:1rem;border-radius:0.875rem;display:flex;align-items:center;gap:0.875rem;"
            >
                <div
                    style="font-size:1.75rem;width:2.5rem;height:2.5rem;display:flex;align-items:center;justify-content:center;background:oklch(from var(--color-error) l c h / 0.12);border-radius:0.625rem;"
                >
                    ❌
                </div>
                <div>
                    <p
                        style="margin:0;font-size:0.7rem;opacity:0.5;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;"
                    >
                        Offline
                    </p>
                    <p
                        style="margin:0;font-size:1.5rem;font-weight:700;color:oklch(from var(--color-error) l c h);"
                    >
                        {offlineRouters}
                    </p>
                </div>
            </div>
            <div
                class="glass-card-flat"
                style="padding:1rem;border-radius:0.875rem;display:flex;align-items:center;gap:0.875rem;"
            >
                <div
                    style="font-size:1.75rem;width:2.5rem;height:2.5rem;display:flex;align-items:center;justify-content:center;background:oklch(from var(--color-info) l c h / 0.12);border-radius:0.625rem;"
                >
                    🔐
                </div>
                <div>
                    <p
                        style="margin:0;font-size:0.7rem;opacity:0.5;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;"
                    >
                        Provisionados
                    </p>
                    <p style="margin:0;font-size:1.5rem;font-weight:700;">
                        {provisionedRouters}
                    </p>
                </div>
            </div>
        </div>
    {/if}

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
        <DataTable items={routers}>
            {#snippet header()}
                <tr>
                    <th class="dt-th">Host / IP</th>
                    <th class="dt-th">Nombre (hostname)</th>
                    <th class="dt-th">Modelo</th>
                    <th class="dt-th">Zona</th>
                    <th class="dt-th" style="text-align:center;">Estado</th>
                    <th class="dt-th" style="text-align:center;">Activo</th>
                    <th class="dt-th" style="text-align:center;">Acciones</th>
                </tr>
            {/snippet}

            {#snippet row(r: Router)}
                {@const badge = statusBadge(r.last_status)}
                <tr>
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

                    <!-- Modelo -->
                    <td class="dt-td">
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

                    <!-- Habilitado -->
                    <td class="dt-td" style="text-align:center;">
                        {#if r.is_enabled}
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

        <!-- Estado vacío -->
        {#if routers.length === 0}
            <div
                class="glass-card-flat"
                style="padding:3rem;border-radius:1rem;text-align:center;opacity:0.6;"
            >
                <p style="font-size:2.5rem;margin:0 0 0.5rem;">🖧</p>
                <p style="font-weight:600;margin:0 0 0.25rem;">
                    Sin routers registrados
                </p>
                <p style="font-size:0.85rem;margin:0;">
                    Añade tu primer router MikroTik con el botón "+ Nuevo
                    Router".
                </p>
            </div>
        {/if}
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
     MODAL — Crear / Editar Router
═══════════════════════════════════════════════════ -->
{#if showModal}
    <div
        style="position:fixed;inset:0;z-index:200;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;padding:1rem;overflow-y:auto;"
        role="dialog"
        aria-modal="true"
    >
        <div
            style="background:var(--color-base-100);border-radius:1rem;width:100%;max-width:520px;box-shadow:0 25px 50px -12px rgba(0,0,0,0.4);overflow:hidden;margin:auto;"
        >
            <!-- Header del modal -->
            <div
                style="padding:1.25rem 1.5rem;border-bottom:1px solid oklch(from var(--color-base-content) l c h / 0.12);display:flex;align-items:center;justify-content:space-between;"
            >
                <h3 style="margin:0;font-size:1.1rem;font-weight:700;">
                    {modalMode === "create"
                        ? "➕ Nuevo Router"
                        : "✏️ Editar Router"}
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
                    saveRouter();
                }}
                style="padding:1.5rem;display:flex;flex-direction:column;gap:1rem;"
            >
                {#if modalError}
                    <div class="alert alert-error alert-sm py-2">
                        <span style="font-size:0.85rem;">{modalError}</span>
                    </div>
                {/if}

                <!-- Host / IP -->
                <label class="form-control w-full">
                    <div class="label">
                        <span class="label-text font-semibold">Host / IP *</span
                        >
                    </div>
                    <input
                        class="input input-bordered input-sm w-full font-mono"
                        type="text"
                        bind:value={fHost}
                        placeholder="ej: 192.168.1.1"
                        required
                        disabled={modalMode === "edit"}
                    />
                    {#if modalMode === "edit"}
                        <div class="label">
                            <span class="label-text-alt opacity-50"
                                >No se puede cambiar el host</span
                            >
                        </div>
                    {/if}
                </label>

                <!-- Usuario + Password -->
                <div
                    style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;"
                >
                    <label class="form-control w-full">
                        <div class="label">
                            <span class="label-text font-semibold"
                                >Usuario API *</span
                            >
                        </div>
                        <input
                            class="input input-bordered input-sm w-full"
                            type="text"
                            bind:value={fUsername}
                            placeholder="admin"
                            required
                        />
                    </label>
                    <label class="form-control w-full">
                        <div class="label">
                            <span class="label-text font-semibold">
                                {modalMode === "create"
                                    ? "Password *"
                                    : "Password (vacío = sin cambio)"}
                            </span>
                        </div>
                        <input
                            class="input input-bordered input-sm w-full"
                            type="password"
                            bind:value={fPassword}
                            placeholder={modalMode === "create"
                                ? "contraseña"
                                : "••••••••"}
                            required={modalMode === "create"}
                        />
                    </label>
                </div>

                <!-- Puertos -->
                <div
                    style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;"
                >
                    <label class="form-control w-full">
                        <div class="label">
                            <span class="label-text font-semibold"
                                >Puerto SSH</span
                            >
                        </div>
                        <input
                            class="input input-bordered input-sm w-full"
                            type="number"
                            bind:value={fSshPort}
                            min="1"
                            max="65535"
                        />
                    </label>
                    <label class="form-control w-full">
                        <div class="label">
                            <span class="label-text font-semibold"
                                >Puerto API</span
                            >
                        </div>
                        <input
                            class="input input-bordered input-sm w-full"
                            type="number"
                            bind:value={fApiPort}
                            min="1"
                            max="65535"
                        />
                    </label>
                </div>

                <!-- Interfaz WAN -->
                {#if modalMode === "edit"}
                    <label class="form-control w-full">
                        <div class="label">
                            <span class="label-text font-semibold"
                                >Interfaz WAN</span
                            >
                            <span class="label-text-alt opacity-50"
                                >Opcional</span
                            >
                        </div>
                        <input
                            class="input input-bordered input-sm w-full font-mono"
                            type="text"
                            bind:value={fWanInterface}
                            placeholder="ej: ether1, sfp-sfpplus1"
                        />
                    </label>
                {/if}

                <!-- Habilitado -->
                <div style="display:flex;align-items:center;gap:0.75rem;">
                    <input
                        type="checkbox"
                        class="toggle toggle-primary toggle-sm"
                        bind:checked={fIsEnabled}
                        id="chk-enabled"
                    />
                    <label
                        for="chk-enabled"
                        class="label-text font-semibold cursor-pointer"
                    >
                        Router Habilitado
                    </label>
                </div>

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
                            <span class="loading loading-spinner loading-xs"
                            ></span>
                        {/if}
                        {modalMode === "create"
                            ? "Agregar Router"
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
            style="background:var(--color-base-100);border-radius:1rem;width:100%;max-width:400px;box-shadow:0 25px 50px -12px rgba(0,0,0,0.4);padding:1.5rem;display:flex;flex-direction:column;gap:1rem;"
        >
            <h3
                style="margin:0;font-size:1.1rem;font-weight:700;color:oklch(from var(--color-error) l c h);"
            >
                🗑️ Eliminar Router
            </h3>
            <p style="margin:0;font-size:0.9rem;opacity:0.8;">
                ¿Estás seguro de que deseas eliminar el router
                <strong style="font-family:monospace;"
                    >{deleteTarget.host}</strong
                >?
                {#if deleteTarget.hostname}
                    <span style="opacity:0.65;">({deleteTarget.hostname})</span>
                {/if}
                Esta acción no se puede deshacer.
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

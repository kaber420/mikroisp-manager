<script lang="ts">
    import { onMount } from "svelte";
    import {
        getRouters,
        createRouter,
        updateRouter,
        deleteRouter,
        provisionRouter,
        repairRouter,
    } from "$lib/api";
    import DataTable from "$lib/components/DataTable.svelte";
    import ProvisionModal from "$lib/components/ProvisionModal.svelte";
    import type { Router, RouterCreate, RouterUpdate } from "$lib/types/router";
    import { notify } from "$lib/stores/notifications";


    // ── Estado principal ──────────────────────────────────────────────────
    let routers = $state<Router[]>([]);
    let loading = $state(true);

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
    let fVendor = $state("mikrotik");
    let fIsProvisioned = $state(false);

    // ── Modal Confirmar Eliminar ─────────────────────────────────────────
    let showDeleteModal = $state(false);
    let deleteTarget = $state<Router | null>(null);
    let deleteLoading = $state(false);

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
    let provisionedRouters = $derived(
        routers.filter((r) => r.is_provisioned).length,
    );

    // ── Carga inicial ─────────────────────────────────────────────────────
    async function loadRouters() {
        loading = true;
        try {
            routers = await getRouters();
        } catch (e: any) {
            notify.error(e?.response?.data?.detail ?? "Error al cargar los routers.");
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
        fVendor = "mikrotik";
        fIsProvisioned = false;
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
        fVendor = r.vendor ?? "mikrotik";
        fIsProvisioned = r.is_provisioned ?? false;
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
                    vendor: fVendor,
                    is_provisioned: fIsProvisioned,
                };
                await createRouter(payload);
                showModal = false;
                notify.success("Router agregado exitosamente.");
                await loadRouters();
                // Sugerir aprovisionamiento si es mikrotik y no fue marcado como aprovisionado
                if (fVendor === 'mikrotik' && !fIsProvisioned) {
                    const created = routers.find(r => r.host === fHost.trim());
                    if (created) {
                        postCreateRouter = created;
                        showPostCreateModal = true;
                    }
                }
            } else if (editTarget) {
                const payload: RouterUpdate = {
                    username: fUsername.trim(),
                    ssh_port: fSshPort,
                    api_port: fApiPort,
                    is_enabled: fIsEnabled,
                    wan_interface: fWanInterface.trim() || null,
                    vendor: fVendor,
                    is_provisioned: fIsProvisioned,
                };
                if (fPassword.trim()) {
                    payload.password = fPassword;
                }
                await updateRouter(editTarget.host, payload);
                showModal = false;
                notify.success("Cambios guardados correctamente.");
                await loadRouters();
            }
        } catch (e: any) {
            notify.error(e?.response?.data?.detail ?? "Error al guardar el router.");
        } finally {
            modalLoading = false;
        }
    }

    // ── Aprovisionamiento desde la lista ──────────────────────────────────
    function openProvision(r: Router) {
        provisionTarget = r;
        showProvisionModal = true;
    }

    async function handleProvision(data: { newApiUser: string; newApiPassword?: string; method: string }) {
        if (!provisionTarget) return;
        isProvisioning = true;
        try {
            await provisionRouter(provisionTarget.host, data.newApiUser, data.newApiPassword, data.method);
            notify.success(`Router ${provisionTarget.host} aprovisionado exitosamente.`);
            showProvisionModal = false;
            showPostCreateModal = false;
            await loadRouters();
        } catch (e: any) {
            notify.error(e?.response?.data?.detail ?? "Error al aprovisionar.");
            showProvisionModal = false;
        } finally {
            isProvisioning = false;
            provisionTarget = null;
        }
    }

    async function handleRenewSSL(r: Router) {
        if (!confirm(`¿Renovar certificados SSL en ${r.host}?`)) return;
        try {
            await repairRouter(r.host, "renew");
            notify.success(`Certificados SSL renovados en ${r.host}.`);
        } catch (e: any) {
            notify.error(e?.response?.data?.detail ?? "Error al renovar SSL.");
        }
    }

    async function handleUnprovision(r: Router) {
        if (!confirm(`¿Desvincular ${r.host}? Perderá el acceso API-SSL hasta que vuelva a aprovisionarse.`)) return;
        try {
            await repairRouter(r.host, "unprovision");
            notify.success(`Router ${r.host} desvinculado correctamente.`);
            await loadRouters();
        } catch (e: any) {
            notify.error(e?.response?.data?.detail ?? "Error al desvincular.");
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
            notify.success("Router eliminado correctamente.");
            await loadRouters();
        } catch (e: any) {
            notify.error(e?.response?.data?.detail ?? "Error al eliminar el router.");
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
                        Routers
                    </h1>
                    <p
                        style="margin:0.25rem 0 0;font-size:0.85rem;opacity:0.5;"
                    >
                        {loading
                            ? "Cargando..."
                            : `${totalRouters} router${totalRouters !== 1 ? "s" : ""} registrado${totalRouters !== 1 ? "s" : ""}`}
                    </p>
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

    <!-- El error ahora se muestra como Toast -->

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
                    <th class="dt-th" style="text-align:center;">Seguridad</th>
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

                    <!-- Seguridad (Provisioning) -->
                    <td class="dt-td" style="text-align:center;">
                        {#if r.vendor === 'mikrotik'}
                            {#if r.is_provisioned}
                                <div class="dropdown dropdown-end">
                                    <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
                                    <div tabindex="0" role="button" class="btn btn-xs btn-info gap-1 text-white">
                                        🔒 Seguro
                                        <svg xmlns="http://www.w3.org/2000/svg" class="w-3 h-3 opacity-70" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" /></svg>
                                    </div>
                                    <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
                                    <ul tabindex="0" class="dropdown-content z-[2] menu p-2 shadow bg-base-100 rounded-box w-52 mt-1 border border-base-200">
                                        <li><button class="text-info text-xs font-bold" onclick={() => handleRenewSSL(r)}>🔄 Renovar SSL / Cert</button></li>
                                        <li><button class="text-error text-xs font-bold" onclick={() => handleUnprovision(r)}>❌ Desvincular (Unprovision)</button></li>
                                    </ul>
                                </div>
                            {:else}
                                <button
                                    class="btn btn-xs btn-success text-white gap-1"
                                    title="Aprovisionar este router (API-SSL)"
                                    onclick={() => openProvision(r)}
                                >
                                    🔐 Aprovisionar
                                </button>
                            {/if}
                        {:else}
                            <span class="badge badge-sm badge-ghost">N/A</span>
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

                <!-- Vendor -->
                <label class="form-control w-full">
                    <div class="label">
                        <span class="label-text font-semibold">Marca (Vendor)</span>
                    </div>
                    <select class="select select-bordered select-sm w-full" bind:value={fVendor}>
                        <option value="mikrotik">MikroTik</option>
                        <option value="ubiquiti">Ubiquiti</option>
                        <option value="cisco">Cisco</option>
                        <option value="otro">Otro</option>
                    </select>
                </label>

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

                <!-- Aprovisionado Manualmente -->
                {#if fVendor === 'mikrotik'}
                    <div style="display:flex;align-items:center;gap:0.75rem;">
                        <input
                            type="checkbox"
                            class="toggle toggle-info toggle-sm"
                            bind:checked={fIsProvisioned}
                            id="chk-provisioned"
                        />
                        <label
                            for="chk-provisioned"
                            class="label-text font-semibold cursor-pointer"
                        >
                            Router Aprovisionado (API-SSL)
                        </label>
                    </div>
                {/if}

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

<!-- ═══════════════════════════════════════════════════
     MODAL — Aprovisionamiento
═══════════════════════════════════════════════════ -->
<ProvisionModal
    bind:show={showProvisionModal}
    {isProvisioning}
    onProvision={handleProvision}
/>

<!-- ═══════════════════════════════════════════════════
     MODAL — Sugerir Aprovisionamiento Post-Creación
═══════════════════════════════════════════════════ -->
{#if showPostCreateModal && postCreateRouter}
    <div
        style="position:fixed;inset:0;z-index:200;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;padding:1rem;"
        role="dialog"
        aria-modal="true"
    >
        <div
            style="background:var(--color-base-100);border-radius:1rem;width:100%;max-width:440px;box-shadow:0 25px 50px -12px rgba(0,0,0,0.4);padding:1.5rem;display:flex;flex-direction:column;gap:1rem;"
        >
            <h3 style="margin:0;font-size:1.1rem;font-weight:700;display:flex;align-items:center;gap:0.5rem;">
                🔐 ¿Aprovisionar ahora?
            </h3>
            <p style="margin:0;font-size:0.9rem;opacity:0.8;">
                El router <strong style="font-family:monospace;">{postCreateRouter.host}</strong> fue creado exitosamente.
                El aprovisionamiento habilita la conexión segura (API-SSL) para que UManager pueda monitorear y gestionar el router.
            </p>
            <div style="display:flex;gap:0.5rem;justify-content:flex-end;">
                <button
                    class="btn btn-ghost btn-sm"
                    onclick={() => { showPostCreateModal = false; postCreateRouter = null; }}
                >Después</button>
                <button
                    class="btn btn-success btn-sm text-white"
                    onclick={() => {
                        if (postCreateRouter) {
                            provisionTarget = postCreateRouter;
                            showPostCreateModal = false;
                            showProvisionModal = true;
                        }
                    }}
                >
                    🔐 Sí, Aprovisionar
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

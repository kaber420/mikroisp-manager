<script lang="ts">
    import { onMount } from "svelte";
    import { getAPs, createAP, updateAP, deleteAP, validateAP } from "$lib/api";
    import DataTable from "$lib/components/DataTable.svelte";
    import type { AP, APCreate, APUpdate, APValidate } from "$lib/types/ap";

    // ── Estado principal ──────────────────────────────────────────────────
    let aps = $state<AP[]>([]);
    let loading = $state(true);
    let pageError = $state<string | null>(null);

    // ── Modal Crear/Editar ────────────────────────────────────────────────
    let showModal = $state(false);
    let modalMode = $state<"create" | "edit">("create");
    let editTarget = $state<AP | null>(null);
    let modalError = $state<string | null>(null);
    let modalLoading = $state(false);

    // Zonas
    import { getZonas } from "$lib/api";
    import type { Zona } from "$lib/types/zona";
    let zonas = $state<Zona[]>([]);

    // Test connection
    let testLoading = $state(false);
    let testResult = $state<{
        status: "success" | "error";
        message: string;
    } | null>(null);

    // Campos del formulario
    let fHost = $state("");
    let fUsername = $state("ubnt");
    let fPassword = $state("");
    let fVendor = $state("ubiquiti");
    let fSshPort = $state<number | null>(22);
    let fApiPort = $state<number | null>(null);
    let fIsEnabled = $state(true);
    let fZonaId = $state<number | null>(null);
    let fIsProvisioned = $state(false);

    // Default ports based on vendor
    $effect(() => {
        if (modalMode === "create" && !fApiPort) {
            fApiPort = fVendor === "ubiquiti" ? 443 : 8729;
        }
    });

    // ── Modal Confirmar Eliminar ─────────────────────────────────────────
    let showDeleteModal = $state(false);
    let deleteTarget = $state<AP | null>(null);
    let deleteLoading = $state(false);

    // ── Estadísticas ──────────────────────────────────────────────────────
    let totalAPs = $derived(aps.length);
    let onlineAPs = $derived(
        aps.filter((a) => a.last_status === "online").length,
    );
    let offlineAPs = $derived(
        aps.filter((a) => a.last_status === "offline").length,
    );

    let ubiquitiAPs = $derived(
        aps.filter((a) => a.vendor === "ubiquiti").length,
    );
    let mikrotikAPs = $derived(
        aps.filter((a) => a.vendor === "mikrotik").length,
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

    // ── Helpers de Formulario ─────────────────────────────────────────────
    function resetForm() {
        fHost = "";
        fUsername = "ubnt";
        fPassword = "";
        fVendor = "ubiquiti";
        fSshPort = 22;
        fApiPort = 443;
        fIsEnabled = true;
        fZonaId = null;
        fIsProvisioned = false;
        modalError = null;
        testResult = null;
    }

    // ── Abrir Modales ──────────────────────────────────────────────────────
    function openCreate() {
        modalMode = "create";
        editTarget = null;
        resetForm();
        showModal = true;
    }

    function openEdit(a: AP) {
        modalMode = "edit";
        editTarget = a;
        fHost = a.host;
        fUsername = a.username;
        fPassword = "";
        fVendor = a.vendor || "ubiquiti";
        fSshPort = a.ssh_port || 22;
        fApiPort = a.api_port || null;
        fIsEnabled = a.is_enabled;
        fZonaId = a.zona_id;
        fIsProvisioned = a.is_provisioned || false;
        modalError = null;
        testResult = null;
        showModal = true;
    }

    function openDelete(a: AP) {
        deleteTarget = a;
        showDeleteModal = true;
    }

    // ── Probar Conexión ────────────────────────────────────────────────────
    async function testConnection() {
        if (!fHost || !fUsername || (!fPassword && modalMode === "create")) {
            modalError = "Completa Host, Usuario y Contraseña para probar.";
            return;
        }

        testLoading = true;
        testResult = null;
        modalError = null;

        try {
            const payload: APValidate = {
                host: fHost.trim(),
                username: fUsername.trim(),
                password: fPassword || undefined,
                vendor: fVendor,
                api_port: fApiPort || undefined,
            };

            const result = await validateAP(payload);
            testResult = { status: "success", message: result.message };
        } catch (e: any) {
            testResult = {
                status: "error",
                message: e?.response?.data?.detail ?? "Error de conexión.",
            };
        } finally {
            testLoading = false;
        }
    }

    // ── Guardar AP ────────────────────────────────────────────────────
    async function saveAP() {
        modalLoading = true;
        modalError = null;
        try {
            if (modalMode === "create") {
                const payload: APCreate = {
                    host: fHost.trim(),
                    username: fUsername.trim(),
                    password: fPassword,
                    vendor: fVendor,
                    ssh_port: fSshPort || undefined,
                    api_port: fApiPort || undefined,
                    is_enabled: fIsEnabled,
                    zona_id: fZonaId || undefined,
                    is_provisioned: fIsProvisioned,
                    role: "access_point",
                };
                await createAP(payload);
            } else if (editTarget) {
                const payload: APUpdate = {
                    username: fUsername.trim(),
                    vendor: fVendor,
                    ssh_port: fSshPort || undefined,
                    api_port: fApiPort || undefined,
                    is_enabled: fIsEnabled,
                    zona_id: fZonaId || undefined,
                    is_provisioned: fIsProvisioned,
                    role: "access_point",
                };
                if (fPassword.trim()) {
                    payload.password = fPassword;
                }
                await updateAP(editTarget.host, payload);
            }
            showModal = false;
            await loadAPs();
        } catch (e: any) {
            modalError = e?.response?.data?.detail ?? "Error al guardar el AP.";
        } finally {
            modalLoading = false;
        }
    }

    // ── Eliminar AP ────────────────────────────────────────────────────
    async function confirmDelete() {
        if (!deleteTarget) return;
        deleteLoading = true;
        try {
            await deleteAP(deleteTarget.host);
            showDeleteModal = false;
            deleteTarget = null;
            await loadAPs();
        } catch (e: any) {
            pageError = e?.response?.data?.detail ?? "Error al eliminar el AP.";
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
    <title>Access Points — UManager</title>
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
                        Access Points
                    </h1>
                    <p
                        style="margin:0.25rem 0 0;font-size:0.85rem;opacity:0.5;"
                    >
                        {loading
                            ? "Cargando..."
                            : `${totalAPs} Access Point${totalAPs !== 1 ? "s" : ""} registrado${totalAPs !== 1 ? "s" : ""}`}
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
                        Nuevo AP
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
                    📡
                </div>
                <div>
                    <p
                        style="margin:0;font-size:0.7rem;opacity:0.5;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;"
                    >
                        Total
                    </p>
                    <p style="margin:0;font-size:1.5rem;font-weight:700;">
                        {totalAPs}
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
                        {onlineAPs}
                    </p>
                </div>
            </div>

            <div
                class="glass-card-flat"
                style="padding:1rem;border-radius:0.875rem;display:flex;align-items:center;gap:0.875rem;"
            >
                <div
                    style="font-size:1.75rem;width:2.5rem;height:2.5rem;display:flex;align-items:center;justify-content:center;background:transparent;border-radius:0.625rem;"
                >
                    <!-- Icono generico para Ubiquiti -->
                    <svg
                        xmlns="http://www.w3.org/2000/svg"
                        class="w-7 h-7"
                        viewBox="0 0 24 24"
                        fill="currentColor"
                        ><path
                            d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-12h2v4h-2zm0 6h2v2h-2z"
                        /></svg
                    >
                </div>
                <div>
                    <p
                        style="margin:0;font-size:0.7rem;opacity:0.5;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;"
                    >
                        Ubiquiti
                    </p>
                    <p style="margin:0;font-size:1.5rem;font-weight:700;">
                        {ubiquitiAPs}
                    </p>
                </div>
            </div>
            <div
                class="glass-card-flat"
                style="padding:1rem;border-radius:0.875rem;display:flex;align-items:center;gap:0.875rem;"
            >
                <div
                    style="font-size:1.75rem;width:2.5rem;height:2.5rem;display:flex;align-items:center;justify-content:center;background:transparent;border-radius:0.625rem;"
                >
                    <!-- Icono generico para MikroTik -->
                    <svg
                        xmlns="http://www.w3.org/2000/svg"
                        class="w-7 h-7"
                        viewBox="0 0 24 24"
                        fill="currentColor"
                        ><path d="M4 6h16v2H4zm0 5h16v2H4zm0 5h16v2H4z" /></svg
                    >
                </div>
                <div>
                    <p
                        style="margin:0;font-size:0.7rem;opacity:0.5;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;"
                    >
                        MikroTik
                    </p>
                    <p style="margin:0;font-size:1.5rem;font-weight:700;">
                        {mikrotikAPs}
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
        <DataTable items={aps}>
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

<!-- ═══════════════════════════════════════════════════
     MODAL — Crear / Editar AP
═══════════════════════════════════════════════════ -->
{#if showModal}
    <!-- Este div utiliza LAS MISMAS CLASES E INLINE STYLES QUE LOS ROUTERS para asegurar consistencia absoluta -->
    <div
        style="position:fixed;inset:0;z-index:200;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;padding:1rem;overflow-y:auto;"
        role="dialog"
        aria-modal="true"
    >
        <div
            style="background:var(--color-base-100);border-radius:1rem;width:100%;max-width:560px;box-shadow:0 25px 50px -12px rgba(0,0,0,0.4);overflow:hidden;margin:auto;"
        >
            <!-- Header del modal -->
            <div
                style="padding:1.25rem 1.5rem;border-bottom:1px solid oklch(from var(--color-base-content) l c h / 0.12);display:flex;align-items:center;justify-content:space-between;"
            >
                <div>
                    <h3 style="margin:0;font-size:1.1rem;font-weight:700;">
                        {modalMode === "create"
                            ? "➕ Nuevo Access Point"
                            : "✏️ Editar Access Point"}
                    </h3>
                    {#if modalMode === "edit"}
                        <p
                            style="margin:0;font-size:0.8rem;opacity:0.6;font-family:monospace;margin-top:0.25rem;"
                        >
                            {editTarget?.host}
                        </p>
                    {/if}
                </div>

                <button
                    class="btn btn-ghost btn-sm btn-circle"
                    onclick={() => (showModal = false)}>✕</button
                >
            </div>

            <!-- Cuerpo del formulario -->
            <form
                onsubmit={(e) => {
                    e.preventDefault();
                    saveAP();
                }}
                style="padding:1.5rem;display:flex;flex-direction:column;gap:1.15rem;"
            >
                {#if modalError}
                    <div class="alert alert-error alert-sm py-2">
                        <span style="font-size:0.85rem;">{modalError}</span>
                    </div>
                {/if}

                <div
                    style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;"
                >
                    <!-- Host / IP -->
                    <label class="form-control w-full">
                        <div class="label">
                            <span class="label-text font-semibold"
                                >Host / IP *</span
                            >
                        </div>
                        <input
                            class="input input-bordered input-sm w-full font-mono"
                            type="text"
                            bind:value={fHost}
                            placeholder="ej: 192.168.1.20"
                            required
                            disabled={modalMode === "edit"}
                        />
                        {#if modalMode === "edit"}
                            <div class="label" style="padding-top:0.25rem;">
                                <span class="label-text-alt opacity-50"
                                    >No se puede cambiar el host</span
                                >
                            </div>
                        {/if}
                    </label>

                    <!-- Vendor -->
                    <label class="form-control w-full">
                        <div class="label">
                            <span class="label-text font-semibold"
                                >Vendor *</span
                            >
                        </div>
                        <select
                            class="select select-bordered select-sm w-full"
                            bind:value={fVendor}
                        >
                            <option value="ubiquiti">Ubiquiti</option>
                            <option value="mikrotik">MikroTik</option>
                        </select>
                    </label>
                </div>

                <div
                    style="display:grid;grid-template-columns:1fr;gap:0.75rem;"
                >
                    <!-- Zona -->
                    <label class="form-control w-full">
                        <div class="label">
                            <span class="label-text font-semibold"
                                >Zona de Cobertura *</span
                            >
                        </div>
                        <select
                            class="select select-bordered select-sm w-full"
                            bind:value={fZonaId}
                            required
                        >
                            <option value={null} disabled selected>
                                -- Selecciona una Zona --
                            </option>
                            {#each zonas as z}
                                <option value={z.id}>
                                    {z.nombre}
                                </option>
                            {/each}
                        </select>
                    </label>
                </div>

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
                            placeholder={fVendor === "ubiquiti"
                                ? "ubnt"
                                : "admin"}
                            required
                        />
                    </label>
                    <label class="form-control w-full">
                        <div class="label">
                            <span class="label-text font-semibold">
                                {modalMode === "create"
                                    ? "Contraseña *"
                                    : "Contraseña"}
                            </span>
                            {#if modalMode === "edit"}
                                <span class="label-text-alt opacity-50"
                                    >(vacío = sin cambio)</span
                                >
                            {/if}
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

                <div
                    style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;"
                >
                    <label class="form-control w-full">
                        <div class="label">
                            <span class="label-text font-semibold"
                                >Puerto HTTP/API</span
                            >
                            <span class="label-text-alt opacity-50"
                                >Opcional</span
                            >
                        </div>
                        <input
                            class="input input-bordered input-sm w-full"
                            type="number"
                            bind:value={fApiPort}
                            min="1"
                            max="65535"
                            placeholder={fVendor === "ubiquiti"
                                ? "443"
                                : "8728"}
                        />
                    </label>
                    <label class="form-control w-full">
                        <div class="label">
                            <span class="label-text font-semibold"
                                >Puerto SSH</span
                            >
                            <span class="label-text-alt opacity-50"
                                >Opcional</span
                            >
                        </div>
                        <input
                            class="input input-bordered input-sm w-full"
                            type="number"
                            bind:value={fSshPort}
                            min="1"
                            max="65535"
                            placeholder="22"
                        />
                    </label>
                </div>

                <!-- Test Connection Results -->
                {#if testResult}
                    <div
                        class="alert {testResult.status === 'success'
                            ? 'alert-success'
                            : 'alert-error'} alert-sm py-2"
                    >
                        <span style="font-size:0.85rem;"
                            >{testResult.message}</span
                        >
                    </div>
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
                        Access Point Habilitado
                    </label>
                </div>

                <!-- Aprovisionado Manualmente -->
                {#if fVendor === 'mikrotik'}
                    <div style="display:flex;align-items:center;gap:0.75rem;">
                        <input
                            type="checkbox"
                            class="toggle toggle-info toggle-sm"
                            bind:checked={fIsProvisioned}
                            id="chk-provisioned-ap"
                        />
                        <label
                            for="chk-provisioned-ap"
                            class="label-text font-semibold cursor-pointer"
                        >
                            AP Aprovisionado (API-SSL)
                        </label>
                    </div>
                {/if}

                <!-- Botones -->
                <div
                    style="display:flex;gap:0.5rem;justify-content:space-between;align-items:center;padding-top:0.5rem;border-top:1px solid oklch(from var(--color-base-content) l c h / 0.08);"
                >
                    <!-- Probar conexión (lado izquierdo) -->
                    <button
                        type="button"
                        class="btn btn-secondary btn-sm"
                        onclick={testConnection}
                        disabled={testLoading}
                    >
                        {#if testLoading}
                            <span class="loading loading-spinner loading-xs"
                            ></span>
                        {:else}
                            🔌
                        {/if}
                        Probar
                    </button>

                    <!-- Guardar / Cancelar (lado derecho) -->
                    <div style="display:flex;gap:0.5rem;">
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
                                ? "Agregar AP"
                                : "Guardar Cambios"}
                        </button>
                    </div>
                </div>
            </form>
        </div>
    </div>
{/if}

<!-- ═══════════════════════════════════════════════════
     MODAL — Confirmar Eliminación
═══════════════════════════════════════════════════ -->
{#if showDeleteModal && deleteTarget}
    <!-- Este modal también utiliza los mismos estilos que el de delete del router -->
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
                🗑️ Eliminar Access Point
            </h3>
            <p style="margin:0;font-size:0.9rem;opacity:0.8;">
                ¿Estás seguro de que deseas eliminar el AP
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

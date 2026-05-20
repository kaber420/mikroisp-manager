<script lang="ts">
    import { createAP, updateAP, validateAP } from "$lib/api";
    import type { AP, APCreate, APUpdate, APValidate } from "$lib/types/ap";
    import type { Zona } from "$lib/types/zona";

    // Propiedades usando runas de Svelte 5
    let {
        show = $bindable(false),
        mode = "create",
        target = null,
        zonas = [],
        onsave,
    } = $props<{
        show: boolean;
        mode: "create" | "edit";
        target: AP | null;
        zonas: Zona[];
        onsave?: () => void;
    }>();

    // Campos del formulario locales
    let fHost = $state("");
    let fUsername = $state("ubnt");
    let fPassword = $state("");
    let fVendor = $state("ubiquiti");
    let fSshPort = $state<number | null>(22);
    let fApiPort = $state<number | null>(null);
    let fIsEnabled = $state(true);
    let fZonaId = $state<number | null>(null);
    let fIsProvisioned = $state(false);

    // Estados de carga e interacción locales
    let modalError = $state<string | null>(null);
    let modalLoading = $state(false);
    let testLoading = $state(false);
    let testResult = $state<{
        status: "success" | "error";
        message: string;
    } | null>(null);

    // Carga de datos / Reset al mostrar el modal
    $effect(() => {
        if (show) {
            if (mode === "edit" && target) {
                fHost = target.host;
                fUsername = target.username;
                fPassword = "";
                fVendor = target.vendor || "ubiquiti";
                fSshPort = target.ssh_port || 22;
                fApiPort = target.api_port || null;
                fIsEnabled = target.is_enabled;
                fZonaId = target.zona_id;
                fIsProvisioned = target.is_provisioned || false;
                modalError = null;
                testResult = null;
            } else {
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
        }
    });

    // Puertos API por defecto según fabricante al crear
    $effect(() => {
        if (show && mode === "create") {
            fApiPort = fVendor === "ubiquiti" ? 443 : 8729;
        }
    });

    // Probar Conexión
    async function testConnection() {
        if (!fHost || !fUsername || (!fPassword && mode === "create")) {
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

    // Guardar AP
    async function saveAP() {
        modalLoading = true;
        modalError = null;
        try {
            if (mode === "create") {
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
            } else if (target) {
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
                await updateAP(target.host, payload);
            }
            show = false;
            if (onsave) onsave();
        } catch (e: any) {
            modalError = e?.response?.data?.detail ?? "Error al guardar el AP.";
        } finally {
            modalLoading = false;
        }
    }
</script>

{#if show}
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
                        {mode === "create"
                            ? "➕ Nuevo Access Point"
                            : "✏️ Editar Access Point"}
                    </h3>
                    {#if mode === "edit"}
                        <p
                            style="margin:0;font-size:0.8rem;opacity:0.6;font-family:monospace;margin-top:0.25rem;"
                        >
                            {target?.host}
                        </p>
                    {/if}
                </div>

                <button
                    class="btn btn-ghost btn-sm btn-circle"
                    onclick={() => (show = false)}>✕</button
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
                            disabled={mode === "edit"}
                        />
                        {#if mode === "edit"}
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
                                {mode === "create"
                                    ? "Contraseña *"
                                    : "Contraseña"}
                            </span>
                            {#if mode === "edit"}
                                <span class="label-text-alt opacity-50"
                                    >(vacío = sin cambio)</span
                                >
                            {/if}
                        </div>
                        <input
                            class="input input-bordered input-sm w-full"
                            type="password"
                            bind:value={fPassword}
                            placeholder={mode === "create"
                                ? "contraseña"
                                : "••••••••"}
                            required={mode === "create"}
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
                            onclick={() => (show = false)}>Cancelar</button
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
                            {mode === "create"
                                ? "Agregar AP"
                                : "Guardar Cambios"}
                        </button>
                    </div>
                </div>
            </form>
        </div>
    </div>
{/if}

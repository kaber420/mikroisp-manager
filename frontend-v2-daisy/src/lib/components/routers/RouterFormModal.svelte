<script lang="ts">
    import { createRouter, updateRouter, repairRouter } from "$lib/api";
    import type { Router, RouterCreate, RouterUpdate } from "$lib/types/router";
    import type { Zona } from "$lib/types/zona";
    import { notify } from "$lib/stores/notifications";

    // Propiedades usando runas de Svelte 5
    let {
        show = $bindable(false),
        mode = "create",
        target = null,
        zonas = [],
        onsave,
        onrequestprovision,
    } = $props<{
        show: boolean;
        mode: "create" | "edit";
        target: Router | null;
        zonas: Zona[];
        onsave?: (host: string, isCreated: boolean, vendor: string, isProvisioned: boolean) => void;
        onrequestprovision?: (r: Router) => void;
    }>();

    // Campos del formulario locales
    let fHost = $state("");
    let fUsername = $state("");
    let fPassword = $state("");
    let fSshPort = $state(22);
    let fApiPort = $state(8728);
    let fIsEnabled = $state(true);
    let fWanInterface = $state("");
    let fVendor = $state("mikrotik");
    let fIsProvisioned = $state(false);
    let fZonaId = $state<number | "">("");

    // Estados de carga e interacción locales
    let modalError = $state<string | null>(null);
    let modalLoading = $state(false);

    // Carga de datos / Reset al mostrar el modal
    $effect(() => {
        if (show) {
            if (mode === "edit" && target) {
                fHost = target.host;
                fUsername = target.username;
                fPassword = "";
                fSshPort = target.ssh_port;
                fApiPort = target.api_port;
                fIsEnabled = target.is_enabled;
                fWanInterface = target.wan_interface ?? "";
                fVendor = target.vendor ?? "mikrotik";
                fIsProvisioned = target.is_provisioned ?? false;
                fZonaId = target.zona_id ?? "";
                modalError = null;
            } else {
                fHost = "";
                fUsername = "";
                fPassword = "";
                fSshPort = 22;
                fApiPort = 8728;
                fIsEnabled = true;
                fWanInterface = "";
                fVendor = "mikrotik";
                fIsProvisioned = false;
                fZonaId = "";
                modalError = null;
            }
        }
    });

    async function saveRouter() {
        modalLoading = true;
        modalError = null;
        try {
            if (mode === "create") {
                const payload: RouterCreate = {
                    host: fHost.trim(),
                    username: fUsername.trim(),
                    password: fPassword,
                    ssh_port: fSshPort,
                    api_port: fApiPort,
                    is_enabled: fIsEnabled,
                    vendor: fVendor,
                    is_provisioned: fIsProvisioned,
                    zona_id: Number(fZonaId),
                };
                await createRouter(payload);
                show = false;
                notify.success("Router agregado exitosamente.");
                if (onsave) {
                    onsave(payload.host, true, payload.vendor, payload.is_provisioned);
                }
            } else if (target) {
                const payload: RouterUpdate = {
                    username: fUsername.trim(),
                    ssh_port: fSshPort,
                    api_port: fApiPort,
                    is_enabled: fIsEnabled,
                    wan_interface: fWanInterface.trim() || null,
                    vendor: fVendor,
                    is_provisioned: fIsProvisioned,
                    zona_id: fZonaId === "" ? null : Number(fZonaId),
                };
                if (fPassword.trim()) {
                    payload.password = fPassword;
                }
                await updateRouter(target.host, payload);
                show = false;
                notify.success("Cambios guardados correctamente.");
                if (onsave) {
                    onsave(target.host, false, payload.vendor ?? "", payload.is_provisioned ?? false);
                }
            }
        } catch (e: any) {
            modalError = e?.response?.data?.detail ?? "Error al guardar el router.";
            notify.error(modalError);
        } finally {
            modalLoading = false;
        }
    }

    async function handleRenewSSL(r: Router) {
        if (!confirm(`¿Renovar certificados SSL en ${r.host}?`)) return;
        try {
            await repairRouter(r.host, "renew");
            notify.success(`Certificados SSL renovados en ${r.host}.`);
            show = false;
            if (onsave) {
                onsave(r.host, false, r.vendor ?? "", r.is_provisioned ?? false);
            }
        } catch (e: any) {
            notify.error(e?.response?.data?.detail ?? "Error al renovar SSL.");
        }
    }

    async function handleUnprovision(r: Router) {
        if (!confirm(`¿Desvincular ${r.host}? Perderá el acceso API-SSL hasta que vuelva a aprovisionarse.`)) return;
        try {
            await repairRouter(r.host, "unprovision");
            notify.success(`Router ${r.host} desvinculado correctamente.`);
            show = false;
            if (onsave) {
                onsave(r.host, false, r.vendor ?? "", false);
            }
        } catch (e: any) {
            notify.error(e?.response?.data?.detail ?? "Error al desvincular.");
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
            style="background:var(--color-base-100);border-radius:1rem;width:100%;max-width:520px;box-shadow:0 25px 50px -12px rgba(0,0,0,0.4);overflow:hidden;margin:auto;"
        >
            <!-- Header del modal -->
            <div
                style="padding:1.25rem 1.5rem;border-bottom:1px solid oklch(from var(--color-base-content) l c h / 0.12);display:flex;align-items:center;justify-content:space-between;"
            >
                <h3 style="margin:0;font-size:1.1rem;font-weight:700;">
                    {mode === "create"
                        ? "➕ Nuevo Router"
                        : "✏️ Editar Router"}
                </h3>
                <button
                    class="btn btn-ghost btn-sm btn-circle"
                    onclick={() => (show = false)}>✕</button
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
                        <span class="label-text font-semibold">Host / IP *</span>
                    </div>
                    <input
                        class="input input-bordered input-sm w-full font-mono"
                        type="text"
                        bind:value={fHost}
                        placeholder="ej: 192.168.1.1"
                        required
                        disabled={mode === "edit"}
                    />
                    {#if mode === "edit"}
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
                                {mode === "create"
                                    ? "Password *"
                                    : "Password (vacío = sin cambio)"}
                            </span>
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
                {#if mode === "edit"}
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
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;">
                    <label class="form-control w-full">
                        <div class="label">
                            <span class="label-text font-semibold">Marca (Vendor) *</span>
                        </div>
                        <select class="select select-bordered select-sm w-full" bind:value={fVendor} required>
                            <option value="mikrotik">MikroTik</option>
                            <option value="ubiquiti">Ubiquiti</option>
                            <option value="cisco">Cisco</option>
                            <option value="otro">Otro</option>
                        </select>
                    </label>

                    <label class="form-control w-full">
                        <div class="label">
                            <span class="label-text font-semibold">Zona *</span>
                        </div>
                        <select class="select select-bordered select-sm w-full" bind:value={fZonaId} required>
                            <option value="" disabled selected>Seleccione una zona</option>
                            {#each zonas as zona}
                                <option value={zona.id}>{zona.nombre}</option>
                            {/each}
                        </select>
                    </label>
                </div>

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

                <!-- Aprovisionado Manualmente y Seguridad -->
                {#if fVendor === 'mikrotik'}
                    <div style="display:flex;align-items:center;justify-content:space-between;gap:0.75rem;flex-wrap:wrap;margin-top:0.5rem;">
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
                        {#if mode === "edit" && target}
                            <div style="display:flex;gap:0.5rem;">
                                {#if fIsProvisioned}
                                    <button type="button" class="btn btn-xs btn-outline btn-info bg-base-100" onclick={() => handleRenewSSL(target!)}>🔄 Renovar SSL</button>
                                    <button type="button" class="btn btn-xs btn-outline btn-error bg-base-100" onclick={() => handleUnprovision(target!)}>❌ Desvincular</button>
                                {:else}
                                    <button type="button" class="btn btn-xs btn-success text-white" onclick={() => {
                                        show = false;
                                        if (onrequestprovision) onrequestprovision(target!);
                                    }}>🔐 Aprovisionar</button>
                                {/if}
                            </div>
                        {/if}
                    </div>
                {/if}

                <!-- Botones -->
                <div
                    style="display:flex;gap:0.5rem;justify-content:flex-end;padding-top:0.5rem;border-top:1px solid oklch(from var(--color-base-content) l c h / 0.08);"
                >
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
                            ? "Agregar Router"
                            : "Guardar Cambios"}
                    </button>
                </div>
            </form>
        </div>
    </div>
{/if}

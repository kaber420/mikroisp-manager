<script lang="ts">
    import { updateRouter } from '$lib/api';
    import { getZonas } from '$lib/api';
    import type { Router, RouterUpdate } from '$lib/types/router';
    import type { Zona } from '$lib/types/zona';
    import { onMount } from 'svelte';

    interface Props {
        router: Router;
        open: boolean;
        onClose: () => void;
        onSaved: (updated: Router) => void;
    }

    let { router, open, onClose, onSaved }: Props = $props();

    // Estado local del formulario
    let username = $state('');
    let password = $state('');
    let apiPort = $state(0);
    let sshPort = $state(0);
    let zonaId = $state<number | null>(null);
    let isEnabled = $state(true);
    let wanInterface = $state('');

    let zonas = $state<Zona[]>([]);
    let saving = $state(false);
    let errorMsg = $state<string | null>(null);
    let successMsg = $state<string | null>(null);

    // Sincronizar formulario cuando cambia el router o se abre el modal
    $effect(() => {
        if (open) {
            username = router.username ?? '';
            password = '';
            apiPort = router.api_port ?? 8728;
            sshPort = router.ssh_port ?? 22;
            zonaId = router.zona_id ?? null;
            isEnabled = router.is_enabled ?? true;
            wanInterface = router.wan_interface ?? '';
            errorMsg = null;
            successMsg = null;
        }
    });

    onMount(async () => {
        try {
            zonas = await getZonas();
        } catch {
            // No crítico
        }
    });

    async function handleSave() {
        saving = true;
        errorMsg = null;
        successMsg = null;
        try {
            const payload: RouterUpdate = {
                username,
                api_port: apiPort,
                ssh_port: sshPort,
                zona_id: zonaId,
                is_enabled: isEnabled,
                wan_interface: wanInterface.trim() || null,
            };
            if (password.trim()) {
                payload.password = password;
            }
            const updated = await updateRouter(router.host, payload);
            successMsg = 'Router actualizado correctamente.';
            setTimeout(() => {
                onSaved(updated);
                onClose();
            }, 800);
        } catch (e: any) {
            errorMsg = e?.response?.data?.detail ?? 'Error al guardar los cambios.';
        } finally {
            saving = false;
        }
    }
</script>

{#if open}
<!-- Overlay -->
<div
    style="position:fixed;inset:0;background:rgba(0,0,0,0.55);backdrop-filter:blur(4px);z-index:9000;display:flex;align-items:center;justify-content:center;padding:1rem;"
    onclick={onClose}
>
    <!-- Modal card -->
    <div
        class="glass-card-flat"
        style="border-radius:1.25rem;width:100%;max-width:540px;padding:1.75rem;box-shadow:0 20px 60px rgba(0,0,0,0.5);border:1px solid oklch(from var(--color-primary) l c h / 0.2);"
        onclick={(e) => e.stopPropagation()}
    >
        <!-- Header -->
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1.25rem;">
            <h2 style="margin:0;font-size:1.15rem;font-weight:800;display:flex;align-items:center;gap:0.5rem;">
                <span style="font-size:1.3rem;">✏️</span>
                Editar Router
                <span style="font-family:monospace;font-size:0.85rem;opacity:0.5;font-weight:400;">/ {router.host}</span>
            </h2>
            <button class="btn btn-ghost btn-sm btn-circle" onclick={onClose} aria-label="Cerrar">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" style="width:1rem;height:1rem;">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
            </button>
        </div>

        <!-- Mensajes -->
        {#if errorMsg}
            <div class="alert alert-error py-2 mb-4" style="font-size:0.85rem;">⚠️ {errorMsg}</div>
        {/if}
        {#if successMsg}
            <div class="alert alert-success py-2 mb-4" style="font-size:0.85rem;">✅ {successMsg}</div>
        {/if}

        <!-- Form -->
        <form onsubmit={(e) => { e.preventDefault(); handleSave(); }} style="display:flex;flex-direction:column;gap:1rem;">
            <!-- Usuario -->
            <div>
                <label style="font-size:0.75rem;font-weight:700;opacity:0.6;text-transform:uppercase;display:block;margin-bottom:0.35rem;">
                    Usuario API
                </label>
                <input
                    type="text"
                    class="input input-bordered w-full input-sm"
                    bind:value={username}
                    required
                    autocomplete="off"
                    placeholder="admin"
                />
            </div>

            <!-- Contraseña -->
            <div>
                <label style="font-size:0.75rem;font-weight:700;opacity:0.6;text-transform:uppercase;display:block;margin-bottom:0.35rem;">
                    Nueva Contraseña <span style="opacity:0.5;text-transform:none;font-weight:400;">(vacío = no cambiar)</span>
                </label>
                <input
                    type="password"
                    class="input input-bordered w-full input-sm"
                    bind:value={password}
                    autocomplete="new-password"
                    placeholder="••••••••"
                />
            </div>

            <!-- Puertos -->
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;">
                <div>
                    <label style="font-size:0.75rem;font-weight:700;opacity:0.6;text-transform:uppercase;display:block;margin-bottom:0.35rem;">
                        Puerto API
                    </label>
                    <input
                        type="number"
                        class="input input-bordered w-full input-sm"
                        bind:value={apiPort}
                        min="1"
                        max="65535"
                        required
                    />
                </div>
                <div>
                    <label style="font-size:0.75rem;font-weight:700;opacity:0.6;text-transform:uppercase;display:block;margin-bottom:0.35rem;">
                        Puerto SSH
                    </label>
                    <input
                        type="number"
                        class="input input-bordered w-full input-sm"
                        bind:value={sshPort}
                        min="1"
                        max="65535"
                    />
                </div>
            </div>

            <!-- Zona -->
            <div>
                <label style="font-size:0.75rem;font-weight:700;opacity:0.6;text-transform:uppercase;display:block;margin-bottom:0.35rem;">
                    Zona
                </label>
                <select class="select select-bordered w-full select-sm" bind:value={zonaId}>
                    <option value={null}>-- Sin zona --</option>
                    {#each zonas as z}
                        <option value={z.id}>{z.nombre}</option>
                    {/each}
                </select>
            </div>
            
            <!-- Interfaz WAN -->
            <div>
                <label style="font-size:0.75rem;font-weight:700;opacity:0.6;text-transform:uppercase;display:block;margin-bottom:0.35rem;">
                    Interfaz WAN <span style="opacity:0.5;text-transform:none;font-weight:400;">(ej: ether1, sfp-sfpplus1)</span>
                </label>
                <input
                    type="text"
                    class="input input-bordered w-full input-sm font-mono"
                    bind:value={wanInterface}
                    placeholder="ether1"
                />
            </div>

            <!-- Habilitado -->
            <label class="label cursor-pointer justify-start gap-3" style="padding:0;">
                <input type="checkbox" class="toggle toggle-success toggle-sm" bind:checked={isEnabled} />
                <span style="font-size:0.85rem;font-weight:600;">Router habilitado para monitoreo</span>
            </label>

            <!-- Acciones -->
            <div style="display:flex;gap:0.75rem;justify-content:flex-end;margin-top:0.5rem;padding-top:0.75rem;border-top:1px solid oklch(from var(--color-base-content) l c h / 0.1);">
                <button type="button" class="btn btn-ghost btn-sm" onclick={onClose}>Cancelar</button>
                <button type="submit" class="btn btn-primary btn-sm" disabled={saving}>
                    {#if saving}
                        <span class="loading loading-spinner loading-xs"></span>
                        Guardando...
                    {:else}
                        💾 Guardar Cambios
                    {/if}
                </button>
            </div>
        </form>
    </div>
</div>
{/if}

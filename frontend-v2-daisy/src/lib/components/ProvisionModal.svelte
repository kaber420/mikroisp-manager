<script lang="ts">
    import { onMount } from "svelte";

    let { 
        show = $bindable(false), 
        router = null, 
        isProvisioning = false,
        onprovision,
        onProvision
    } = $props<{
        show: boolean;
        router?: any;
        isProvisioning?: boolean;
        onprovision?: (data: any) => void;
        onProvision?: (data: any) => void;
    }>();

    let newApiUser = $state("omni_admin");
    let newApiPassword = $state("");
    let method = $state("ssh"); // ssh (vía script), api-ssl o api

    function handleSubmit() {
        const payload = {
            newApiUser,
            newApiPassword: newApiPassword || undefined,
            method
        };
        if (onprovision) onprovision(payload);
        if (onProvision) onProvision(payload);
    }

    // Reset when opening
    $effect(() => {
        if (show) {
            newApiPassword = "";
        }
    });
</script>

{#if show}
<div class="modal modal-open">
    <div class="modal-box max-w-md bg-gradient-to-br from-base-100 to-base-200 border border-base-content/10">
        <div class="flex items-center gap-4 mb-6">
            <div class="w-12 h-12 bg-primary/20 rounded-2xl flex items-center justify-center text-2xl">⚡</div>
            <div>
                <h3 class="font-black text-xl">Aprovisionar Router</h3>
                <p class="text-xs opacity-60">{router?.hostname || router?.host}</p>
            </div>
        </div>

        <div class="space-y-4">
            <div class="alert alert-info text-[10px] leading-relaxed py-2 shadow-sm border-info/20">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-4 h-4"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                <span>Esto creará un nuevo usuario en el Mikrotik, habilitará el servicio API-SSL y generará certificados seguros para la gestión remota.</span>
            </div>

            <div class="form-control">
                <label class="label py-1" for="api-user">
                    <span class="label-text font-bold text-xs uppercase opacity-60">Nuevo Usuario API</span>
                </label>
                <input 
                    id="api-user"
                    type="text" 
                    bind:value={newApiUser}
                    class="input input-bordered input-sm bg-base-200/50" 
                    placeholder="ej. omni_admin" 
                />
            </div>

            <div class="form-control">
                <label class="label py-1" for="api-pass">
                    <span class="label-text font-bold text-xs uppercase opacity-60">Contraseña API (Opcional)</span>
                    <span class="label-text-alt opacity-40">Auto-generar si vacío</span>
                </label>
                <input 
                    id="api-pass"
                    type="password" 
                    bind:value={newApiPassword}
                    class="input input-bordered input-sm bg-base-200/50" 
                    placeholder="••••••••" 
                />
            </div>

            <div class="form-control">
                <label class="label py-1" for="conn-method">
                    <span class="label-text font-bold text-xs uppercase opacity-60">Método de Conexión</span>
                </label>
                <select id="conn-method" bind:value={method} class="select select-bordered select-sm bg-base-200/50">
                    <option value="ssh">🛠️ SSH Script (Sugerido - Primario)</option>
                    <option value="api-ssl">🚀 API SSL (Secundario - Puerto 8729)</option>
                    <option value="api">⚠️ API Estándar (Fallback - Puerto 8728)</option>
                </select>
            </div>
        </div>

        <div class="modal-action gap-2">
            <button class="btn btn-ghost btn-sm px-6" onclick={() => show = false} disabled={isProvisioning}>Cancelar</button>
            <button 
                class="btn btn-primary btn-sm px-6 gap-2" 
                onclick={handleSubmit} 
                disabled={isProvisioning}
            >
                {#if isProvisioning}
                    <span class="loading loading-spinner loading-xs"></span>
                    Procesando...
                {:else}
                    Iniciar Provisión
                {/if}
            </button>
        </div>
    </div>
</div>
{/if}

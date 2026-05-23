<script lang="ts">
    import { untrack } from 'svelte';

    let { 
        showModal = $bindable(false), 
        settings = { autoJoin: false, welcomeMessage: "" }, 
        onSave 
    } = $props<{
        showModal: boolean;
        settings?: any;
        onSave?: (newSettings: any) => void;
    }>();

    // Fix state_referenced_locally by using untrack or just a simple copy if reactive sync is not needed
    let localSettings = $state({ ...settings });

    function handleSave() {
        if (onSave) {
            onSave(localSettings);
        }
        showModal = false;
    }
</script>

{#if showModal}
    <div class="fixed inset-0 z-[1000] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
        <div class="glass-card max-w-md w-full p-6 space-y-6 bg-base-100 rounded-2xl">
            <h3 class="text-xl font-bold">Ajustes de Sala de Espera</h3>
            
            <div class="space-y-4">
                <div class="form-control">
                    <label class="label cursor-pointer justify-start gap-4">
                        <input type="checkbox" class="toggle toggle-primary" bind:checked={localSettings.autoJoin} />
                        <span class="label-text">Unirse automáticamente</span>
                    </label>
                </div>
                
                <div class="form-control">
                    <label class="label" for="welcome-msg">
                        <span class="label-text">Mensaje de Bienvenida</span>
                    </label>
                    <textarea id="welcome-msg" class="textarea textarea-bordered h-24" bind:value={localSettings.welcomeMessage}></textarea>
                </div>
            </div>

            <div class="flex justify-end gap-3 mt-8">
                <button class="btn btn-ghost" onclick={() => showModal = false}>Cancelar</button>
                <button class="btn btn-primary" onclick={handleSave}>Guardar Cambios</button>
            </div>
        </div>
    </div>
{/if}


<script lang="ts">
    let { show = $bindable(false) } = $props();
</script>

{#if show}
<div class="modal modal-open">
    <div class="modal-box max-w-2xl bg-gradient-to-br from-base-100 to-base-200">
        <div class="flex items-center gap-4 mb-6">
            <div class="w-12 h-12 bg-primary/20 rounded-2xl flex items-center justify-center text-2xl">📱</div>
            <div>
                <h3 class="font-black text-xl">Configura la App Móvil</h3>
                <p class="text-xs opacity-60">Escanea el código para vincular tu cuenta admin.</p>
            </div>
        </div>
        
        <div class="flex justify-center p-8 bg-white rounded-3xl mb-6 shadow-inner">
            <!-- Placeholder for QR -->
            <div class="w-48 h-48 bg-neutral-100 flex items-center justify-center text-neutral-400 font-bold italic">
                Cargando QR...
            </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
            <button class="btn btn-outline btn-sm">Google Play</button>
            <button class="btn btn-outline btn-sm">App Store</button>
        </div>

        <div class="modal-action">
            <button class="btn btn-ghost" onclick={() => show = false}>Cerrar</button>
        </div>
    </div>
</div>
{/if}

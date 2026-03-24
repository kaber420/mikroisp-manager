<script lang="ts">
    let { show = false } = $props();
    let isOpen = $state(show);

    export function open() { isOpen = true; }
</script>

{#if isOpen}
<div class="modal modal-open">
    <div class="modal-box">
        <h3 class="font-bold text-lg">¡Configuración inicial completada!</h3>
        <p class="py-4">Bienvenido a su nuevo sistema OmniWISP. Ahora puede empezar a configurar sus routers y planes.</p>
        <div class="modal-action">
            <button class="btn btn-primary" onclick={() => isOpen = false}>Entendido</button>
        </div>
    </div>
</div>
{/if}

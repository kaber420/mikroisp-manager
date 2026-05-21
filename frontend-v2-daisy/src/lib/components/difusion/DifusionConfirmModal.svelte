<script lang="ts">
    let {
        targetLabel,
        message,
        onconfirm,
        dialogRef = $bindable<HTMLDialogElement | undefined>(undefined),
    }: {
        targetLabel: () => string;
        message: string;
        onconfirm?: () => void;
        dialogRef?: HTMLDialogElement;
    } = $props();
</script>

<dialog bind:this={dialogRef} class="modal modal-bottom sm:modal-middle">
    <div class="modal-box">
        <h3 class="mb-1 text-lg font-bold">Confirmar Broadcast</h3>
        <p class="text-base-content/60 mb-4 text-sm">Estás a punto de enviar a:</p>

        <div class="bg-warning/10 border border-warning/30 rounded-xl px-4 py-3 text-center">
            <p class="text-lg font-semibold">{targetLabel()}</p>
        </div>

        {#if message.trim()}
            <div class="mt-4 rounded-xl border border-base-300 bg-base-200 p-3">
                <p class="line-clamp-4 text-sm">{message.trim()}</p>
            </div>
        {/if}

        <p class="text-base-content/50 mt-4 text-xs">
            ⚠️ Esta acción no se puede deshacer. Los mensajes se enviarán inmediatamente.
        </p>

        <div class="modal-action">
            <form method="dialog">
                <button class="btn">Cancelar</button>
            </form>
            <button onclick={onconfirm} class="btn btn-warning gap-2">
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    class="h-4 w-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                    />
                </svg>
                Sí, enviar ahora
            </button>
        </div>
    </div>
    <form method="dialog" class="modal-backdrop">
        <button>cerrar</button>
    </form>
</dialog>

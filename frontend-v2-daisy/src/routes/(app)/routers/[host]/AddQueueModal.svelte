<script lang="ts">
    import { addSimpleQueue } from "$lib/api";

    let {
        show = $bindable(false),
        routerHost,
        onsuccess,
    } = $props<{
        show: boolean;
        routerHost: string;
        onsuccess?: () => void;
    }>();

    let loading = $state(false);
    let errorMsg = $state<string | null>(null);

    // Form fields
    let name = $state("");
    let target = $state("");
    let maxLimit = $state("");
    let isParent = $state(false);

    $effect(() => {
        if (show) {
            errorMsg = null;
            name = "";
            target = "";
            maxLimit = "";
            isParent = false;
        }
    });

    function close() {
        show = false;
    }

    async function handleSubmit() {
        if (!name || !maxLimit) {
            errorMsg = "Por favor, completa Nombre y Max Limit.";
            return;
        }

        loading = true;
        errorMsg = null;

        const payload = {
            host: routerHost,
            name,
            max_limit: maxLimit,
            target: target || undefined,
            is_parent: isParent,
        };

        try {
            await addSimpleQueue(routerHost, payload);
            if (onsuccess) onsuccess();
            close();
        } catch (e: any) {
            errorMsg =
                e.response?.data?.detail ||
                e.message ||
                "Error al guardar la cola";
        } finally {
            loading = false;
        }
    }
</script>

{#if show}
    <div class="modal modal-open z-50">
        <div class="modal-box">
            <h3 class="font-bold text-lg mb-4">Agregar Cola (Simple Queue)</h3>

            {#if errorMsg}
                <div class="alert alert-error text-sm py-2 mb-4">
                    <span>{errorMsg}</span>
                </div>
            {/if}

            <form
                onsubmit={(e) => {
                    e.preventDefault();
                    handleSubmit();
                }}
                class="space-y-4"
            >
                <div class="form-control">
                    <label class="label" for="queue-name"
                        ><span class="label-text">Nombre</span></label
                    >
                    <input
                        id="queue-name"
                        type="text"
                        class="input input-bordered w-full"
                        bind:value={name}
                        required
                        placeholder="Ej: PLAN-50M"
                    />
                </div>

                <div class="form-control">
                    <label class="label" for="queue-target"
                        ><span class="label-text">Target (IP o Red)</span
                        ></label
                    >
                    <input
                        id="queue-target"
                        type="text"
                        class="input input-bordered w-full"
                        bind:value={target}
                        placeholder="Ej: 192.168.10.0/24 (Opcional)"
                    />
                </div>

                <div class="form-control">
                    <label class="label" for="queue-max-limit"
                        ><span class="label-text"
                            >Max Limit (Upload/Download)</span
                        ></label
                    >
                    <input
                        id="queue-max-limit"
                        type="text"
                        class="input input-bordered w-full"
                        bind:value={maxLimit}
                        required
                        placeholder="Ej: 50M/50M"
                    />
                </div>

                <div class="form-control">
                    <label class="label cursor-pointer justify-start gap-4">
                        <span class="label-text"
                            >Es cola padre / infraestructura</span
                        >
                        <input
                            type="checkbox"
                            class="toggle toggle-primary"
                            bind:checked={isParent}
                        />
                    </label>
                </div>

                <div class="modal-action">
                    <button
                        type="button"
                        class="btn btn-ghost"
                        onclick={close}
                        disabled={loading}>Cancelar</button
                    >
                    <button
                        type="submit"
                        class="btn btn-primary"
                        disabled={loading}
                    >
                        {#if loading}<span
                                class="loading loading-spinner loading-sm"
                            ></span>{/if}
                        Guardar
                    </button>
                </div>
            </form>
        </div>
        <form method="dialog" class="modal-backdrop">
            <button onclick={close}>close</button>
        </form>
    </div>
{/if}

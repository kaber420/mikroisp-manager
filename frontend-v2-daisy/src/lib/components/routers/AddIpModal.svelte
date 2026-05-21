<script lang="ts">
    import { addIpAddress } from "$lib/api";
    import type { InterfaceData } from "$lib/types/router";

    let {
        show = $bindable(false),
        routerHost,
        interfaces = [],
        onsuccess,
    } = $props<{
        show: boolean;
        routerHost: string;
        interfaces: InterfaceData[];
        onsuccess?: () => void;
    }>();

    let loading = $state(false);
    let errorMsg = $state<string | null>(null);

    // Form fields
    let address = $state("");
    let ifaceName = $state("");
    let comment = $state("");

    $effect(() => {
        if (show) {
            errorMsg = null;
            address = "";
            ifaceName = "";
            comment = "managed by umonitor";
        }
    });

    function close() {
        show = false;
    }

    async function handleSubmit() {
        if (!address || !ifaceName) {
            errorMsg = "Por favor, completa los campos requeridos.";
            return;
        }

        loading = true;
        errorMsg = null;

        try {
            await addIpAddress(routerHost, {
                address,
                interface: ifaceName,
                comment,
            });
            if (onsuccess) onsuccess();
            close();
        } catch (e: any) {
            errorMsg =
                e.response?.data?.detail || e.message || "Error al agregar IP";
        } finally {
            loading = false;
        }
    }
</script>

{#if show}
    <div class="modal modal-open z-50">
        <div class="modal-box">
            <h3
                class="font-bold text-lg mb-4 text-primary flex items-center gap-2"
            >
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                    class="w-5 h-5"
                >
                    <path
                        d="M10.75 4.75a.75.75 0 0 0-1.5 0v4.5h-4.5a.75.75 0 0 0 0 1.5h4.5v4.5a.75.75 0 0 0 1.5 0v-4.5h4.5a.75.75 0 0 0 0-1.5h-4.5v-4.5Z"
                    />
                </svg>
                Agregar Dirección IP
            </h3>

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
                    <label class="label" for="ip-address">
                        <span class="label-text font-bold"
                            >Dirección IP (con CIDR)</span
                        >
                    </label>
                    <input
                        id="ip-address"
                        type="text"
                        class="input input-bordered w-full"
                        bind:value={address}
                        required
                        placeholder="Ej: 192.168.88.1/24"
                    />
                </div>

                <div class="form-control">
                    <label class="label" for="ip-interface">
                        <span class="label-text font-bold">Interfaz</span>
                    </label>
                    <select
                        id="ip-interface"
                        class="select select-bordered w-full"
                        bind:value={ifaceName}
                        required
                    >
                        <option value="" disabled
                            >Seleccionar interfaz...</option
                        >
                        {#each interfaces as intf}
                            <option value={intf.name}
                                >{intf.name} ({intf.type})</option
                            >
                        {/each}
                    </select>
                </div>

                <div class="form-control">
                    <label class="label" for="ip-comment">
                        <span class="label-text font-bold">Comentario</span>
                    </label>
                    <input
                        id="ip-comment"
                        type="text"
                        class="input input-bordered w-full"
                        bind:value={comment}
                        placeholder="Comentario opcional"
                    />
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
                        class="btn btn-primary px-8"
                        disabled={loading}
                    >
                        {#if loading}<span
                                class="loading loading-spinner loading-sm"
                            ></span>{/if}
                        Agregar
                    </button>
                </div>
            </form>
        </div>
        <form method="dialog" class="modal-backdrop">
            <button onclick={close}>close</button>
        </form>
    </div>
{/if}

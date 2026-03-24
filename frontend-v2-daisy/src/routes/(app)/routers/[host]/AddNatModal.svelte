<script lang="ts">
    import { addNatRule } from "$lib/api";
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
    let outInterface = $state("");
    let comment = $state("");

    $effect(() => {
        if (show) {
            errorMsg = null;
            outInterface = "";
            comment = "masquerade managed by umonitor";
        }
    });

    function close() {
        show = false;
    }

    async function handleSubmit() {
        loading = true;
        errorMsg = null;

        try {
            await addNatRule(routerHost, {
                out_interface: outInterface || undefined,
                comment,
            });
            if (onsuccess) onsuccess();
            close();
        } catch (e: any) {
            errorMsg =
                e.response?.data?.detail ||
                e.message ||
                "Error al agregar regla NAT";
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
                        fill-rule="evenodd"
                        d="M10 1a4.5 4.5 0 0 0-4.5 4.5V9H5a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-6a2 2 0 0 0-2-2h-.5V5.5A4.5 4.5 0 0 0 10 1Zm3 8V5.5a3 3 0 1 0-6 0V9h6Z"
                        clip-rule="evenodd"
                    />
                </svg>
                Agregar Regla NAT (Masquerade)
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
                    <label class="label" for="nat-out-interface">
                        <span class="label-text font-bold"
                            >Interfaz de Salida (WAN)</span
                        >
                        <span class="label-text-alt opacity-50 italic"
                            >Opcional</span
                        >
                    </label>
                    <select
                        id="nat-out-interface"
                        class="select select-bordered w-full"
                        bind:value={outInterface}
                    >
                        <option value="">Todas las interfaces</option>
                        {#each interfaces as intf}
                            <option value={intf.name}
                                >{intf.name} ({intf.type})</option
                            >
                        {/each}
                    </select>
                </div>

                <div class="form-control">
                    <label class="label" for="nat-comment">
                        <span class="label-text font-bold">Comentario</span>
                    </label>
                    <input
                        id="nat-comment"
                        type="text"
                        class="input input-bordered w-full"
                        bind:value={comment}
                        required
                        placeholder="Ej: masquerade vlan10"
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
                        Adicionar
                    </button>
                </div>
            </form>
        </div>
        <form method="dialog" class="modal-backdrop">
            <button onclick={close}>close</button>
        </form>
    </div>
{/if}

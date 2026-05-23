<script lang="ts">
    import { updateCPE } from "$lib/api";
    import type { CPEGlobalInfo } from "$lib/types/cpe";

    let {
        show = $bindable(false),
        cpe,
        onsave,
    }: {
        show: boolean;
        cpe: CPEGlobalInfo | null;
        onsave?: () => void;
    } = $props();

    let editHostname = $state("");
    let editSaving = $state(false);
    let editError = $state<string | null>(null);

    // Sincronizar hostname cuando cambia el CPE objetivo
    $effect(() => {
        if (cpe) {
            editHostname = cpe.cpe_hostname ?? "";
            editError = null;
        }
    });

    async function saveEdit() {
        if (!cpe) return;
        editSaving = true;
        editError = null;
        try {
            await updateCPE(cpe.cpe_mac, { hostname: editHostname || null });
            show = false;
            onsave?.();
        } catch (e: any) {
            editError = e?.response?.data?.detail ?? "Error al guardar.";
        } finally {
            editSaving = false;
        }
    }
</script>

{#if show && cpe}
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
    <div
        class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
        role="dialog"
        aria-modal="true"
        tabindex="-1"
        onclick={(e) => {
            if (e.target === e.currentTarget) show = false;
        }}
        onkeydown={(e) => {
            if (e.key === 'Escape') show = false;
        }}
    >
        <div
            class="bg-base-100 rounded-2xl shadow-2xl border border-base-300 w-full max-w-sm"
            role="document"
            onclick={(e) => e.stopPropagation()}
            onkeydown={(e) => e.stopPropagation()}
        >
            <div class="flex items-center justify-between p-5 border-b border-base-200">
                <h3 class="text-lg font-bold">Editar CPE</h3>
                <button
                    class="btn btn-ghost btn-sm btn-circle"
                    onclick={() => (show = false)}>✕</button
                >
            </div>

            <div class="p-5 flex flex-col gap-4">
                {#if editError}
                    <div class="alert alert-error py-2 text-sm">{editError}</div>
                {/if}

                <div>
                    <label class="label pb-1"
                        ><span class="label-text text-xs font-bold uppercase opacity-60"
                            >MAC Address</span
                        ></label
                    >
                    <input
                        type="text"
                        readonly
                        value={cpe.cpe_mac}
                        class="input input-bordered input-sm w-full font-mono opacity-60 cursor-not-allowed"
                    />
                </div>

                <div>
                    <label class="label pb-1"
                        ><span class="label-text text-xs font-bold uppercase opacity-60"
                            >Hostname / Alias</span
                        ></label
                    >
                    <input
                        type="text"
                        class="input input-bordered input-sm w-full"
                        placeholder="Ej: Casa García"
                        bind:value={editHostname}
                    />
                    <p class="text-xs opacity-50 mt-1">
                        Se mostrará como nombre del CPE en el sistema.
                    </p>
                </div>
            </div>

            <div class="flex justify-end gap-2 p-5 border-t border-base-200">
                <button class="btn btn-ghost btn-sm" onclick={() => (show = false)}
                    >Cancelar</button
                >
                <button
                    class="btn btn-primary btn-sm"
                    onclick={saveEdit}
                    disabled={editSaving}
                >
                    {#if editSaving}<span class="loading loading-spinner loading-xs"></span>{/if}
                    Guardar
                </button>
            </div>
        </div>
    </div>
{/if}

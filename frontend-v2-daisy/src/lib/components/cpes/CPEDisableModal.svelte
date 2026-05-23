<script lang="ts">
    import { disableCPE } from "$lib/api";
    import type { CPEGlobalInfo } from "$lib/types/cpe";

    let {
        show = $bindable(false),
        cpe,
        onconfirm,
    }: {
        show: boolean;
        cpe: CPEGlobalInfo | null;
        onconfirm?: () => void;
    } = $props();

    let disabling = $state(false);
    let disableError = $state<string | null>(null);

    $effect(() => {
        if (cpe) disableError = null;
    });

    async function confirmDisable() {
        if (!cpe) return;
        disabling = true;
        disableError = null;
        try {
            await disableCPE(cpe.cpe_mac);
            show = false;
            onconfirm?.();
        } catch (e: any) {
            disableError = e?.response?.data?.detail ?? "Error al deshabilitar.";
        } finally {
            disabling = false;
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
                <h3 class="text-lg font-bold text-warning">Deshabilitar CPE</h3>
                <button
                    class="btn btn-ghost btn-sm btn-circle"
                    onclick={() => (show = false)}>✕</button
                >
            </div>
            <div class="p-5">
                {#if disableError}
                    <div class="alert alert-error py-2 text-sm mb-3">{disableError}</div>
                {/if}
                <p class="text-sm">
                    ¿Confirmas que deseas deshabilitar el CPE <strong>{cpe.cpe_hostname ?? cpe.cpe_mac}</strong>?
                </p>
                <p class="text-xs opacity-50 mt-2">
                    El CPE quedará inactivo pero permanecerá en la base de datos. Puedes
                    eliminarlo después.
                </p>
            </div>
            <div class="flex justify-end gap-2 p-5 border-t border-base-200">
                <button class="btn btn-ghost btn-sm" onclick={() => (show = false)}
                    >Cancelar</button
                >
                <button
                    class="btn btn-warning btn-sm"
                    onclick={confirmDisable}
                    disabled={disabling}
                >
                    {#if disabling}<span class="loading loading-spinner loading-xs"></span>{/if}
                    Deshabilitar
                </button>
            </div>
        </div>
    </div>
{/if}

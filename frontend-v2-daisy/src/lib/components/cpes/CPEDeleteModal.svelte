<script lang="ts">
    import { deleteCPE } from "$lib/api";
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

    let deleting = $state(false);
    let deleteError = $state<string | null>(null);

    $effect(() => {
        if (cpe) deleteError = null;
    });

    async function confirmDelete() {
        if (!cpe) return;
        deleting = true;
        deleteError = null;
        try {
            await deleteCPE(cpe.cpe_mac);
            show = false;
            onconfirm?.();
        } catch (e: any) {
            deleteError =
                e?.response?.data?.detail ??
                "No se puede eliminar. Deshabilite el CPE primero.";
        } finally {
            deleting = false;
        }
    }
</script>

{#if show && cpe}
    <div
        style="position:fixed;inset:0;z-index:100;display:flex;align-items:center;justify-content:center;padding:1rem;background:rgba(0,0,0,0.5);backdrop-filter:blur(4px);"
        onclick={(e) => {
            if (e.target === e.currentTarget) show = false;
        }}
    >
        <div
            class="bg-base-100 rounded-2xl shadow-2xl border border-base-300 w-full max-w-sm"
        >
            <div class="flex items-center justify-between p-5 border-b border-base-200">
                <h3 class="text-lg font-bold text-error">Eliminar CPE</h3>
                <button
                    class="btn btn-ghost btn-sm btn-circle"
                    onclick={() => (show = false)}>✕</button
                >
            </div>
            <div class="p-5">
                {#if deleteError}
                    <div class="alert alert-error py-2 text-sm mb-3">{deleteError}</div>
                {/if}
                <p class="text-sm">
                    ¿Confirmas que deseas eliminar <strong>permanentemente</strong> el CPE
                    <strong>{cpe.cpe_hostname ?? cpe.cpe_mac}</strong>?
                </p>
                <p class="text-xs text-error mt-2 font-semibold">
                    ⚠ Esta acción no se puede deshacer.
                </p>
            </div>
            <div class="flex justify-end gap-2 p-5 border-t border-base-200">
                <button class="btn btn-ghost btn-sm" onclick={() => (show = false)}
                    >Cancelar</button
                >
                <button
                    class="btn btn-error btn-sm"
                    onclick={confirmDelete}
                    disabled={deleting}
                >
                    {#if deleting}<span class="loading loading-spinner loading-xs"></span
                        >{/if}
                    Eliminar
                </button>
            </div>
        </div>
    </div>
{/if}

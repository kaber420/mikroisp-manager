<script lang="ts">
    import { deleteAP } from "$lib/api";
    import type { AP } from "$lib/types/ap";

    // Propiedades usando runas de Svelte 5
    let {
        show = $bindable(false),
        target = null,
        onconfirm,
    } = $props<{
        show: boolean;
        target: AP | null;
        onconfirm?: () => void;
    }>();

    // Estado local
    let deleteLoading = $state(false);
    let deleteError = $state<string | null>(null);

    // Limpiar errores cuando cambie el target o la visibilidad
    $effect(() => {
        if (show) {
            deleteError = null;
            deleteLoading = false;
        }
    });

    async function confirmDelete() {
        if (!target) return;
        deleteLoading = true;
        deleteError = null;
        try {
            await deleteAP(target.host);
            show = false;
            if (onconfirm) onconfirm();
        } catch (e: any) {
            deleteError = e?.response?.data?.detail ?? "Error al eliminar el AP.";
        } finally {
            deleteLoading = false;
        }
    }
</script>

{#if show && target}
    <div
        style="position:fixed;inset:0;z-index:200;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;padding:1rem;"
        role="dialog"
        aria-modal="true"
    >
        <div
            style="background:var(--color-base-100);border-radius:1rem;width:100%;max-width:400px;box-shadow:0 25px 50px -12px rgba(0,0,0,0.4);padding:1.5rem;display:flex;flex-direction:column;gap:1rem;"
        >
            <h3
                style="margin:0;font-size:1.1rem;font-weight:700;color:oklch(from var(--color-error) l c h);"
            >
                🗑️ Eliminar Access Point
            </h3>

            {#if deleteError}
                <div class="alert alert-error alert-sm py-2">
                    <span style="font-size:0.85rem;">{deleteError}</span>
                </div>
            {/if}

            <p style="margin:0;font-size:0.9rem;opacity:0.8;">
                ¿Estás seguro de que deseas eliminar el AP
                <strong style="font-family:monospace;"
                    >{target.host}</strong
                >?
                {#if target.hostname}
                    <span style="opacity:0.65;">({target.hostname})</span>
                {/if}
                Esta acción no se puede deshacer.
            </p>
            <div style="display:flex;gap:0.5rem;justify-content:flex-end;">
                <button
                    class="btn btn-ghost btn-sm"
                    onclick={() => (show = false)}>Cancelar</button
                >
                <button
                    class="btn btn-error btn-sm"
                    onclick={confirmDelete}
                    disabled={deleteLoading}
                >
                    {#if deleteLoading}
                        <span class="loading loading-spinner loading-xs"></span>
                    {/if}
                    Eliminar
                </button>
            </div>
        </div>
    </div>
{/if}

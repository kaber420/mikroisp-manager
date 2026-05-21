<script lang="ts">
    import { deleteZona } from "$lib/api";
    import { notify } from "$lib/stores/notifications";
    import type { Zona } from "$lib/types/zona";

    let {
        show = $bindable(false),
        target,
        onconfirm,
    } = $props<{
        show: boolean;
        target: Zona | null;
        onconfirm?: () => void;
    }>();

    let deleteLoading = $state(false);

    async function confirmDelete() {
        if (!target) return;
        deleteLoading = true;
        try {
            await deleteZona(target.id);
            show = false;
            notify.success("Zona eliminada correctamente.");
            if (onconfirm) onconfirm();
        } catch (e: any) {
            notify.error(e?.response?.data?.detail ?? "Error al eliminar la zona.");
            show = false;
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
            style="background:var(--color-base-100);border-radius:1rem;width:100%;max-width:380px;box-shadow:0 25px 50px -12px rgba(0,0,0,0.4);padding:1.5rem;display:flex;flex-direction:column;gap:1rem;"
        >
            <h3 style="margin:0;font-size:1.1rem;font-weight:700;color:var(--color-error);">
                🗑️ Eliminar Zona
            </h3>
            <p style="margin:0;font-size:0.9rem;opacity:0.8;">
                ¿Estás seguro de que quieres eliminar la zona
                <strong>{target.nombre}</strong>? Esta acción no se puede deshacer.
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

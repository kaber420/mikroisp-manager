<script lang="ts">
    import { deleteUser } from "$lib/api";
    import type { User } from "$lib/types/user";

    // Propiedades usando runas de Svelte 5
    let {
        show = $bindable(false),
        target = null,
        onconfirm,
    } = $props<{
        show: boolean;
        target: User | null;
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
            await deleteUser(target.username);
            show = false;
            if (onconfirm) onconfirm();
        } catch (e: any) {
            deleteError = e?.response?.data?.detail ?? "Error al eliminar el usuario.";
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
            <h3
                style="margin:0;font-size:1.1rem;font-weight:700;color:var(--color-error);"
            >
                🗑️ Eliminar Usuario
            </h3>

            {#if deleteError}
                <div class="alert alert-error alert-sm py-2">
                    <span style="font-size:0.85rem;">{deleteError}</span>
                </div>
            {/if}

            <p style="margin:0;font-size:0.9rem;opacity:0.8;">
                ¿Estás seguro de que quieres eliminar al usuario
                <strong>{target.username}</strong>? Esta acción no se
                puede deshacer.
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

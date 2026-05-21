<script lang="ts">
    import { createZona } from "$lib/api";
    import { notify } from "$lib/stores/notifications";
    import type { ZonaCreate } from "$lib/types/zona";

    let {
        show = $bindable(false),
        onsave,
    } = $props<{
        show: boolean;
        onsave?: () => void;
    }>();

    let fNombre = $state("");
    let modalLoading = $state(false);

    $effect(() => {
        if (show) {
            fNombre = "";
            modalLoading = false;
        }
    });

    async function saveZona() {
        modalLoading = true;
        try {
            const payload: ZonaCreate = { nombre: fNombre.trim() };
            await createZona(payload);
            show = false;
            notify.success("Zona creada correctamente.");
            if (onsave) onsave();
        } catch (e: any) {
            notify.error(e?.response?.data?.detail ?? "Error al guardar la zona.");
        } finally {
            modalLoading = false;
        }
    }
</script>

{#if show}
    <div
        style="position:fixed;inset:0;z-index:200;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;padding:1rem;"
        role="dialog"
        aria-modal="true"
    >
        <div
            style="background:var(--color-base-100);border-radius:1rem;width:100%;max-width:440px;box-shadow:0 25px 50px -12px rgba(0,0,0,0.4);overflow:hidden;"
        >
            <!-- Header -->
            <div
                style="padding:1.25rem 1.5rem;border-bottom:1px solid oklch(from var(--color-base-content) l c h / 0.12);display:flex;align-items:center;justify-content:space-between;"
            >
                <h3 style="margin:0;font-size:1.1rem;font-weight:700;">➕ Nueva Zona</h3>
                <button class="btn btn-ghost btn-sm btn-circle" onclick={() => (show = false)}>✕</button>
            </div>

            <!-- Body -->
            <form
                onsubmit={(e) => { e.preventDefault(); saveZona(); }}
                style="padding:1.5rem;display:flex;flex-direction:column;gap:1rem;"
            >
                <label class="form-control w-full">
                    <div class="label">
                        <span class="label-text font-semibold">Nombre *</span>
                    </div>
                    <input
                        class="input input-bordered input-sm w-full"
                        type="text"
                        bind:value={fNombre}
                        placeholder="ej: Zona Norte, Centro..."
                        required
                    />
                </label>

                <div style="display:flex;gap:0.5rem;justify-content:flex-end;padding-top:0.25rem;">
                    <button
                        type="button"
                        class="btn btn-ghost btn-sm"
                        onclick={() => (show = false)}>Cancelar</button
                    >
                    <button
                        type="submit"
                        class="btn btn-primary btn-sm"
                        disabled={modalLoading}
                    >
                        {#if modalLoading}
                            <span class="loading loading-spinner loading-xs"></span>
                        {/if}
                        Crear Zona
                    </button>
                </div>
            </form>
        </div>
    </div>
{/if}

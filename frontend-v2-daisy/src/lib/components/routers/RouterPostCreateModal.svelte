<script lang="ts">
    import type { Router } from "$lib/types/router";

    // Propiedades usando runas de Svelte 5
    let {
        show = $bindable(false),
        target = null,
        onprovision,
    } = $props<{
        show: boolean;
        target: Router | null;
        onprovision?: () => void;
    }>();
</script>

{#if show && target}
    <div
        style="position:fixed;inset:0;z-index:200;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;padding:1rem;"
        role="dialog"
        aria-modal="true"
    >
        <div
            style="background:var(--color-base-100);border-radius:1rem;width:100%;max-width:440px;box-shadow:0 25px 50px -12px rgba(0,0,0,0.4);padding:1.5rem;display:flex;flex-direction:column;gap:1rem;"
        >
            <h3 style="margin:0;font-size:1.1rem;font-weight:700;display:flex;align-items:center;gap:0.5rem;">
                🔐 ¿Aprovisionar ahora?
            </h3>
            <p style="margin:0;font-size:0.9rem;opacity:0.8;">
                El router <strong style="font-family:monospace;">{target.host}</strong> fue creado exitosamente.
                El aprovisionamiento habilita la conexión segura (API-SSL) para que OmniWISP pueda monitorear y gestionar el router.
            </p>
            <div style="display:flex;gap:0.5rem;justify-content:flex-end;">
                <button
                    class="btn btn-ghost btn-sm"
                    onclick={() => { show = false; }}
                >Después</button>
                <button
                    class="btn btn-success btn-sm text-white"
                    onclick={() => {
                        show = false;
                        if (onprovision) onprovision();
                    }}
                >
                    🔐 Sí, Aprovisionar
                </button>
            </div>
        </div>
    </div>
{/if}

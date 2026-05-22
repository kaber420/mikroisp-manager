<script lang="ts">
    import { goto } from "$app/navigation";
    import type { Snippet } from "svelte";

    export interface AdminToolbarProps {
        title: string;          // Título principal de la sección
        subtitle?: string;       // Subtítulo, descripción o conteos simples
        backUrl?: string;        // URL opcional para el botón Volver (si no se pasa, no se renderiza)
        stats?: Snippet;        // Fragmento opcional para métricas complejas (ej. Routers Online/Offline)
        actions?: Snippet;      // Fragmento opcional para botones principales (ej. Nuevo Cliente)
        tabs?: Snippet;         // Fragmento opcional para menús de pestañas inferiores (ej. Detalle de Cliente)
    }

    let {
        title,
        subtitle,
        backUrl,
        stats,
        actions,
        tabs
    }: AdminToolbarProps = $props();
</script>

<div
    class="glass-card-flat"
    style="border-radius:1rem;display:flex;flex-direction:column;overflow:hidden;"
>
    <div style="padding:1.25rem 1.5rem;display:flex;flex-direction:column;gap:0.75rem;">
        <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:0.75rem;">
            <!-- Grupo Izquierdo: Volver, Título/Subtítulo y Métricas -->
            <div style="display:flex;align-items:center;gap:1.25rem;flex-wrap:wrap;">
                <div style="display:flex;align-items:center;gap:0.75rem;">
                    {#if backUrl}
                        <button
                            class="btn btn-ghost btn-sm btn-square"
                            onclick={() => goto(backUrl)}
                            title="Volver"
                        >
                            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
                            </svg>
                        </button>
                    {/if}
                    <div>
                        <h1 style="margin:0;font-size:1.5rem;font-weight:800;letter-spacing:-0.025em;line-height:1.2;">
                            {title}
                        </h1>
                        {#if subtitle}
                            <p style="margin:0.25rem 0 0;font-size:0.85rem;opacity:0.5;line-height:1.2;">
                                {subtitle}
                            </p>
                        {/if}
                    </div>
                </div>

                {#if stats}
                    {@render stats()}
                {/if}
            </div>

            <!-- Grupo Derecho: Botones y Acciones -->
            {#if actions}
                <div style="display:flex;align-items:center;gap:0.75rem;flex-wrap:wrap;">
                    {@render actions()}
                </div>
            {/if}
        </div>
    </div>

    <!-- Pestañas de Navegación Inferior (Opcional) -->
    {#if tabs}
        {@render tabs()}
    {/if}
</div>

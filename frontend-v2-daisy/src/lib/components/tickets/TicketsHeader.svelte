<script lang="ts">
    import type { TicketType } from "$lib/types/ticket";

    interface Props {
        total: number;
        filterType: TicketType | "all";
        onOpenModal: () => void;
        onFilterChange: (type: TicketType | "all") => void;
    }

    let { total, filterType, onOpenModal, onFilterChange }: Props = $props();

    const TABS: [TicketType | "all", string][] = [
        ["all", "📋 Todos"],
        ["support", "🛠️ Soporte"],
        ["installation", "🔧 Instalación"],
    ];
</script>

<div
    class="glass-card-flat"
    style="border-radius:1rem;display:flex;flex-direction:column;overflow:hidden;"
>
    <!-- Título + botón nuevo ticket -->
    <div style="padding:1.25rem 1.5rem;display:flex;flex-direction:column;gap:0.75rem;">
        <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:0.75rem;">
            <div>
                <h1 class="text-3xl font-black bg-gradient-to-br from-primary to-secondary bg-clip-text text-transparent drop-shadow-sm">
                    Tickets de Soporte
                </h1>
                <p style="margin:0.25rem 0 0;font-size:0.85rem;opacity:0.5;">
                    {total} ticket{total !== 1 ? "s" : ""} registrados
                </p>
            </div>
            <div style="display:flex;align-items:center;gap:0.75rem;flex-wrap:wrap;">
                <button class="btn btn-primary btn-sm gap-2" onclick={onOpenModal}>
                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                    </svg>
                    Nuevo Ticket
                </button>
            </div>
        </div>
    </div>

    <!-- Pestañas de tipo -->
    <div
        style="background:oklch(from var(--color-base-content) l c h / 0.02);border-top:1px solid oklch(from var(--color-base-content) l c h / 0.08);padding:0 1.5rem;display:flex;gap:1.5rem;"
        role="tablist"
    >
        {#each TABS as [val, label]}
            <button
                role="tab"
                aria-selected={filterType === val}
                onclick={() => onFilterChange(val)}
                style="padding:0.85rem 0;font-size:0.85rem;font-weight:{filterType === val ? '800' : '600'};color:{filterType === val ? 'oklch(from var(--color-primary) l c h)' : 'inherit'};opacity:{filterType === val ? '1' : '0.5'};border-bottom:3px solid {filterType === val ? 'oklch(from var(--color-primary) l c h)' : 'transparent'};background:none;cursor:pointer;transition:all 0.2s;"
            >
                {label}
            </button>
        {/each}
    </div>
</div>

<script lang="ts">
    import { onMount } from 'svelte';
    
    let { 
        pools = $bindable([]), 
        onSelect,
        techId = "",
        isConnected = $bindable(false),
        isLoading = $bindable(false)
    } = $props<{
        pools?: any[];
        onSelect?: (pool: any) => void;
        techId?: string;
        isConnected?: boolean;
        isLoading?: boolean;
    }>();

    export function refreshPool() {
        fetchPools();
    }

    async function fetchPools() {
        isLoading = true;
        try {
            isConnected = true;
            // Simulated fetch
            pools = [];
        } catch (e) {
            isConnected = false;
        } finally {
            isLoading = false;
        }
    }

    onMount(() => {
        fetchPools();
    });
</script>

<div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
    {#each pools as pool}
        <button 
            class="glass-card-flat p-4 text-left hover:scale-[1.02] transition-all hover:bg-primary/5 group"
            onclick={() => onSelect(pool)}
        >
            <div class="flex items-center gap-3">
                <div class="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center text-xl">
                    📸
                </div>
                <div>
                    <h5 class="font-bold text-sm tracking-tight">{pool.name}</h5>
                    <p class="text-[10px] opacity-50 uppercase font-bold">{pool.participantCount} Participantes</p>
                </div>
            </div>
        </button>
    {:else}
        <div class="col-span-full py-12 text-center opacity-30 italic text-sm">
            No hay salas activas en este momento.
        </div>
    {/each}
</div>

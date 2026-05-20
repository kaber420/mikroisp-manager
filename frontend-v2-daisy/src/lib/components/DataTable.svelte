<script lang="ts">
    import { onMount, untrack } from 'svelte';

    type T = any;
    
    interface Props {
        // Client-side mode
        items?: T[] | null;
        
        // Server-side mode
        loadData?: (page: number, pageSize: number, search: string) => Promise<{ items: T[], total: number, total_pages: number }>;
        initialItems?: T[];
        initialTotal?: number;
        initialPage?: number;
        initialTotalPages?: number;
        
        // Snippets
        header: import('svelte').Snippet;
        row: import('svelte').Snippet<[T]>;
        filters?: import('svelte').Snippet;
    }

    let { 
        items = null,
        loadData = null,
        initialItems = [],
        initialTotal = 0,
        initialPage = 1,
        initialTotalPages = 1,
        header,
        row,
        filters
    } = $props<Props>();

    // Internal state - use untrack to avoid state_referenced_locally warnings if intended
    let currentPage = $state(initialPage);
    let totalPages = $state(initialTotalPages);
    let totalItems = $state(initialTotal);
    let currentItems = $state(items || initialItems);
    let pageSize = $state(10);
    let searchQuery = $state("");
    let loading = $state(false);

    // Sync items and apply client-side search filtering if no remote loadData is active
    $effect(() => {
        if (items !== null) {
            if (!loadData && searchQuery) {
                const query = searchQuery.toLowerCase().trim();
                currentItems = items.filter((item: any) => {
                    return Object.entries(item).some(([_, val]) => {
                        if (val === null || val === undefined || typeof val === 'object' || typeof val === 'function') return false;
                        return String(val).toLowerCase().includes(query);
                    });
                });
            } else {
                currentItems = items;
            }
        }
    });

    onMount(() => {
        if (loadData && items === null) {
            untrack(() => refresh());
        }
    });

    export async function refresh() {
        if (!loadData) return;
        loading = true;
        try {
            const res = await loadData(currentPage, pageSize, searchQuery);
            currentItems = res.items;
            totalItems = res.total;
            totalPages = res.total_pages;
        } catch (e) {
            console.error("Error loading data:", e);
        } finally {
            loading = false;
        }
    }

    function changePage(p: number) {
        if (p < 1 || p > totalPages) return;
        currentPage = p;
        refresh();
    }

    function handleSearch(e: Event) {
        searchQuery = (e.target as HTMLInputElement).value;
        currentPage = 1;
        refresh();
    }
</script>

<div class="flex flex-col gap-4">
    <!-- Top Bar -->
    <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div class="flex items-center gap-2 w-full sm:w-auto">
            <div class="relative w-full sm:w-64">
                <span class="absolute inset-y-0 left-3 flex items-center opacity-30">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
                        <path fill-rule="evenodd" d="M9 3.5a5.5 5.5 0 1 0 0 11 5.5 5.5 0 0 0 0-11ZM2 9a7 7 0 1 1 12.452 4.391l3.328 3.329a.75.75 0 1 1-1.06 1.06l-3.329-3.328A7 7 0 0 1 2 9Z" clip-rule="evenodd" />
                    </svg>
                </span>
                <input 
                    type="text" 
                    placeholder="Buscar..." 
                    class="input input-bordered input-sm w-full pl-9 rounded-lg"
                    value={searchQuery}
                    oninput={handleSearch}
                />
            </div>
            {#if filters}
                {@render filters()}
            {/if}
        </div>

        {#if loadData}
            <div class="text-xs opacity-50 font-medium">
                Total: {totalItems} registros
            </div>
        {/if}
    </div>

    <!-- Table Container -->
    <div class="overflow-x-auto bg-base-100 rounded-xl shadow-sm border border-base-content/5 relative min-h-[200px]">
        {#if loading}
            <div class="absolute inset-0 bg-base-100/50 backdrop-blur-[1px] z-10 flex items-center justify-center">
                <span class="loading loading-spinner loading-md text-primary"></span>
            </div>
        {/if}
        
        <table class="table table-sm table-zebra w-full text-xs">
            <thead class="bg-base-200/50">
                {@render header()}
            </thead>
            <tbody>
                {#each currentItems as item}
                    {@render row(item)}
                {:else}
                    <tr>
                        <td colspan="20" class="py-20 text-center opacity-30 italic">
                            No se encontraron resultados
                        </td>
                    </tr>
                {/each}
            </tbody>
        </table>
    </div>

    <!-- Pagination -->
    {#if loadData && totalPages > 1}
        <div class="flex justify-between items-center px-1">
            <span class="text-[10px] opacity-40 font-bold uppercase tracking-widest">Página {currentPage} de {totalPages}</span>
            <div class="join">
                <button 
                    class="join-item btn btn-xs px-4" 
                    disabled={currentPage === 1 || loading}
                    onclick={() => changePage(currentPage - 1)}
                >Anterior</button>
                <button 
                    class="join-item btn btn-xs px-4" 
                    disabled={currentPage === totalPages || loading}
                    onclick={() => changePage(currentPage + 1)}
                >Siguiente</button>
            </div>
        </div>
    {/if}
</div>

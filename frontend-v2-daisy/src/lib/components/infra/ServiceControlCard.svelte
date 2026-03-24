<script lang="ts">
    let { title, status, icon, color = "primary", onToggle, isLoading = false } = $props<{
        title: string;
        status: boolean | string;
        icon: string;
        color?: string;
        onToggle: () => void;
        isLoading?: boolean;
    }>();

    const isActive = $derived(status === true || status === "true" || status === "enabled");
</script>

<div class="glass-card-flat p-4 flex items-center justify-between group">
    <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-{color}/10 text-{color} flex items-center justify-center text-xl">
            <span>{icon}</span>
        </div>
        <div>
            <h4 class="font-bold text-sm">{title}</h4>
            <p class="text-[10px] opacity-50 uppercase tracking-wider font-bold">
                {isActive ? 'Activo' : 'Inactivo'}
            </p>
        </div>
    </div>

    <button 
        class="btn btn-sm btn-circle {isActive ? 'btn-success' : 'btn-ghost border-base-300'}"
        onclick={onToggle}
        disabled={isLoading}
    >
        {#if isLoading}
            <span class="loading loading-spinner loading-xs"></span>
        {:else if isActive}
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
                <path fill-rule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clip-rule="evenodd" />
            </svg>
        {:else}
            <div class="w-2 h-2 rounded-full bg-base-content/20"></div>
        {/if}
    </button>
</div>

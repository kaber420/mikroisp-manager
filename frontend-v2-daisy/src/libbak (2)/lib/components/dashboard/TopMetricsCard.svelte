<script lang="ts">
    import { onMount, onDestroy } from 'svelte';

    let { data } = $props<{ data: any }>();

    let currentTabIndex = $state(0);
    let interval: any;

    const tabs = [
        { id: 'signal', label: 'Peores Señales (dBm)', icon: '📉', color: 'rose' },
        { id: 'airtime', label: 'Uso de Aire (APs)', icon: '🌬️', color: 'amber' },
        { id: 'consumption', label: 'Más Consumo (WAN)', icon: '🚀', color: 'blue' },
        { id: 'offline', label: 'Más Tiempo Caídos', icon: '⏱️', color: 'slate' }
    ];

    onMount(() => {
        interval = setInterval(() => {
            currentTabIndex = (currentTabIndex + 1) % tabs.length;
        }, 8000);
    });

    onDestroy(() => {
        if (interval) clearInterval(interval);
    });

    function getItems(tabId: string) {
        return data.tops?.[tabId] || [];
    }
</script>

<div class="glass-card p-5 flex flex-col h-full min-h-[460px]">
    <div class="flex items-center justify-between mb-6">
        <div class="flex items-center gap-3">
            <span class="text-xl">{tabs[currentTabIndex].icon}</span>
            <h3 class="font-bold text-lg tracking-tight">{tabs[currentTabIndex].label}</h3>
        </div>
        <div class="flex gap-1">
            {#each tabs as tab, i}
                <button 
                    onclick={() => currentTabIndex = i}
                    class="w-2.5 h-2.5 rounded-full transition-all duration-300 {currentTabIndex === i ? 'bg-primary w-6' : 'bg-base-content/10'}"
                ></button>
            {/each}
        </div>
    </div>

    <div class="flex-1 space-y-3">
        {#each getItems(tabs[currentTabIndex].id) as item, i}
            <div class="flex items-center justify-between p-3 rounded-2xl bg-base-200/40 border border-base-content/5 group hover:bg-base-200/70 transition-all duration-300">
                <div class="flex items-center gap-4 min-w-0">
                    <div class="w-8 h-8 rounded-xl bg-base-100 flex items-center justify-center font-black text-xs opacity-50 border border-base-content/5 group-hover:scale-110 transition-transform">
                        {i + 1}
                    </div>
                    <div class="flex flex-col min-w-0">
                        <span class="text-sm font-bold truncate opacity-90">{item.name || item.host || item.mac}</span>
                        <span class="text-[10px] opacity-40 font-medium">{item.router_host || item.info || 'Dispositivo'}</span>
                    </div>
                </div>
                
                <div class="flex flex-col items-end shrink-0">
                    <span class="text-sm font-black text-{tabs[currentTabIndex].color}-500">
                        {item.value} {item.unit || ''}
                    </span>
                    {#if item.subvalue}
                        <span class="text-[10px] opacity-30 font-medium">{item.subvalue}</span>
                    {/if}
                </div>
            </div>
        {:else}
            <div class="flex flex-col items-center justify-center h-full opacity-20 py-20 grayscale">
                <span class="text-4xl mb-4">🏜️</span>
                <p class="text-sm font-bold italic">Nada que reportar aquí...</p>
            </div>
        {/each}
    </div>
</div>

<style>
    /* Soporte para colores dinámicos en Tailwind si no están en uso */
    .text-rose-500 { color: oklch(0.645 0.246 16.439); }
    .text-amber-500 { color: oklch(0.769 0.188 70.08); }
    .text-blue-500 { color: oklch(0.623 0.214 259.815); }
    .text-slate-500 { color: oklch(0.551 0.027 264.364); }
</style>

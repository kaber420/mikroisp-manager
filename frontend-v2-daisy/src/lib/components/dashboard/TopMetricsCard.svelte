<script lang="ts">
    import { onMount, onDestroy } from 'svelte';

    let { data } = $props<{ data: any }>();

    let currentTabIndex = $state(0);
    let interval: any;
    let settingsDropdownRef: HTMLDetailsElement;

    // Default visibility matching the old frontend
    let topsVisibility = $state({
        signal: true,
        airtime: false,
        consumption: true,
        offline: true
    });

    const ALL_TABS = [
        { id: 'signal', label: 'Peores Señales (dBm)', icon: '📉', color: 'rose' },
        { id: 'airtime', label: 'Uso de Aire (APs)', icon: '🌬️', color: 'amber' },
        { id: 'consumption', label: 'Más Consumo (WAN)', icon: '🚀', color: 'blue' },
        { id: 'offline', label: 'Más Tiempo Caídos', icon: '⏱️', color: 'slate' }
    ];

    let tabs = $derived(ALL_TABS.filter(t => topsVisibility[t.id as keyof typeof topsVisibility]));

    function loadPreferences() {
        if (typeof localStorage === 'undefined') return;
        try {
            const stored = localStorage.getItem('dashboard_tops_v2');
            if (stored) {
                topsVisibility = { ...topsVisibility, ...JSON.parse(stored) };
            }
        } catch (e) {
            console.error("Error loading dashboard preferences", e);
        }
    }

    function savePreferences() {
        if (typeof localStorage === 'undefined') return;
        try {
            localStorage.setItem('dashboard_tops_v2', JSON.stringify(topsVisibility));
        } catch (e) {
            console.error("Error saving dashboard preferences", e);
        }
    }

    function toggleVisibility(id: keyof typeof topsVisibility) {
        topsVisibility[id] = !topsVisibility[id];
        if (tabs.length === 0) {
            currentTabIndex = 0;
        } else if (currentTabIndex >= tabs.length) {
            currentTabIndex = tabs.length - 1;
        }
        savePreferences();
    }

    // Close dropdown when clicking outside
    function handleClickOutside(event: MouseEvent) {
        if (settingsDropdownRef && !settingsDropdownRef.contains(event.target as Node)) {
            settingsDropdownRef.removeAttribute('open');
        }
    }

    onMount(() => {
        loadPreferences();
        document.addEventListener('click', handleClickOutside);
        
        interval = setInterval(() => {
            if (tabs.length > 0) {
                currentTabIndex = (currentTabIndex + 1) % tabs.length;
            }
        }, 8000);
    });

    onDestroy(() => {
        if (interval) clearInterval(interval);
        if (typeof document !== 'undefined') {
            document.removeEventListener('click', handleClickOutside);
        }
    });

    function formatBytes(bytes: number) {
        if (!bytes || bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    function formatBps(bps: number) {
        if (!bps || bps === 0) return '0 bps';
        const k = 1000;
        const sizes = ['bps', 'kbps', 'Mbps', 'Gbps'];
        const i = Math.floor(Math.log(bps) / Math.log(k));
        return parseFloat((bps / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    function getMappedItems(tabId: string) {
        const rawItems = data.tops?.[tabId] || [];
        return rawItems.map((item: any) => {
            if (tabId === 'signal') {
                return {
                    name: item.cpe_hostname || item.cpe_mac,
                    info: `AP: ${item.ap_host}`,
                    value: item.signal,
                    unit: 'dBm',
                    subvalue: null
                };
            }
            if (tabId === 'airtime') {
                return {
                    name: item.hostname || item.host,
                    info: 'Access Point',
                    value: item.airtime_total_usage,
                    unit: '%',
                    subvalue: null
                };
            }
            if (tabId === 'consumption') {
                const rx = formatBytes(item.wan_rx_bytes || 0);
                const tx = formatBytes(item.wan_tx_bytes || 0);
                return {
                    name: item.hostname,
                    info: item.host,
                    value: `${rx} ↓ · ${tx} ↑`,
                    unit: '',
                    subvalue: `Total: ${formatBytes(item.total_bytes || 0)} | Actual: ${formatBps(item.total_bps || 0)}`
                };
            }

            if (tabId === 'offline') {
                return {
                    name: item.hostname || item.host,
                    info: item.device_type,
                    value: item.last_checked,
                    unit: '',
                    subvalue: null
                };
            }
            return item;
        });
    }
</script>



<div class="glass-card p-5 flex flex-col h-full min-h-[460px] relative">
    <div class="flex items-center justify-between mb-6">
        <div class="flex items-center gap-3">
            {#if tabs.length > 0}
                <span class="text-xl">{tabs[currentTabIndex].icon}</span>
                <h3 class="font-bold text-lg tracking-tight">{tabs[currentTabIndex].label}</h3>
            {:else}
                <span class="text-xl">⚙️</span>
                <h3 class="font-bold text-lg tracking-tight opacity-50">Tops Ocultos</h3>
            {/if}
        </div>
        
        <div class="flex items-center gap-3">
            <!-- Indicator Dots -->
            <div class="flex gap-1">
                {#each tabs as tab, i}
                    <button 
                        onclick={() => currentTabIndex = i}
                        class="w-2.5 h-2.5 rounded-full transition-all duration-300 {currentTabIndex === i ? 'bg-primary w-6' : 'bg-base-content/10'}"
                        aria-label={`Ver ${tab.label}`}
                    ></button>
                {/each}
            </div>
            
            <!-- Settings Dropdown -->
            <details class="dropdown dropdown-end" bind:this={settingsDropdownRef}>
                <summary class="btn btn-sm btn-ghost btn-circle">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="opacity-60"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>
                </summary>
                <div class="dropdown-content z-[1] menu p-4 shadow-xl bg-base-100 rounded-box w-64 border border-base-200 mt-2">
                    <h4 class="text-xs font-bold uppercase opacity-50 mb-3 tracking-wider">Tops Visibles</h4>
                    <ul class="space-y-2">
                        {#each ALL_TABS as tab}
                            <li class="p-0">
                                <label class="label cursor-pointer flex justify-between p-2 rounded-lg hover:bg-base-200 transition-colors">
                                    <span class="label-text flex items-center gap-2">
                                        <span>{tab.icon}</span>
                                        <span class="text-xs font-semibold">{tab.label.split('(')[0].trim()}</span>
                                    </span> 
                                    <input 
                                        type="checkbox" 
                                        class="toggle toggle-sm toggle-primary" 
                                        checked={topsVisibility[tab.id as keyof typeof topsVisibility]} 
                                        onchange={() => toggleVisibility(tab.id as keyof typeof topsVisibility)}
                                    />
                                </label>
                            </li>
                        {/each}
                    </ul>
                    <div class="divider mt-2 mb-1"></div>
                    <p class="text-[10px] text-center opacity-40">Rotan automáticamente cada 8s</p>
                </div>
            </details>
        </div>
    </div>

    <div class="flex-1 space-y-3">
        {#if tabs.length > 0}
            <!-- Use a keyed block to force transition/re-render when tab changes -->
            {#key currentTabIndex}
                <div class="space-y-3 animate-fade-in">
                    {#each getMappedItems(tabs[currentTabIndex].id) as item, i}
                        <div class="flex items-center justify-between p-3 rounded-2xl bg-base-200/40 border border-base-content/5 group hover:bg-base-200/70 transition-all duration-300">
                            <div class="flex items-center gap-4 min-w-0">
                                <div class="w-8 h-8 rounded-xl bg-base-100 flex items-center justify-center font-black text-xs opacity-50 border border-base-content/5 group-hover:scale-110 transition-transform">
                                    {i + 1}
                                </div>
                                <div class="flex flex-col min-w-0">
                                    <span class="text-sm font-bold truncate opacity-90">{item.name || 'Sin nombre'}</span>
                                    <span class="text-[10px] opacity-40 font-medium">{item.info || 'Dispositivo'}</span>
                                </div>
                            </div>
                            
                            <div class="flex flex-col items-end shrink-0">
                                <span class="text-sm font-black text-{tabs[currentTabIndex].color}-500">
                                    {item.value || 0} {item.unit || ''}
                                </span>
                                {#if item.subvalue}
                                    <span class="text-[10px] opacity-30 font-medium">{item.subvalue}</span>
                                {/if}
                            </div>
                        </div>
                    {:else}
                        <div class="flex flex-col items-center justify-center h-full opacity-20 py-16 grayscale">
                            <span class="text-4xl mb-4">🏜️</span>
                            <p class="text-sm font-bold italic">Nada que reportar aquí...</p>
                        </div>
                    {/each}
                </div>
            {/key}
        {:else}
            <div class="flex flex-col items-center justify-center h-full opacity-30 py-20">
                <span class="text-5xl mb-4">⚙️</span>
                <p class="text-sm font-bold">Todos los Tops están ocultos</p>
                <p class="text-xs opacity-70 mt-2">Usa el menú superior para activarlos</p>
            </div>
        {/if}
    </div>
</div>

<style>
    /* Soporte para colores dinámicos en Tailwind si no están en uso */
    .text-rose-500 { color: oklch(0.645 0.246 16.439); }
    .text-amber-500 { color: oklch(0.769 0.188 70.08); }
    .text-blue-500 { color: oklch(0.623 0.214 259.815); }
    .text-slate-500 { color: oklch(0.551 0.027 264.364); }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(4px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .animate-fade-in {
        animation: fadeIn 0.4s ease-out forwards;
    }
</style>

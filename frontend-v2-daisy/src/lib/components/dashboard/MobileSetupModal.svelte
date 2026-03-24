<script lang="ts">
    import { onMount } from 'svelte';
    import { request } from '$lib/api/index';

    let { show = $bindable(false) } = $props();

    let config: { server_url: string; ca_sha256: string } | null = $state(null);
    let loading = $state(true);
    let error = $state('');
    let activeTab = $state<'qr' | 'ca'>('qr');

    // Force unique URL for image to bypass cache
    let qrTimestamp = $derived(show ? new Date().getTime() : 0);

    $effect(() => {
        if (show) {
            loading = true;
            error = '';
            request('/security/bootstrap-config')
                .then(res => {
                    config = res;
                    loading = false;
                })
                .catch(err => {
                    error = 'No se pudo cargar la configuración de seguridad. Verifica que el CA esté generado.';
                    loading = false;
                });
        }
    });

    async function regenerateQR() {
        loading = true;
        try {
            await request('/security/bootstrap-qr/regenerate', { method: 'POST' });
            // Re-fetch config to refresh UI
            const res = await request('/security/bootstrap-config');
            config = res;
            // Hack to force image reload: close and reopen or just update timestamp wait no, timestamp is bound to show
            // but we can just add a random param
            qrTimestamp = new Date().getTime();
        } catch (e: any) {
            error = e.message || 'Error regenerando código QR';
        }
        loading = false;
    }
</script>

{#if show}
<div class="modal modal-open">
    <div class="modal-box max-w-2xl bg-gradient-to-br from-base-100 to-base-200">
        <div class="flex items-center gap-4 mb-6">
            <div class="w-12 h-12 bg-primary/20 rounded-2xl flex items-center justify-center text-2xl">📱</div>
            <div>
                <h3 class="font-black text-xl">Configura la App Móvil</h3>
                <p class="text-xs opacity-60">Escanea el código para vincular tu cuenta admin de forma segura.</p>
            </div>
        </div>
        
        <div class="tabs tabs-boxed bg-base-200/50 p-1 mb-4 flex">
            <button class="tab flex-1 {activeTab === 'qr' ? 'tab-active bg-primary text-primary-content font-bold shadow-lg' : ''}" onclick={() => activeTab = 'qr'}>
                🔑 App Móvil
            </button>
            <button class="tab flex-1 {activeTab === 'ca' ? 'tab-active bg-primary text-primary-content font-bold shadow-lg' : ''}" onclick={() => activeTab = 'ca'}>
                🛡️ Certificado CA
            </button>
        </div>

        {#if loading}
            <div class="flex flex-col items-center justify-center h-64 gap-4">
                <span class="loading loading-spinner loading-lg text-primary"></span>
                <p class="text-sm font-medium opacity-60">Cargando configuración de seguridad...</p>
            </div>
        {:else if error}
            <div class="alert alert-error shadow-lg">
                <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                <span>{error}</span>
            </div>
        {:else if config}
            {#if activeTab === 'qr'}
                <div class="bg-base-100 rounded-2xl p-6 border border-base-content/5 shadow-sm">
                    <div class="flex flex-col md:flex-row gap-8 items-center md:items-start">
                        <!-- QR Code Area -->
                        <div class="flex flex-col items-center gap-2">
                            <div class="p-4 bg-white rounded-2xl shadow-inner border border-stone-200">
                                <img 
                                    src="/api/security/bootstrap-qr.png?t={qrTimestamp}" 
                                    alt="QR Config" 
                                    class="w-48 h-48 object-contain"
                                    onerror={(e) => { (e.currentTarget as HTMLImageElement).style.display='none'; error="Error cargando imagen QR"; }}
                                />
                            </div>
                            <button class="btn btn-xs btn-ghost text-xs opacity-50 hover:opacity-100" onclick={regenerateQR}>
                                🔄 Regenerar QR
                            </button>
                        </div>
                        
                        <!-- Server Details Area -->
                        <div class="flex-1 space-y-4 w-full">
                            <h4 class="font-bold text-sm uppercase tracking-wider opacity-50 border-b border-base-content/10 pb-2">Información del Servidor</h4>
                            
                            <div class="space-y-1">
                                <span class="text-xs opacity-50 font-medium">URL del Servidor</span>
                                <div class="font-mono text-sm break-all font-bold text-primary bg-primary/10 p-2 rounded-lg border border-primary/20">
                                    {config.server_url}
                                </div>
                            </div>
                            
                            <div class="space-y-1">
                                <span class="text-xs opacity-50 font-medium">Auto-configuración Segura</span>
                                <p class="text-xs opacity-80 leading-relaxed">
                                    Abre la aplicación µMonitor V2 en tu celular, ve a <span class="badge badge-sm badge-neutral">Ajustes</span> &rarr; <span class="badge badge-sm badge-neutral">Cuentas</span> y selecciona escanear este código QR.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            {:else}
                <div class="bg-base-100 rounded-2xl p-6 border border-base-content/5 shadow-sm text-center">
                    <div class="w-16 h-16 bg-success/20 text-success rounded-full flex items-center justify-center text-3xl mx-auto mb-4">
                        🛡️
                    </div>
                    <h3 class="font-bold text-lg mb-2">Certificado de Autoridad (CA)</h3>
                    <p class="text-sm opacity-70 mb-6 max-w-md mx-auto">
                        Para que las aplicaciones móviles o otros dispositivos confíen en este servidor local, necesitas instalar el certificado CA Raíz en ellos.
                    </p>
                    
                    <div class="bg-base-200 p-4 rounded-xl mb-6 text-left border border-base-content/10 max-w-md mx-auto">
                        <span class="block text-xs uppercase tracking-widest opacity-50 font-bold mb-1">Fingerprint (SHA256)</span>
                        <code class="text-xs font-mono break-all text-success font-bold select-all tracking-tight">
                            {config.ca_sha256}
                        </code>
                    </div>
                    
                    <a href="/api/security/ca-certificate" download="umonitor-ca.crt" target="_blank" class="btn btn-success shadow-lg shadow-success/30 gap-2">
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" x2="12" y1="15" y2="3"></line></svg>
                        Descargar Certificado CA
                    </a>
                </div>
            {/if}
        {/if}

        <div class="modal-action">
            <button class="btn btn-ghost" onclick={() => show = false}>Cerrar</button>
        </div>
    </div>
</div>
{/if}


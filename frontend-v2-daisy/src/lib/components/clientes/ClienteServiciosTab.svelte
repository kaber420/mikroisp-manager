<script lang="ts">
    import type { ClientService } from '$lib/types/client';

    interface Props {
        services: ClientService[];
        servicesLoading: boolean;
        servicesError: string;
        liveStatus: Record<number, any>;
        liveStatusLoading: Record<number, boolean>;
        onsync: (svc: ClientService) => void;
        ondelete: (svc: ClientService) => void;
        onopenplan: (svc: ClientService) => void;
    }

    let {
        services,
        servicesLoading,
        servicesError,
        liveStatus,
        liveStatusLoading,
        onsync,
        ondelete,
        onopenplan,
    }: Props = $props();

    function formatBytes(bytes: number | undefined | null): string {
        if (!bytes || bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    function statusLabel(status: string): string {
        const map: Record<string, string> = {
            active: 'Activo', suspended: 'Suspendido', inactive: 'Inactivo',
        };
        return map[status] ?? status;
    }

    function statusBadgeClass(status: string): string {
        if (status === 'active') return 'badge-success';
        if (status === 'suspended') return 'badge-warning';
        return 'badge-neutral';
    }
</script>

<div class="glass-card-flat" style="border-radius:1rem;overflow:hidden;">
    <div style="padding:1rem 1.25rem;border-bottom:1px solid color-mix(in oklch,currentColor 10%,transparent);display:flex;align-items:center;justify-content:space-between;">
        <span style="font-weight:700;font-size:1rem;">Servicios de Red</span>
    </div>
    <div style="padding:1.25rem;display:flex;flex-direction:column;gap:1rem;">
        {#if servicesLoading}
            <div style="text-align:center;padding:2rem;opacity:0.5;">
                <span class="loading loading-spinner loading-md"></span>
                <p style="margin-top:0.5rem;">Cargando servicios...</p>
            </div>
        {:else if servicesError}
            <div class="alert alert-error"><span>{servicesError}</span></div>
        {:else if services.length === 0}
            <p style="text-align:center;opacity:0.5;padding:2rem;">Sin servicios configurados para este cliente.</p>
        {:else}
            {#each services as svc (svc.id)}
                {@const live = liveStatus[svc.id]}
                {@const liveLoading = liveStatusLoading[svc.id]}
                {@const isPPPoE = svc.service_type === 'pppoe'}
                <div style="border-radius:0.75rem;border:1px solid {isPPPoE ? 'color-mix(in oklch,oklch(60% 0.15 240) 40%,transparent)' : 'color-mix(in oklch,oklch(60% 0.15 280) 40%,transparent)'};padding:1rem;background:color-mix(in oklch,{isPPPoE ? 'oklch(60% 0.15 240)' : 'oklch(60% 0.15 280)'} 5%,transparent);">
                    <!-- Service header -->
                    <div style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:0.5rem;margin-bottom:0.75rem;">
                        <div style="display:flex;align-items:center;gap:0.5rem;flex-wrap:wrap;">
                            <span class="badge badge-sm" style="background:color-mix(in oklch,{isPPPoE ? 'oklch(60% 0.15 240)' : 'oklch(60% 0.15 280)'} 30%,transparent);">
                                {isPPPoE ? 'PPPoE' : 'Simple Queue'}
                            </span>
                            <span class="badge {statusBadgeClass(svc.status)} badge-sm">{statusLabel(svc.status)}</span>
                            <code style="font-size:0.85rem;font-weight:600;">{svc.pppoe_username || svc.ip_address || '—'}</code>
                        </div>
                        <!-- Actions -->
                        <div style="display:flex;gap:0.5rem;flex-shrink:0;">
                            <button class="btn btn-xs btn-warning" onclick={() => onsync(svc)} title="Sincronizar al router">
                                <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                                </svg>
                                Sync
                            </button>
                            <button class="btn btn-xs btn-info" onclick={() => onopenplan(svc)} title="Cambiar plan">
                                <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                                </svg>
                                Plan
                            </button>
                            <button class="btn btn-xs btn-error" onclick={() => ondelete(svc)} title="Eliminar servicio">
                                <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                            </button>
                        </div>
                    </div>

                    <!-- Service meta info -->
                    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:0.5rem;font-size:0.8rem;margin-bottom:0.75rem;opacity:0.7;">
                        <span>Router: <code>{svc.router_host}</code></span>
                        {#if svc.plan_name}
                            <span>Plan: <strong style="color:var(--color-primary,oklch(60% 0.15 240))">{svc.plan_name} {svc.plan_price != null ? `($${svc.plan_price.toFixed(2)})` : ''}</strong></span>
                        {/if}
                        {#if svc.billing_day}
                            <span>Día facturación: <strong>{svc.billing_day}</strong></span>
                        {/if}
                        {#if svc.notes}
                            <span>Notas: {svc.notes}</span>
                        {/if}
                    </div>

                    <!-- Live status -->
                    <div style="border-top:1px solid color-mix(in oklch,currentColor 10%,transparent);padding-top:0.75rem;">
                        {#if liveLoading}
                            <div style="display:flex;align-items:center;gap:0.5rem;opacity:0.5;font-size:0.8rem;">
                                <span class="loading loading-spinner loading-xs"></span>
                                Consultando router...
                            </div>
                        {:else if !live}
                            <p style="font-size:0.8rem;opacity:0.5;">Estado no disponible.</p>
                        {:else if live.error}
                            <p class="text-error" style="font-size:0.8rem;">Error al consultar el router.</p>
                        {:else if !live.found}
                            <p class="text-warning" style="font-size:0.8rem;">⚠ No encontrado en el router. Usa Sync para recrearlo.</p>
                        {:else if isPPPoE}
                            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:0.5rem;font-size:0.82rem;">
                                <div style="display:flex;justify-content:space-between;">
                                    <span style="opacity:0.6;">Cuenta:</span>
                                    <strong class="{live.account_status === 'Activo' ? 'text-success' : 'text-warning'}">{live.account_status ?? '—'}</strong>
                                </div>
                                <div style="display:flex;justify-content:space-between;">
                                    <span style="opacity:0.6;">Red:</span>
                                    <strong class="{live.is_online ? 'text-success' : 'text-error'}">{live.is_online ? `Online (${live.online_ip ?? ''})` : 'Offline'}</strong>
                                </div>
                                {#if live.is_online && live.uptime}
                                    <div style="display:flex;justify-content:space-between;">
                                        <span style="opacity:0.6;">Uptime:</span>
                                        <strong>{live.uptime}</strong>
                                    </div>
                                {/if}
                                {#if live.profile}
                                    <div style="display:flex;justify-content:space-between;">
                                        <span style="opacity:0.6;">Perfil:</span>
                                        <code>{live.profile}</code>
                                    </div>
                                {/if}
                                <div style="display:flex;justify-content:space-between;grid-column:1/-1;">
                                    <span style="opacity:0.6;">Uso (↑ / ↓):</span>
                                    <strong>{formatBytes(live.bytes_out)} / {formatBytes(live.bytes_in)}</strong>
                                </div>
                            </div>
                        {:else}
                            <!-- Simple Queue live -->
                            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:0.5rem;font-size:0.82rem;">
                                <div style="display:flex;justify-content:space-between;">
                                    <span style="opacity:0.6;">Nombre Queue:</span>
                                    <code>{live.name ?? '—'}</code>
                                </div>
                                <div style="display:flex;justify-content:space-between;">
                                    <span style="opacity:0.6;">Target:</span>
                                    <code>{live.target ?? svc.ip_address ?? '—'}</code>
                                </div>
                                <div style="display:flex;justify-content:space-between;">
                                    <span style="opacity:0.6;">Límite:</span>
                                    <strong>{live.max_limit ?? '—'}</strong>
                                </div>
                                <div style="display:flex;justify-content:space-between;grid-column:1/-1;">
                                    <span style="opacity:0.6;">Uso (↑ / ↓):</span>
                                    <strong>{formatBytes(live.bytes_up)} / {formatBytes(live.bytes_down)}</strong>
                                </div>
                            </div>
                        {/if}
                    </div>
                </div>
            {/each}
        {/if}
    </div>
</div>

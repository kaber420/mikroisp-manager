<script lang="ts">
    import type { ClientService } from '$lib/types/client';

    interface Props {
        open: boolean;
        service: ClientService | null;
        availablePlans: any[];
        loading: boolean;
        error: string;
        onconfirm: (planId: number) => void;
        onclose: () => void;
    }

    let { open, service, availablePlans, loading, error, onconfirm, onclose }: Props = $props();

    let selectedPlanId = $state('');

    // Reset selection when modal opens
    $effect(() => {
        if (open) selectedPlanId = '';
    });
</script>

{#if open}
    <div style="position:fixed;inset:0;z-index:1000;display:flex;align-items:center;justify-content:center;padding:1rem;background:rgba(0,0,0,0.6);">
        <div class="glass-card-flat" style="border-radius:1rem;width:100%;max-width:460px;overflow:hidden;">
            <div style="padding:1.25rem 1.5rem;font-weight:700;font-size:1.1rem;border-bottom:1px solid color-mix(in oklch,currentColor 10%,transparent);display:flex;justify-content:space-between;align-items:center;">
                <span>Cambiar Plan del Servicio</span>
                <button class="btn btn-ghost btn-xs btn-circle" onclick={onclose}>✕</button>
            </div>
            <div style="padding:1.5rem;display:flex;flex-direction:column;gap:1rem;">
                {#if service}
                    <p style="font-size:0.85rem;opacity:0.7;">
                        Servicio: <code>{service.pppoe_username || service.ip_address}</code>
                        · Router: <code>{service.router_host}</code>
                    </p>
                {/if}
                {#if loading}
                    <div style="text-align:center;padding:1.5rem;"><span class="loading loading-spinner loading-md"></span></div>
                {:else}
                    <div>
                        <label class="label" style="font-size:0.85rem;">Nuevo Plan</label>
                        <select bind:value={selectedPlanId} class="select select-bordered w-full">
                            <option value="">Selecciona un plan...</option>
                            {#each availablePlans as plan (plan.id)}
                                <option value={String(plan.id)}>{plan.name} — ${plan.price ?? '0.00'} ({plan.max_limit ?? 'N/A'})</option>
                            {/each}
                        </select>
                        {#if availablePlans.length === 0}
                            <p style="font-size:0.8rem;opacity:0.5;margin-top:0.5rem;">No hay planes disponibles para este tipo de servicio.</p>
                        {/if}
                    </div>
                    {#if error}
                        <div class="alert alert-error p-2 text-sm"><span>{error}</span></div>
                    {/if}
                    <div style="display:flex;justify-content:flex-end;gap:0.75rem;padding-top:0.5rem;">
                        <button class="btn btn-ghost btn-sm" onclick={onclose}>Cancelar</button>
                        <button
                            class="btn btn-primary btn-sm"
                            onclick={() => onconfirm(parseInt(selectedPlanId))}
                            disabled={!selectedPlanId || loading}
                        >
                            {#if loading}<span class="loading loading-spinner loading-xs"></span>{/if}
                            Cambiar Plan
                        </button>
                    </div>
                {/if}
            </div>
        </div>
    </div>
{/if}

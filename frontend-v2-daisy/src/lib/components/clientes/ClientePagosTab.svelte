<script lang="ts">
    import type { ClientService, Payment, PaymentCreate } from '$lib/types/client';

    interface Props {
        services: ClientService[];
        payments: Payment[];
        paymentsLoading: boolean;
        paymentError: string;
        paymentSuccess: string;
        submittingPayment: boolean;
        billingDay: number;
        onregister: (payload: PaymentCreate) => void;
    }

    let {
        services,
        payments,
        paymentsLoading,
        paymentError,
        paymentSuccess,
        submittingPayment,
        billingDay,
        onregister,
    }: Props = $props();

    // --- Internal form state ---
    let selectedMonth = $state('');
    let currentYear = $state(new Date().getFullYear());
    let paymentAmount = $state('');
    let paymentMethod = $state('Efectivo');
    let paymentNotes = $state('');

    const MONTHS = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];

    let paidMonths = $derived(new Set(payments.map((p) => p.mes_correspondiente)));

    // Auto-fill amount when services load and amount is empty
    $effect(() => {
        if (services.length > 0 && services[0].plan_price && !paymentAmount) {
            paymentAmount = services[0].plan_price.toFixed(2);
        }
    });

    function getCycleDates(yearMonth: string): string {
        const [year, month] = yearMonth.split('-').map(Number);
        const bd = billingDay;
        const start = new Date(year, month - 1, bd);
        const end = new Date(year, month, bd);
        const opts: Intl.DateTimeFormatOptions = { day: 'numeric', month: 'long', year: 'numeric' };
        return `${start.toLocaleDateString('es-MX', opts)} al ${end.toLocaleDateString('es-MX', opts)}`;
    }

    function selectMonth(yearMonth: string) {
        if (paidMonths.has(yearMonth)) return;
        selectedMonth = yearMonth;
        if (services.length > 0 && services[0].plan_price) {
            paymentAmount = services[0].plan_price.toFixed(2);
        }
    }

    function handleSubmit(e: SubmitEvent) {
        e.preventDefault();
        if (!selectedMonth) return;
        if (!paymentAmount || parseFloat(paymentAmount) <= 0) return;

        const payload: PaymentCreate = {
            monto: parseFloat(paymentAmount),
            mes_correspondiente: selectedMonth,
            metodo_pago: paymentMethod,
            notas: paymentNotes || undefined,
        };

        onregister(payload);

        // Reset month & notes after submit (amount stays for next payment)
        selectedMonth = '';
        paymentNotes = '';
    }
</script>

<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:1.5rem;">
    <!-- Registrar Pago -->
    <div class="glass-card-flat" style="border-radius:1rem;overflow:hidden;">
        <div style="padding:1rem 1.25rem;font-weight:700;font-size:1rem;border-bottom:1px solid color-mix(in oklch,currentColor 10%,transparent);">
            Registrar Pago
        </div>

        <!-- Plan info banner -->
        {#if services.length > 0 && services[0].plan_name}
            <div style="margin:1rem 1.25rem 0;padding:0.75rem 1rem;border-radius:0.75rem;background:color-mix(in oklch,var(--color-primary,oklch(60% 0.15 240)) 12%,transparent);border:1px solid color-mix(in oklch,var(--color-primary,oklch(60% 0.15 240)) 30%,transparent);display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <p style="font-size:0.7rem;text-transform:uppercase;letter-spacing:0.05em;opacity:0.55;margin:0;">Plan del Cliente</p>
                    <p style="font-weight:700;font-size:1rem;margin:0;color:var(--color-primary,oklch(60% 0.15 240));">{services[0].plan_name}</p>
                </div>
                <div style="text-align:right;">
                    <p style="font-size:0.7rem;text-transform:uppercase;opacity:0.55;margin:0;">Precio Mensual</p>
                    <p style="font-size:1.4rem;font-weight:800;margin:0;color:oklch(75% 0.15 145);">${services[0].plan_price?.toFixed(2) ?? '—'}</p>
                </div>
            </div>
        {/if}

        <form onsubmit={handleSubmit} style="padding:1.25rem;display:flex;flex-direction:column;gap:1rem;">
            <!-- Month selector -->
            <div>
                <label style="display:block;font-size:0.85rem;font-weight:600;margin-bottom:0.75rem;text-align:center;">Seleccionar Mes a Pagar</label>
                <div style="border:1px solid color-mix(in oklch,currentColor 15%,transparent);border-radius:0.75rem;padding:1rem;background:color-mix(in oklch,currentColor 3%,transparent);">
                    <!-- Year navigator -->
                    <div style="display:flex;align-items:center;justify-content:center;gap:1.5rem;margin-bottom:0.75rem;">
                        <button type="button" class="btn btn-ghost btn-xs btn-circle" onclick={() => currentYear--}>
                            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg>
                        </button>
                        <span style="font-weight:700;font-size:1.1rem;min-width:50px;text-align:center;">{currentYear}</span>
                        <button type="button" class="btn btn-ghost btn-xs btn-circle" onclick={() => currentYear++}>
                            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
                        </button>
                    </div>
                    <!-- Month grid -->
                    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:0.5rem;">
                        {#each MONTHS as monthName, idx}
                            {@const monthNum = String(idx + 1).padStart(2, '0')}
                            {@const ym = `${currentYear}-${monthNum}`}
                            {@const isPaid = paidMonths.has(ym)}
                            {@const isSelected = selectedMonth === ym}
                            <button
                                type="button"
                                disabled={isPaid}
                                onclick={() => selectMonth(ym)}
                                class="btn btn-xs"
                                style="height:2.5rem;position:relative;{isPaid ? 'background:color-mix(in oklch,oklch(75% 0.15 145) 20%,transparent);border-color:oklch(75% 0.15 145);color:oklch(75% 0.15 145);cursor:not-allowed;' : isSelected ? 'background:color-mix(in oklch,var(--color-primary,oklch(60% 0.15 240)) 25%,transparent);border-color:var(--color-primary,oklch(60% 0.15 240));outline:2px solid var(--color-primary,oklch(60% 0.15 240));outline-offset:1px;' : ''}"
                            >
                                {monthName}
                                {#if isPaid}
                                    <span style="position:absolute;top:2px;right:2px;width:10px;height:10px;border-radius:50%;background:oklch(75% 0.15 145);display:flex;align-items:center;justify-content:center;font-size:6px;">✓</span>
                                {/if}
                            </button>
                        {/each}
                    </div>
                </div>
                {#if selectedMonth}
                    <div style="margin-top:0.5rem;padding:0.5rem 0.75rem;border-radius:0.5rem;background:color-mix(in oklch,var(--color-primary,oklch(60% 0.15 240)) 10%,transparent);font-size:0.8rem;color:var(--color-primary,oklch(60% 0.15 240));font-weight:600;">
                        📅 Ciclo: {getCycleDates(selectedMonth)}
                    </div>
                {/if}
            </div>

            <!-- Amount & Method -->
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;">
                <div>
                    <label class="label" style="font-size:0.8rem;">Monto</label>
                    <input type="number" step="0.01" min="0" bind:value={paymentAmount} required class="input input-sm input-bordered w-full" placeholder="0.00" style="font-size:1rem;font-weight:700;" />
                </div>
                <div>
                    <label class="label" style="font-size:0.8rem;">Método de Pago</label>
                    <select bind:value={paymentMethod} class="select select-sm select-bordered w-full">
                        <option>Efectivo</option>
                        <option>Transferencia</option>
                        <option>Otro</option>
                    </select>
                </div>
            </div>
            <div>
                <label class="label" style="font-size:0.8rem;">Notas (Opcional)</label>
                <input type="text" bind:value={paymentNotes} class="input input-sm input-bordered w-full" placeholder="Referencia, comentario..." />
            </div>

            {#if paymentError}
                <div class="alert alert-error p-2 text-sm"><span>{paymentError}</span></div>
            {/if}
            {#if paymentSuccess}
                <div class="alert alert-success p-2 text-sm"><span>{paymentSuccess}</span></div>
            {/if}

            <div style="text-align:right;">
                <button type="submit" class="btn btn-primary btn-sm" disabled={submittingPayment || !selectedMonth}>
                    {#if submittingPayment}<span class="loading loading-spinner loading-xs"></span>{/if}
                    Registrar Pago &amp; Reactivar
                </button>
            </div>
        </form>
    </div>

    <!-- Historial de pagos -->
    <div class="glass-card-flat" style="border-radius:1rem;overflow:hidden;">
        <div style="padding:1rem 1.25rem;font-weight:700;font-size:1rem;border-bottom:1px solid color-mix(in oklch,currentColor 10%,transparent);display:flex;justify-content:space-between;align-items:center;">
            <span>Historial de Pagos</span>
            {#if payments.length > 0}
                <span class="badge badge-neutral badge-sm">{payments.length}</span>
            {/if}
        </div>
        <div style="padding:1rem;max-height:520px;overflow-y:auto;display:flex;flex-direction:column;gap:0.5rem;">
            {#if paymentsLoading}
                <div style="text-align:center;padding:2rem;opacity:0.5;">
                    <span class="loading loading-spinner loading-md"></span>
                </div>
            {:else if payments.length === 0}
                <p style="text-align:center;opacity:0.5;padding:2rem;">Sin pagos registrados.</p>
            {:else}
                {#each payments as payment (payment.id)}
                    <div style="display:flex;justify-content:space-between;align-items:center;padding:0.75rem;border-radius:0.5rem;background:color-mix(in oklch,currentColor 4%,transparent);border:1px solid color-mix(in oklch,currentColor 8%,transparent);">
                        <div>
                            <p style="margin:0;font-weight:700;font-size:0.9rem;">
                                ${payment.monto.toFixed(2)}
                                <span style="font-weight:500;opacity:0.6;font-size:0.8rem;"> · {payment.mes_correspondiente}</span>
                            </p>
                            <p style="margin:0.2rem 0 0;font-size:0.75rem;opacity:0.55;">
                                {new Date(payment.fecha_pago).toLocaleString('es-MX', { dateStyle: 'medium', timeStyle: 'short' })}
                                {#if payment.metodo_pago} · {payment.metodo_pago}{/if}
                            </p>
                            {#if payment.notas}
                                <p style="margin:0.2rem 0 0;font-size:0.73rem;color:oklch(70% 0.12 60);">{payment.notas}</p>
                            {/if}
                        </div>
                        <a
                            href="/payment/{payment.id}/receipt"
                            target="_blank"
                            rel="noopener"
                            class="btn btn-ghost btn-xs"
                            title="Ver recibo"
                        >
                            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
                            </svg>
                        </a>
                    </div>
                {/each}
            {/if}
        </div>
    </div>
</div>

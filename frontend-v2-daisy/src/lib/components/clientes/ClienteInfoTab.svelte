<script lang="ts">
    import type { Client } from '$lib/types/client';

    let { client }: { client: Client } = $props();
</script>

<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:1.5rem;">
    <!-- Datos de contacto -->
    <div class="glass-card-flat" style="border-radius:1rem;overflow:hidden;">
        <div style="padding:1rem 1.25rem;font-weight:700;font-size:1rem;border-bottom:1px solid color-mix(in oklch,currentColor 10%,transparent);">
            Datos de Contacto
        </div>
        <div style="padding:1.25rem;display:flex;flex-direction:column;gap:0.75rem;font-size:0.875rem;">
            {#each [
                { label: 'Dirección', val: client.address },
                { label: 'Teléfono', val: client.phone_number },
                { label: 'WhatsApp', val: client.whatsapp_number },
                { label: 'Email', val: client.email },
                { label: 'Telegram', val: client.telegram_contact },
                { label: 'Día de facturación', val: client.billing_day ? `Día ${client.billing_day}` : null },
            ] as field}
                <div style="display:flex;justify-content:space-between;gap:1rem;align-items:flex-start;">
                    <span style="opacity:0.55;min-width:120px;">{field.label}</span>
                    <span style="font-weight:600;text-align:right;">{field.val ?? '—'}</span>
                </div>
            {/each}
            {#if client.coordinates}
                <div style="display:flex;justify-content:space-between;gap:1rem;align-items:flex-start;">
                    <span style="opacity:0.55;min-width:120px;">Coordenadas</span>
                    <a
                        href="https://maps.google.com/maps?q={client.coordinates}"
                        target="_blank"
                        rel="noopener noreferrer"
                        class="link link-primary"
                        style="font-weight:600;text-align:right;"
                    >{client.coordinates}</a>
                </div>
            {/if}
        </div>
    </div>

    <!-- Notas -->
    {#if client.notes}
        <div class="glass-card-flat" style="border-radius:1rem;overflow:hidden;">
            <div style="padding:1rem 1.25rem;font-weight:700;font-size:1rem;border-bottom:1px solid color-mix(in oklch,currentColor 10%,transparent);">
                Notas
            </div>
            <div style="padding:1.25rem;font-size:0.875rem;white-space:pre-wrap;opacity:0.8;">
                {client.notes}
            </div>
        </div>
    {/if}
</div>

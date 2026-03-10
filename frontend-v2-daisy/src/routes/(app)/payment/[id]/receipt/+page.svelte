<script lang="ts">
    import type { PageData } from './$types';
    import { onMount } from 'svelte';

    export let data: PageData;
    const { receipt } = data;

    function handlePrint() {
        window.print();
    }

    function handleBack() {
        window.history.back();
    }
</script>

<svelte:head>
    <title>Recibo de Pago #{receipt.payment.id}</title>
</svelte:head>

<div class="receipt-outer-container bg-white min-h-screen flex flex-col items-center py-4 sm:py-8">
    <!-- Botones de Acción (Ocultos al imprimir) -->
    <div class="w-full max-w-[80mm] flex justify-between mb-6 no-print px-4">
        <button class="btn btn-ghost btn-sm" on:click={handleBack}>
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4 mr-1">
                <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
            </svg>
            Volver
        </button>
        <button class="btn btn-primary btn-sm px-6" on:click={handlePrint}>
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4 mr-1">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6.72 13.89l-2.1 2.1m2.1-2.1l2.1 2.1m-2.1-2.1h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0zM15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 12h-2.25m-3 0h-2.25m-3 0H6.75" />
            </svg>
            Imprimir
        </button>
    </div>

    <!-- Ticket de Pago -->
    <div class="receipt-container bg-white text-black p-4 font-mono w-full max-w-[80mm] border border-base-200 sm:shadow-lg rounded-none">
        <!-- Cabecera -->
        <div class="text-center mb-4">
            {#if receipt.isp_logo}
                <div class="flex justify-center mb-2">
                    <img src={receipt.isp_logo} alt="Logo" class="max-w-[120px] h-auto object-contain" />
                </div>
            {/if}
            <h2 class="text-lg font-bold uppercase leading-none mb-1">{receipt.isp_name || 'ISP Local'}</h2>
            {#if receipt.isp_address}
                <p class="text-[10px] leading-tight mb-0.5">{receipt.isp_address}</p>
            {/if}
            {#if receipt.isp_phone}
                <p class="text-[10px] leading-tight">Tel: {receipt.isp_phone}</p>
            {/if}
        </div>

        <div class="border-t border-dashed border-black my-2"></div>

        <!-- Información del Pago -->
        <div class="text-[11px] space-y-0.5">
            <div class="flex justify-between">
                <span class="font-bold">FOLIO:</span>
                <span>#{receipt.payment.id}</span>
            </div>
            <div class="flex justify-between">
                <span class="font-bold">FECHA:</span>
                <span>{new Date(receipt.payment.fecha_pago).toLocaleString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
            </div>
        </div>

        <div class="border-t border-dashed border-black my-2"></div>

        <!-- Información del Cliente -->
        <div class="text-[11px] space-y-0.5">
            <div class="flex justify-between items-start">
                <span class="font-bold shrink-0 mr-2">CLIENTE:</span>
                <span class="text-right flex-1 break-words">{receipt.client.name}</span>
            </div>
            {#if receipt.client.address}
                <div class="flex justify-between items-start">
                    <span class="font-bold shrink-0 mr-2">UBICACIÓN:</span>
                    <span class="text-right flex-1 break-words">{receipt.client.address}</span>
                </div>
            {/if}
        </div>

        <div class="border-t border-dashed border-black my-2"></div>

        <!-- Detalle de Concepto -->
        <div class="text-[11px]">
            <p class="font-bold uppercase mb-0.5">CONCEPTO:</p>
            <p class="leading-tight">Servicio de Internet</p>
            <p class="text-[10px] opacity-80 italic">Periodo: {receipt.start_date} - {receipt.end_date}</p>
        </div>

        <div class="border-t border-dashed border-black my-2"></div>

        <!-- Totales -->
        <div class="flex justify-between text-base font-bold mt-1">
            <span>TOTAL:</span>
            <span>${Number(receipt.payment.monto).toFixed(2)}</span>
        </div>

        <div class="flex justify-between text-[11px] mt-0.5">
            <span>Método:</span>
            <span class="capitalize">{receipt.payment.metodo_pago || 'Efectivo'}</span>
        </div>

        <!-- Footer -->
        <div class="text-center mt-6 text-[9px] space-y-0.5 italic leading-tight">
            {#if receipt.ticket_message}
                <p>{receipt.ticket_message}</p>
            {:else}
                <p>¡Gracias por su pago!</p>
                <p>Conserve este comprobante para cualquier aclaración.</p>
            {/if}
        </div>
    </div>
</div>

<style>
    /* Estilos específicos para evitar colores de fondo de DaisyUI */
    :global(html, body) {
        background-color: white !important;
    }

    .receipt-container {
        color: black !important;
        background-color: white !important;
        box-sizing: border-box;
    }

    @media print {
        :global(body) {
            margin: 0 !important;
            padding: 0 !important;
            width: 80mm !important;
        }

        .receipt-outer-container {
            padding: 0 !important;
            background: white !important;
            min-height: 0 !important;
        }

        .no-print {
            display: none !important;
        }

        .receipt-container {
            box-shadow: none !important;
            border: none !important;
            width: 80mm !important;
            max-width: 80mm !important;
            margin: 0 !important;
            padding: 2mm !important; /* Mínimo padding para no desperdiciar papel */
        }

        @page {
            size: 80mm auto;
            margin: 0;
        }
    }
</style>

<script lang="ts">
    import { user } from "$lib/stores/auth";
    import { fade, fly } from "svelte/transition";
    import type { PageData } from './$types';
    import { marked } from 'marked';

    let { data } = $props<{ data: PageData }>();

    // Calculamos el estado general basándonos en los datos reales
    const client = $derived(data.me);
    const tickets = $derived(data.tickets);
    const announcements = $derived(data.announcements || []);
    const criticalAlerts = $derived(announcements.filter((a: any) => a.type === 'critical'));
    const newsFeeds = $derived(announcements.filter((a: any) => a.type !== 'critical'));
    
    const serviceStatus = $derived(client?.service_status || "Desconocido");
    
    function fmtDate(date: string | null) {
        if (!date) return "--";
        // Asegurar que se interprete como UTC si falta el indicador de zona
        const hasTZ = date.includes('Z') || date.includes('+');
        const d = new Date(hasTZ ? date : date + 'Z');
        if (isNaN(d.getTime())) return date;
        return d.toLocaleDateString("es-ES", { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
    }
</script>

<svelte:head>
	<title>Dashboard | Portal de Clientes — OmniWISP</title>
</svelte:head>

<div class="space-y-8" in:fade={{ duration: 400 }}>
    <!-- Header Bienvenida -->
    <section class="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-base-300 pb-6">
        <div>
            <h1 class="text-4xl font-black tracking-tight mb-2">
                ¡Hola, <span class="bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">{$user?.username || "Cliente"}</span>!
            </h1>
            <p class="opacity-60 text-lg">Bienvenido a tu panel de gestión de servicios.</p>
        </div>
        <div class="flex items-center gap-3">
             <div class="badge badge-success badge-lg gap-2 py-4 px-6 font-bold shadow-lg shadow-success/10">
                <span class="w-2 h-2 bg-white rounded-full animate-pulse"></span>
                Servicio {serviceStatus}
             </div>
        </div>
    </section>

    <!-- Alertas Criticas -->
    {#if criticalAlerts.length > 0}
        <div class="space-y-3 mb-6" in:fade={{ delay: 100 }}>
            {#each criticalAlerts as alert}
                <div class="alert alert-error shadow-lg">
                    <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
                    <div class="flex-1">
                        <h3 class="font-bold text-lg">{alert.title}</h3>
                        <div class="text-sm max-w-none text-current opacity-90 mt-1 prose-a:text-current prose-a:underline">
                            {@html marked(alert.content)}
                        </div>
                    </div>
                </div>
            {/each}
        </div>
    {/if}

    <!-- Grid de Resumen -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <!-- Tarjeta Plan -->
        <div class="card bg-base-100 shadow-xl border border-base-200 overflow-hidden group hover:border-primary/50 transition-all duration-300" in:fly={{ y: 20, delay: 100 }}>
            <div class="p-6">
                <div class="flex items-center justify-between mb-4">
                    <span class="text-3xl">🌐</span>
                    <span class="badge badge-outline badge-primary font-bold">Plan Actual</span>
                </div>
                <h3 class="text-2xl font-bold mb-1">Mis Servicios</h3>
                <p class="text-sm opacity-50">Gestiona tus planes de internet</p>
                <div class="mt-6">
                    <a href="/portal/planes" class="btn btn-primary btn-sm btn-block rounded-xl group-hover:shadow-lg transition-all">Ver Detalles</a>
                </div>
            </div>
            <div class="h-1 w-full bg-gradient-to-r from-primary to-secondary opacity-20 group-hover:opacity-100 transition-opacity"></div>
        </div>

        <!-- Tarjeta Facturación -->
        <div class="card bg-base-100 shadow-xl border border-base-200 overflow-hidden group hover:border-secondary/50 transition-all duration-300" in:fly={{ y: 20, delay: 200 }}>
            <div class="p-6">
                <div class="flex items-center justify-between mb-4">
                    <span class="text-3xl">💳</span>
                    <span class="badge badge-outline badge-secondary font-bold">Pendiente</span>
                </div>
                <h3 class="text-3xl font-black mb-1">$0.00</h3>
                <p class="text-sm opacity-50">Sin facturas pendientes</p>
                <div class="mt-6">
                    <button class="btn btn-secondary btn-sm btn-block rounded-xl group-hover:shadow-lg transition-all" disabled>Historico Pagos</button>
                </div>
            </div>
            <div class="h-1 w-full bg-gradient-to-r from-secondary to-accent opacity-20 group-hover:opacity-100 transition-opacity"></div>
        </div>

        <!-- Tarjeta Soporte -->
        <div class="card bg-base-100 shadow-xl border border-base-200 overflow-hidden group hover:border-accent/50 transition-all duration-300" in:fly={{ y: 20, delay: 300 }}>
            <div class="p-6">
                <div class="flex items-center justify-between mb-4">
                    <span class="text-3xl">🛠️</span>
                    <span class="badge badge-outline badge-accent font-bold">Soporte Tecnico</span>
                </div>
                <h3 class="text-2xl font-bold mb-1">¿Necesitas ayuda?</h3>
                <p class="text-sm opacity-50">Habla con un técnico experto</p>
                <div class="mt-6">
                    <a href="/portal/tickets" class="btn btn-accent btn-sm btn-block rounded-xl group-hover:shadow-lg transition-all">Abrir Ticket</a>
                </div>
            </div>
            <div class="h-1 w-full bg-gradient-to-r from-accent to-primary opacity-20 group-hover:opacity-100 transition-opacity"></div>
        </div>
    </div>

    <!-- Sección Inferior Layout -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
    
        <!-- Datos del Cliente (2/3) -->
        <section class="lg:col-span-2 card bg-base-100 shadow-2xl border border-base-200 overflow-hidden h-full" in:fly={{ y: 30, delay: 400 }}>
            <div class="p-6 border-b border-base-300 flex items-center justify-between bg-base-200/50">
                <h2 class="text-xl font-bold flex items-center gap-2">
                    <span class="text-primary">👤</span> Mi Información
                </h2>
            </div>
            <div class="p-8">
                <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <!-- Nombre -->
                    <div class="flex flex-col gap-1">
                        <span class="text-[10px] uppercase font-bold opacity-50 tracking-wider">Nombre Completo</span>
                        <span class="text-sm font-semibold">{client?.name || 'No especificado'}</span>
                    </div>
                    
                    <!-- Dirección -->
                    <div class="flex flex-col gap-1">
                        <span class="text-[10px] uppercase font-bold opacity-50 tracking-wider">Dirección</span>
                        <span class="text-sm font-semibold">{client?.address || 'No especificada'}</span>
                    </div>
                    
                    <!-- Día de Facturación -->
                    <div class="flex flex-col gap-1">
                        <span class="text-[10px] uppercase font-bold opacity-50 tracking-wider">Día de Facturación</span>
                        <span class="text-sm font-semibold">
                            {#if client?.billing_day}
                                Los días {client.billing_day} de cada mes
                            {:else}
                                No configurado
                            {/if}
                        </span>
                    </div>
                    
                    <!-- Teléfono Principal -->
                    <div class="flex flex-col gap-1">
                        <span class="text-[10px] uppercase font-bold opacity-50 tracking-wider">Teléfono Principal</span>
                        <span class="text-sm font-semibold">{client?.phone_number || 'No registrado'}</span>
                    </div>

                    <!-- Correo -->
                    <div class="flex flex-col gap-1">
                        <span class="text-[10px] uppercase font-bold opacity-50 tracking-wider">Correo Electrónico</span>
                        <span class="text-sm font-semibold truncate" title="{client?.email}">{client?.email || 'No registrado'}</span>
                    </div>

                    <!-- WhatsApp -->
                    <div class="flex flex-col gap-1">
                        <span class="text-[10px] uppercase font-bold opacity-50 tracking-wider">WhatsApp</span>
                        {#if client?.whatsapp_number}
                            <a href="https://wa.me/{client.whatsapp_number.replace(/\D/g,'')}" target="_blank" class="text-sm text-success hover:underline font-bold flex items-center gap-1">
                                💬 {client.whatsapp_number}
                            </a>
                        {:else}
                            <span class="text-sm font-semibold opacity-50">No registrado</span>
                        {/if}
                    </div>

                    <!-- Telegram -->
                    <div class="flex flex-col gap-1">
                        <span class="text-[10px] uppercase font-bold opacity-50 tracking-wider">Telegram</span>
                        {#if client?.telegram_contact}
                            <a href="https://t.me/{client.telegram_contact.replace('@','')}" target="_blank" class="text-sm text-info hover:underline font-bold flex items-center gap-1">
                                ✈️ {client.telegram_contact}
                            </a>
                        {:else}
                            <span class="text-sm font-semibold opacity-50">No registrado</span>
                        {/if}
                    </div>
                </div>
                
                <div class="mt-8 pt-6 border-t border-base-200 flex justify-end">
                    <p class="text-xs opacity-50 italic">
                        Para actualizar cualquier dato, por favor contacta con soporte.
                    </p>
                </div>
            </div>
        </section>
        
        <!-- Novedades (1/3) -->
        <section class="lg:col-span-1 card bg-base-100 shadow-2xl border border-base-200 overflow-hidden h-[500px]" in:fly={{ y: 30, delay: 500 }}>
            <div class="p-6 border-b border-base-300 flex items-center bg-base-200/50 shrink-0">
                <h2 class="text-xl font-bold flex items-center gap-2">
                    <span class="text-primary">📰</span> Novedades
                </h2>
            </div>
            <div class="p-6 overflow-y-auto flex-1 flex flex-col gap-5">
                {#if newsFeeds.length > 0}
                    {#each newsFeeds as news}
                        <div class="card bg-base-200 shadow-sm overflow-hidden">
                            {#if news.image_url}
                                <figure><img src={news.image_url} alt="Novedad" class="w-full h-32 object-cover bg-neutral" /></figure>
                            {/if}
                            <div class="card-body p-4">
                                <h3 class="card-title text-base leading-tight">
                                    {news.title}
                                    {#if news.type === 'promotion'}
                                    <div class="badge badge-success badge-sm shrink-0">PROMO</div>
                                    {/if}
                                </h3>
                                <!-- Evitar estilos conflictivos de prose -->
                                <div class="text-sm opacity-80 mt-1 space-y-2 [&>p]:mb-2 [&>ul]:list-disc [&>ul]:ml-4">
                                    {@html marked(news.content)}
                                </div>
                                <span class="text-[10px] opacity-40 mt-2 font-mono">{fmtDate(news.start_date)}</span>
                            </div>
                        </div>
                    {/each}
                {:else}
                    <div class="flex flex-col items-center justify-center h-full opacity-50 pt-10">
                        <span class="text-5xl mb-3">📭</span>
                        <p class="text-sm font-bold">Sin novedades</p>
                        <p class="text-xs">Te mantendremos informado.</p>
                    </div>
                {/if}
            </div>
        </section>

    </div>

</div>

<style>
    /* Efecto sutil de glassmorphism para las tarjetas si el fondo está activo */
    :global(.lava-lamp-active) .card {
        background-color: rgba(var(--b1) / 0.7);
        backdrop-filter: blur(12px);
    }
</style>

<script lang="ts">
    import { fade, fly } from "svelte/transition";
    import type { PageData } from './$types';

    let { data } = $props<{ data: PageData }>();

    const planes = $derived(data.planes);
</script>

<svelte:head>
	<title>Mis Planes | Portal de Clientes</title>
</svelte:head>

<div class="space-y-8" in:fade={{ duration: 400 }}>
    <section class="border-b border-base-300 pb-6">
        <h1 class="text-4xl font-black tracking-tight mb-2">Gestiona tu <span class="bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">Conectividad</span></h1>
        <p class="opacity-60 text-lg">Revisa tu plan actual o mejora tu velocidad con nuestras ofertas exclusivas.</p>
    </section>

    {#if planes && planes.length > 0}
        <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
            {#each planes as plan, i}
                <div 
                    class="card bg-base-100 shadow-xl border-2 {plan.actual ? 'border-primary ring-4 ring-primary/10' : 'border-base-200'} relative overflow-hidden flex flex-col group hover:scale-[1.02] transition-all duration-300"
                    in:fly={{ y: 30, delay: 100 * i }}
                >
                    {#if plan.actual}
                        <div class="absolute top-0 right-0 bg-primary text-primary-content text-[10px] font-black px-4 py-1 uppercase tracking-widest rounded-bl-xl shadow-lg">
                            Tu Plan Actual
                        </div>
                    {/if}

                    <div class="p-8 flex-1">
                        <h3 class="text-2xl font-bold mb-1">{plan.perfil}</h3>
                        <div class="flex items-baseline gap-1 mb-6">
                            <span class="text-4xl font-black">${plan.price}</span>
                            <span class="text-sm opacity-50 font-medium">/mes</span>
                        </div>

                        <div class="space-y-4 mb-8">
                            <div class="flex items-center gap-3 bg-base-200/50 p-3 rounded-xl border border-base-300">
                                <span class="text-2xl">⚡</span>
                                <div>
                                    <p class="text-[10px] uppercase font-bold opacity-50 leading-none">Usuario PPPoE / IP</p>
                                    <p class="font-bold text-xs">{plan.pppoe_user || 'Sin asignar'} &bull; {plan.ipv4_address || 'Sin IP'}</p>
                                </div>
                            </div>

                            <ul class="space-y-3">
                                {#each plan.features as feature}
                                    <li class="flex items-start gap-3 text-sm opacity-80">
                                        <span class="text-success text-xs mt-1">✓</span>
                                        {feature}
                                    </li>
                                {/each}
                            </ul>
                        </div>
                    </div>

                    <div class="p-6 bg-base-200/30 border-t border-base-200 mt-auto">
                        {#if plan.estado_servicio === 'Activo'}
                            <button class="btn btn-outline btn-block rounded-xl border-base-300 no-animation cursor-default opacity-50 mb-2">
                                Servicio Activo
                            </button>
                        {:else}
                            <button class="btn btn-warning btn-block rounded-xl shadow-lg shadow-warning/20 mb-2">
                                {plan.estado_servicio}
                            </button>
                        {/if}
                        <button class="btn btn-primary btn-block rounded-xl shadow-lg shadow-primary/20 group-hover:shadow-primary/40 transition-shadow">
                            Solicitar Upgrade 🚀
                        </button>
                    </div>
                </div>
            {/each}
        </div>
    {:else}
        <div class="flex flex-col items-center justify-center py-16 px-4 text-center bg-base-100/50 rounded-3xl border border-base-200 border-dashed mt-8">
            <div class="bg-base-200 p-6 rounded-full mb-6">
                <span class="text-6xl grayscale opacity-50">📡</span>
            </div>
            <h2 class="text-3xl font-bold mb-4">Aún no tienes servicios asignados</h2>
            <p class="opacity-70 max-w-lg mx-auto text-lg mb-8">
                Tu cuenta ha sido creada exitosamente, pero aún no detectamos un plan de internet activo o una instalación asociada a tu perfil. 
                Si contrataste un servicio recientemente, el equipo técnico debe estar programando tu instalación.
            </p>
            <a href="/portal/tickets" class="btn btn-primary rounded-xl px-8 shadow-lg shadow-primary/20">
                Contactar Soporte
            </a>
        </div>
    {/if}

    <!-- Banner Informativo -->
    <div class="alert bg-gradient-to-r from-base-100 to-base-200 border border-base-300 rounded-2xl p-8 shadow-inner" in:fade={{ delay: 500 }}>
        <div class="flex flex-col md:flex-row items-center gap-6 w-full text-center md:text-left">
            <span class="text-6xl animate-bounce">💡</span>
            <div class="flex-1">
                <h3 class="text-xl font-bold">¿Necesitas algo a medida?</h3>
                <p class="opacity-60 text-sm">Ofrecemos soluciones personalizadas para empresas y condominios. Contacta con nuestro equipo comercial.</p>
            </div>
            <button class="btn btn-secondary rounded-xl px-8">Consultar Ventas</button>
        </div>
    </div>
</div>

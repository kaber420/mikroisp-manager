<script lang="ts">
    // import { onMount } from 'svelte';
    // import { api } from '$lib/api';
</script>

<svelte:head>
    <title>Configuración — UManager</title>
</svelte:head>

<div class="mb-6 flex justify-between items-center">
    <div>
        <h1 class="text-3xl font-bold">Sistema y Configuración</h1>
        <p class="text-base-content/60 mt-1">
            Ajustes globales, usuarios del sistema y roles de acceso.
        </p>
    </div>
</div>

<div class="grid grid-cols-1 md:grid-cols-3 gap-6">
    <!-- Usuarios -->
    <div
        class="card bg-base-100 shadow-xl border border-base-200 transition-transform hover:scale-[1.02]"
    >
        <div class="card-body items-center text-center">
            <div class="p-4 bg-primary/10 text-primary rounded-full mb-2">
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    class="h-8 w-8"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"
                    />
                </svg>
            </div>
            <h2 class="card-title">Gestión de Usuarios</h2>
            <p class="text-sm text-base-content/60">
                Crea personal de soporte, cobranza y administradores.
            </p>
            <div class="card-actions mt-4 w-full">
                <button class="btn btn-primary btn-block">Ir a Usuarios</button>
            </div>
        </div>
    </div>

    <!-- Ajustes Generales -->
    <div
        class="card bg-base-100 shadow-xl border border-base-200 transition-transform hover:scale-[1.02]"
    >
        <div class="card-body items-center text-center">
            <div
                class="p-4 bg-neutral-focus/10 text-neutral-focus rounded-full mb-2"
            >
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    class="h-8 w-8 opacity-70"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                    />
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                    />
                </svg>
            </div>
            <h2 class="card-title text-base-content">Ajustes Generales</h2>
            <p class="text-sm text-base-content/60">
                Configura la moneda, logo y opciones de red del ISP.
            </p>
            <div class="card-actions mt-4 w-full">
                <button class="btn btn-outline btn-block">Ir a Ajustes</button>
            </div>
        </div>
    </div>

    <!-- API y Logs -->
    <div
        class="card bg-base-100 shadow-xl border border-base-200 transition-transform hover:scale-[1.02]"
    >
        <div class="card-body items-center text-center">
            <div class="p-4 bg-info/10 text-info rounded-full mb-2">
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    class="h-8 w-8"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
                    />
                </svg>
            </div>
            <h2 class="card-title">Monitor de Logs</h2>
            <p class="text-sm text-base-content/60">
                Visor de eventos del sistema y estado del backend.
            </p>
            <div class="card-actions mt-4 w-full">
                <button class="btn btn-outline btn-info btn-block"
                    >Ir a Logs</button
                >
            </div>
        </div>
    </div>
</div>

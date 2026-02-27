<script lang="ts">
    // Clientes placeholder
</script>

<div class="space-y-6">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
        <div>
            <h2 class="text-2xl font-bold text-gray-900">
                Gestión de Clientes
            </h2>
            <p class="text-gray-500 mt-1">
                Administra los usuarios y CPEs de la red
            </p>
        </div>
        <button class="btn-primary"> + Nuevo Cliente </button>
    </div>

    <!-- Content Area -->
    <div class="card p-8 text-center ring-1 ring-gray-900/5">
        <div
            class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-50 text-blue-600 mb-4"
        >
            <svg
                class="w-8 h-8"
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
        <h3 class="text-lg font-semibold text-gray-900">
            Módulo en Construcción
        </h3>
        <p class="text-gray-500 mt-2 max-w-md mx-auto">
            Próximamente conectaremos esta vista con el endpoint /api/clients de
            FastAPI para mostrar la tabla con TailwindCSS.
        </p>
    </div>
</div>

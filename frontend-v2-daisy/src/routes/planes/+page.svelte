<script lang="ts">
    // Planes placeholder
</script>

<div class="space-y-6">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
        <div>
            <h2 class="text-2xl font-bold text-gray-900">Gestión de Planes</h2>
            <p class="text-gray-500 mt-1">
                Configura las velocidades y precios de los planes
            </p>
        </div>
        <button class="btn-primary"> + Nuevo Plan </button>
    </div>

    <!-- Content Area -->
    <div class="glass-card p-8 text-center">
        <div
            class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-secondary/10 text-secondary mb-4"
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
                    d="M13 10V3L4 14h7v7l9-11h-7z"
                />
            </svg>
        </div>
        <h3 class="text-lg font-semibold">Módulo en Construcción</h3>
        <p class="opacity-60 mt-2 max-w-md mx-auto">
            Próximamente conectaremos esta vista con el endpoint /api/plans de
            FastAPI.
        </p>
    </div>
</div>

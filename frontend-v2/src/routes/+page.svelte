<script lang="ts">
    import { onMount } from "svelte";
    import { user } from "$lib/stores/auth";
    import { api } from "$lib/api";

    let stats = $state({
        total_clients: 0,
        active_clients: 0,
        suspended_clients: 0,
    });

    onMount(async () => {
        // Example fetch to a future/existing dashboard stats API
        try {
            const response = await api.get("/dashboard/stats");
            stats = response.data;
        } catch (err) {
            console.warn("Could not fetch dashboard stats", err);
        }
    });
</script>

<div class="space-y-6">
    <div class="flex justify-between items-center">
        <h1 class="text-3xl font-bold text-gray-800">Panel de Control</h1>
        <div class="text-gray-500">
            Bienvenido, <span class="font-semibold text-indigo-600"
                >{$user?.username || "Usuario"}</span
            >
        </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <!-- Stats Cards -->
        <div class="bg-white rounded-lg shadow p-6 border-l-4 border-blue-500">
            <div class="flex items-center">
                <div class="text-blue-500">
                    <svg
                        class="h-8 w-8"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                        ><path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
                        ></path></svg
                    >
                </div>
                <div class="ml-4">
                    <h2 class="text-gray-500 text-sm uppercase tracking-wide">
                        Total Clientes
                    </h2>
                    <div class="text-3xl font-bold text-gray-800">
                        {stats.total_clients}
                    </div>
                </div>
            </div>
        </div>

        <div class="bg-white rounded-lg shadow p-6 border-l-4 border-green-500">
            <div class="flex items-center">
                <div class="text-green-500">
                    <svg
                        class="h-8 w-8"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                        ><path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                        ></path></svg
                    >
                </div>
                <div class="ml-4">
                    <h2 class="text-gray-500 text-sm uppercase tracking-wide">
                        Clientes Activos
                    </h2>
                    <div class="text-3xl font-bold text-gray-800">
                        {stats.active_clients}
                    </div>
                </div>
            </div>
        </div>

        <div class="bg-white rounded-lg shadow p-6 border-l-4 border-red-500">
            <div class="flex items-center">
                <div class="text-red-500">
                    <svg
                        class="h-8 w-8"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                        ><path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                        ></path></svg
                    >
                </div>
                <div class="ml-4">
                    <h2 class="text-gray-500 text-sm uppercase tracking-wide">
                        Clientes Suspendidos
                    </h2>
                    <div class="text-3xl font-bold text-gray-800">
                        {stats.suspended_clients}
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Main Content Area -->
    <div class="bg-white rounded-lg shadow p-6">
        <h2 class="text-xl font-semibold mb-4 text-gray-700">
            Bienvenido al nuevo Frontend SvelteKit
        </h2>
        <p class="text-gray-600 mb-4">
            Esta versión funciona en paralelo a la original y consume la API
            REST del backend.
        </p>
        <div class="bg-indigo-50 border-l-4 border-indigo-400 p-4">
            <div class="flex">
                <div class="flex-shrink-0">
                    <svg
                        class="h-5 w-5 text-indigo-400"
                        viewBox="0 0 20 20"
                        fill="currentColor"
                    >
                        <path
                            fill-rule="evenodd"
                            d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                            clip-rule="evenodd"
                        />
                    </svg>
                </div>
                <div class="ml-3">
                    <p class="text-sm text-indigo-700">
                        Puedes cambiar libremente entre esta versión V2 y la
                        versión clásica SSR de Jinja.
                    </p>
                </div>
            </div>
        </div>
    </div>
</div>

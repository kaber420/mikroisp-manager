<script lang="ts">
    import axios from "axios";
    import { goto } from "$app/navigation";

    let username = $state("");
    let email = $state("");
    let password = $state("");
    let passwordConfirm = $state("");
    let errorMsg = $state("");
    let loading = $state(false);

    async function handleSubmit(e: Event) {
        e.preventDefault();
        loading = true;
        errorMsg = "";

        if (password !== passwordConfirm) {
            errorMsg = "Las contraseñas no coinciden.";
            loading = false;
            return;
        }

        if (password.length < 6) {
            errorMsg = "La contraseña debe tener al menos 6 caracteres.";
            loading = false;
            return;
        }

        try {
            // POST to backend setup endpoint - el router de setup está bajo /api/setup
            const response = await axios.post(
                "/api/setup",
                { username, email, password },
                {
                    headers: {
                        "Content-Type": "application/json",
                        Accept: "application/json",
                    },
                    withCredentials: true,
                    validateStatus: (s: number) => s < 400 || s === 403,
                },
            );

            if (response.status === 200 || response.status === 201) {
                // Setup ok — go to login with success message
                goto("/login?setup=success");
            } else if (response.status === 403) {
                errorMsg =
                    "El sistema ya está configurado. No puedes crear más usuarios desde aquí.";
            } else {
                errorMsg =
                    response.data?.detail ||
                    "Error al crear el usuario. Intenta de nuevo.";
            }
        } catch (err: any) {
            errorMsg =
                err.response?.data?.detail ||
                "Error de conexión. Intenta de nuevo.";
        } finally {
            loading = false;
        }
    }
</script>

<svelte:head>
    <title>Setup Inicial — OmniWISP</title>
</svelte:head>

<div class="min-h-screen bg-gray-100 flex items-center justify-center p-4">
    <div class="w-full max-w-md bg-white rounded-2xl shadow-lg p-8">
        <div class="flex flex-col items-center mb-8">
            <svg
                class="h-12 w-12 text-indigo-600 mb-3"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke-width="1.5"
                stroke="currentColor"
            >
                <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z"
                />
            </svg>

            <h1 class="text-2xl font-bold text-gray-800">
                ¡Bienvenido a <span class="text-indigo-600">OmniWISP</span>!
            </h1>
            <p class="text-gray-500 text-sm mt-1 text-center">
                Crea tu cuenta de administrador de sistema para continuar
            </p>
        </div>

        {#if errorMsg}
            <div
                class="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg p-3 mb-5 text-center flex items-center justify-center gap-2"
            >
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke-width="1.5"
                    stroke="currentColor"
                    class="w-5 h-5"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3Z"
                    />
                </svg>
                {errorMsg}
            </div>
        {/if}

        <form class="space-y-4" onsubmit={(e) => { e.preventDefault(); handleSubmit(e); }} action="javascript:void(0)">
            <div>
                <label
                    for="username"
                    class="block text-xs font-semibold uppercase text-gray-500 mb-1"
                >
                    Usuario
                </label>
                <input
                    id="username"
                    type="text"
                    bind:value={username}
                    required
                    placeholder="admin"
                    class="w-full border border-gray-300 rounded-xl py-2.5 px-4 text-gray-800 focus:outline-none focus:ring-2 focus:ring-indigo-400 transition-all"
                />
            </div>
            <div>
                <label
                    for="email"
                    class="block text-xs font-semibold uppercase text-gray-500 mb-1"
                >
                    Correo Electrónico
                </label>
                <input
                    id="email"
                    type="email"
                    bind:value={email}
                    required
                    placeholder="admin@example.com"
                    class="w-full border border-gray-300 rounded-xl py-2.5 px-4 text-gray-800 focus:outline-none focus:ring-2 focus:ring-indigo-400 transition-all"
                />
            </div>
            <div>
                <label
                    for="password"
                    class="block text-xs font-semibold uppercase text-gray-500 mb-1"
                >
                    Contraseña
                </label>
                <input
                    id="password"
                    type="password"
                    bind:value={password}
                    required
                    minlength="6"
                    placeholder="••••••••"
                    class="w-full border border-gray-300 rounded-xl py-2.5 px-4 text-gray-800 focus:outline-none focus:ring-2 focus:ring-indigo-400 transition-all"
                />
            </div>
            <div>
                <label
                    for="passwordConfirm"
                    class="block text-xs font-semibold uppercase text-gray-500 mb-1"
                >
                    Confirmar Contraseña
                </label>
                <input
                    id="passwordConfirm"
                    type="password"
                    bind:value={passwordConfirm}
                    required
                    minlength="6"
                    placeholder="••••••••"
                    class="w-full border border-gray-300 rounded-xl py-2.5 px-4 text-gray-800 focus:outline-none focus:ring-2 focus:ring-indigo-400 transition-all"
                />
            </div>
            <button
                type="submit"
                disabled={loading}
                class="w-full h-11 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white font-semibold rounded-xl transition-colors shadow-md mt-2"
            >
                {loading ? "Creando administrador..." : "Crear Administrador"}
            </button>
        </form>

        <p class="text-center text-gray-400 text-xs mt-6">
            © 2026 OmniWISP
        </p>
    </div>
</div>

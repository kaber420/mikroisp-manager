<script lang="ts">
    import axios from "axios";
    import { goto } from "$app/navigation";

    let username = $state("");
    let password = $state("");
    let errorMsg = $state("");
    let loading = $state(false);

    async function handleSubmit(e: Event) {
        e.preventDefault();
        loading = true;
        errorMsg = "";

        const formData = new URLSearchParams();
        formData.append("username", username);
        formData.append("password", password);

        try {
            // POST to /auth/cookie/login through Vite proxy (same origin :5173)
            // This way the cookie is set for :5173 — NOT for :7777
            const response = await axios.post("/auth/cookie/login", formData, {
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded",
                    Accept: "application/json",
                },
                withCredentials: true,
                // Prevent axios from following redirect automatically
                maxRedirects: 0,
                validateStatus: (s: number) => s < 400 || s === 422,
            });

            if (
                response.status === 200 ||
                response.status === 204 ||
                response.status === 303
            ) {
                // Login ok — go to dashboard
                goto("/");
            } else {
                errorMsg =
                    response.data?.detail || "Usuario o contraseña incorrectos";
            }
        } catch (err: any) {
            if (err.response?.status === 400 || err.response?.status === 422) {
                errorMsg = "Usuario o contraseña incorrectos";
            } else if (err.response?.status === 429) {
                errorMsg =
                    "⚠️ Demasiados intentos. Por favor, espera un momento.";
            } else {
                errorMsg = "Error de conexión. Intenta de nuevo.";
            }
        } finally {
            loading = false;
        }
    }
</script>

<svelte:head>
    <title>Login — UMonitor V2</title>
</svelte:head>

<div class="min-h-screen bg-gray-100 flex items-center justify-center p-4">
    <div class="w-full max-w-md bg-white rounded-2xl shadow-lg p-8">
        <div class="flex flex-col items-center mb-8">
            <svg
                class="h-12 w-12 text-indigo-600 mb-3"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
            >
                <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2V9M9 21H5a2 2 0 01-2-2V9m0 0h18"
                />
            </svg>
            <h1 class="text-2xl font-bold text-gray-800">
                µMonitor <span class="text-indigo-600">V2</span>
            </h1>
            <p class="text-gray-500 text-sm mt-1">
                Ingresa tus credenciales para continuar
            </p>
        </div>

        {#if errorMsg}
            <div
                class="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg p-3 mb-5 text-center"
            >
                {errorMsg}
            </div>
        {/if}

        <form onsubmit={handleSubmit} class="space-y-5">
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
                    placeholder="••••••••"
                    class="w-full border border-gray-300 rounded-xl py-2.5 px-4 text-gray-800 focus:outline-none focus:ring-2 focus:ring-indigo-400 transition-all"
                />
            </div>
            <button
                type="submit"
                disabled={loading}
                class="w-full h-11 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white font-semibold rounded-xl transition-colors shadow-md"
            >
                {loading ? "Ingresando..." : "Iniciar Sesión"}
            </button>
        </form>

        <p class="text-center text-gray-400 text-xs mt-6">
            © 2025 µISP Monitor System
        </p>
    </div>
</div>

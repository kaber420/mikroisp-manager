<script lang="ts">
	import "../app.css";
	import { onMount } from "svelte";
	import { page } from "$app/stores";
	import { goto } from "$app/navigation";
	import { api } from "$lib/api";
	import { checkSession, requireAuth } from "$lib/authutils";
	import { isAuthenticated, initialized, user } from "$lib/stores/auth";

	let { children } = $props();

	onMount(async () => {
		// Verificar sesión al cargar cualquier página del layout
		await checkSession();
		// Si está en una ruta protegida y no está autenticado, redirigir
		if ($page.url.pathname !== "/login") {
			requireAuth($isAuthenticated);
		}
	});

	async function handleLogout() {
		try {
			await api.post("/auth/cookie/logout", {});
		} catch (_) {
			// Ignorar error, limpiar sesión igualmente
		} finally {
			isAuthenticated.set(false);
			user.set(null);
			initialized.set(false);
			goto("/login");
		}
	}
</script>

<!-- Spinner mientras se verifica la sesión -->
{#if !$initialized && $page.url.pathname !== "/login"}
	<div class="min-h-screen bg-gray-50 flex items-center justify-center">
		<div class="text-center">
			<div
				class="w-10 h-10 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto"
			></div>
			<p class="text-gray-500 mt-3 text-sm">Verificando sesión...</p>
		</div>
	</div>
{:else if $page.url.pathname === "/login"}
	<!-- Página de login sin layout de sidebar -->
	{@render children()}
{:else}
	<!-- Layout principal solo si está autenticado -->
	<div
		class="min-h-screen bg-gray-50 text-slate-800 font-sans flex antialiased"
	>
		<!-- Sidebar -->
		<aside
			class="w-64 bg-white border-r border-gray-200 flex flex-col shadow-sm"
		>
			<div class="h-16 flex items-center px-6 border-b border-gray-100">
				<span
					class="text-xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent"
					>Manager V2</span
				>
			</div>
			<nav class="flex-1 px-4 py-6 space-y-2">
				<a
					href="/"
					class="block px-4 py-2.5 rounded-xl bg-blue-50 text-blue-700 font-medium transition-colors"
					>Dashboard</a
				>
				<a
					href="/clientes"
					class="block px-4 py-2.5 rounded-xl text-gray-600 hover:bg-gray-50 hover:text-gray-900 font-medium transition-colors"
					>Clientes</a
				>
				<a
					href="/planes"
					class="block px-4 py-2.5 rounded-xl text-gray-600 hover:bg-gray-50 hover:text-gray-900 font-medium transition-colors"
					>Planes</a
				>
			</nav>
			<!-- Usuario y logout al fondo del sidebar -->
			<div class="px-4 py-4 border-t border-gray-100">
				{#if $user}
					<p class="text-xs text-gray-400 truncate mb-2">
						{$user.email ?? $user.username ?? "Usuario"}
					</p>
				{/if}
				<button
					onclick={handleLogout}
					class="w-full text-left px-4 py-2.5 rounded-xl text-red-600 hover:bg-red-50 font-medium transition-colors text-sm"
				>
					Cerrar sesión
				</button>
			</div>
		</aside>

		<!-- Main Content -->
		<div class="flex-1 flex flex-col">
			<!-- Top Navbar -->
			<header
				class="h-16 bg-white/70 backdrop-blur-md border-b border-gray-200 flex items-center justify-between px-8 sticky top-0 z-10 transition-all"
			>
				<h1 class="text-lg font-semibold text-gray-800">
					Panel de Control
				</h1>
				<div class="flex items-center gap-4">
					<a
						href={__BACKEND_URL__}
						class="text-sm font-medium text-gray-500 hover:text-gray-900 transition-colors"
						>Volver a Clásica</a
					>
					<div
						class="w-8 h-8 rounded-full bg-gradient-to-tr from-indigo-500 to-purple-500 text-white flex items-center justify-center font-bold shadow-md"
					>
						{($user?.email?.[0] ?? "A").toUpperCase()}
					</div>
				</div>
			</header>

			<!-- Page Content -->
			<main class="flex-1 p-8 overflow-y-auto">
				{@render children()}
			</main>
		</div>
	</div>
{/if}

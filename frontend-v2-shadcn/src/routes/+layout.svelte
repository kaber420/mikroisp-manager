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
			<div class="p-4 border-t border-gray-100">
				{#if $user && $user.username}
					<div
						class="flex items-center gap-3 mb-4 p-2 rounded-xl bg-gray-50 border border-gray-100"
					>
						<div
							class="w-10 h-10 rounded-full bg-gradient-to-tr from-indigo-500 to-purple-500 text-white flex items-center justify-center font-bold shadow-sm shrink-0"
						>
							{$user.username[0].toUpperCase()}
						</div>
						<div class="flex flex-col min-w-0 flex-1">
							<span
								class="text-sm font-semibold text-gray-800 truncate"
							>
								{$user.username}
							</span>
							<div class="flex items-center gap-1 mt-0.5">
								{#if $user.role === "admin" || $user.is_superuser}
									<svg
										class="w-3 h-3 text-amber-500"
										fill="currentColor"
										viewBox="0 0 20 20"
										><path
											d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"
										></path></svg
									>
									<span
										class="text-xs font-medium text-amber-600"
										>Admin</span
									>
								{:else if $user.role === "tecnico"}
									<svg
										class="w-3 h-3 text-blue-500"
										fill="none"
										stroke="currentColor"
										viewBox="0 0 24 24"
										><path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
										></path><path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
										></path></svg
									>
									<span
										class="text-xs font-medium text-blue-600 capitalize"
										>{$user.role}</span
									>
								{:else if $user.role === "cobranza"}
									<svg
										class="w-3 h-3 text-emerald-500"
										fill="none"
										stroke="currentColor"
										viewBox="0 0 24 24"
										><path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
										></path></svg
									>
									<span
										class="text-xs font-medium text-emerald-600 capitalize"
										>{$user.role}</span
									>
								{:else}
									<svg
										class="w-3 h-3 text-gray-500"
										fill="none"
										stroke="currentColor"
										viewBox="0 0 24 24"
										><path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
										></path></svg
									>
									<span
										class="text-xs font-medium text-gray-600 capitalize"
										>{$user.role || "Usuario"}</span
									>
								{/if}
							</div>
						</div>
					</div>
				{/if}
				<button
					onclick={handleLogout}
					class="w-full text-center px-4 py-2.5 rounded-xl text-red-600 hover:bg-red-50 hover:text-red-700 font-medium transition-colors text-sm border border-transparent hover:border-red-100 flex items-center justify-center gap-2"
				>
					<svg
						class="w-4 h-4"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
						><path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
						></path></svg
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
				<div></div>
				<div class="flex items-center gap-4"></div>
			</header>

			<!-- Page Content -->
			<main class="flex-1 p-8 overflow-y-auto">
				{@render children()}
			</main>
		</div>
	</div>
{/if}

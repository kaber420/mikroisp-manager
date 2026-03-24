<script lang="ts">
	import { page } from "$app/stores";
	import LavaLampBackground from "$lib/components/LavaLampBackground.svelte";
	import { theme } from "$lib/stores/theme";
	import { onMount } from "svelte";

	onMount(() => {
		theme.init();
	});

	// Configuración reactiva según código de error
	let errorConfig = $derived(
		$page.status === 404
			? {
					icon: "🔍",
					title: "Página No Encontrada",
					description: "La ruta que buscas no existe o fue movida a otro lugar.",
					colorClass: "text-warning",
					showLogout: false,
				}
			: $page.status === 403
				? {
						icon: "🔒",
						title: "Acceso Denegado",
						description: "No tienes permisos suficientes para acceder a este recurso.",
						colorClass: "text-error",
						showLogout: true,
					}
				: {
						icon: "⚠️",
						title: "Error Interno del Servidor",
						description: "Algo salió mal en el servidor. Intenta recargar la página.",
						colorClass: "text-error",
						showLogout: false,
					},
	);
</script>

<svelte:head>
	<title>Error {$page.status} — OmniWISP</title>
</svelte:head>

<LavaLampBackground />

<!-- Contenedor principal a pantalla completa -->
<div class="min-h-screen flex items-center justify-center p-4">
	<div
		class="card bg-base-100/70 backdrop-blur-xl shadow-2xl border border-base-300/50 w-full max-w-md text-center"
	>
		<div class="card-body gap-5">
			<!-- Icono principal -->
			<div class="text-7xl select-none" role="img" aria-label={errorConfig.title}>
				{errorConfig.icon}
			</div>

			<!-- Código de error en grande -->
			<div class="font-black text-7xl {errorConfig.colorClass} opacity-30 leading-none">
				{$page.status}
			</div>

			<!-- Título y descripción -->
			<div class="space-y-2">
				<h1 class="text-2xl font-bold">{errorConfig.title}</h1>
				<p class="text-base-content/60 text-sm">{errorConfig.description}</p>

				<!-- Mensaje técnico opcional -->
				{#if $page.error?.message}
					<div
						class="mt-3 p-3 bg-base-200 rounded-lg text-xs font-mono text-left opacity-70 break-words"
					>
						<span class="text-base-content/40 uppercase text-[10px] tracking-wider block mb-1"
							>Detalle técnico</span
						>
						{$page.error.message}
					</div>
				{/if}
			</div>

			<!-- Botones de acción -->
			<div class="flex flex-col sm:flex-row gap-3 justify-center pt-2">
				<a href="/" class="btn btn-primary btn-sm gap-2">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						class="h-4 w-4"
						fill="none"
						viewBox="0 0 24 24"
						stroke="currentColor"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"
						/>
					</svg>
					Ir al Dashboard
				</a>

				<button
					onclick={() => history.back()}
					class="btn btn-ghost btn-sm gap-2 border border-base-300"
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						class="h-4 w-4"
						fill="none"
						viewBox="0 0 24 24"
						stroke="currentColor"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M10 19l-7-7m0 0l7-7m-7 7h18"
						/>
					</svg>
					Ir Atrás
				</button>

				{#if errorConfig.showLogout}
					<a href="/login" class="btn btn-error btn-outline btn-sm gap-2">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							class="h-4 w-4"
							fill="none"
							viewBox="0 0 24 24"
							stroke="currentColor"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
							/>
						</svg>
						Cerrar Sesión
					</a>
				{/if}
			</div>

			<!-- Footer de la tarjeta -->
			<p class="text-[11px] text-base-content/30 pt-1">
				OmniWISP — Si el problema persiste, contacta al administrador del sistema.
			</p>
		</div>
	</div>
</div>

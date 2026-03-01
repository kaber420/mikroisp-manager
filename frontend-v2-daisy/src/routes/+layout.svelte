<script lang="ts">
	import "../app.css";
	import { onMount } from "svelte";
	import { page } from "$app/stores";
	import { api } from "$lib/api";
	import { initSession, clearSession } from "$lib/authutils";
	import { user, sessionState } from "$lib/stores/auth";
	import { theme, THEMES, type ThemeId } from "$lib/stores/theme";
	import SessionMonitor from "$lib/components/SessionMonitor.svelte";

	let { children } = $props();

	onMount(() => {
		theme.init();
		// Auth Optimista: pinta inmediato desde caché, verifica en background
		if ($page.url.pathname !== "/login") {
			initSession($page.url.pathname);
		}
	});

	async function handleLogout() {
		try {
			await api.post("/auth/cookie/logout", {});
		} catch (_) {
			// Ignorar error, limpiar sesión igualmente
		} finally {
			clearSession();
			window.location.href = "/login";
		}
	}

	// Clases reactivas para el Avatar según el estado de la sesión
	let avatarRingClass = $derived(
		$sessionState === "active"
			? "ring-success shadow-[0_0_12px_rgba(0,255,0,0.5)]"
			: $sessionState === "warning"
				? "ring-warning shadow-[0_0_12px_rgba(255,165,0,0.8)]"
				: "ring-neutral shadow-none opacity-50",
	);

	function setTheme(id: ThemeId) {
		theme.setTheme(id);
	}

	// Obtener inicial/avatar del usuario
	function getUserInitial(username: string | undefined | null): string {
		if (!username) return "?";
		return username[0].toUpperCase();
	}

	// Obtener badge de rol
	function getRoleBadge(role: string | undefined | null): string {
		if (!role) return "badge-ghost";
		const map: Record<string, string> = {
			admin: "badge-warning",
			tecnico: "badge-info",
			cobranza: "badge-success",
		};
		return map[role] || "badge-ghost";
	}

	// 4 Módulos Principales
	const mainModules = [
		{
			href: "/",
			label: "Principal",
			emoji: "📊",
			color: "hover:bg-primary hover:text-primary-content",
			desc: "Dashboard General",
		},
		{
			href: "/routers",
			label: "Infraestructura",
			emoji: "📡",
			color: "hover:bg-secondary hover:text-secondary-content",
			desc: "Routers, Switches, APs...",
		},
		{
			href: "/clientes",
			label: "Gestión",
			emoji: "👥",
			color: "hover:bg-info hover:text-info-content",
			desc: "Clientes, Planes y Zonas",
		},
		{
			href: "/configuracion",
			label: "Sistema",
			emoji: "⚙️",
			color: "hover:bg-neutral hover:text-neutral-content",
			desc: "Usuarios y Ajustes",
		},
	];

	// Definición de submenús contextuales
	const subMenus: Record<string, { href: string; label: string }[]> = {
		// Grupo: Infraestructura
		"/routers": [
			{ href: "/routers", label: "Dashboard Routers" },
			{ href: "/switches", label: "Switches" },
			{ href: "/access-points", label: "Access Points" },
			{ href: "/cpes", label: "CPEs" },
		],
		"/switches": [
			{ href: "/routers", label: "Routers" },
			{ href: "/switches", label: "Dashboard Switches" },
			{ href: "/access-points", label: "Access Points" },
			{ href: "/cpes", label: "CPEs" },
		],
		"/access-points": [
			{ href: "/routers", label: "Routers" },
			{ href: "/switches", label: "Switches" },
			{ href: "/access-points", label: "Dashboard APs" },
			{ href: "/cpes", label: "CPEs" },
		],
		"/cpes": [
			{ href: "/routers", label: "Routers" },
			{ href: "/switches", label: "Switches" },
			{ href: "/access-points", label: "Access Points" },
			{ href: "/cpes", label: "Dashboard CPEs" },
		],

		// Grupo: Gestión
		"/clientes": [
			{ href: "/clientes", label: "Base de Datos" },
			{ href: "/planes", label: "Planes" },
			{ href: "/zonas", label: "Zonas" },
		],
		"/planes": [
			{ href: "/clientes", label: "Clientes" },
			{ href: "/planes", label: "Gestión de Planes" },
			{ href: "/zonas", label: "Zonas" },
		],
		"/zonas": [
			{ href: "/clientes", label: "Clientes" },
			{ href: "/planes", label: "Planes" },
			{ href: "/zonas", label: "Zonas de Cobertura" },
		],

		// Grupo: Sistema
		"/configuracion": [
			{ href: "/configuracion", label: "Ajustes Generales" },
			{ href: "/usuarios", label: "Usuarios" },
		],
		"/usuarios": [
			{ href: "/configuracion", label: "Configuración" },
			{ href: "/usuarios", label: "Control de Acceso (Usuarios)" },
		],
	};

	// Submenú actual (reactivo derivado)
	let currentSubMenu = $derived(subMenus[$page.url.pathname] || []);
</script>

{#if $page.url.pathname === "/login"}
	<!-- Página de login sin layout -->
	{@render children()}
{:else}
	<!-- Layout principal -->
	<div class="min-h-screen bg-base-200 flex flex-col antialiased">
		<!-- ===== TOP NAVBAR ===== -->
		<div class="navbar bg-base-100 shadow-md sticky top-0 z-50 px-4">
			<!-- IZQUIERDA: Menú App Grid + Logo -->
			<div class="navbar-start gap-2">
				<!-- Botón de Mega Menú (App Grid) -->
				<div class="dropdown">
					<div
						tabindex="0"
						role="button"
						class="btn btn-ghost btn-circle"
						aria-label="Menú de módulos"
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							class="h-6 w-6"
							fill="none"
							viewBox="0 0 24 24"
							stroke="currentColor"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M4 6h16M4 12h16M4 18h7"
							/>
						</svg>
					</div>
					<!-- Mega Menu tipo App Grid -->
					<div
						tabindex="0"
						class="dropdown-content mt-3 z-[60] p-4 shadow-2xl bg-base-200 rounded-2xl w-80 border border-base-300"
					>
						<p
							class="text-xs font-bold uppercase tracking-widest text-base-content/50 mb-3 px-1"
						>
							Módulos del Sistema
						</p>
						<div class="grid grid-cols-2 gap-3">
							{#each mainModules as mod}
								<a
									href={mod.href}
									class="flex flex-col items-center justify-center p-4 bg-base-100 rounded-xl border border-base-300 {mod.color} transition-all duration-200 hover:scale-105 hover:shadow-md group"
								>
									<span
										class="text-3xl mb-2 group-hover:scale-110 transition-transform"
										>{mod.emoji}</span
									>
									<span
										class="font-semibold text-sm text-center leading-tight"
										>{mod.label}</span
									>
									<span
										class="text-[10px] px-1 opacity-60 text-center mt-1 hidden group-hover:block leading-tight"
										>{mod.desc}</span
									>
								</a>
							{/each}
						</div>
					</div>
				</div>

				<!-- Logo -->
				<a href="/" class="btn btn-ghost gap-2 px-2">
					<span
						class="text-xl font-black bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent"
					>
						UManager
					</span>
					<span
						class="badge badge-outline badge-sm border-base-300 font-mono"
						>v2</span
					>
				</a>
			</div>

			<!-- CENTRO: Navegación contextual (desktop only) -->
			<div class="navbar-center hidden lg:flex">
				{#if currentSubMenu.length > 0}
					<div class="join bg-base-200 p-1 rounded-full">
						{#each currentSubMenu as nav}
							<a
								href={nav.href}
								class="btn btn-sm btn-ghost join-item rounded-full transition-all text-xs
									{$page.url.pathname === nav.href
									? 'bg-base-100 shadow-sm font-bold text-primary'
									: ''}"
							>
								{nav.label}
							</a>
						{/each}
					</div>
				{/if}
			</div>

			<!-- DERECHA: Herramientas globales -->
			<div class="navbar-end gap-1">
				<!-- Selector de Temas -->
				<div class="dropdown dropdown-end">
					<div
						tabindex="0"
						role="button"
						class="btn btn-ghost btn-circle"
						aria-label="Cambiar tema"
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							class="h-5 w-5"
							fill="none"
							viewBox="0 0 24 24"
							stroke="currentColor"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01"
							/>
						</svg>
					</div>
					<div
						tabindex="0"
						class="dropdown-content z-[60] mt-4 shadow-2xl bg-base-200 rounded-2xl w-56 border border-base-300 p-2"
					>
						<p
							class="text-xs font-bold uppercase tracking-widest text-base-content/50 mb-2 px-2"
						>
							Seleccionar Tema
						</p>
						<ul class="menu menu-sm p-0">
							{#each THEMES as t}
								<li>
									<button
										onclick={() => setTheme(t.id)}
										class="flex justify-between items-center rounded-lg
											{$theme === t.id ? 'bg-primary text-primary-content font-semibold' : ''}"
									>
										<span>{t.emoji} {t.label}</span>
										{#if $theme === t.id}
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
													d="M5 13l4 4L19 7"
												/>
											</svg>
										{/if}
									</button>
								</li>
							{/each}
						</ul>
					</div>
				</div>

				<!-- Menú de perfil/usuario -->
				<div class="dropdown dropdown-end">
					<div
						tabindex="0"
						role="button"
						class="btn btn-ghost btn-circle"
						aria-label="Menú de usuario"
					>
						<div class="avatar placeholder">
							<div
								class="bg-gradient-to-br from-primary to-secondary text-primary-content rounded-full w-9 grid place-items-center font-bold text-sm ring ring-offset-base-100 ring-offset-2 transition-all duration-1000 {avatarRingClass}"
							>
								<span>{getUserInitial($user?.username)}</span>
							</div>
						</div>
					</div>
					<div
						tabindex="0"
						class="dropdown-content z-[60] mt-4 shadow-2xl bg-base-200 rounded-2xl w-56 border border-base-300"
					>
						<!-- Info del usuario -->
						<div class="p-4 border-b border-base-300">
							<div class="flex items-center gap-3">
								<div class="avatar placeholder">
									<div
										class="bg-gradient-to-br from-primary to-secondary text-primary-content rounded-full w-10 grid place-items-center font-bold ring ring-offset-base-100 ring-offset-2 transition-all duration-1000 {avatarRingClass}"
									>
										<span
											>{getUserInitial(
												$user?.username,
											)}</span
										>
									</div>
								</div>
								<div class="min-w-0">
									<p class="font-semibold text-sm truncate">
										{$user?.username || "Usuario"}
									</p>
									{#if $user?.role}
										<span
											class="badge badge-xs {getRoleBadge(
												$user.role,
											)} capitalize"
										>
											{$user.role}
										</span>
									{/if}
								</div>
							</div>
						</div>
						<!-- Opciones del menú -->
						<ul class="menu menu-sm p-2">
							<li>
								<a href="/configuracion" class="rounded-lg">
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
											d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
										/>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
										/>
									</svg>
									Configuración
								</a>
							</li>
							<li>
								<button
									onclick={handleLogout}
									class="text-error hover:bg-error hover:text-error-content rounded-lg"
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
											d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
										/>
									</svg>
									Cerrar Sesión
								</button>
							</li>
						</ul>
					</div>
				</div>
			</div>
		</div>

		<!-- ===== CONTENIDO PRINCIPAL ===== -->
		<main
			class="flex-1 container mx-auto max-w-full px-4 py-6 overflow-y-auto"
		>
			{@render children()}
		</main>

		<!-- ===== FOOTER MINIMALISTA ===== -->
		<footer
			class="footer footer-center py-3 bg-base-100 text-base-content/40 text-xs border-t border-base-200"
		>
			<aside>
				<p>
					UManager v2 &mdash; DaisyUI Edition &copy; {new Date().getFullYear()}
				</p>
			</aside>
		</footer>

		<!-- Monitor de sesión (global a la aplicación, invisible excepto durante warning) -->
		<SessionMonitor timeoutMinutes={15} warningMinutes={1} />
	</div>
{/if}

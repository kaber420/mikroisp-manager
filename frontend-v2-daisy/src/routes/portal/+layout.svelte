<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import { page } from "$app/stores";
    import { initSession, clearSession } from "$lib/authutils";
    import { user, sessionState } from "$lib/stores/auth";
    import SessionMonitor from "$lib/components/SessionMonitor.svelte";
    import { theme } from "$lib/stores/theme";
    import LavaLampBackground from "$lib/components/LavaLampBackground.svelte";
    import NotificationContainer from "$lib/components/NotificationContainer.svelte";
    import { logout } from "$lib/api";

	let { children } = $props();

	onMount(() => {
		// Inicializa la sesión específica para el portal de clientes
		initSession($page.url.pathname);
	});

	async function handleLogout() {
        try {
            await logout();
		} catch (_) {
			// Ignorar error, limpiar sesión igualmente
		} finally {
			clearSession();
			window.location.href = "/login";
		}
	}

	// Obtener inicial/avatar del usuario
	function getUserInitial(username: string | undefined | null): string {
		if (!username) return "?";
		return username[0].toUpperCase();
	}

	// Módulos del Portal de Clientes
	const clientModules = [
		{
			href: "/portal",
			label: "Dashboard",
			emoji: "🏠",
		},
		{
			href: "/portal/planes",
			label: "Mis Planes",
			emoji: "📦",
		},
		{
			href: "/portal/tickets",
			label: "Soporte",
			emoji: "🛠️",
		}
	];
</script>

<LavaLampBackground />

<div
	class="min-h-screen flex flex-col antialiased {$theme.lavaLampActive
		? 'bg-transparent'
		: 'bg-base-200'}"
>
	<!-- ===== CLIENT NAVBAR ===== -->
	<header class="navbar bg-base-100 shadow-md sticky top-0 z-50 px-6">
		<div class="navbar-start gap-4">
			<a href="/portal" class="flex items-center gap-2 group">
				<div class="w-10 h-10 bg-gradient-to-br from-primary to-secondary rounded-xl flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform duration-300">
                    <span class="text-white font-bold text-xl">O</span>
                </div>
				<div class="flex flex-col">
                    <span class="text-lg font-black bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent leading-none">
                        OmniWISP
                    </span>
                    <span class="text-[10px] font-bold uppercase tracking-wider opacity-50 leading-none">
                        Portal Clientes
                    </span>
                </div>
			</a>
		</div>

		<div class="navbar-center hidden lg:flex">
			<nav class="join bg-base-200 p-1 rounded-full">
				{#each clientModules as nav}
					<a
						href={nav.href}
						class="btn btn-sm btn-ghost join-item rounded-full transition-all text-xs gap-2
							{$page.url.pathname === nav.href
							? 'bg-base-100 shadow-sm font-bold text-primary'
							: 'opacity-70 hover:opacity-100'}"
					>
                        <span>{nav.emoji}</span>
						{nav.label}
					</a>
				{/each}
			</nav>
		</div>

		<div class="navbar-end gap-3">
			<div class="dropdown dropdown-end">
				<div
					tabindex="0"
					role="button"
					class="btn btn-ghost btn-circle avatar placeholder ring ring-primary ring-offset-base-100 ring-offset-1"
					aria-label="Menú de usuario"
				>
					<div class="bg-neutral text-neutral-content rounded-full w-10">
						<span class="text-xs font-bold">{getUserInitial($user?.username)}</span>
					</div>
				</div>
				<ul
					class="dropdown-content mt-3 z-[60] p-2 shadow-2xl bg-base-200 rounded-2xl w-52 border border-base-300"
				>
                    <li class="px-4 py-3 border-b border-base-300 mb-2">
                        <p class="font-bold text-sm truncate">{$user?.username || "Cliente OmniWISP"}</p>
                        <p class="text-[10px] opacity-50 uppercase tracking-tighter">Acceso Cliente</p>
                    </li>
					<li>
						<a href="/portal/perfil" class="flex items-center gap-3 p-3 hover:bg-base-300 rounded-xl transition-colors">
                            <span>👤</span> Mi Cuenta
                        </a>
					</li>
					<li>
						<button
							onclick={handleLogout}
							class="w-full flex items-center gap-3 p-3 text-error hover:bg-error/10 hover:text-error rounded-xl transition-colors"
						>
							<span>🚪</span> Cerrar Sesión
						</button>
					</li>
				</ul>
			</div>
		</div>
	</header>

	<main class="flex-1 container mx-auto max-w-6xl px-4 py-8 overflow-y-auto">
		{@render children()}
	</main>

	<footer
		class="footer footer-center py-6 bg-base-100 text-base-content/40 text-xs border-t border-base-200"
	>
		<div class="flex flex-col gap-1">
			<p class="font-bold">OmniWISP Portal &bull; Edición Suscriptores</p>
            <p>&copy; {new Date().getFullYear()} Todos los derechos reservados.</p>
		</div>
	</footer>

	<SessionMonitor timeoutMinutes={30} warningMinutes={5} />
	<NotificationContainer />
</div>

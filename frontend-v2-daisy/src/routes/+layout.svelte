<script lang="ts">
	import "../app.css";
	import { theme } from "$lib/stores/theme";
	import { onMount } from "svelte";
    import PostSetupModal from "$lib/components/PostSetupModal.svelte";
    import { isAuthenticated } from "$lib/stores/auth";

	let { children } = $props();

	onMount(() => {
		// Inicializa el tema seleccionado almacenado en localStorage
		theme.init();
	});
</script>

{@render children()}

<!-- Solo mostrar modales administrativos de MVP OmniWisp si estamos logueados -->
{#if $isAuthenticated}
    <PostSetupModal />
{/if}

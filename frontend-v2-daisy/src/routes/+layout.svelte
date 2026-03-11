<script lang="ts">
	import "../app.css";
	import { theme } from "$lib/stores/theme";
	import { onMount } from "svelte";

	let { children } = $props();

	onMount(() => {
		// Inicializa el tema seleccionado almacenado en localStorage
		theme.init();
	});
</script>

{@render children()}

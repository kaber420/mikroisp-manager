<script lang="ts">
  import "../app.css";
  import { onMount } from "svelte";
  import { checkSession, requireAuth } from "$lib/authutils";
  import { isAuthenticated, initialized } from "$lib/stores/auth";

  let { children } = $props();

  onMount(async () => {
    await checkSession();
    // Watch for unauthenticated state after init
    initialized.subscribe((isInit) => {
      if (isInit) {
        isAuthenticated.subscribe((isAuth) => {
          requireAuth(isAuth);
        });
      }
    });
  });
</script>

<svelte:head>
  <title>UMonitor V2</title>
</svelte:head>

<div class="app min-h-screen bg-gray-50 text-gray-900 flex flex-col font-sans">
  {#if $initialized}
    {#if $isAuthenticated}
      <!-- Main Layout when authenticated -->
      <nav
        class="bg-indigo-600 text-white p-4 flex justify-between items-center shadow-md"
      >
        <div class="font-bold text-xl">UMonitor V2</div>
        <div class="space-x-4">
          <a href="/" class="hover:text-indigo-200 transition-colors"
            >Dashboard</a
          >
          <a href="/clients" class="hover:text-indigo-200 transition-colors"
            >Clientes</a
          >
          <!-- Link back to old version -->
          <button
            onclick={() =>
              (window.location.href = `${window.location.protocol}//${window.location.hostname}:${__UVICORN_PORT__}/`)}
            class="bg-indigo-800 hover:bg-indigo-900 px-3 py-1 rounded transition-colors text-sm border border-indigo-400"
            >Volver a Clásica</button
          >
        </div>
      </nav>

      <main class="flex-grow p-6">
        {@render children()}
      </main>
    {:else}
      <div class="flex items-center justify-center min-h-screen">
        <div
          class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"
        ></div>
        <p class="ml-3 text-gray-600">Redirigiendo al login...</p>
      </div>
    {/if}
  {:else}
    <!-- Loading State -->
    <div class="flex items-center justify-center min-h-screen">
      <div
        class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"
      ></div>
    </div>
  {/if}
</div>

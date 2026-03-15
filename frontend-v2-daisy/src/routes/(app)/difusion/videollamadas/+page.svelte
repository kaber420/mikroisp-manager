<script lang="ts">
  import { user } from '$lib/stores/auth';
  import PoolList from '$lib/components/video/PoolList.svelte';
  import WaitingRoomSettingsModal from '$lib/components/video/WaitingRoomSettingsModal.svelte';

  let isConnected = $state(false);
  let isLoading = $state(false);
  let poolList: any = $state();
  let showSettingsModal = $state(false);
</script>

<svelte:head>
  <title>Panel de Videollamadas — OmniWISP</title>
</svelte:head>

<div class="mb-6 flex sm:flex-row flex-col items-center justify-between gap-4 p-6 bg-base-100/60 backdrop-blur-md rounded-2xl shadow-sm border border-base-200">
  <div class="flex items-center gap-4">
    <div class="bg-primary/10 text-primary rounded-xl p-3">
      <svg xmlns="http://www.w3.org/2000/svg" class="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
      </svg>
    </div>
    <div>
      <h1 class="text-3xl font-black bg-gradient-to-br from-primary to-secondary bg-clip-text text-transparent drop-shadow-sm">
        Videollamadas de Soporte
      </h1>
      <p class="text-base-content/60 font-medium mt-1">Gestión en tiempo real de llamadas con clientes</p>
    </div>
  </div>

  <div class="flex items-center gap-3">
    <!-- Botón de actualización integrado -->
    <button 
      class="btn btn-circle btn-ghost {isLoading ? 'loading' : ''}" 
      onclick={() => poolList?.refreshPool()} 
      disabled={isLoading}
      title="Actualizar lista"
    >
      {#if !isLoading}
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
        </svg>
      {/if}
    </button>

    <!-- Indicador de conexión WS -->
    <div class="badge {isConnected ? 'badge-success' : 'badge-error'} badge-outline h-10 gap-2 px-4 font-bold transition-all">
      <span class="relative flex h-2 w-2">
        {#if isConnected}
          <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-current opacity-75"></span>
        {/if}
        <span class="relative inline-flex rounded-full h-2 w-2 bg-current"></span>
      </span>
      <span class="text-[10px] tracking-widest">{isConnected ? 'EN LÍNEA' : 'DESCONECTADO'}</span>
    </div>

    <button class="btn btn-outline border-base-300 gap-2 shadow-sm" onclick={() => showSettingsModal = true}>
      <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4h4" />
      </svg>
      Sala de Espera
    </button>
    
    <a href="/configuracion" class="btn btn-ghost border-base-300 gap-2 shadow-sm">
      <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
      Configurar LiveKit
    </a>
  </div>
</div>

<PoolList bind:this={poolList} techId={$user?.id || ''} bind:isConnected bind:isLoading />

<WaitingRoomSettingsModal bind:showModal={showSettingsModal} />

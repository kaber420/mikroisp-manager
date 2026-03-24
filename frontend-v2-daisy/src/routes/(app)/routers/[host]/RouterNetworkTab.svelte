<script lang="ts">
    import { onMount } from "svelte";
    import { getRouterFullDetails, deleteIpAddress } from "$lib/api";
    import AddIpModal from "./AddIpModal.svelte";

    let { routerHost } = $props<{ routerHost: string }>();

    let loading = $state(true);
    let errorMsg = $state<string | null>(null);

    let ipAddresses = $state<any[]>([]);
    let interfaces = $state<any[]>([]);
    let showAddModal = $state(false);

    onMount(() => {
        fetchData();
    });

    async function fetchData() {
        loading = true;
        errorMsg = null;
        try {
            const data = await getRouterFullDetails(routerHost);
            ipAddresses = data.ip_addresses || [];
            interfaces = data.interfaces || [];
        } catch (e: any) {
            errorMsg =
                e.response?.data?.detail ||
                e.message ||
                "Error al cargar datos de red";
        } finally {
            loading = false;
        }
    }

    async function handleDelete(address: string) {
        if (
            !confirm(
                `¿Estás seguro de que quieres eliminar la dirección IP ${address}?`,
            )
        )
            return;

        try {
            await deleteIpAddress(routerHost, address);
            await fetchData();
        } catch (e: any) {
            alert(`Error: ${e.response?.data?.detail || e.message}`);
        }
    }
</script>

<div class="space-y-6">
    <div class="glass-card-flat p-6 rounded-2xl">
        <div class="flex justify-between items-center mb-6">
            <h2 class="text-xl font-bold flex items-center gap-2">
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke-width="1.5"
                    stroke="currentColor"
                    class="w-6 h-6 text-primary"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M12 21v-8.25M15.75 21v-8.25M8.25 21v-8.25M3 9l9-6 9 6m-1.5 12V10.332A48.315 48.315 0 0 0 12 9.75c-2.551 0-5.056.2-7.5.582V21M3 21h18M12 6.75h.008v.008H12V6.75Z"
                    />
                </svg>
                Direcciones IP
            </h2>
            <button
                class="btn btn-sm btn-primary"
                onclick={() => (showAddModal = true)}
            >
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                    class="w-4 h-4"
                >
                    <path
                        d="M10.75 4.75a.75.75 0 0 0-1.5 0v4.5h-4.5a.75.75 0 0 0 0 1.5h4.5v4.5a.75.75 0 0 0 1.5 0v-4.5h4.5a.75.75 0 0 0 0-1.5h-4.5v-4.5Z"
                    />
                </svg>
                Adicionar IP
            </button>
        </div>

        {#if loading}
            <div class="flex justify-center p-8">
                <span class="loading loading-spinner text-primary"></span>
            </div>
        {:else if errorMsg}
            <div class="alert alert-error mb-4">
                <span>{errorMsg}</span>
                <button class="btn btn-sm" onclick={fetchData}
                    >Reintentar</button
                >
            </div>
        {:else}
            <div
                class="overflow-x-auto rounded-lg border border-base-content/10"
            >
                <table class="table table-sm w-full">
                    <thead class="bg-base-200">
                        <tr>
                            <th>Dirección</th>
                            <th>Interfaz</th>
                            <th>Network</th>
                            <th>Comentario</th>
                            <th class="w-1">Acciones</th>
                        </tr>
                    </thead>
                    <tbody>
                        {#each ipAddresses as ip}
                            <tr
                                class="hover focus:outline-none focus:bg-base-200"
                            >
                                <td class="font-bold text-primary font-mono"
                                    >{ip.address}</td
                                >
                                <td
                                    ><span class="badge badge-outline badge-sm"
                                        >{ip.interface}</span
                                    ></td
                                >
                                <td class="opacity-70 font-mono text-xs"
                                    >{ip.network || "-"}</td
                                >
                                <td class="italic opacity-60 text-xs"
                                    >{ip.comment || ""}</td
                                >
                                <td>
                                    <button
                                        class="btn btn-ghost btn-xs btn-square text-error"
                                        onclick={() => handleDelete(ip.address)}
                                        title="Eliminar"
                                    >
                                        <svg
                                            xmlns="http://www.w3.org/2000/svg"
                                            viewBox="0 0 20 20"
                                            fill="currentColor"
                                            class="w-4 h-4"
                                        >
                                            <path
                                                fill-rule="evenodd"
                                                d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.807a2.75 2.75 0 002.742-2.53l.841-10.52.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4zM8.58 7.72a.75.75 0 00-1.5.06l.3 7.5a.75.75 0 101.5-.06l-.3-7.5zm4.34.06a.75.75 0 10-1.5-.06l-.3 7.5a.75.75 0 101.5.06l.3-7.5z"
                                                clip-rule="evenodd"
                                            />
                                        </svg>
                                    </button>
                                </td>
                            </tr>
                        {:else}
                            <tr>
                                <td
                                    colspan="5"
                                    class="text-center py-8 text-base-content/50"
                                >
                                    No se encontraron direcciones IP
                                    configuradas.
                                </td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>
        {/if}
    </div>
</div>

<AddIpModal
    bind:show={showAddModal}
    {routerHost}
    {interfaces}
    onsuccess={fetchData}
/>

<script lang="ts">
    import { onMount } from "svelte";
    import { getRouterFullDetails, deleteSimpleQueue } from "$lib/api";
    import type { SimpleQueue } from "$lib/types/queue";
    import AddQueueModal from "./AddQueueModal.svelte";

    let { routerHost } = $props<{ routerHost: string }>();

    let queues = $state<SimpleQueue[]>([]);
    let loading = $state(true);
    let errorMsg = $state<string | null>(null);

    let showAddModal = $state(false);

    onMount(() => {
        fetchQueues();
    });

    async function fetchQueues() {
        loading = true;
        errorMsg = null;
        try {
            const data = await getRouterFullDetails(routerHost);
            queues = data.simple_queues || [];
        } catch (e: any) {
            errorMsg =
                e.response?.data?.detail ||
                e.message ||
                "Error al cargar colas.";
        } finally {
            loading = false;
        }
    }

    async function handleDelete(queue: SimpleQueue) {
        if (
            !confirm(
                `¿Estás seguro de que quieres eliminar la cola "${queue.name}"?`,
            )
        )
            return;

        const id = queue[".id"] || (queue as any).id;
        try {
            await deleteSimpleQueue(routerHost, id);
            await fetchQueues();
        } catch (e: any) {
            alert(`Error: ${e.response?.data?.detail || e.message}`);
        }
    }

    function openAddModal() {
        showAddModal = true;
    }
</script>

<div class="space-y-6">
    <div class="glass-card-flat p-6 rounded-2xl">
        <div
            class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6"
        >
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
                        d="M3.75 6A2.25 2.25 0 0 1 6 3.75h2.25A2.25 2.25 0 0 1 10.5 6v2.25a2.25 2.25 0 0 1-2.25 2.25H6a2.25 2.25 0 0 1-2.25-2.25V6ZM3.75 15.75A2.25 2.25 0 0 1 6 13.5h2.25a2.25 2.25 0 0 1 2.25 2.25V18a2.25 2.25 0 0 1-2.25 2.25H6A2.25 2.25 0 0 1 3.75 18v-2.25ZM13.5 6a2.25 2.25 0 0 1 2.25-2.25H18A2.25 2.25 0 0 1 20.25 6v2.25A2.25 2.25 0 0 1 18 10.5h-2.25a2.25 2.25 0 0 1-2.25-2.25V6ZM13.5 15.75a2.25 2.25 0 0 1 2.25-2.25H18a2.25 2.25 0 0 1 2.25 2.25V18A2.25 2.25 0 0 1 18 20.25h-2.25A2.25 2.25 0 0 1 13.5 18v-2.25Z"
                    />
                </svg>
                Simple Queues
            </h2>

            <button class="btn btn-sm btn-primary" onclick={openAddModal}>
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
                Añadir Cola
            </button>
        </div>

        {#if loading}
            <div class="flex justify-center p-8">
                <span class="loading loading-spinner text-primary"></span>
            </div>
        {:else if errorMsg}
            <div class="alert alert-error mb-4">
                <span>{errorMsg}</span>
                <button class="btn btn-sm" onclick={fetchQueues}
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
                            <th>Nombre</th>
                            <th>Target</th>
                            <th>Límite Máx. (TX/RX)</th>
                            <th>Padre / Comentario</th>
                            <th class="w-1">Acciones</th>
                        </tr>
                    </thead>
                    <tbody>
                        {#each queues as queue}
                            <tr
                                class="hover focus:outline-none focus:bg-base-200"
                            >
                                <td class="font-medium">{queue.name}</td>
                                <td class="opacity-70 font-mono text-sm"
                                    >{queue.target || "N/A"}</td
                                >
                                <td class="font-mono text-sm">
                                    <span class="badge badge-sm badge-ghost"
                                        >{queue["max-limit"] ||
                                            "Sin Límite"}</span
                                    >
                                </td>
                                <td class="opacity-70 text-xs shadow-sm">
                                    {#if queue.parent && queue.parent !== "none"}
                                        <div class="mb-1">
                                            <span class="font-bold opacity-70"
                                                >Padre:</span
                                            >
                                            {queue.parent}
                                        </div>
                                    {/if}
                                    {#if queue.comment}
                                        <div
                                            class="italic text-base-content/60"
                                        >
                                            "{queue.comment}"
                                        </div>
                                    {/if}
                                </td>
                                <td>
                                    <button
                                        class="btn btn-ghost btn-xs btn-square text-error"
                                        onclick={() => handleDelete(queue)}
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
                                    No se encontraron colas configuradas.
                                </td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>
        {/if}
    </div>
</div>

<AddQueueModal bind:show={showAddModal} {routerHost} onsuccess={fetchQueues} />

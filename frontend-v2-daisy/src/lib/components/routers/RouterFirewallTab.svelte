<script lang="ts">
    import { onMount } from "svelte";
    import { getRouterFullDetails, deleteNatRule } from "$lib/api";
    import AddNatModal from "./AddNatModal.svelte";

    let { routerHost } = $props<{ routerHost: string }>();

    let loading = $state(true);
    let errorMsg = $state<string | null>(null);

    let natRules = $state<any[]>([]);
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
            natRules = data.nat_rules || [];
            interfaces = data.interfaces || [];
        } catch (e: any) {
            errorMsg =
                e.response?.data?.detail ||
                e.message ||
                "Error al cargar datos de firewall";
        } finally {
            loading = false;
        }
    }

    async function handleDelete(comment: string) {
        if (!comment) {
            alert(
                "No se puede eliminar una regla sin comentario identificador.",
            );
            return;
        }
        if (
            !confirm(
                `¿Estás seguro de que quieres eliminar la regla NAT con comentario "${comment}"?`,
            )
        )
            return;

        try {
            await deleteNatRule(routerHost, comment);
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
                        d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z"
                    />
                </svg>
                Reglas NAT (Firewall)
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
                Adicionar Masquerade
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
                            <th>Chain</th>
                            <th>Action</th>
                            <th>Out Interface</th>
                            <th>Src Address</th>
                            <th>Comentario</th>
                            <th class="w-1">Acciones</th>
                        </tr>
                    </thead>
                    <tbody>
                        {#each natRules as rule}
                            <tr
                                class="hover focus:outline-none focus:bg-base-200"
                            >
                                <td
                                    ><span class="badge badge-sm"
                                        >{rule.chain}</span
                                    ></td
                                >
                                <td class="font-bold">{rule.action}</td>
                                <td>{rule["out-interface"] || "any"}</td>
                                <td class="font-mono text-xs"
                                    >{rule["src-address"] || "-"}</td
                                >
                                <td class="italic opacity-60 text-xs"
                                    >{rule.comment || ""}</td
                                >
                                <td>
                                    {#if rule.comment}
                                        <button
                                            class="btn btn-ghost btn-xs btn-square text-error"
                                            onclick={() =>
                                                handleDelete(rule.comment)}
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
                                    {:else}
                                        <span class="opacity-20">-</span>
                                    {/if}
                                </td>
                            </tr>
                        {:else}
                            <tr>
                                <td
                                    colspan="6"
                                    class="text-center py-8 text-base-content/50"
                                >
                                    No se encontraron reglas NAT configuradas.
                                </td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>
        {/if}
    </div>
</div>

<AddNatModal
    bind:show={showAddModal}
    {routerHost}
    {interfaces}
    onsuccess={fetchData}
/>

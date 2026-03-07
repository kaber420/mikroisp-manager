<script lang="ts">
    import { onMount } from "svelte";
    import {
        getRouterFullDetails,
        updateInterfaceState,
        deleteInterface,
    } from "$lib/api";
    import type { InterfaceData } from "$lib/types/router";
    import VlanModal from "./VlanModal.svelte";
    import BridgeModal from "./BridgeModal.svelte";

    let { routerHost } = $props<{ routerHost: string }>();

    let loading = $state(true);
    let errorMsg = $state<string | null>(null);

    // Data from full-details
    let interfacesList = $state<InterfaceData[]>([]);
    let ipAddresses = $state<any[]>([]);
    let bridgePorts = $state<any[]>([]);

    // Filters
    let currentFilter = $state<"general" | "ppp" | "all">("general");
    const FILTER_TYPES = {
        general: ["ether", "bridge", "vlan", "wlan", "bonding", "loopback"],
        ppp: [
            "pppoe-out",
            "pptp-out",
            "l2tp-out",
            "ovpn-out",
            "sstp-out",
            "ipip",
            "gre",
            "eoip",
            "pppoe-in",
            "pptp-in",
            "l2tp-in",
        ],
    };

    // Modal state
    let showVlanModal = $state(false);
    let showBridgeModal = $state(false);
    let editingVlan = $state<InterfaceData | null>(null);
    let editingBridge = $state<InterfaceData | null>(null);

    // Computed filtered interfaces
    let filteredInterfaces = $derived(() => {
        let filtered = interfacesList;
        if (currentFilter === "general") {
            filtered = interfacesList.filter((i) =>
                FILTER_TYPES.general.includes(i.type),
            );
        } else if (currentFilter === "ppp") {
            filtered = interfacesList.filter(
                (i) => FILTER_TYPES.ppp.includes(i.type) && i.name !== "none",
            );
        }

        // Sort by type then name
        return filtered.sort((a, b) => {
            if (a.type !== b.type) return a.type.localeCompare(b.type);
            return a.name.localeCompare(b.name);
        });
    });

    onMount(() => {
        fetchInterfaces();
    });

    async function fetchInterfaces() {
        loading = true;
        errorMsg = null;
        try {
            const data = await getRouterFullDetails(routerHost);
            interfacesList = data.interfaces || [];
            ipAddresses = data.ip_addresses || [];
            bridgePorts = data.bridge_ports || [];
        } catch (e: any) {
            errorMsg =
                e.response?.data?.detail ||
                e.message ||
                "Error al cargar interfaces";
        } finally {
            loading = false;
        }
    }

    function fmtBytes(bytes: number | null | undefined): string {
        if (bytes == null || bytes === 0) return "0 B";
        const units = ["B", "KB", "MB", "GB", "TB"];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return (bytes / Math.pow(1024, i)).toFixed(1) + " " + units[i];
    }

    function getIpForInterface(ifaceName: string): string {
        const ip = ipAddresses.find((i) => i.interface === ifaceName);
        return ip ? ip.address : "(Dinámica)";
    }

    // --- Actions ---

    async function toggleInterfaceState(iface: InterfaceData) {
        if (
            !confirm(
                `¿Estás seguro de que quieres ${iface.disabled === "true" || iface.disabled === true ? "HABILITAR" : "DESHABILITAR"} la interfaz ${iface.name}?`,
            )
        )
            return;

        const isCurrentlyDisabled =
            iface.disabled === "true" || iface.disabled === true;
        const newDisabledState = !isCurrentlyDisabled;
        const id = iface[".id"] || iface.id;

        try {
            await updateInterfaceState(routerHost, id!, newDisabledState);
            await fetchInterfaces(); // Refresh
        } catch (e: any) {
            alert(`Error: ${e.response?.data?.detail || e.message}`);
        }
    }

    async function handleDelete(iface: InterfaceData) {
        if (
            !confirm(
                `¿Estás seguro de que quieres ELIMINAR PERMANENTEMENTE la interfaz "${iface.name}"?`,
            )
        )
            return;

        const id = iface[".id"] || iface.id;
        try {
            await deleteInterface(routerHost, id!, iface.type);
            await fetchInterfaces(); // Refresh
        } catch (e: any) {
            alert(`Error: ${e.response?.data?.detail || e.message}`);
        }
    }

    function openEditModal(iface: InterfaceData) {
        if (iface.type === "vlan") {
            editingVlan = iface;
            showVlanModal = true;
        } else if (iface.type === "bridge") {
            editingBridge = iface;
            showBridgeModal = true;
        }
    }

    function openCreateVlan() {
        editingVlan = null;
        showVlanModal = true;
    }

    function openCreateBridge() {
        editingBridge = null;
        showBridgeModal = true;
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
                        d="M12 21v-8.25M15.75 21v-8.25M8.25 21v-8.25M3 9l9-6 9 6m-1.5 12V10.332A48.315 48.315 0 0 0 12 9.75c-2.551 0-5.056.2-7.5.582V21M3 21h18M12 6.75h.008v.008H12V6.75Z"
                    />
                </svg>
                Network Interfaces
            </h2>

            <div class="flex flex-wrap items-center gap-2">
                <div class="join">
                    <button
                        class="btn btn-sm join-item {currentFilter === 'general'
                            ? 'btn-active'
                            : ''}"
                        onclick={() => (currentFilter = "general")}
                        >General</button
                    >
                    <button
                        class="btn btn-sm join-item {currentFilter === 'ppp'
                            ? 'btn-active'
                            : ''}"
                        onclick={() => (currentFilter = "ppp")}
                        >Túneles/PPP</button
                    >
                    <button
                        class="btn btn-sm join-item {currentFilter === 'all'
                            ? 'btn-active'
                            : ''}"
                        onclick={() => (currentFilter = "all")}>Todas</button
                    >
                </div>

                <div class="flex gap-2 ml-auto sm:ml-4">
                    <button
                        class="btn btn-sm btn-primary"
                        onclick={openCreateVlan}
                    >
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            viewBox="0 0 20 20"
                            fill="currentColor"
                            class="w-4 h-4"
                            ><path
                                d="M10.75 4.75a.75.75 0 0 0-1.5 0v4.5h-4.5a.75.75 0 0 0 0 1.5h4.5v4.5a.75.75 0 0 0 1.5 0v-4.5h4.5a.75.75 0 0 0 0-1.5h-4.5v-4.5Z"
                            /></svg
                        >
                        Add VLAN
                    </button>
                    <button
                        class="btn btn-sm btn-primary"
                        onclick={openCreateBridge}
                    >
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            viewBox="0 0 20 20"
                            fill="currentColor"
                            class="w-4 h-4"
                            ><path
                                d="M10.75 4.75a.75.75 0 0 0-1.5 0v4.5h-4.5a.75.75 0 0 0 0 1.5h4.5v4.5a.75.75 0 0 0 1.5 0v-4.5h4.5a.75.75 0 0 0 0-1.5h-4.5v-4.5Z"
                            /></svg
                        >
                        Add Bridge
                    </button>
                </div>
            </div>
        </div>

        {#if loading}
            <div class="flex justify-center p-8">
                <span class="loading loading-spinner text-primary"></span>
            </div>
        {:else if errorMsg}
            <div class="alert alert-error mb-4">
                <span>{errorMsg}</span>
                <button class="btn btn-sm" onclick={fetchInterfaces}
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
                            <th class="w-1">Status</th>
                            <th>Name</th>
                            <th>Type</th>
                            <th class="hidden md:table-cell">MAC Address</th>
                            <th class="hidden sm:table-cell">IP Address</th>
                            <th class="text-right">RX</th>
                            <th class="text-right">TX</th>
                            <th class="hidden lg:table-cell">Uptime</th>
                            <th class="w-1">Acciones</th>
                        </tr>
                    </thead>
                    <tbody>
                        {#each filteredInterfaces() as iface}
                            {@const isDisabled =
                                iface.disabled === "true" ||
                                iface.disabled === true}
                            {@const isActuallyRunning =
                                iface.running === "true" ||
                                iface.running === true}
                            {@const isRunning =
                                isActuallyRunning && !isDisabled}
                            {@const canBeDeleted = [
                                "vlan",
                                "bridge",
                                "bonding",
                            ].includes(iface.type)}
                            {@const canBeDisabled = ![
                                "pppoe-out",
                                "pptp-out",
                                "l2tp-out",
                            ].includes(iface.type)}
                            {@const isManaged =
                                iface.comment &&
                                iface.comment.includes("managed by umonitor")}
                            {@const canEdit =
                                iface.type === "bridge" ||
                                (isManaged && iface.type === "vlan")}

                            <tr
                                class="hover focus:outline-none focus:bg-base-200 {isDisabled
                                    ? 'opacity-50'
                                    : ''}"
                            >
                                <td class="text-center">
                                    <div
                                        class="w-3 h-3 rounded-full mx-auto {isRunning
                                            ? 'bg-success'
                                            : 'bg-base-content/30'}"
                                        title={isDisabled
                                            ? "Disabled"
                                            : isActuallyRunning
                                              ? "Up"
                                              : "Down"}
                                    ></div>
                                </td>
                                <td class="font-medium whitespace-nowrap"
                                    >{iface.name}</td
                                >
                                <td
                                    ><span class="badge badge-sm badge-ghost"
                                        >{iface.type}</span
                                    ></td
                                >
                                <td
                                    class="hidden md:table-cell text-xs opacity-70 font-mono"
                                    >{iface["mac-address"] || "N/A"}</td
                                >
                                <td
                                    class="hidden sm:table-cell text-xs opacity-70"
                                    >{getIpForInterface(iface.name)}</td
                                >
                                <td
                                    class="text-right text-xs font-mono whitespace-nowrap"
                                    >{fmtBytes(iface["rx-byte"])}</td
                                >
                                <td
                                    class="text-right text-xs font-mono whitespace-nowrap"
                                    >{fmtBytes(iface["tx-byte"])}</td
                                >
                                <td
                                    class="hidden lg:table-cell text-xs opacity-70 whitespace-nowrap"
                                    >{iface.uptime || "N/A"}</td
                                >
                                <td>
                                    <div class="flex items-center gap-1">
                                        {#if canEdit}
                                            <button
                                                class="btn btn-ghost btn-xs btn-square text-primary"
                                                onclick={() =>
                                                    openEditModal(iface)}
                                                title="Editar"
                                            >
                                                <svg
                                                    xmlns="http://www.w3.org/2000/svg"
                                                    viewBox="0 0 20 20"
                                                    fill="currentColor"
                                                    class="w-4 h-4"
                                                    ><path
                                                        d="M5.433 13.917l1.262-3.155A4 4 0 017.58 9.42l6.92-6.918a2.121 2.121 0 013 3l-6.92 6.918c-.383.383-.84.685-1.343.886l-3.154 1.262a.5.5 0 01-.65-.65z"
                                                    /><path
                                                        d="M3.5 5.75c0-.69.56-1.25 1.25-1.25H10A.75.75 0 0010 3H4.75A2.75 2.75 0 002 5.75v9.5A2.75 2.75 0 004.75 18h9.5A2.75 2.75 0 0017 15.25V10a.75.75 0 00-1.5 0v5.25c0 .69-.56 1.25-1.25 1.25h-9.5c-.69 0-1.25-.56-1.25-1.25v-9.5z"
                                                    /></svg
                                                >
                                            </button>
                                        {/if}

                                        {#if canBeDisabled}
                                            {#if isDisabled}
                                                <button
                                                    class="btn btn-ghost btn-xs btn-square text-success"
                                                    onclick={() =>
                                                        toggleInterfaceState(
                                                            iface,
                                                        )}
                                                    title="Habilitar"
                                                >
                                                    <svg
                                                        xmlns="http://www.w3.org/2000/svg"
                                                        viewBox="0 0 20 20"
                                                        fill="currentColor"
                                                        class="w-4 h-4"
                                                        ><path
                                                            fill-rule="evenodd"
                                                            d="M2 10a8 8 0 1116 0 8 8 0 01-16 0zm6.39-2.908a.75.75 0 01.766.027l3.5 2.25a.75.75 0 010 1.262l-3.5 2.25A.75.75 0 018 12.25v-4.5a.75.75 0 01.39-.658z"
                                                            clip-rule="evenodd"
                                                        /></svg
                                                    >
                                                </button>
                                            {:else}
                                                <button
                                                    class="btn btn-ghost btn-xs btn-square text-warning"
                                                    onclick={() =>
                                                        toggleInterfaceState(
                                                            iface,
                                                        )}
                                                    title="Deshabilitar"
                                                >
                                                    <svg
                                                        xmlns="http://www.w3.org/2000/svg"
                                                        viewBox="0 0 20 20"
                                                        fill="currentColor"
                                                        class="w-4 h-4"
                                                        ><path
                                                            fill-rule="evenodd"
                                                            d="M2 10a8 8 0 1116 0 8 8 0 01-16 0zm5-2.25A.75.75 0 017.75 7h4.5a.75.75 0 01.75.75v4.5a.75.75 0 01-.75.75h-4.5a.75.75 0 01-.75-.75v-4.5z"
                                                            clip-rule="evenodd"
                                                        /></svg
                                                    >
                                                </button>
                                            {/if}
                                        {/if}

                                        {#if canBeDeleted}
                                            <button
                                                class="btn btn-ghost btn-xs btn-square text-error"
                                                onclick={() =>
                                                    handleDelete(iface)}
                                                title="Eliminar"
                                            >
                                                <svg
                                                    xmlns="http://www.w3.org/2000/svg"
                                                    viewBox="0 0 20 20"
                                                    fill="currentColor"
                                                    class="w-4 h-4"
                                                    ><path
                                                        fill-rule="evenodd"
                                                        d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.807a2.75 2.75 0 002.742-2.53l.841-10.52.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4zM8.58 7.72a.75.75 0 00-1.5.06l.3 7.5a.75.75 0 101.5-.06l-.3-7.5zm4.34.06a.75.75 0 10-1.5-.06l-.3 7.5a.75.75 0 101.5.06l.3-7.5z"
                                                        clip-rule="evenodd"
                                                    /></svg
                                                >
                                            </button>
                                        {/if}
                                    </div>
                                </td>
                            </tr>
                        {:else}
                            <tr>
                                <td
                                    colspan="9"
                                    class="text-center py-8 text-base-content/50"
                                >
                                    No se encontraron interfaces congruentes
                                    para este filtro.
                                </td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>
        {/if}
    </div>
</div>

<VlanModal
    bind:show={showVlanModal}
    vlan={editingVlan}
    {routerHost}
    interfaces={interfacesList}
    onsuccess={fetchInterfaces}
/>

<BridgeModal
    bind:show={showBridgeModal}
    bridge={editingBridge}
    {routerHost}
    interfaces={interfacesList}
    {bridgePorts}
    onsuccess={fetchInterfaces}
/>

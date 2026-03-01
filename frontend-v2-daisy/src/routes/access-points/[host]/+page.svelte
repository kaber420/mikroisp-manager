<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import { page } from "$app/stores";
    import type { AP } from "$lib/types/ap";
    import { syncAPCPEs } from "$lib/api";

    // ── Props & Estado Base ────────────────────────────────────────────────
    let { data } = $props<{ data: { ap: AP } }>();
    let ap = $derived(data.ap);

    // ── Websocket State ───────────────────────────────────────────────────
    let ws: WebSocket | null = null;
    let wsStatus = $state<
        "connecting" | "connected" | "error" | "disconnected"
    >("connecting");
    let wsErrorMsg = $state<string | null>(null);
    let liveData = $state<any>(null);

    // ── Acciones estado ───────────────────────────────────────────────────
    let syncLoading = $state(false);
    let syncResult = $state<{ status: string; message: string } | null>(null);

    // ── Ciclo de vida WebSocket ───────────────────────────────────────────
    onMount(() => {
        connectWebSocket();
    });

    onDestroy(() => {
        if (ws) {
            ws.close();
            ws = null;
        }
    });

    function connectWebSocket() {
        if (!ap) return;

        wsStatus = "connecting";
        wsErrorMsg = null;

        // Protocol logic (ws/wss)
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsUrl = `${protocol}//${window.location.host}/api/ws/aps/${ap.host}/resources`;

        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            wsStatus = "connected";
            wsErrorMsg = null;
        };

        ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);

                if (message.type === "resources") {
                    liveData = message.data;
                    wsStatus = "connected";
                } else if (message.type === "error") {
                    wsStatus = "error";
                    wsErrorMsg = message.data.message;
                } else if (message.type === "loading") {
                    // Esperando primer set de datos
                }
            } catch (err) {
                console.error("Error parseando WS message:", err);
            }
        };

        ws.onerror = (err) => {
            wsStatus = "error";
            wsErrorMsg = "Error en la conexión WebSocket";
            console.error("WS Error:", err);
        };

        ws.onclose = (event) => {
            if (wsStatus !== "error") {
                wsStatus = "disconnected";
            }
        };
    }

    // ── Acciones de Red ───────────────────────────────────────────────────
    async function handleSyncCPEs() {
        syncLoading = true;
        syncResult = null;
        try {
            const result = await syncAPCPEs(ap.host);
            syncResult = {
                status: "success",
                message: `Sincronización exitosa. ${result.updated_cpes || 0} CPEs actualizados.`,
            };
        } catch (e: any) {
            syncResult = {
                status: "error",
                message:
                    e?.response?.data?.detail ?? "Error sincronizando CPEs",
            };
        } finally {
            syncLoading = false;
            // Limpiar mensaje tras 5s
            setTimeout(() => {
                syncResult = null;
            }, 5000);
        }
    }

    // ── Format helpers ────────────────────────────────────────────────────
    function formatBytes(bytes: number | null | undefined): string {
        if (bytes == null) return "0 B";
        const k = 1024;
        const sizes = ["B", "KB", "MB", "GB", "TB"];
        if (bytes === 0) return "0 B";
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
    }
</script>

<svelte:head>
    <title>{ap.hostname || ap.host} — AP Details</title>
</svelte:head>

<div class="flex flex-col gap-6 max-w-7xl mx-auto w-full">
    <!-- Header Block -->
    <div class="card bg-base-100 shadow-sm border border-base-200">
        <div class="card-body p-6">
            <div class="text-sm breadcrumbs opacity-60 mb-2">
                <ul>
                    <li><a href="/access-points">Access Points</a></li>
                    <li>{ap.host}</li>
                </ul>
            </div>
            <div
                class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4"
            >
                <div class="flex flex-col gap-1">
                    <div class="flex items-center gap-3">
                        <h1 class="text-3xl font-black m-0">
                            {ap.hostname || ap.host}
                        </h1>
                        <span
                            class="badge {ap.last_status === 'online'
                                ? 'badge-success'
                                : 'badge-error'} badge-sm font-bold shadow-sm"
                        >
                            {ap.last_status || "desconocido"}
                        </span>
                        {#if ap.is_provisioned}
                            <span
                                class="badge badge-info badge-sm gap-1 font-bold shadow-sm"
                            >
                                <svg
                                    xmlns="http://www.w3.org/2000/svg"
                                    viewBox="0 0 20 20"
                                    fill="currentColor"
                                    class="w-3 h-3"
                                >
                                    <path
                                        fill-rule="evenodd"
                                        d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z"
                                        clip-rule="evenodd"
                                    />
                                </svg>
                                Seguro
                            </span>
                        {/if}
                    </div>
                    <p class="text-sm opacity-60 font-mono m-0">
                        {ap.host} • {ap.vendor
                            ? ap.vendor.toUpperCase()
                            : "VENDOR DESCONOCIDO"} • {liveData?.model ||
                            ap.model ||
                            "Modelo Descocido"}
                    </p>
                </div>

                <div class="flex gap-2">
                    <button
                        class="btn btn-primary"
                        onclick={handleSyncCPEs}
                        disabled={syncLoading}
                    >
                        {#if syncLoading}
                            <span class="loading loading-spinner loading-sm"
                            ></span>
                        {:else}
                            <svg
                                xmlns="http://www.w3.org/2000/svg"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke-width="2"
                                stroke="currentColor"
                                class="w-5 h-5"
                            >
                                <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99"
                                />
                            </svg>
                        {/if}
                        Sincronizar IPs CPEs
                    </button>
                </div>
            </div>

            <!-- Mensajes de Alerta -->
            {#if syncResult || wsStatus === "error"}
                <div class="flex flex-col gap-2 mt-4">
                    {#if syncResult}
                        <div
                            class="alert {syncResult.status === 'success'
                                ? 'alert-success'
                                : 'alert-error'} shadow-sm py-2"
                        >
                            <span>{syncResult.message}</span>
                        </div>
                    {/if}
                    {#if wsStatus === "error"}
                        <div class="alert alert-warning shadow-sm py-2 px-4">
                            <svg
                                xmlns="http://www.w3.org/2000/svg"
                                class="stroke-current shrink-0 h-5 w-5"
                                fill="none"
                                viewBox="0 0 24 24"
                                ><path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    stroke-width="2"
                                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                                /></svg
                            >
                            <span class="text-sm font-medium"
                                >{wsErrorMsg || "Sin conexión WebSocket."}</span
                            >
                            <button
                                class="btn btn-xs btn-outline ml-auto"
                                onclick={connectWebSocket}
                                >Vincular de Nuevo</button
                            >
                        </div>
                    {/if}
                </div>
            {/if}
        </div>
    </div>

    <!-- KPIs Rápidos en Grid (Live Metrics) -->
    <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        <!-- SSID -->
        <div class="card bg-base-100 shadow-sm border border-base-200">
            <div class="card-body p-4 text-center items-center justify-center">
                <span
                    class="text-[10px] uppercase font-bold opacity-50 tracking-wider"
                    >Red (SSID)</span
                >
                <span class="text-xl font-black text-base-content mt-1"
                    >{liveData?.essid || "--"}</span
                >
            </div>
        </div>
        <!-- Clientes -->
        <div
            class="card bg-base-100 shadow-sm border border-base-200 align-center"
        >
            <div class="card-body p-4 text-center items-center justify-center">
                <span
                    class="text-[10px] uppercase font-bold opacity-50 tracking-wider"
                    >CPEs Conectados</span
                >
                <span class="text-3xl font-black text-primary mt-1"
                    >{liveData?.client_count ?? "--"}</span
                >
            </div>
        </div>
        <!-- Frecuencia -->
        <div class="card bg-base-100 shadow-sm border border-base-200">
            <div class="card-body p-4 text-center items-center justify-center">
                <span
                    class="text-[10px] uppercase font-bold opacity-50 tracking-wider"
                    >Canal / Freq</span
                >
                <span class="text-xl font-black mt-1 text-secondary"
                    >{liveData?.frequency || "--"}</span
                >
                <span class="text-[10px] opacity-50 font-bold"
                    >{liveData?.chanbw || "-"} MHz HW</span
                >
            </div>
        </div>
        <!-- Ruido -->
        <div
            class="card bg-base-100 shadow-sm border border-base-200 overflow-hidden relative"
        >
            <div class="card-body p-4 text-center items-center justify-center">
                <span
                    class="text-[10px] uppercase font-bold opacity-50 tracking-wider"
                    >Ruido Fondo</span
                >
                <span
                    class="text-2xl font-black mt-1 {liveData?.noise_floor > -80
                        ? 'text-warning'
                        : 'text-success'}">{liveData?.noise_floor || "--"}</span
                >
                <span class="text-[10px] opacity-50 font-bold">dBm</span>
            </div>
            {#if liveData?.noise_floor > -80}
                <div
                    class="absolute bottom-0 left-0 w-full h-1 bg-warning"
                ></div>
            {/if}
        </div>
        <!-- CPU Load (Si existe) -->
        <div
            class="card bg-base-100 shadow-sm border border-base-200 lg:col-span-2"
        >
            <div
                class="card-body p-4 flex flex-row items-center justify-between"
            >
                <div class="flex-1 px-2">
                    <div
                        class="flex justify-between text-xs font-bold mb-1 opacity-70"
                    >
                        <span>CPU</span>
                        <span>{liveData?.extra?.cpu_load ?? "--"}%</span>
                    </div>
                    <progress
                        class="progress w-full {liveData?.extra?.cpu_load > 85
                            ? 'progress-error'
                            : 'progress-primary'}"
                        value={liveData?.extra?.cpu_load || 0}
                        max="100"
                    ></progress>
                </div>
                <div class="flex-1 px-2 border-l border-base-200 ml-2">
                    <div
                        class="flex justify-between text-xs font-bold mb-1 opacity-70"
                    >
                        <span>RAM</span>
                        <span>{liveData?.extra?.memory_usage ?? "--"}%</span>
                    </div>
                    <progress
                        class="progress w-full {liveData?.extra?.memory_usage >
                        85
                            ? 'progress-error'
                            : 'progress-info'}"
                        value={liveData?.extra?.memory_usage || 0}
                        max="100"
                    ></progress>
                </div>
            </div>
        </div>
    </div>

    <!-- Tabla de Clientes en Vivo -->
    <div class="card bg-base-100 shadow-sm border border-base-200 flex-1">
        <div class="card-body p-0 flex flex-col h-full">
            <div
                class="p-4 border-b border-base-200 flex justify-between items-center bg-base-200/30"
            >
                <h2 class="card-title text-base m-0 flex items-center gap-2">
                    <svg
                        xmlns="http://www.w3.org/2000/svg"
                        viewBox="0 0 24 24"
                        fill="currentColor"
                        class="w-5 h-5 text-primary"
                    >
                        <path
                            fill-rule="evenodd"
                            d="M1.5 4.5a3 3 0 013-3h1.372c.86 0 1.61.586 1.819 1.42l1.105 4.423a1.875 1.875 0 01-.694 1.955l-1.293.97c-.135.101-.164.249-.126.352a11.285 11.285 0 006.697 6.697c.103.038.25.009.352-.126l.97-1.293a1.875 1.875 0 011.955-.694l4.423 1.105c.834.209 1.42.959 1.42 1.82V19.5a3 3 0 01-3 3h-2.25C8.552 22.5 1.5 15.448 1.5 6.75V4.5z"
                            clip-rule="evenodd"
                        />
                    </svg>
                    Estaciones (CPEs)
                </h2>
                {#if wsStatus === "connecting" || (wsStatus === "connected" && !liveData)}
                    <span class="loading loading-spinner w-4 h-4 text-primary"
                    ></span>
                {:else if wsStatus === "connected"}
                    <span
                        class="flex items-center gap-2 text-xs font-bold text-success opacity-80"
                    >
                        <span
                            class="w-2 h-2 rounded-full bg-success animate-pulse"
                        ></span>
                        LIVE
                    </span>
                {/if}
            </div>

            <div class="overflow-x-auto w-full max-h-[500px]">
                <table class="table table-zebra table-pin-rows table-sm w-full">
                    <thead>
                        <tr class="bg-base-200 border-none">
                            <th>#</th>
                            <th>CPE / Hostname</th>
                            <th>MAC / IP</th>
                            <th class="text-center">Señal dBm</th>
                            <th class="text-center">Modulación TX/RX</th>
                            <th class="text-right">Tráfico (Mbps)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {#if liveData?.clients?.length > 0}
                            {#each liveData.clients as client, index}
                                <tr class="hover border-base-200">
                                    <td class="text-xs opacity-50 font-bold"
                                        >{index + 1}</td
                                    >
                                    <td>
                                        <div class="font-bold text-sm">
                                            {client.cpe_hostname ||
                                                "Desconocido"}
                                        </div>
                                    </td>
                                    <td>
                                        <div class="font-mono text-xs">
                                            {client.cpe_mac}
                                        </div>
                                        <div
                                            class="font-mono text-xs opacity-60 text-primary font-bold"
                                        >
                                            {client.ip_address || "Sin IP"}
                                        </div>
                                    </td>
                                    <td class="text-center">
                                        <div
                                            class="badge badge-sm font-bold border-none text-white shadow-sm {client.signal >
                                            -65
                                                ? 'bg-success'
                                                : client.signal > -75
                                                  ? 'bg-warning'
                                                  : 'bg-error'}"
                                        >
                                            {client.signal}
                                        </div>
                                    </td>
                                    <td class="text-center">
                                        <div
                                            class="font-mono text-[11px] opacity-80 bg-base-200 rounded px-2 py-1 inline-block"
                                        >
                                            <span class="text-info font-bold"
                                                >TX:</span
                                            >
                                            {client.tx_rate || "--"} <br />
                                            <span class="text-primary font-bold"
                                                >RX:</span
                                            >
                                            {client.rx_rate || "--"}
                                        </div>
                                    </td>
                                    <td class="text-right">
                                        <div
                                            class="font-mono text-xs text-info font-bold inline-flex items-center gap-1 w-20 justify-end"
                                        >
                                            ↓ {(
                                                client.throughput_rx_kbps / 1024
                                            ).toFixed(1)}
                                        </div>
                                        <br />
                                        <div
                                            class="font-mono text-xs text-primary font-bold inline-flex items-center gap-1 w-20 justify-end mt-1"
                                        >
                                            ↑ {(
                                                client.throughput_tx_kbps / 1024
                                            ).toFixed(1)}
                                        </div>
                                    </td>
                                </tr>
                            {/each}
                        {:else if liveData}
                            <tr>
                                <td
                                    colspan="6"
                                    class="text-center py-16 opacity-50"
                                >
                                    <div class="text-4xl mb-2">📡</div>
                                    <h3 class="font-bold">Sin clientes</h3>
                                    <p class="text-sm">
                                        No hay estaciones conectadas
                                        actualmente.
                                    </p>
                                </td>
                            </tr>
                        {:else}
                            <tr>
                                <td colspan="6" class="text-center py-16">
                                    <span
                                        class="loading loading-spinner loading-lg text-primary"
                                    ></span>
                                    <p
                                        class="mt-4 text-sm font-bold opacity-50"
                                    >
                                        Obteniendo telemetría en vivo...
                                    </p>
                                </td>
                            </tr>
                        {/if}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>

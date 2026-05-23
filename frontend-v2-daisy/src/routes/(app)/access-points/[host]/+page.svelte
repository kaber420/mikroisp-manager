<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import { page } from "$app/stores";
    import type { AP } from "$lib/types/ap";
    import { syncAPCPEs, getAPHistory, provisionAP, repairAP } from "$lib/api";
    import ProvisionModal from "$lib/components/ProvisionModal.svelte";

    // ── Props & Estado Base ────────────────────────────────────────────────
    let { data } = $props<{ data: { ap: AP } }>();
    let ap = $derived(data.ap);

    // ── Websocket / Live Mode State ─────────────────────────────────────────
    let isLiveMode = $state(false);
    let ws: WebSocket | null = null;
    let wsStatus = $state<
        "connecting" | "connected" | "error" | "disconnected"
    >("disconnected");
    let wsErrorMsg = $state<string | null>(null);

    // ── Datos de la Interfaz ───────────────────────────────────────────────
    let displayData = $state<any>(null); // Datos que se muestran (Históricos o Live)
    let historicalCpes = $state<any[]>([]); // CPEs cargados desde la DB
    let dataLoading = $state(true);

    // ── Acciones estado ───────────────────────────────────────────────────
    let syncLoading = $state(false);
    let syncResult = $state<{ status: string; message: string } | null>(null);

    // ── Aprovisionamiento ──────────────────────────────────────────────────
    let showProvisionModal = $state(false);
    let isProvisioning = $state(false);
    let provisionResult = $state<{status: string, message: string} | null>(null);

    async function handleProvision(data: { newApiUser: string; newApiPassword?: string; method: string }) {
        isProvisioning = true;
        provisionResult = null;
        try {
            const res = await provisionAP(ap.host, {
                new_api_user: data.newApiUser,
                new_api_password: data.newApiPassword || "",
                method: data.method
            });
            provisionResult = { status: "success", message: res.message || "AP aprovisionado exitosamente." };
            ap.is_provisioned = true;
            showProvisionModal = false;
        } catch (e: any) {
            provisionResult = { status: "error", message: e?.response?.data?.detail ?? "Error al aprovisionar el AP." };
            showProvisionModal = false;
        } finally {
            isProvisioning = false;
            setTimeout(() => { provisionResult = null; }, 6000);
        }
    }

    async function handleUnprovision() {
        if (!confirm("¿Desvincular AP? Perderá el acceso API-SSL hasta que vuelva a aprovisionarse.")) return;
        provisionResult = null;
        try {
            await repairAP(ap.host, "unprovision");
            provisionResult = { status: "success", message: "AP desvinculado correctamente." };
            ap.is_provisioned = false;
        } catch (e: any) {
            provisionResult = { status: "error", message: e?.response?.data?.detail ?? "Error al desvincular el AP." };
        } finally {
            setTimeout(() => { provisionResult = null; }, 6000);
        }
    }

    // ── Historial AP ──────────────────────────────────────────────────────
    let apHistory = $state<any[]>([]);
    let historyLoading = $state(false);
    // Historial en vivo (últimos N puntos del backend Redis/memoria)
    let liveHistory = $state<any[]>([]);

    // ── Ciclo de vida WebSocket ───────────────────────────────────────────
    onMount(() => {
        // Por defecto, cargar datos de la base de datos (histórico)
        loadHistoricalData();
        loadAPHistory();
    });

    onDestroy(() => {
        stopLiveMode();
    });

    async function loadHistoricalData() {
        if (!ap) return;
        dataLoading = true;
        try {
            // Obtener CPEs de la Base de Datos
            const protocol = window.location.protocol;
            const cpesRes = await fetch(
                `${protocol}//${window.location.host}/api/aps/${ap.host}/cpes`,
            );

            if (cpesRes.ok) {
                historicalCpes = await cpesRes.json();
            }

            // Inicializar displayData con los datos del AP base y los CPEs históricos
            displayData = {
                essid: ap.essid,
                frequency: ap.frequency,
                chanbw: ap.chanbw,
                noise_floor: ap.noise_floor,
                client_count: ap.client_count,
                clients: historicalCpes,
                model: ap.model,
                total_tx_bytes: ap.total_tx_bytes,
                total_rx_bytes: ap.total_rx_bytes,
                extra: { cpu_load: null, memory_usage: null },
            };
        } catch (e) {
            console.error("Error loading historical data:", e);
        } finally {
            dataLoading = false;
        }
    }

    // ── Cargar historial de métricas del AP ───────────────────────────────
    async function loadAPHistory() {
        historyLoading = true;
        try {
            const res = await getAPHistory(ap.host, "24h");
            apHistory = res?.history ?? [];
        } catch (e) {
            apHistory = [];
        } finally {
            historyLoading = false;
        }
    }

    function toggleLiveMode() {
        if (isLiveMode) {
            stopLiveMode();
        } else {
            startLiveMode();
        }
    }

    function stopLiveMode() {
        isLiveMode = false;
        if (ws) {
            ws.close();
            ws = null;
        }
        wsStatus = "disconnected";
        liveHistory = [];

        // Volver a mostrar los datos estáticos de la DB
        displayData = {
            essid: ap.essid,
            frequency: ap.frequency,
            chanbw: ap.chanbw,
            noise_floor: ap.noise_floor,
            client_count: historicalCpes.length,
            clients: historicalCpes,
            model: ap.model,
            total_tx_bytes: ap.total_tx_bytes,
            total_rx_bytes: ap.total_rx_bytes,
            extra: { cpu_load: null, memory_usage: null },
        };
    }

    function startLiveMode() {
        if (!ap) return;

        isLiveMode = true;
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
                    // Combinar CPEs en vivo con CPEs históricos
                    const liveCpes = message.data.clients || [];

                    // Actualizar el DOM reactivamente
                    displayData = message.data;
                    // Actualizar historial en vivo
                    if (Array.isArray(message.data?.live_history)) {
                        liveHistory = message.data.live_history;
                    }
                    wsStatus = "connected";
                } else if (message.type === "error") {
                    wsStatus = "error";
                    wsErrorMsg = message.data.message;
                    stopLiveMode();
                }
            } catch (err) {
                console.error("Error parseando WS message:", err);
            }
        };

        ws.onerror = (err) => {
            wsStatus = "error";
            wsErrorMsg = "Error en la conexión WebSocket";
            console.error("WS Error:", err);
            stopLiveMode();
        };

        ws.onclose = (event) => {
            if (wsStatus !== "error") {
                wsStatus = "disconnected";
            }
            if (isLiveMode) {
                // Si se cerró inesperadamente pero el modo sigue "Live", forzamos a apagar
                stopLiveMode();
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
            // Recargar datos históricos si no estamos en Live Mode
            if (!isLiveMode) {
                await loadHistoricalData();
            }
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

    // Genera puntos SVG para sparklines
    function toSparkPoints(vals: (number | null)[], w = 200, h = 40): string {
        const clean = vals.filter((v) => v != null) as number[];
        if (clean.length < 2) return "";
        const min = Math.min(...clean);
        const max = Math.max(...clean);
        const range = max - min || 1;
        return vals
            .map((v, i) => {
                const x = (i / (vals.length - 1)) * w;
                const y = v == null ? h : h - ((v - min) / range) * (h - 4) - 2;
                return `${x.toFixed(1)},${y.toFixed(1)}`;
            })
            .join(" ");
    }

    let clientHistory = $derived(
        apHistory.map((p: any) => p.client_count as number | null),
    );
    let txHistory = $derived(
        apHistory.map((p: any) => p.total_throughput_tx as number | null),
    );
    let rxHistory = $derived(
        apHistory.map((p: any) => p.total_throughput_rx as number | null),
    );

    // ── Arrays para gráficas live ──────────────────────────────────────────
    let liveClientsHistory = $derived(
        liveHistory.map((p: any) => p.clients as number | null),
    );
    let liveTxHistory = $derived(
        liveHistory.map((p: any) => p.tx_kbps as number | null),
    );
    let liveRxHistory = $derived(
        liveHistory.map((p: any) => p.rx_kbps as number | null),
    );

    function fmtKbps(kbps: number | null | undefined): string {
        if (kbps == null) return "--";
        if (kbps < 1000) return `${kbps} KB/s`;
        return `${(kbps / 1024).toFixed(1)} MB/s`;
    }
</script>

<svelte:head>
    <title>{ap.hostname || ap.host} — AP Details</title>
</svelte:head>

<div class="flex flex-col gap-6 max-w-7xl mx-auto w-full">
    <!-- Header Block -->
    <div class="glass-card-flat" style="border-radius:1rem;">
        <div class="p-6 flex flex-col gap-4">
            <div
                class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 relative"
            >
                <!-- ProvisionResult Toast -->
                {#if provisionResult}
                    <div class="toast toast-top toast-center z-[100] absolute top-[-50px]">
                        <div class="alert {provisionResult.status === 'success' ? 'alert-success' : 'alert-error'} shadow-lg py-2">
                            <span class="text-sm font-bold text-white">{provisionResult.message}</span>
                        </div>
                    </div>
                {/if}
                <div class="flex flex-col gap-1">
                    <div class="flex items-center gap-3">
                        <a
                            href="/access-points"
                            class="hover:bg-base-200 p-1 rounded-lg transition-colors -ml-2"
                            title="Volver a Access Points"
                        >
                            <svg
                                xmlns="http://www.w3.org/2000/svg"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke-width="3"
                                stroke="currentColor"
                                class="w-6 h-6"
                                ><path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    d="M15.75 19.5L8.25 12l7.5-7.5"
                                /></svg
                            >
                        </a>
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
                        {#if ap.vendor === 'mikrotik'}
                            {#if ap.is_provisioned}
                                <div class="dropdown dropdown-end">
                                    <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
                                    <div tabindex="0" role="button" class="badge badge-info badge-sm gap-1 font-bold shadow-sm cursor-pointer mb-0">
                                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-3 h-3">
                                            <path fill-rule="evenodd" d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z" clip-rule="evenodd" />
                                        </svg>
                                        Seguro
                                        <svg xmlns="http://www.w3.org/2000/svg" class="w-3 h-3 ml-1 opacity-70" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" /></svg>
                                    </div>
                                    <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
                                    <ul tabindex="0" class="dropdown-content z-[2] menu p-2 shadow bg-base-100 rounded-box w-52 mt-1 border border-base-200">
                                        <li><button class="text-error text-xs font-bold" onclick={handleUnprovision}>Desvincular (Unprovision)</button></li>
                                    </ul>
                                </div>
                            {:else}
                                <button class="btn btn-xs btn-success text-white px-2 h-6 min-h-6" onclick={() => (showProvisionModal = true)}>
                                    Aprovisionar
                                </button>
                            {/if}
                        {/if}
                    </div>
                    <p class="text-sm opacity-60 font-mono m-0 mt-1">
                        {ap.host} • {ap.vendor
                            ? ap.vendor.toUpperCase()
                            : "VENDOR DESCONOCIDO"} • {displayData?.model ||
                            ap.model ||
                            "Modelo Descocido"}
                    </p>
                </div>

                <div class="flex flex-wrap items-center gap-4">
                    <!-- Live Mode Toggle -->
                    <div class="form-control">
                        <label class="label cursor-pointer flex gap-3">
                            <span
                                class="label-text font-bold uppercase text-[10px] tracking-wider opacity-70"
                            >
                                {#if wsStatus === "connecting"}
                                    <span
                                        class="loading loading-spinner loading-xs text-primary mr-1"
                                    ></span> Conectando...
                                {:else if isLiveMode}
                                    <span
                                        class="text-success flex items-center gap-1"
                                        ><span
                                            class="w-2 h-2 rounded-full bg-success animate-pulse"
                                        ></span> Modo En Vivo</span
                                    >
                                {:else}
                                    Modo Histórico
                                {/if}
                            </span>
                            <input
                                type="checkbox"
                                class="toggle toggle-primary toggle-sm"
                                checked={isLiveMode}
                                onchange={toggleLiveMode}
                            />
                        </label>
                    </div>

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
                                >{wsErrorMsg ||
                                    "Error al iniciar el modo en vivo. Se volverá al historial."}</span
                            >
                            <button
                                class="btn btn-xs btn-outline ml-auto"
                                onclick={stopLiveMode}>Aceptar</button
                            >
                        </div>
                    {/if}
                </div>
            {/if}
        </div>
    </div>

    <!-- KPIs Rápidos en Grid -->
    <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4">
        <!-- SSID -->
        <div class="glass-card-flat" style="border-radius:0.875rem;">
            <div
                class="p-4 flex flex-col text-center items-center justify-center h-full"
            >
                <span
                    class="text-[10px] uppercase font-bold opacity-50 tracking-wider"
                    >Red (SSID)</span
                >
                <div
                    class="text-xl font-black text-base-content mt-1 w-full truncate px-2"
                    title={displayData?.essid || "--"}
                >
                    {#if dataLoading && !isLiveMode}
                        <span class="loading loading-dots loading-sm opacity-50"
                        ></span>
                    {:else}
                        {displayData?.essid || "--"}
                    {/if}
                </div>
            </div>
        </div>
        <!-- Clientes -->
        <div class="glass-card-flat" style="border-radius:0.875rem;">
            <div
                class="p-4 flex flex-col text-center items-center justify-center h-full"
            >
                <span
                    class="text-[10px] uppercase font-bold opacity-50 tracking-wider"
                    >CPEs Conectados</span
                >
                <div class="text-3xl font-black text-primary mt-1">
                    {#if dataLoading && !isLiveMode}
                        <span class="loading loading-dots loading-sm opacity-50"
                        ></span>
                    {:else}
                        {displayData?.client_count ?? "--"}
                    {/if}
                </div>
            </div>
        </div>
        <!-- Frecuencia -->
        <div class="glass-card-flat" style="border-radius:0.875rem;">
            <div
                class="p-4 flex flex-col text-center items-center justify-center h-full"
            >
                <span
                    class="text-[10px] uppercase font-bold opacity-50 tracking-wider"
                    >Canal / Freq</span
                >
                <div class="text-xl font-black mt-1 text-secondary">
                    {#if dataLoading && !isLiveMode}
                        <span class="loading loading-dots loading-sm opacity-50"
                        ></span>
                    {:else}
                        {displayData?.frequency || "--"}
                    {/if}
                </div>
                <!-- Solo mostrar el unit label si hay dato -->
                <span class="text-[10px] opacity-50 font-bold"
                    >{displayData?.chanbw
                        ? displayData.chanbw + " MHz HW"
                        : "-"}</span
                >
            </div>
        </div>
        <!-- Ruido -->
        <div
            class="glass-card-flat overflow-hidden relative"
            style="border-radius:0.875rem;"
        >
            <div
                class="p-4 flex flex-col text-center items-center justify-center h-full"
            >
                <span
                    class="text-[10px] uppercase font-bold opacity-50 tracking-wider"
                    >Ruido Fondo</span
                >
                <div
                    class="text-2xl font-black mt-1 {displayData?.noise_floor >
                    -80
                        ? 'text-warning'
                        : 'text-success'}"
                >
                    {#if dataLoading && !isLiveMode}
                        <span class="loading loading-dots loading-sm opacity-50"
                        ></span>
                    {:else}
                        {displayData?.noise_floor || "--"}
                    {/if}
                </div>
                <span class="text-[10px] opacity-50 font-bold">dBm</span>
            </div>
            {#if displayData?.noise_floor > -80}
                <div
                    class="absolute bottom-0 left-0 w-full h-1 bg-warning"
                ></div>
            {/if}
        </div>
        <!-- Tráfico Total -->
        <div
            class="glass-card-flat lg:col-span-2"
            style="border-radius:0.875rem;"
        >
            <div class="p-4 flex flex-row items-center justify-between h-full">
                <div class="flex-1 px-2 text-center">
                    <span
                        class="text-[10px] uppercase font-bold opacity-50 tracking-wider"
                        >Total TX</span
                    >
                    <div class="text-xl font-black mt-1 text-info">
                        {#if dataLoading && !isLiveMode}
                            <span
                                class="loading loading-dots loading-sm opacity-50"
                            ></span>
                        {:else}
                            {displayData?.total_tx_bytes != null
                                ? formatBytes(displayData.total_tx_bytes)
                                : "--"}
                        {/if}
                    </div>
                </div>
                <div
                    class="flex-1 px-2 border-l border-base-200 ml-2 text-center"
                >
                    <span
                        class="text-[10px] uppercase font-bold opacity-50 tracking-wider"
                        >Total RX</span
                    >
                    <div class="text-xl font-black mt-1 text-primary">
                        {#if dataLoading && !isLiveMode}
                            <span
                                class="loading loading-dots loading-sm opacity-50"
                            ></span>
                        {:else}
                            {displayData?.total_rx_bytes != null
                                ? formatBytes(displayData.total_rx_bytes)
                                : "--"}
                        {/if}
                    </div>
                </div>
            </div>
        </div>
        <!-- CPU Load (Si existe en LiveMode) -->
        <div
            class="glass-card-flat lg:col-span-2"
            style="border-radius:0.875rem;"
        >
            <div class="p-4 flex flex-row items-center justify-between h-full">
                <div class="flex-1 px-2">
                    <div
                        class="flex justify-between text-xs font-bold mb-1 opacity-70"
                    >
                        <span>CPU</span>
                        <span>{displayData?.extra?.cpu_load ?? "--"}%</span>
                    </div>
                    <progress
                        class="progress w-full {displayData?.extra?.cpu_load >
                        85
                            ? 'progress-error'
                            : 'progress-primary'}"
                        value={displayData?.extra?.cpu_load || 0}
                        max="100"
                    ></progress>
                </div>
                <div class="flex-1 px-2 border-l border-base-200 ml-2">
                    <div
                        class="flex justify-between text-xs font-bold mb-1 opacity-70"
                    >
                        <span>RAM</span>
                        <span>{displayData?.extra?.memory_usage ?? "--"}%</span>
                    </div>
                    <progress
                        class="progress w-full {displayData?.extra
                            ?.memory_usage > 85
                            ? 'progress-error'
                            : 'progress-info'}"
                        value={displayData?.extra?.memory_usage || 0}
                        max="100"
                    ></progress>
                </div>
            </div>
        </div>
    </div>

    <!-- Gráficas de Tendencia -->
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;">
        <!-- Clientes Conectados -->
        <div class="glass-card-flat" style="border-radius:1rem;">
            <div class="p-4 flex flex-col">
                <p
                    class="text-[10px] uppercase font-bold opacity-50 tracking-wider m-0"
                >
                    {isLiveMode
                        ? "Clientes — En Vivo"
                        : "Clientes conectados — 24h"}
                </p>
                {#if isLiveMode}
                    {#if liveHistory.length >= 2}
                        <svg
                            viewBox="0 0 200 44"
                            preserveAspectRatio="none"
                            class="w-full mt-2"
                            style="height:56px;"
                        >
                            <defs>
                                <linearGradient
                                    id="ap-lv-client-grad"
                                    x1="0"
                                    y1="0"
                                    x2="0"
                                    y2="1"
                                >
                                    <stop
                                        offset="0%"
                                        stop-color="oklch(from var(--color-primary) l c h)"
                                        stop-opacity="0.3"
                                    />
                                    <stop
                                        offset="100%"
                                        stop-color="oklch(from var(--color-primary) l c h)"
                                        stop-opacity="0"
                                    />
                                </linearGradient>
                            </defs>
                            <polygon
                                points="0,44 {toSparkPoints(
                                    liveClientsHistory,
                                    200,
                                    40,
                                )} 200,44"
                                fill="url(#ap-lv-client-grad)"
                            />
                            <polyline
                                points={toSparkPoints(
                                    liveClientsHistory,
                                    200,
                                    40,
                                )}
                                fill="none"
                                stroke="oklch(from var(--color-primary) l c h)"
                                stroke-width="1.5"
                                stroke-linejoin="round"
                                stroke-linecap="round"
                            />
                        </svg>
                        <div
                            class="flex justify-between text-[10px] opacity-40 mt-1"
                        >
                            <span
                                >hace ~{Math.round(
                                    (liveHistory.length * 3) / 60,
                                )} min</span
                            >
                            <span
                                >ahora: {liveHistory.at(-1)?.clients ?? "?"} clientes</span
                            >
                        </div>
                    {:else}
                        <p class="text-xs opacity-40 text-center py-4">
                            <span class="loading loading-spinner loading-xs"
                            ></span> Acumulando...
                        </p>
                    {/if}
                {:else if historyLoading}
                    <div class="flex justify-center items-center h-14">
                        <span class="loading loading-spinner loading-sm"></span>
                    </div>
                {:else if clientHistory.some((v) => v != null)}
                    <svg
                        viewBox="0 0 200 44"
                        preserveAspectRatio="none"
                        class="w-full mt-2"
                        style="height:56px;"
                    >
                        <defs>
                            <linearGradient
                                id="ap-client-grad"
                                x1="0"
                                y1="0"
                                x2="0"
                                y2="1"
                            >
                                <stop
                                    offset="0%"
                                    stop-color="oklch(from var(--color-primary) l c h)"
                                    stop-opacity="0.3"
                                />
                                <stop
                                    offset="100%"
                                    stop-color="oklch(from var(--color-primary) l c h)"
                                    stop-opacity="0"
                                />
                            </linearGradient>
                        </defs>
                        <polygon
                            points="0,44 {toSparkPoints(
                                clientHistory,
                                200,
                                40,
                            )} 200,44"
                            fill="url(#ap-client-grad)"
                        />
                        <polyline
                            points={toSparkPoints(clientHistory, 200, 40)}
                            fill="none"
                            stroke="oklch(from var(--color-primary) l c h)"
                            stroke-width="1.5"
                            stroke-linejoin="round"
                            stroke-linecap="round"
                        />
                    </svg>
                    <div
                        class="flex justify-between text-[10px] opacity-40 mt-1"
                    >
                        {#if apHistory.length > 0}
                            <span
                                >{new Date(
                                    apHistory[0].timestamp,
                                ).toLocaleTimeString("es", {
                                    hour: "2-digit",
                                    minute: "2-digit",
                                })}</span
                            >
                            <span
                                >Máx: {Math.max(
                                    ...(clientHistory.filter(
                                        (v) => v != null,
                                    ) as number[]),
                                )} clientes</span
                            >
                            <span
                                >{new Date(
                                    apHistory[apHistory.length - 1].timestamp,
                                ).toLocaleTimeString("es", {
                                    hour: "2-digit",
                                    minute: "2-digit",
                                })}</span
                            >
                        {/if}
                    </div>
                {:else}
                    <p class="text-xs opacity-40 text-center py-4">
                        Sin datos históricos
                    </p>
                {/if}
            </div>
        </div>

        <!-- Throughput TX/RX -->
        <div
            class="glass-card-flat"
            style="border-radius:1rem;{isLiveMode
                ? 'border:1px solid oklch(from var(--color-success) l c h / 0.2);'
                : ''}"
        >
            <div class="p-4 flex flex-col">
                <div class="flex items-center justify-between m-0">
                    <p
                        class="text-[10px] uppercase font-bold opacity-50 tracking-wider m-0"
                    >
                        {isLiveMode
                            ? "Throughput — En Vivo"
                            : "Throughput TX/RX — 24h"}
                    </p>
                    <div class="flex gap-2 text-[9px] opacity-60">
                        <span class="flex items-center gap-1">
                            <span
                                style="display:inline-block;width:8px;height:2px;background:oklch(from var(--color-warning) l c h);"
                            ></span>TX
                        </span>
                        <span class="flex items-center gap-1">
                            <span
                                style="display:inline-block;width:8px;height:2px;background:oklch(from var(--color-success) l c h);"
                            ></span>RX
                        </span>
                    </div>
                </div>
                {#if isLiveMode}
                    {#if liveHistory.length >= 3}
                        {@const lastTx = liveTxHistory
                            .filter((v) => v != null)
                            .at(-1)}
                        {@const lastRx = liveRxHistory
                            .filter((v) => v != null)
                            .at(-1)}
                        <div class="flex gap-3 text-[10px] font-bold mt-1 mb-1">
                            <span
                                style="color:oklch(from var(--color-warning) l c h);"
                                >↑ {fmtKbps(lastTx)}</span
                            >
                            <span
                                style="color:oklch(from var(--color-success) l c h);"
                                >↓ {fmtKbps(lastRx)}</span
                            >
                        </div>
                        <svg
                            viewBox="0 0 200 44"
                            preserveAspectRatio="none"
                            class="w-full mt-1"
                            style="height:52px;"
                        >
                            <defs>
                                <linearGradient
                                    id="ap-lv-tx-grad"
                                    x1="0"
                                    y1="0"
                                    x2="0"
                                    y2="1"
                                >
                                    <stop
                                        offset="0%"
                                        stop-color="oklch(from var(--color-warning) l c h)"
                                        stop-opacity="0.2"
                                    />
                                    <stop
                                        offset="100%"
                                        stop-color="oklch(from var(--color-warning) l c h)"
                                        stop-opacity="0"
                                    />
                                </linearGradient>
                            </defs>
                            <polygon
                                points="0,44 {toSparkPoints(
                                    liveTxHistory,
                                    200,
                                    40,
                                )} 200,44"
                                fill="url(#ap-lv-tx-grad)"
                            />
                            <polyline
                                points={toSparkPoints(liveTxHistory, 200, 40)}
                                fill="none"
                                stroke="oklch(from var(--color-warning) l c h)"
                                stroke-width="1.5"
                                stroke-linejoin="round"
                                stroke-linecap="round"
                            />
                            <polyline
                                points={toSparkPoints(liveRxHistory, 200, 40)}
                                fill="none"
                                stroke="oklch(from var(--color-success) l c h)"
                                stroke-width="1.5"
                                stroke-linejoin="round"
                                stroke-linecap="round"
                                stroke-dasharray="4 2"
                            />
                        </svg>
                    {:else}
                        <p class="text-xs opacity-40 text-center py-4">
                            <span class="loading loading-spinner loading-xs"
                            ></span> Acumulando datos...
                        </p>
                    {/if}
                {:else if historyLoading}
                    <div class="flex justify-center items-center h-14">
                        <span class="loading loading-spinner loading-sm"></span>
                    </div>
                {:else if txHistory.some((v) => v != null) || rxHistory.some((v) => v != null)}
                    <svg
                        viewBox="0 0 200 44"
                        preserveAspectRatio="none"
                        class="w-full mt-2"
                        style="height:56px;"
                    >
                        <defs>
                            <linearGradient
                                id="ap-tx-grad"
                                x1="0"
                                y1="0"
                                x2="0"
                                y2="1"
                            >
                                <stop
                                    offset="0%"
                                    stop-color="oklch(from var(--color-info) l c h)"
                                    stop-opacity="0.2"
                                />
                                <stop
                                    offset="100%"
                                    stop-color="oklch(from var(--color-info) l c h)"
                                    stop-opacity="0"
                                />
                            </linearGradient>
                        </defs>
                        {#if txHistory.some((v) => v != null)}
                            <polygon
                                points="0,44 {toSparkPoints(
                                    txHistory,
                                    200,
                                    40,
                                )} 200,44"
                                fill="url(#ap-tx-grad)"
                            />
                            <polyline
                                points={toSparkPoints(txHistory, 200, 40)}
                                fill="none"
                                stroke="oklch(from var(--color-warning) l c h)"
                                stroke-width="1.5"
                                stroke-linejoin="round"
                                stroke-linecap="round"
                            />
                        {/if}
                        {#if rxHistory.some((v) => v != null)}
                            <polyline
                                points={toSparkPoints(rxHistory, 200, 40)}
                                fill="none"
                                stroke="oklch(from var(--color-success) l c h)"
                                stroke-width="1.5"
                                stroke-linejoin="round"
                                stroke-linecap="round"
                                stroke-dasharray="4 2"
                            />
                        {/if}
                    </svg>
                {:else}
                    <p class="text-xs opacity-40 text-center py-4">
                        Sin datos históricos
                    </p>
                {/if}
            </div>
        </div>
    </div>

    <!-- Tabla de Clientes (Históricos o Live) -->
    <div class="glass-card-flat flex-1 mb-8" style="border-radius:1rem;">
        <div class="p-0 flex flex-col h-full">
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
                {#if wsStatus === "connecting" || dataLoading}
                    <span class="loading loading-spinner w-4 h-4 text-primary"
                    ></span>
                {:else if isLiveMode && wsStatus === "connected"}
                    <span
                        class="flex items-center gap-2 text-xs font-bold text-success opacity-80 bg-success/10 px-2 py-1 rounded border border-success/20"
                    >
                        <span
                            class="w-2 h-2 rounded-full bg-success animate-pulse"
                        ></span>
                        DATOS EN VIVO
                    </span>
                {:else}
                    <span
                        class="flex items-center gap-2 text-xs font-bold text-base-content/50 opacity-80 bg-base-200 px-2 py-1 rounded"
                    >
                        HISTÓRICO (Base de Datos)
                    </span>
                {/if}
            </div>

            <div class="overflow-x-auto w-full max-h-[600px]">
                <table class="table table-zebra table-pin-rows table-sm w-full">
                    <thead>
                        <tr class="bg-base-200 border-none">
                            <th>#</th>
                            <th>CPE / Hostname</th>
                            <th>MAC / IP</th>
                            <th class="text-center">Señal dBm</th>
                            <th class="text-center">Modulación TX/RX</th>
                            <th class="text-right">Tráfico Total</th>
                            <th class="text-right">Tráfico (Mbps)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {#if displayData?.clients?.length > 0}
                            {#each displayData.clients as client, index}
                                <tr
                                    class="hover border-base-200 {isLiveMode &&
                                    client.throughput_rx_kbps !== undefined
                                        ? ''
                                        : 'opacity-80 grayscale-[30%]'}"
                                >
                                    <td class="text-xs opacity-50 font-bold"
                                        >{index + 1}</td
                                    >
                                    <td>
                                        <div class="font-bold text-sm">
                                            {client.cpe_hostname ||
                                                "Desconocido"}
                                        </div>
                                        {#if !isLiveMode && client.timestamp}
                                            <div class="text-[10px] opacity-50">
                                                Visto: {new Date(
                                                    client.timestamp,
                                                ).toLocaleString()}
                                            </div>
                                        {/if}
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
                                        {#if client.signal != null}
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
                                        {:else}
                                            <span class="opacity-30">--</span>
                                        {/if}
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
                                            class="font-mono text-[11px] opacity-80 bg-base-200 rounded px-2 py-1 inline-block text-right"
                                        >
                                            <span class="text-info font-bold"
                                                >TX:</span
                                            >
                                            {client.total_tx_bytes != null
                                                ? formatBytes(
                                                      client.total_tx_bytes,
                                                  )
                                                : "--"} <br />
                                            <span class="text-primary font-bold"
                                                >RX:</span
                                            >
                                            {client.total_rx_bytes != null
                                                ? formatBytes(
                                                      client.total_rx_bytes,
                                                  )
                                                : "--"}
                                        </div>
                                    </td>
                                    <td class="text-right">
                                        <div
                                            class="font-mono text-xs text-info font-bold inline-flex items-center gap-1 w-20 justify-end"
                                        >
                                            ↓ {client.throughput_rx_kbps != null
                                                ? (
                                                      client.throughput_rx_kbps /
                                                      1024
                                                  ).toFixed(1)
                                                : "--"}
                                        </div>
                                        <br />
                                        <div
                                            class="font-mono text-xs text-primary font-bold inline-flex items-center gap-1 w-20 justify-end mt-1"
                                        >
                                            ↑ {client.throughput_tx_kbps != null
                                                ? (
                                                      client.throughput_tx_kbps /
                                                      1024
                                                  ).toFixed(1)
                                                : "--"}
                                        </div>
                                    </td>
                                </tr>
                            {/each}
                        {:else if dataLoading}
                            <tr>
                                <td colspan="6" class="text-center py-16">
                                    <span
                                        class="loading loading-spinner loading-lg text-primary"
                                    ></span>
                                    <p
                                        class="mt-4 text-sm font-bold opacity-50"
                                    >
                                        Obteniendo datos...
                                    </p>
                                </td>
                            </tr>
                        {:else if displayData}
                            <tr>
                                <td
                                    colspan="6"
                                    class="text-center py-16 opacity-50"
                                >
                                    <div class="text-4xl mb-2">📡</div>
                                    <h3 class="font-bold">Sin clientes</h3>
                                    <p class="text-sm">
                                        No hay estaciones conectadas o
                                        registradas actualmente.
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

<ProvisionModal bind:show={showProvisionModal} {isProvisioning} onProvision={handleProvision} />

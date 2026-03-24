<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import { getRouterHistory, provisionRouter, repairRouter } from "$lib/api";
    import type { Router, RouterHistoryPoint } from "$lib/types/router";
    import RouterPlansTab from "./RouterPlansTab.svelte";
    import RouterInterfacesTab from "./RouterInterfacesTab.svelte";
    import RouterEditModal from "./RouterEditModal.svelte";
    import RouterBackupsTab from "./RouterBackupsTab.svelte";
    import QueuesTab from "./QueuesTab.svelte";
    import RouterNetworkTab from "./RouterNetworkTab.svelte";
    import RouterFirewallTab from "./RouterFirewallTab.svelte";
    import RouterUsersTab from "./RouterUsersTab.svelte";
    import RouterPPPTab from "./RouterPPPTab.svelte";
    import ProvisionModal from "$lib/components/ProvisionModal.svelte";
    import { notify } from "$lib/stores/notifications";

    // ── Props ──────────────────────────────────────────────────────────────
    let { data } = $props<{ data: { router: Router } }>();
    let router = $state(data.router);

    // ── Modal de edición ───────────────────────────────────────────────────
    let showEditModal = $state(false);

    // ── Aprovisionamiento ──────────────────────────────────────────────────
    let showProvisionModal = $state(false);
    let isProvisioning = $state(false);

    async function handleProvision(data: { newApiUser: string; newApiPassword?: string; method: string }) {
        isProvisioning = true;
        try {
            const res = await provisionRouter(router.host, data.newApiUser, data.newApiPassword, data.method);
            notify.success(res.message || "Router aprovisionado exitosamente.");
            router.is_provisioned = true;
            showProvisionModal = false;
        } catch (e: any) {
            notify.error(e?.response?.data?.detail ?? "Error al aprovisionar el router.");
            showProvisionModal = false;
        } finally {
            isProvisioning = false;
        }
    }

    async function handleUnprovision() {
        if (!confirm("¿Desvincular router? Perderá el acceso API-SSL hasta que vuelva a aprovisionarse.")) return;
        try {
            await repairRouter(router.host, "unprovision");
            notify.success("Router desvinculado correctamente.");
            router.is_provisioned = false;
        } catch (e: any) {
            notify.error(e?.response?.data?.detail ?? "Error al desvincular el router.");
        }
    }

    // ── Sistema de pestañas ────────────────────────────────────────────────
    let activeTab = $state<
        | "overview"
        | "planes"
        | "backups"
        | "interfaces"
        | "queues"
        | "network"
        | "firewall"
        | "users"
        | "ppp"
    >("overview");

    // ── Modo Live / Histórico ──────────────────────────────────────────────
    let isLiveMode = $state(false);
    let ws: WebSocket | null = null;
    let wsStatus = $state<
        "connecting" | "connected" | "error" | "disconnected"
    >("disconnected");
    let wsErrorMsg = $state<string | null>(null);

    // ── Datos históricos ───────────────────────────────────────────────────
    let historyData = $state<RouterHistoryPoint[]>([]);
    let historyLoading = $state(true);
    let historyError = $state<string | null>(null);

    // ── Datos Live (del WS) ────────────────────────────────────────────────
    let liveData = $state<any>(null);
    // Historial en vivo (últimos N puntos recibidos del backend Redis/memoria)
    let liveHistory = $state<any[]>([]);

    // ── KPIs actuales (histórico o live según modo) ────────────────────────
    let latestPoint = $derived(
        historyData.length > 0 ? historyData[historyData.length - 1] : null,
    );

    let displayCpu = $derived(
        isLiveMode && liveData
            ? (liveData.cpu_load ?? null)
            : (latestPoint?.cpu_load ?? null),
    );
    let displayRamPct = $derived(() => {
        const free =
            isLiveMode && liveData
                ? liveData.free_memory
                : latestPoint?.free_memory;
        const total =
            isLiveMode && liveData
                ? liveData.total_memory
                : latestPoint?.total_memory;
        if (free == null || total == null || total === 0) return null;
        return Math.round(((total - free) / total) * 100);
    });
    let displayUptime = $derived(
        isLiveMode && liveData
            ? (liveData.uptime ?? "--")
            : (latestPoint?.uptime ?? "--"),
    );
    let displayTemp = $derived(
        isLiveMode && liveData
            ? (liveData.temperature ?? null)
            : (latestPoint?.temperature ?? null),
    );
    let displayVoltage = $derived(
        isLiveMode && liveData
            ? (liveData.voltage ?? null)
            : (latestPoint?.voltage ?? null),
    );

    let displayTxBytes = $derived(
        isLiveMode && liveData
            ? (liveData.wan_tx_bytes ?? null)
            : (latestPoint?.wan_tx_bytes ?? null),
    );

    let displayRxBytes = $derived(
        isLiveMode && liveData
            ? (liveData.wan_rx_bytes ?? null)
            : (latestPoint?.wan_rx_bytes ?? null),
    );

    let displayTotalDisk = $derived(
        isLiveMode && liveData
            ? (liveData.total_disk ?? null)
            : (latestPoint?.total_disk ?? null),
    );

    let displayFreeDisk = $derived(
        isLiveMode && liveData
            ? (liveData.free_disk ?? null)
            : (latestPoint?.free_disk ?? null),
    );

    // ── Ciclo de vida ──────────────────────────────────────────────────────
    onMount(() => {
        loadHistory();
    });

    onDestroy(() => {
        stopLiveMode();
    });

    // ── Cargar historial ───────────────────────────────────────────────────
    async function loadHistory() {
        historyLoading = true;
        historyError = null;
        try {
            const res = await getRouterHistory(router.host, 24);
            historyData = res.data ?? [];
        } catch (e: any) {
            historyError =
                e?.response?.data?.detail ?? "Error al cargar el historial.";
        } finally {
            historyLoading = false;
        }
    }

    // ── Toggle Live Mode ───────────────────────────────────────────────────
    function toggleLiveMode() {
        if (isLiveMode) {
            stopLiveMode();
        } else {
            startLiveMode();
        }
    }

    function stopLiveMode() {
        isLiveMode = false;
        liveData = null;
        liveHistory = [];
        if (ws) {
            ws.close();
            ws = null;
        }
        wsStatus = "disconnected";
    }

    function startLiveMode() {
        isLiveMode = true;
        wsStatus = "connecting";
        wsErrorMsg = null;
        liveData = null;

        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsUrl = `${protocol}//${window.location.host}/api/routers/${router.host}/ws/resources`;

        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            wsStatus = "connected";
            wsErrorMsg = null;
        };

        ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                if (msg.type === "resources") {
                    liveData = msg.data;
                    // Actualizar historial en vivo si viene del backend
                    if (Array.isArray(msg.data?.live_history)) {
                        liveHistory = msg.data.live_history;
                    }
                    wsStatus = "connected";
                } else if (msg.type === "loading") {
                    // aun cargando, no hacemos nada
                } else if (msg.type === "error") {
                    wsErrorMsg = msg.data?.message ?? "Error en el dispositivo";
                    wsStatus = "error";
                    stopLiveMode();
                }
            } catch (err) {
                console.error("WS parse error:", err);
            }
        };

        ws.onerror = () => {
            wsStatus = "error";
            wsErrorMsg = "No se pudo conectar al WebSocket";
            stopLiveMode();
        };

        ws.onclose = () => {
            if (wsStatus !== "error") wsStatus = "disconnected";
            if (isLiveMode) stopLiveMode();
        };
    }

    // ── Helpers ────────────────────────────────────────────────────────────
    function fmtBytes(bytes: number | null | undefined): string {
        if (bytes == null) return "--";
        if (bytes === 0) return "0 B";
        const units = ["B", "KB", "MB", "GB"];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return (bytes / Math.pow(1024, i)).toFixed(1) + " " + units[i];
    }

    function fmtTime(ts: string): string {
        return new Date(ts).toLocaleTimeString("es", {
            hour: "2-digit",
            minute: "2-digit",
        });
    }

    // Normaliza un array de valores a escala 0-100 para mini-gráficas SVG
    function toSparkPoints(
        data: (number | null)[],
        width = 200,
        height = 40,
    ): string {
        const vals = data.filter((v) => v != null) as number[];
        if (vals.length < 2) return "";
        const min = Math.min(...vals);
        const max = Math.max(...vals);
        const range = max - min || 1;
        return data
            .map((v, i) => {
                const x = (i / (data.length - 1)) * width;
                const y =
                    v == null ? height : height - ((v - min) / range) * height;
                return `${x.toFixed(1)},${y.toFixed(1)}`;
            })
            .join(" ");
    }

    let cpuHistory = $derived(historyData.map((p) => p.cpu_load));
    let ramPctHistory = $derived(
        historyData.map((p) => {
            if (
                p.free_memory == null ||
                p.total_memory == null ||
                p.total_memory === 0
            )
                return null;
            return Math.round(
                ((p.total_memory - p.free_memory) / p.total_memory) * 100,
            );
        }),
    );

    // ── Arrays para gráficas live ──────────────────────────────────────────
    let liveCpuHistory = $derived(
        liveHistory.map((p: any) => p.cpu as number | null),
    );
    let liveRamHistory = $derived(
        liveHistory.map((p: any) => p.ram as number | null),
    );
    // tx_kbps / rx_kbps vienen directamente del backend (bps / 1024)
    let liveTxKbps = $derived(
        liveHistory.map((p: any) => (p.tx_kbps ?? null) as number | null),
    );
    let liveRxKbps = $derived(
        liveHistory.map((p: any) => (p.rx_kbps ?? null) as number | null),
    );

    // ── Arrays para gráficas históricas de WAN ─────────────────────────────
    let historyTxKbps = $derived(
        historyData.map((p) =>
            p.wan_tx_bps != null ? Math.round(p.wan_tx_bps / 1024) : null,
        ),
    );
    let historyRxKbps = $derived(
        historyData.map((p) =>
            p.wan_rx_bps != null ? Math.round(p.wan_rx_bps / 1024) : null,
        ),
    );

    function fmtKbps(kbps: number | null | undefined): string {
        if (kbps == null) return "--";
        if (kbps < 1000) return `${kbps} KB/s`;
        return `${(kbps / 1024).toFixed(1)} MB/s`;
    }
</script>

<svelte:head>
    <title>{router.hostname || router.host} — Router</title>
</svelte:head>

<!-- ── CONTENEDOR PRINCIPAL ─────────────────────────────────────────────── -->
<div
    style="display:flex;flex-direction:column;gap:1.5rem;max-width:1200px;margin:0 auto;width:100%;"
>
    <!-- ── HEADER ─────────────────────────────────────────────────────────── -->
    <div
        class="glass-card-flat"
        style="border-radius:1rem;display:flex;flex-direction:column;overflow:hidden;"
    >
        <div
            style="padding:1.25rem 1.5rem;display:flex;flex-direction:column;gap:0.75rem;"
        >
            <div
                style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:0.75rem;"
            >
                <!-- Título + Breadcrumb -->
                <div style="display:flex;align-items:center;gap:0.75rem;">
                    <a
                        href="/routers"
                        class="btn btn-ghost btn-sm btn-circle"
                        title="Volver a Routers"
                    >
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke-width="2.5"
                            stroke="currentColor"
                            style="width:1.1rem;height:1.1rem;"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                d="M15.75 19.5L8.25 12l7.5-7.5"
                            />
                        </svg>
                    </a>
                    <div>
                        <h1 style="margin:0;font-size:1.5rem;font-weight:800;">
                            {router.hostname || router.host}
                        </h1>
                        <p
                            style="margin:0;font-size:0.8rem;opacity:0.5;font-family:monospace;"
                        >
                            {router.host}
                            {#if router.model}
                                · {router.model}{/if}
                            {#if router.firmware}
                                · {router.firmware}{/if}
                            {#if router.zona_nombre}
                                · 📍 {router.zona_nombre}{/if}
                        </p>
                    </div>
                </div>

                <!-- Badges + Toggle + Editar -->
                <div
                class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 relative"
            >
                    <!-- Status badge -->
                    <span
                        class="badge badge-sm {router.last_status === 'online'
                            ? 'badge-success'
                            : router.last_status === 'offline'
                              ? 'badge-error'
                              : 'badge-ghost'} font-bold"
                    >
                        {router.last_status || "desconocido"}
                    </span>
                    <!-- Enabled Badge -->
                    {#if !router.is_enabled}
                        <span
                            class="badge badge-sm badge-ghost font-bold opacity-60"
                        >
                            Deshabilitado
                        </span>
                    {/if}
                    <!-- Provisioning Buttons/Badges -->
                    {#if router.vendor === 'mikrotik'}
                        {#if router.is_provisioned}
                            <div class="dropdown dropdown-end">
                                <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
                                <div tabindex="0" role="button" class="btn btn-sm btn-info gap-1 text-white pr-2 mb-0">
                                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="w-3 h-3">
                                        <path fill-rule="evenodd" d="M8 1a3.5 3.5 0 0 0-3.5 3.5V7A1.5 1.5 0 0 0 3 8.5v5A1.5 1.5 0 0 0 4.5 15h7a1.5 1.5 0 0 0 1.5-1.5v-5A1.5 1.5 0 0 0 11.5 7V4.5A3.5 3.5 0 0 0 8 1Zm2 6V4.5a2 2 0 1 0-4 0V7h4Z" clip-rule="evenodd" />
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
                            <button class="btn btn-sm btn-success text-white" onclick={() => (showProvisionModal = true)}>
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4 mr-1">
                                    <path fill-rule="evenodd" d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z" clip-rule="evenodd" />
                                </svg>
                                Aprovisionar
                            </button>
                        {/if}
                    {/if}

                    <!-- Botón Editar -->
                    <button
                        class="btn btn-ghost btn-xs gap-1"
                        onclick={() => (showEditModal = true)}
                        title="Editar configuración del router"
                    >
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke-width="2"
                            stroke="currentColor"
                            style="width:0.85rem;height:0.85rem;"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                d="M16.862 4.487a2.25 2.25 0 113.182 3.182L8.108 19.605a4.5 4.5 0 01-1.897 1.13l-3.26.909a.75.75 0 01-.921-.921l.909-3.26a4.5 4.5 0 011.13-1.897L16.862 4.487z"
                            />
                        </svg>
                        Editar
                    </button>

                    <!-- Live Mode Toggle -->
                    <label
                        class="label cursor-pointer flex gap-2"
                        style="padding:0;"
                    >
                        <span
                            style="font-size:0.7rem;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;opacity:0.7;"
                        >
                            {#if wsStatus === "connecting"}
                                <span
                                    class="loading loading-spinner loading-xs text-primary"
                                ></span>
                                Conectando...
                            {:else if isLiveMode}
                                <span
                                    style="color:oklch(from var(--color-success) l c h);display:flex;align-items:center;gap:0.3rem;"
                                >
                                    <span
                                        style="width:0.5rem;height:0.5rem;border-radius:50%;background:oklch(from var(--color-success) l c h);animation:pulse 1.5s infinite;"
                                    ></span>
                                    En Vivo
                                </span>
                            {:else}
                                Histórico
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
            </div>
        </div>

        <!-- Error WS -->
        {#if wsStatus === "error" && wsErrorMsg}
            <div class="alert alert-warning py-2 mx-6 mb-4">
                <span style="font-size:0.85rem;">⚠️ {wsErrorMsg}</span>
                <button
                    class="btn btn-xs btn-ghost ml-auto"
                    onclick={stopLiveMode}>Cerrar</button
                >
            </div>
        {/if}

        <!-- Pestañas de Navegación integradas al header -->
        <div
            style="background:oklch(from var(--color-base-content) l c h / 0.02);border-top:1px solid oklch(from var(--color-base-content) l c h / 0.08);padding:0 1.5rem;display:flex;gap:1.5rem;"
            role="tablist"
        >
            {#each [{ id: "overview", label: "📊 Overview" }, { id: "planes", label: "📋 Planes Locales" }, { id: "interfaces", label: "🔌 Interfaces" }, { id: "network", label: "🌐 Network" }, { id: "firewall", label: "🛡️ Firewall" }, { id: "queues", label: "🚦 Queues" }, { id: "backups", label: "💾 Backups" }, { id: "users", label: "👤 Usuarios" }, { id: "ppp", label: "🔗 PPP" }] as tab}
                <button
                    role="tab"
                    aria-selected={activeTab === tab.id}
                    onclick={() => (activeTab = tab.id as any)}
                    style="padding:0.85rem 0;font-size:0.85rem;font-weight:{activeTab ===
                    tab.id
                        ? '800'
                        : '600'};color:{activeTab === tab.id
                        ? 'oklch(from var(--color-primary) l c h)'
                        : 'inherit'};opacity:{activeTab === tab.id
                        ? '1'
                        : '0.5'};border-bottom:3px solid {activeTab === tab.id
                        ? 'oklch(from var(--color-primary) l c h)'
                        : 'transparent'};background:none;cursor:pointer;transition:all 0.2s;"
                >
                    {tab.label}
                </button>
            {/each}
        </div>
    </div>

    <!-- ── CONTENIDO DINÁMICO POR PESTAÑA ─────────────────────────────────── -->
    {#if activeTab === "overview"}
        <!-- ── KPI CARDS ──────────────────────────────────────────────────────── -->
        <div
            style="display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:1rem;"
        >
            <!-- CPU + RAM — una sola card con progress bars (igual que AP detail) -->
            <div
                class="glass-card-flat"
                style="padding:1rem;border-radius:0.875rem;grid-column:span 2;"
            >
                <div style="display:flex;align-items:center;">
                    <div style="flex:1;padding:0 0.5rem 0 0;">
                        <div
                            style="display:flex;justify-content:space-between;font-size:0.7rem;font-weight:700;margin-bottom:0.35rem;opacity:0.7;"
                        >
                            <span>CPU</span>
                            <span
                                >{displayCpu != null
                                    ? `${displayCpu}%`
                                    : "--"}</span
                            >
                        </div>
                        <progress
                            class="progress w-full {displayCpu != null &&
                            displayCpu > 85
                                ? 'progress-error'
                                : 'progress-primary'}"
                            value={displayCpu || 0}
                            max="100"
                        ></progress>
                    </div>
                    <div
                        style="flex:1;padding:0 0 0 0.75rem;border-left:1px solid oklch(from var(--color-base-content) l c h / 0.1);"
                    >
                        <div
                            style="display:flex;justify-content:space-between;font-size:0.7rem;font-weight:700;margin-bottom:0.35rem;opacity:0.7;"
                        >
                            <span>RAM</span>
                            <span
                                >{displayRamPct() != null
                                    ? `${displayRamPct()}%`
                                    : "--"}</span
                            >
                        </div>
                        <progress
                            class="progress w-full {displayRamPct() != null &&
                            displayRamPct()! > 85
                                ? 'progress-error'
                                : 'progress-info'}"
                            value={displayRamPct() || 0}
                            max="100"
                        ></progress>
                    </div>
                </div>
                {#if isLiveMode && liveData && liveData.free_memory != null}
                    <p
                        style="margin:0.35rem 0 0;font-size:0.65rem;opacity:0.4;text-align:right;"
                    >
                        RAM libre: {fmtBytes(liveData.free_memory)} / {fmtBytes(
                            liveData.total_memory,
                        )}
                    </p>
                {/if}
            </div>

            <!-- Tráfico WAN Total -->
            <div
                class="glass-card-flat"
                style="padding:1rem;border-radius:0.875rem;grid-column:span 2;"
            >
                <div
                    style="display:flex;align-items:center;justify-content:space-between;height:100%;"
                >
                    <div style="flex:1;text-align:center;padding:0 0.5rem;">
                        <span
                            style="font-size:0.65rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;opacity:0.5;"
                            >Total TX (WAN)</span
                        >
                        <div
                            style="font-size:1.5rem;font-weight:800;margin-top:0.25rem;color:oklch(from var(--color-info) l c h);"
                        >
                            {#if !isLiveMode && historyLoading}
                                <span
                                    class="loading loading-dots loading-sm opacity-50"
                                ></span>
                            {:else}
                                {displayTxBytes != null
                                    ? fmtBytes(displayTxBytes)
                                    : "--"}
                            {/if}
                        </div>
                    </div>
                    <div
                        style="flex:1;text-align:center;padding:0 0.5rem;border-left:1px solid oklch(from var(--color-base-content) l c h / 0.1);"
                    >
                        <span
                            style="font-size:0.65rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;opacity:0.5;"
                            >Total RX (WAN)</span
                        >
                        <div
                            style="font-size:1.5rem;font-weight:800;margin-top:0.25rem;color:oklch(from var(--color-primary) l c h);"
                        >
                            {#if !isLiveMode && historyLoading}
                                <span
                                    class="loading loading-dots loading-sm opacity-50"
                                ></span>
                            {:else}
                                {displayRxBytes != null
                                    ? fmtBytes(displayRxBytes)
                                    : "--"}
                            {/if}
                        </div>
                    </div>
                </div>
            </div>

            <!-- Uptime -->
            <div
                class="glass-card-flat"
                style="padding:1rem;border-radius:0.875rem;text-align:center;"
            >
                <p
                    style="margin:0;font-size:0.65rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;opacity:0.5;"
                >
                    Uptime
                </p>
                <p
                    style="margin:0.5rem 0 0;font-size:1rem;font-weight:800;word-break:break-word;"
                >
                    {displayUptime}
                </p>
            </div>

            <!-- Temperatura -->
            <div
                class="glass-card-flat"
                style="padding:1rem;border-radius:0.875rem;text-align:center;"
            >
                <p
                    style="margin:0;font-size:0.65rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;opacity:0.5;"
                >
                    Temperatura
                </p>
                <p
                    style="margin:0.5rem 0 0;font-size:1.75rem;font-weight:800;color:{displayTemp !=
                        null && displayTemp > 60
                        ? 'oklch(from var(--color-error) l c h)'
                        : displayTemp != null && displayTemp > 50
                          ? 'oklch(from var(--color-warning) l c h)'
                          : 'inherit'};"
                >
                    {displayTemp != null ? `${displayTemp}°C` : "--"}
                </p>
            </div>

            <!-- Voltaje -->
            <div
                class="glass-card-flat"
                style="padding:1rem;border-radius:0.875rem;text-align:center;"
            >
                <p
                    style="margin:0;font-size:0.65rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;opacity:0.5;"
                >
                    Voltaje
                </p>
                <p style="margin:0.5rem 0 0;font-size:1.75rem;font-weight:800;">
                    {displayVoltage != null ? `${displayVoltage}V` : "--"}
                </p>
            </div>

            <!-- Disco --->
            {#if displayTotalDisk != null}
                <div
                    class="glass-card-flat"
                    style="padding:1rem;border-radius:0.875rem;text-align:center;"
                >
                    <p
                        style="margin:0;font-size:0.65rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;opacity:0.5;"
                    >
                        Disco
                    </p>
                    <p
                        style="margin:0.5rem 0 0;font-size:1rem;font-weight:800;"
                    >
                        {fmtBytes(displayFreeDisk)} libre
                    </p>
                    <p style="margin:0;font-size:0.7rem;opacity:0.5;">
                        de {fmtBytes(displayTotalDisk)}
                    </p>
                </div>
            {/if}
        </div>

        <!-- ── GRÁFICAS ─────────────────────────────────────────────────────────── -->
        <!-- Fila 1: CPU + RAM unificadas -->
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;">
            <!-- CPU + RAM sparkline (dos líneas, una card) -->
            <div
                class="glass-card-flat"
                style="padding:1.25rem;border-radius:1rem;"
            >
                <div
                    style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.75rem;"
                >
                    <p
                        style="margin:0;font-size:0.75rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;opacity:0.6;"
                    >
                        {isLiveMode
                            ? "CPU + RAM — En Vivo"
                            : "CPU + RAM — Últimas 24h"}
                    </p>
                    <div
                        style="display:flex;gap:0.6rem;font-size:0.6rem;opacity:0.6;"
                    >
                        <span
                            style="display:flex;align-items:center;gap:0.25rem;"
                        >
                            <span
                                style="width:8px;height:2px;display:inline-block;background:oklch(from var(--color-primary) l c h);border-radius:2px;"
                            ></span>CPU
                        </span>
                        <span
                            style="display:flex;align-items:center;gap:0.25rem;"
                        >
                            <span
                                style="width:8px;height:2px;display:inline-block;background:oklch(from var(--color-info) l c h);border-radius:2px;"
                            ></span>RAM
                        </span>
                    </div>
                </div>
                {#if isLiveMode}
                    {#if liveHistory.length >= 2}
                        <svg
                            viewBox="0 0 200 48"
                            preserveAspectRatio="none"
                            style="width:100%;height:60px;"
                        >
                            <defs>
                                <linearGradient
                                    id="lv-cpu-grad"
                                    x1="0"
                                    y1="0"
                                    x2="0"
                                    y2="1"
                                >
                                    <stop
                                        offset="0%"
                                        stop-color="oklch(from var(--color-primary) l c h)"
                                        stop-opacity="0.2"
                                    />
                                    <stop
                                        offset="100%"
                                        stop-color="oklch(from var(--color-primary) l c h)"
                                        stop-opacity="0"
                                    />
                                </linearGradient>
                                <linearGradient
                                    id="lv-ram-grad"
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
                            <polygon
                                points="0,48 {toSparkPoints(
                                    liveCpuHistory,
                                    200,
                                    42,
                                )} 200,48"
                                fill="url(#lv-cpu-grad)"
                            />
                            <polygon
                                points="0,48 {toSparkPoints(
                                    liveRamHistory,
                                    200,
                                    42,
                                )} 200,48"
                                fill="url(#lv-ram-grad)"
                            />
                            <polyline
                                points={toSparkPoints(liveCpuHistory, 200, 42)}
                                fill="none"
                                stroke="oklch(from var(--color-primary) l c h)"
                                stroke-width="1.5"
                                stroke-linejoin="round"
                                stroke-linecap="round"
                            />
                            <polyline
                                points={toSparkPoints(liveRamHistory, 200, 42)}
                                fill="none"
                                stroke="oklch(from var(--color-info) l c h)"
                                stroke-width="1.5"
                                stroke-linejoin="round"
                                stroke-linecap="round"
                            />
                        </svg>
                        <div
                            style="display:flex;justify-content:space-between;font-size:0.6rem;opacity:0.35;margin-top:0.25rem;"
                        >
                            <span
                                >hace ~{Math.round(
                                    (liveHistory.length * 2) / 60,
                                )} min</span
                            >
                            <span>ahora</span>
                        </div>
                    {:else}
                        <p
                            style="font-size:0.8rem;opacity:0.4;text-align:center;padding:1.5rem 0;"
                        >
                            <span class="loading loading-spinner loading-xs"
                            ></span> Acumulando datos...
                        </p>
                    {/if}
                {:else if historyLoading}
                    <div
                        style="height:60px;display:flex;align-items:center;justify-content:center;"
                    >
                        <span class="loading loading-spinner loading-sm"></span>
                    </div>
                {:else if cpuHistory.some((v) => v != null) || ramPctHistory.some((v) => v != null)}
                    <svg
                        viewBox="0 0 200 48"
                        preserveAspectRatio="none"
                        style="width:100%;height:60px;"
                    >
                        <defs>
                            <linearGradient
                                id="cpu-grad"
                                x1="0"
                                y1="0"
                                x2="0"
                                y2="1"
                            >
                                <stop
                                    offset="0%"
                                    stop-color="oklch(from var(--color-primary) l c h)"
                                    stop-opacity="0.2"
                                />
                                <stop
                                    offset="100%"
                                    stop-color="oklch(from var(--color-primary) l c h)"
                                    stop-opacity="0"
                                />
                            </linearGradient>
                            <linearGradient
                                id="ram-grad"
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
                        <polygon
                            points="0,48 {toSparkPoints(
                                cpuHistory,
                                200,
                                42,
                            )} 200,48"
                            fill="url(#cpu-grad)"
                        />
                        <polygon
                            points="0,48 {toSparkPoints(
                                ramPctHistory,
                                200,
                                42,
                            )} 200,48"
                            fill="url(#ram-grad)"
                        />
                        <polyline
                            points={toSparkPoints(cpuHistory, 200, 42)}
                            fill="none"
                            stroke="oklch(from var(--color-primary) l c h)"
                            stroke-width="1.5"
                            stroke-linejoin="round"
                            stroke-linecap="round"
                        />
                        <polyline
                            points={toSparkPoints(ramPctHistory, 200, 42)}
                            fill="none"
                            stroke="oklch(from var(--color-info) l c h)"
                            stroke-width="1.5"
                            stroke-linejoin="round"
                            stroke-linecap="round"
                        />
                    </svg>
                    <div
                        style="display:flex;justify-content:space-between;font-size:0.65rem;opacity:0.4;margin-top:0.25rem;"
                    >
                        {#if historyData.length > 0}
                            <span>{fmtTime(historyData[0].timestamp)}</span>
                            <span
                                >{fmtTime(
                                    historyData[historyData.length - 1]
                                        .timestamp,
                                )}</span
                            >
                        {/if}
                    </div>
                {:else}
                    <p
                        style="font-size:0.8rem;opacity:0.4;text-align:center;padding:1rem 0;"
                    >
                        Sin datos en la BD
                    </p>
                {/if}
            </div>

            <!-- Throughput WAN Live (solo en live mode) o histórico TX/RX -->
            <div
                class="glass-card-flat"
                style="padding:1.25rem;border-radius:1rem;{isLiveMode
                    ? 'border:1px solid oklch(from var(--color-success) l c h / 0.2);'
                    : ''}"
            >
                <div
                    style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.75rem;"
                >
                    <p
                        style="margin:0;font-size:0.75rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;opacity:0.6;"
                    >
                        {isLiveMode
                            ? "Throughput WAN — En Vivo"
                            : "TX / RX WAN — Últimas 24h"}
                    </p>
                    <div
                        style="display:flex;gap:0.6rem;font-size:0.6rem;opacity:0.6;"
                    >
                        <span
                            style="display:flex;align-items:center;gap:0.25rem;"
                        >
                            <span
                                style="width:8px;height:2px;display:inline-block;background:oklch(from var(--color-warning) l c h);border-radius:2px;"
                            ></span>TX
                        </span>
                        <span
                            style="display:flex;align-items:center;gap:0.25rem;"
                        >
                            <span
                                style="width:8px;height:2px;display:inline-block;background:oklch(from var(--color-success) l c h);border-radius:2px;"
                            ></span>RX
                        </span>
                    </div>
                </div>

                {#if isLiveMode}
                    {#if liveHistory.length >= 3}
                        {@const maxKbps = Math.max(
                            1,
                            ...(liveTxKbps.filter(
                                (v) => v != null,
                            ) as number[]),
                            ...(liveRxKbps.filter(
                                (v) => v != null,
                            ) as number[]),
                        )}
                        {@const lastTx = liveTxKbps
                            .filter((v) => v != null)
                            .at(-1)}
                        {@const lastRx = liveRxKbps
                            .filter((v) => v != null)
                            .at(-1)}
                        <div
                            style="display:flex;gap:1rem;font-size:0.7rem;font-weight:700;margin-bottom:0.4rem;"
                        >
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
                            viewBox="0 0 200 48"
                            preserveAspectRatio="none"
                            style="width:100%;height:60px;"
                        >
                            <defs>
                                <linearGradient
                                    id="lv-tx-grad"
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
                                <linearGradient
                                    id="lv-rx-grad"
                                    x1="0"
                                    y1="0"
                                    x2="0"
                                    y2="1"
                                >
                                    <stop
                                        offset="0%"
                                        stop-color="oklch(from var(--color-success) l c h)"
                                        stop-opacity="0.2"
                                    />
                                    <stop
                                        offset="100%"
                                        stop-color="oklch(from var(--color-success) l c h)"
                                        stop-opacity="0"
                                    />
                                </linearGradient>
                            </defs>
                            <polygon
                                points="0,48 {toSparkPoints(
                                    liveTxKbps,
                                    200,
                                    42,
                                )} 200,48"
                                fill="url(#lv-tx-grad)"
                            />
                            <polygon
                                points="0,48 {toSparkPoints(
                                    liveRxKbps,
                                    200,
                                    42,
                                )} 200,48"
                                fill="url(#lv-rx-grad)"
                            />
                            <polyline
                                points={toSparkPoints(liveTxKbps, 200, 42)}
                                fill="none"
                                stroke="oklch(from var(--color-warning) l c h)"
                                stroke-width="1.5"
                                stroke-linejoin="round"
                                stroke-linecap="round"
                            />
                            <polyline
                                points={toSparkPoints(liveRxKbps, 200, 42)}
                                fill="none"
                                stroke="oklch(from var(--color-success) l c h)"
                                stroke-width="1.5"
                                stroke-linejoin="round"
                                stroke-linecap="round"
                            />
                        </svg>
                        <div
                            style="display:flex;justify-content:space-between;font-size:0.6rem;opacity:0.35;margin-top:0.25rem;"
                        >
                            <span
                                >hace ~{Math.round(
                                    (liveHistory.length * 2) / 60,
                                )} min</span
                            >
                            <span>ahora</span>
                        </div>
                    {:else}
                        <p
                            style="font-size:0.8rem;opacity:0.4;text-align:center;padding:1.5rem 0;"
                        >
                            <span class="loading loading-spinner loading-xs"
                            ></span> Acumulando datos...
                        </p>
                    {/if}
                {:else if historyLoading}
                    <div
                        style="height:60px;display:flex;align-items:center;justify-content:center;"
                    >
                        <span class="loading loading-spinner loading-sm"></span>
                    </div>
                {:else if historyTxKbps.some((v) => v != null) || historyRxKbps.some((v) => v != null)}
                    <div
                        style="display:flex;justify-content:flex-end;gap:1rem;font-size:0.7rem;font-weight:800;margin-bottom:0.5rem;"
                    >
                        <span
                            style="color:oklch(from var(--color-warning) l c h);"
                        >
                            ↑ {fmtKbps(
                                historyTxKbps[historyTxKbps.length - 1] ?? 0,
                            )}
                        </span>
                        <span
                            style="color:oklch(from var(--color-success) l c h);"
                        >
                            ↓ {fmtKbps(
                                historyRxKbps[historyRxKbps.length - 1] ?? 0,
                            )}
                        </span>
                    </div>
                    <svg
                        viewBox="0 0 200 48"
                        preserveAspectRatio="none"
                        style="width:100%;height:60px;"
                    >
                        <defs>
                            <linearGradient
                                id="hist-tx-grad"
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
                            <linearGradient
                                id="hist-rx-grad"
                                x1="0"
                                y1="0"
                                x2="0"
                                y2="1"
                            >
                                <stop
                                    offset="0%"
                                    stop-color="oklch(from var(--color-success) l c h)"
                                    stop-opacity="0.2"
                                />
                                <stop
                                    offset="100%"
                                    stop-color="oklch(from var(--color-success) l c h)"
                                    stop-opacity="0"
                                />
                            </linearGradient>
                        </defs>
                        <polygon
                            points="0,48 {toSparkPoints(
                                historyTxKbps,
                                200,
                                42,
                            )} 200,48"
                            fill="url(#hist-tx-grad)"
                        />
                        <polygon
                            points="0,48 {toSparkPoints(
                                historyRxKbps,
                                200,
                                42,
                            )} 200,48"
                            fill="url(#hist-rx-grad)"
                        />
                        <polyline
                            points={toSparkPoints(historyTxKbps, 200, 42)}
                            fill="none"
                            stroke="oklch(from var(--color-warning) l c h)"
                            stroke-width="1.5"
                            stroke-linejoin="round"
                            stroke-linecap="round"
                        />
                        <polyline
                            points={toSparkPoints(historyRxKbps, 200, 42)}
                            fill="none"
                            stroke="oklch(from var(--color-success) l c h)"
                            stroke-width="1.5"
                            stroke-linejoin="round"
                            stroke-linecap="round"
                        />
                    </svg>
                    <div
                        style="display:flex;justify-content:space-between;font-size:0.65rem;opacity:0.4;margin-top:0.25rem;"
                    >
                        {#if historyData.length > 0}
                            <span>{fmtTime(historyData[0].timestamp)}</span>
                            <span
                                >{fmtTime(
                                    historyData[historyData.length - 1]
                                        .timestamp,
                                )}</span
                            >
                        {/if}
                    </div>
                {:else}
                    <p
                        style="font-size:0.8rem;opacity:0.4;text-align:center;padding:1.5rem 0;"
                    >
                        Aún no hay datos de interfaces recopilados. Revisa la
                        configuración del router.
                    </p>
                {/if}
            </div>
        </div>
    {/if}

    <!-- ── OTROS PANELES ─────────────────────────────────────────────────── -->
    {#if activeTab === "planes"}
        <RouterPlansTab routerHost={router.host} />
    {:else if activeTab === "interfaces"}
        <RouterInterfacesTab routerHost={router.host} />
    {:else if activeTab === "queues"}
        <QueuesTab routerHost={router.host} />
    {:else if activeTab === "network"}
        <RouterNetworkTab routerHost={router.host} />
    {:else if activeTab === "firewall"}
        <RouterFirewallTab routerHost={router.host} />
    {:else if activeTab === "backups"}
        <RouterBackupsTab host={router.host} />
    {:else if activeTab === "users"}
        <div class="glass-card-flat" style="padding:1.5rem;border-radius:1rem;">
            <RouterUsersTab host={router.host} />
        </div>
    {:else if activeTab === "ppp"}
        <div class="glass-card-flat" style="padding:1.5rem;border-radius:1rem;">
            <RouterPPPTab host={router.host} />
        </div>
    {/if}
</div>

<!-- Modal de Edición -->
<RouterEditModal
    {router}
    open={showEditModal}
    onClose={() => (showEditModal = false)}
    onSaved={(updated) => {
        router = updated;
        showEditModal = false;
    }}
/>

<style>
    @keyframes pulse {
        0%,
        100% {
            opacity: 1;
        }
        50% {
            opacity: 0.4;
        }
    }
</style>

<ProvisionModal bind:show={showProvisionModal} {isProvisioning} onProvision={handleProvision} />


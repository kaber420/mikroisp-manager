<script lang="ts">
    import { updateZonaInfra, getZonaAutodoc, syncZonaAutodoc } from "$lib/api";
    import { notify } from "$lib/stores/notifications";
    import type { ZonaDetail, ZonaInfra } from "$lib/types/zona";
    import { marked } from "marked";
    import DOMPurify from "dompurify";

    let { zona, zonaId, canEdit = false, onsave } = $props<{
        zona: ZonaDetail;
        zonaId: number;
        canEdit?: boolean;
        onsave?: () => void;
    }>();

    function fmt(val: string | null | undefined): string {
        return val?.trim() ? val : "—";
    }

    function fmtDate(val: string | null | undefined): string {
        if (!val) return "—";
        try {
            return new Date(val).toLocaleDateString("es", { day: "2-digit", month: "short", year: "numeric" });
        } catch { return val; }
    }

    // ── Estado de edición (Manual) ──────────────────────────────────────────
    let isEditing = $state(false);
    let fIpGestion = $state(zona.infraestructura?.direccion_ip_gestion ?? "");
    let fGateway = $state(zona.infraestructura?.gateway_predeterminado ?? "");
    let fDns = $state(zona.infraestructura?.servidores_dns ?? "");
    let fVlans = $state(zona.infraestructura?.vlans_utilizadas ?? "");
    let fEquipos = $state(zona.infraestructura?.equipos_criticos ?? "");
    let fMantenimiento = $state(zona.infraestructura?.proximo_mantenimiento ?? "");
    let saving = $state(false);
    let errorMsg = $state<string | null>(null);

    // ── Estado de Autodocumentación y Puertos ──────────────────────────────
    let autodoc = $state<any>(null);
    let loadingAutodoc = $state(true);
    let autodocError = $state<string | null>(null);
    let isSyncing = $state(false);
    let subTab = $state<"ports" | "markdown">("ports");

    let parsedMarkdown = $derived.by(() => {
        if (!autodoc?.markdown) return "";
        try {
            return DOMPurify.sanitize(marked.parse(autodoc.markdown) as string);
        } catch (e) {
            return `<p class="text-error">Error al renderizar Markdown: ${e}</p>`;
        }
    });

    $effect(() => {
        const infra = zona.infraestructura;
        fIpGestion = infra?.direccion_ip_gestion ?? "";
        fGateway = infra?.gateway_predeterminado ?? "";
        fDns = infra?.servidores_dns ?? "";
        fVlans = infra?.vlans_utilizadas ?? "";
        fEquipos = infra?.equipos_criticos ?? "";
        fMantenimiento = infra?.proximo_mantenimiento ?? "";
    });

    // Cargar autodoc cuando cambia la zona
    $effect(() => {
        if (zonaId) {
            loadAutodoc();
        }
    });

    async function loadAutodoc() {
        loadingAutodoc = true;
        autodocError = null;
        try {
            autodoc = await getZonaAutodoc(zonaId);
        } catch (e: any) {
            autodocError = e?.response?.data?.detail ?? "No se ha generado la ficha técnica aún.";
            autodoc = null;
        } finally {
            loadingAutodoc = false;
        }
    }

    async function handleSync() {
        isSyncing = true;
        try {
            await syncZonaAutodoc(zonaId);
            notify.success("Sincronización de red iniciada en segundo plano.");
            // Esperar 4 segundos y recargar datos de autodocumentación
            setTimeout(loadAutodoc, 4000);
        } catch (e: any) {
            notify.error(e?.response?.data?.detail ?? "Error al iniciar sincronización.");
        } finally {
            isSyncing = false;
        }
    }

    async function save() {
        saving = true;
        errorMsg = null;
        try {
            const payload: Partial<ZonaInfra> = {
                direccion_ip_gestion: fIpGestion.trim() || null,
                gateway_predeterminado: fGateway.trim() || null,
                servidores_dns: fDns.trim() || null,
                vlans_utilizadas: fVlans.trim() || null,
                equipos_criticos: fEquipos.trim() || null,
                proximo_mantenimiento: fMantenimiento || null,
            };
            await updateZonaInfra(zonaId, payload);
            notify.success("Infraestructura guardada.");
            isEditing = false;
            if (onsave) onsave();
        } catch (e: any) {
            errorMsg = e?.response?.data?.detail ?? "Error al guardar infraestructura.";
        } finally {
            saving = false;
        }
    }

    // Clases dinámicas para renderizado premium de puertos físicos
    function getPortClass(port: any): string {
        if (port.disabled) return "border-red-500/40 bg-red-500/5 text-red-500/60 line-through cursor-not-allowed";
        if (port.running) {
            if (port.poe && port.poe !== "off") {
                return "border-amber-500/60 bg-emerald-500/10 text-emerald-400 shadow-[0_0_8px_rgba(245,158,11,0.15)] hover:scale-105";
            }
            return "border-emerald-500/60 bg-emerald-500/10 text-emerald-400 hover:scale-105";
        }
        return "border-base-content/10 bg-base-200/50 text-base-content/40 hover:bg-base-200 hover:text-base-content/75";
    }

    function getTooltipText(port: any): string {
        const parts = [];
        parts.push(`Tipo: ${port.type || 'ether'}`);
        if (port.disabled) parts.push("DESHABILITADO");
        else parts.push(port.running ? "🟢 Activo (UP)" : "⚪ Desconectado (DOWN)");
        if (port.speed) parts.push(`Velocidad: ${port.speed}`);
        if (port.bridge) parts.push(`Bridge: ${port.bridge}`);
        if (port.vlans && port.vlans.length > 0) {
            parts.push(`VLANs: ${port.vlans.map((v: any) => v.id).join(", ")}`);
        }
        if (port.poe && port.poe !== "off") {
            parts.push(`PoE: ${port.poe}${port.poe_power ? ` (${port.poe_power}W)` : ""}`);
        }
        if (port.comment) parts.push(`"${port.comment}"`);
        return parts.join(" | ");
    }
</script>

<div class="flex flex-col gap-6">
    <!-- ── BLOQUE A: DATOS MANUALES DE INFRAESTRUCTURA ──────────────────────── -->
    <div class="glass-card-flat" style="border-radius:1rem;padding:1.5rem;">
        {#if isEditing}
            <!-- MODO EDICIÓN -->
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1.5rem;">
                <h3 style="margin:0;font-size:1.1rem;font-weight:700;opacity:0.9;">🔌 Editar Datos de Red Manuales</h3>
                <div style="display:flex;align-items:center;gap:0.5rem;">
                    {#if saving}<span class="loading loading-spinner loading-sm text-primary"></span>{/if}
                    <button type="button" class="btn btn-xs btn-neutral" onclick={() => (isEditing = false)}>Cancelar</button>
                </div>
            </div>

            <form onsubmit={(e) => { e.preventDefault(); save(); }} style="display:flex;flex-direction:column;gap:1.25rem;">
                {#if errorMsg}
                    <div class="alert alert-error py-2"><span style="font-size:0.85rem;">{errorMsg}</span></div>
                {/if}

                <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(220px, 1fr));gap:1rem;">
                    <label class="form-control">
                        <div class="label"><span class="label-text font-semibold opacity-70">IP de Gestión</span></div>
                        <input class="input input-bordered input-sm font-mono bg-base-100" type="text" bind:value={fIpGestion} placeholder="192.168.X.X" />
                    </label>
                    <label class="form-control">
                        <div class="label"><span class="label-text font-semibold opacity-70">Gateway</span></div>
                        <input class="input input-bordered input-sm font-mono bg-base-100" type="text" bind:value={fGateway} placeholder="192.168.X.1" />
                    </label>
                    <label class="form-control">
                        <div class="label"><span class="label-text font-semibold opacity-70">Servidores DNS</span></div>
                        <input class="input input-bordered input-sm font-mono bg-base-100" type="text" bind:value={fDns} placeholder="8.8.8.8, 1.1.1.1" />
                    </label>
                    <label class="form-control">
                        <div class="label"><span class="label-text font-semibold opacity-70">VLANs Utilizadas</span></div>
                        <input class="input input-bordered input-sm font-mono bg-base-100" type="text" bind:value={fVlans} placeholder="10, 20..." />
                    </label>
                </div>

                <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(250px, 1fr));gap:1rem;">
                    <label class="form-control">
                        <div class="label"><span class="label-text font-semibold opacity-70">Equipos Críticos</span></div>
                        <textarea class="textarea textarea-bordered textarea-sm bg-base-100" bind:value={fEquipos} rows="2" placeholder="ej: Core switch principal..."></textarea>
                    </label>
                    <label class="form-control">
                        <div class="label"><span class="label-text font-semibold opacity-70">Próximo Mantenimiento</span></div>
                        <input class="input input-bordered input-sm bg-base-100" type="date" bind:value={fMantenimiento} />
                    </label>
                </div>

                <div style="text-align:right;">
                    <button type="submit" class="btn btn-primary btn-sm px-6" disabled={saving}>Guardar</button>
                </div>
            </form>

        {:else if zona.infraestructura}
            <!-- MODO LECTURA -->
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1.5rem;">
                <h3 style="margin:0;font-size:1.1rem;font-weight:700;opacity:0.9;">🔌 Datos de Red Manuales</h3>
                {#if canEdit}
                    <button type="button" class="btn btn-xs btn-outline btn-primary" onclick={() => (isEditing = true)}>✏️ Editar</button>
                {/if}
            </div>

            {@const infra = zona.infraestructura}
            <table style="width:100%;border-collapse:collapse;">
                <tbody>
                    {#each [
                        { label: "IP Gestión", value: fmt(infra.direccion_ip_gestion), mono: true },
                        { label: "Gateway", value: fmt(infra.gateway_predeterminado), mono: true },
                        { label: "Servidores DNS", value: fmt(infra.servidores_dns), mono: false },
                        { label: "VLANs Utilizadas", value: fmt(infra.vlans_utilizadas), mono: true },
                        { label: "Equipos Críticos", value: fmt(infra.equipos_criticos), mono: false },
                        { label: "Próx. Mantenimiento", value: fmtDate(infra.proximo_mantenimiento), mono: false },
                    ] as row}
                        <tr style="border-bottom:1px solid oklch(from var(--color-base-content) l c h / 0.07);">
                            <td style="padding:0.75rem 1rem 0.75rem 0;font-size:0.78rem;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;opacity:0.4;width:13rem;vertical-align:top;">{row.label}</td>
                            <td style="padding:0.75rem 0;font-size:0.9rem;font-family:{row.mono ? 'monospace' : 'inherit'};">{row.value}</td>
                        </tr>
                    {/each}
                </tbody>
            </table>

        {:else}
            <!-- MODO VACÍO -->
            <div style="text-align:center;padding:2.5rem;opacity:0.5;">
                <p style="font-size:2rem;margin:0 0 0.5rem;">🔌</p>
                <p style="margin:0;font-size:0.9rem;">Sin datos de infraestructura configurados.</p>
                {#if canEdit}
                    <button class="btn btn-sm btn-outline mt-4" onclick={() => (isEditing = true)}>Configurar infraestructura</button>
                {/if}
            </div>
        {/if}
    </div>

    <!-- ── BLOQUE B: AUTODOCUMENTACIÓN Y PUERTOS MIKROTIK ───────────────────── -->
    <div class="glass-card-flat" style="border-radius:1rem;padding:1.5rem;">
        <div class="flex items-center justify-between mb-4 flex-wrap gap-2">
            <div>
                <h3 class="margin:0 font-bold text-lg flex items-center gap-2">
                    🖥️ Autodocumentación y Puertos Físicos
                </h3>
                {#if autodoc?.last_updated}
                    <p class="text-xs opacity-50 mt-1">Última sinc: {new Date(autodoc.last_updated).toLocaleString()}</p>
                {/if}
            </div>
            {#if canEdit}
                <button 
                    type="button" 
                    class="btn btn-xs btn-primary btn-outline" 
                    disabled={isSyncing || loadingAutodoc} 
                    onclick={handleSync}
                >
                    {#if isSyncing}
                        <span class="loading loading-spinner loading-xs"></span> Sincronizando...
                    {:else}
                        🔄 Sincronizar Red
                    {/if}
                </button>
            {/if}
        </div>

        {#if loadingAutodoc}
            <!-- Skeleton de Carga -->
            <div class="flex flex-col gap-4 py-6">
                <div class="h-8 bg-base-content/5 rounded w-1/4 animate-pulse"></div>
                <div class="grid grid-cols-4 sm:grid-cols-8 gap-3">
                    {#each Array(8) as _}
                        <div class="h-16 bg-base-content/5 rounded-lg animate-pulse"></div>
                    {/each}
                </div>
            </div>

        {:else if autodocError && !autodoc}
            <!-- Estado sin Sincronización -->
            <div class="text-center py-8 opacity-75">
                <p class="text-3xl mb-2">⚡</p>
                <p class="text-sm font-semibold mb-1">Estructura física no mapeada aún</p>
                <p class="text-xs opacity-65 max-w-md mx-auto mb-4">
                    La ficha técnica y la cuadrícula física de puertos para los routers/switches MikroTik de esta zona no se han consolidado.
                </p>
                {#if canEdit}
                    <button class="btn btn-sm btn-primary" disabled={isSyncing} onclick={handleSync}>
                        {#if isSyncing}
                            <span class="loading loading-spinner loading-xs"></span> Generando...
                        {:else}
                            🚀 Mapear Estructura Ahora
                        {/if}
                    </button>
                {/if}
            </div>

        {:else if autodoc}
            <!-- Selector de Vistas -->
            <div class="tabs tabs-boxed mb-4 w-fit bg-base-200/50">
                <button 
                    class="tab tab-sm {subTab === 'ports' ? 'tab-active font-semibold' : ''}" 
                    onclick={() => subTab = 'ports'}
                >
                    🔌 Vista de Puertos
                </button>
                <button 
                    class="tab tab-sm {subTab === 'markdown' ? 'tab-active font-semibold' : ''}" 
                    onclick={() => subTab = 'markdown'}
                >
                    📄 Ficha Técnica (Markdown)
                </button>
            </div>

            {#if subTab === "ports"}
                <!-- VISTA A: CUADRÍCULA DE PUERTOS FÍSICOS -->
                <div class="flex flex-col gap-6">
                    {#each autodoc.ports as dev}
                        <div class="border border-base-content/10 bg-base-200/20 p-4 rounded-xl shadow-inner">
                            <!-- Cabecera del Dispositivo -->
                            <div class="flex items-center justify-between flex-wrap gap-2 mb-4 border-b border-base-content/5 pb-2">
                                <div class="flex items-center gap-2">
                                    <span class="badge badge-sm uppercase font-mono tracking-wider {dev.type === 'router' ? 'badge-primary' : 'badge-secondary'}">{dev.type}</span>
                                    <h4 class="font-extrabold text-sm text-base-content/95">{dev.hostname}</h4>
                                    <span class="text-xs opacity-50 font-mono">({dev.host})</span>
                                </div>
                                <div class="flex items-center gap-2 flex-wrap">
                                    <span class="badge badge-outline badge-xs text-xs font-mono">{dev.model}</span>
                                    {#if dev.status === "online"}
                                        <span class="badge badge-success badge-xs font-semibold">ONLINE</span>
                                    {:else}
                                        <span class="badge badge-error badge-xs font-semibold">OFFLINE</span>
                                    {/if}
                                    {#if dev.cpu_load && dev.cpu_load !== "N/A"}
                                        <span class="badge badge-ghost badge-xs font-mono">CPU: {dev.cpu_load}%</span>
                                    {/if}
                                    {#if dev.temperature}
                                        <span class="badge badge-ghost badge-xs font-mono">Temp: {dev.temperature}°C</span>
                                    {/if}
                                    {#if dev.voltage}
                                        <span class="badge badge-ghost badge-xs font-mono">{dev.voltage}V</span>
                                    {/if}
                                </div>
                            </div>

                            <!-- Grilla de Jacks -->
                            {#if dev.ports && dev.ports.length > 0}
                                <div class="flex flex-wrap gap-3 justify-center sm:justify-start bg-base-100/50 p-4 rounded-lg border border-base-content/5">
                                    {#each dev.ports as port}
                                        <div class="tooltip tooltip-bottom cursor-help" data-tip={getTooltipText(port)}>
                                            <div class="flex flex-col items-center justify-center p-3 border-2 rounded-lg w-16 h-16 transition-all duration-200 {getPortClass(port)}">
                                                <span class="font-bold text-[10px] tracking-wide uppercase">{port.name}</span>
                                                
                                                {#if port.running && !port.disabled}
                                                    <span class="text-[8px] opacity-75 font-mono">{port.speed || '1G'}</span>
                                                {:else if port.disabled}
                                                    <span class="text-[8px] opacity-60">OFF</span>
                                                {:else}
                                                    <span class="text-[8px] opacity-55">DOWN</span>
                                                {/if}
                                                
                                                {#if port.poe && port.poe !== "off" && port.running}
                                                    <span class="text-[8px] text-amber-500 font-extrabold mt-0.5" title="PoE Out Activo">⚡</span>
                                                {/if}
                                            </div>
                                        </div>
                                    {/each}
                                </div>
                            {:else}
                                <div class="text-center py-6 opacity-60 text-xs">
                                    ⚠️ No se pudo obtener la estructura de interfaces físicas de este equipo.
                                </div>
                            {/if}
                        </div>
                    {/each}
                </div>

            {:else}
                <!-- VISTA B: FICHA TÉCNICA EN MARKDOWN -->
                <div class="prose max-w-none bg-base-100/60 p-6 rounded-lg border border-base-content/5 overflow-auto max-h-[550px] text-base-content/90 leading-relaxed font-sans">
                    {@html parsedMarkdown}
                </div>
            {/if}
        {/if}
    </div>
</div>

<style>
    /* Estilos personalizados para que el Markdown luzca extremadamente premium y encaje con OmniWISP */
    :global(.prose h1) {
        font-size: 1.5rem !important;
        font-weight: 800 !important;
        margin-top: 1.5rem !important;
        margin-bottom: 0.75rem !important;
        color: var(--color-base-content) !important;
    }
    :global(.prose h2) {
        font-size: 1.25rem !important;
        font-weight: 700 !important;
        margin-top: 1.5rem !important;
        margin-bottom: 0.5rem !important;
        color: var(--color-base-content) !important;
        border-bottom: 1px solid oklch(from var(--color-base-content) l c h / 0.15);
        padding-bottom: 0.25rem;
    }
    :global(.prose h3) {
        font-size: 1.1rem !important;
        font-weight: 700 !important;
        margin-top: 1.25rem !important;
        margin-bottom: 0.5rem !important;
        color: var(--color-base-content) !important;
    }
    :global(.prose table) {
        width: 100% !important;
        margin: 1rem 0 !important;
        border-collapse: collapse !important;
        font-size: 0.85rem !important;
    }
    :global(.prose th) {
        background: oklch(from var(--color-base-content) l c h / 0.05) !important;
        font-weight: 700 !important;
        padding: 0.5rem 0.75rem !important;
        border-bottom: 2px solid oklch(from var(--color-base-content) l c h / 0.15) !important;
        text-align: left !important;
    }
    :global(.prose td) {
        padding: 0.5rem 0.75rem !important;
        border-bottom: 1px solid oklch(from var(--color-base-content) l c h / 0.08) !important;
    }
    :global(.prose ul) {
        list-style-type: disc !important;
        padding-left: 1.5rem !important;
        margin: 0.75rem 0 !important;
    }
    :global(.prose li) {
        margin-bottom: 0.25rem !important;
    }
</style>

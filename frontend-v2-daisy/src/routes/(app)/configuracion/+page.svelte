<script lang="ts">
    import { onMount } from "svelte";
    import { theme } from "$lib/stores/theme";
    import {
        getSettings,
        updateSettings,
        getSystemServicesStatus,
        getSystemServices,
        updateSystemServices,
        testServiceConnection,
        getAuditLogs,
        getAuditLogFilters,
        forceBilling,
        backupNow,
        restartBots,
        type AuditLog,
    } from "$lib/api";
    import { notify } from "$lib/stores/notifications";

    // ─── Estado de tabs ────────────────────────────────────────────────
    let activeTab = $state<
        "general" | "auditoria" | "bots" | "apariencia" | "infraestructura" | "videollamadas"
    >("general");


    // ═══════════════════════════════════════════════════════════════════
    // TAB 1: GENERAL
    // ═══════════════════════════════════════════════════════════════════
    let generalSettings = $state<Record<string, string>>({});
    let generalLoading = $state(true);
    let generalSaving = $state(false);

    async function loadGeneralSettings() {
        try {
            generalSettings = await getSettings();
        } catch {
            notify.error("Error al cargar configuración");
        } finally {
            generalLoading = false;
        }
    }

    function getS(key: string) {
        return generalSettings[key] ?? "";
    }
    function setS(key: string, val: string) {
        generalSettings = { ...generalSettings, [key]: val };
    }

    async function saveGeneralSettings() {
        generalSaving = true;
        try {
            await updateSettings(generalSettings);
            notify.success("Configuración guardada correctamente");
        } catch {
            notify.error("Error al guardar configuración");
        } finally {
            generalSaving = false;
        }
    }

    async function onForceBilling() {
        try {
            const res = await forceBilling();
            notify.success(res.message);
        } catch {
            notify.error("Error al forzar actualización");
        }
    }

    async function onBackupNow() {
        try {
            await backupNow();
            notify.success("Backup completado");
        } catch {
            notify.error("Error al realizar backup");
        }
    }

    // ═══════════════════════════════════════════════════════════════════
    // TAB 2: AUDITORÍA
    // ═══════════════════════════════════════════════════════════════════
    let auditLogs = $state<AuditLog[]>([]);
    let auditTotal = $state(0);
    let auditPage = $state(1);
    let auditPageSize = $state(20);
    let auditTotalPages = $state(1);
    let auditLoading = $state(false);
    let auditFilters = $state<{ actions: string[]; usernames: string[] }>({
        actions: [],
        usernames: [],
    });
    let auditActionFilter = $state("all");
    let auditUserFilter = $state("all");

    async function loadAuditLogs() {
        auditLoading = true;
        try {
            const action =
                auditActionFilter !== "all" ? auditActionFilter : undefined;
            const username =
                auditUserFilter !== "all" ? auditUserFilter : undefined;
            const res = await getAuditLogs(
                auditPage,
                auditPageSize,
                action,
                username,
            );
            auditLogs = res.items;
            auditTotal = res.total;
            auditTotalPages = res.total_pages;
        } catch {
            notify.error("Error al cargar logs de auditoría");
        } finally {
            auditLoading = false;
        }
    }

    async function loadAuditFilters() {
        try {
            auditFilters = await getAuditLogFilters();
        } catch {}
    }

    function fmtDate(ts: string) {
        const d = new Date(ts);
        return d.toLocaleDateString("es-MX", {
            day: "2-digit",
            month: "2-digit",
            year: "2-digit",
        });
    }
    function fmtTime(ts: string) {
        const d = new Date(ts);
        return d.toLocaleTimeString("es-MX", {
            hour: "2-digit",
            minute: "2-digit",
        });
    }
    function actionBadge(action: string) {
        if (["DELETE", "BACKUP", "REPAIR"].includes(action))
            return "badge-error";
        if (["CREATE", "PROVISION"].includes(action)) return "badge-success";
        if (["UPDATE", "LOGIN"].includes(action)) return "badge-info";
        return "badge-ghost";
    }

    // ═══════════════════════════════════════════════════════════════════
    // TAB 3: BOTS
    // ═══════════════════════════════════════════════════════════════════
    let botSaving = $state(false);
    let botRestarting = $state(false);

    async function saveBotSettings() {
        botSaving = true;
        try {
            await updateSettings(generalSettings);
            notify.success("Configuración de bots guardada");
        } catch {
            notify.error("Error al guardar bots");
        } finally {
            botSaving = false;
        }
    }

    async function onRestartBots() {
        botRestarting = true;
        try {
            await updateSettings(generalSettings);
            const res = await restartBots();
            notify.success(res.message);
        } catch {
            notify.error("Error al reiniciar bots");
        } finally {
            botRestarting = false;
        }
    }

    // ═══════════════════════════════════════════════════════════════════
    // TAB 4: SISTEMA (Infraestructura)
    // ═══════════════════════════════════════════════════════════════════
    let sysConfig = $state<any>({
        db_provider: "sqlite",
        postgres_host: "",
        postgres_port: 5432,
        postgres_db: "umanager",
        postgres_user: "postgres",
        postgres_password: "",
        cache_provider: "memory",
        redict_password: "",
        redict_db: 0,
        livekit_url: "ws://localhost:7880",
        livekit_api_key: "",
        livekit_api_secret: ""
    });
    let sysStatus = $state<any>(null);
    let sysLoading = $state(true);
    let sysSaving = $state(false);

    let dbTesting = $state(false);
    let cacheTesting = $state(false);

    async function loadSystemSettings() {
        try {
            sysStatus = await getSystemServicesStatus();
            sysConfig.db_provider = sysStatus.db?.backend || 'sqlite';
            sysConfig.cache_provider = sysStatus.cache?.backend || 'memory';

            const srv = await getSystemServices();
            if (srv.db) {
                if (srv.db.provider) sysConfig.db_provider = srv.db.provider;
                if (srv.db.host) sysConfig.postgres_host = srv.db.host;
                if (srv.db.port) sysConfig.postgres_port = srv.db.port;
                if (srv.db.database) sysConfig.postgres_db = srv.db.database;
                if (srv.db.user) sysConfig.postgres_user = srv.db.user;
                if (srv.db.password) sysConfig.postgres_password = srv.db.password;
            }
            if (srv.cache) {
                if (srv.cache.provider) sysConfig.cache_provider = srv.cache.provider;
                if (srv.cache.host) sysConfig.redict_host = srv.cache.host;
                if (srv.cache.port) sysConfig.redict_port = srv.cache.port;
                if (srv.cache.db !== undefined) sysConfig.redict_db = srv.cache.db;
                if (srv.cache.password) sysConfig.redict_password = srv.cache.password;
            }
            if (srv.livekit) {
                if (srv.livekit.url) sysConfig.livekit_url = srv.livekit.url;
                if (srv.livekit.api_key) sysConfig.livekit_api_key = srv.livekit.api_key;
                if (srv.livekit.api_secret) sysConfig.livekit_api_secret = srv.livekit.api_secret;
            }
        } catch {
            notify.error("Error al cargar config del sistema");
        } finally {
            sysLoading = false;
        }
    }

    async function saveSystemSettings() {
        sysSaving = true;
        try {
            const data = {
                db: sysConfig.db_provider === 'sqlite' ? { provider: 'sqlite' } : {
                    provider: 'postgres',
                    host: sysConfig.postgres_host,
                    port: sysConfig.postgres_port,
                    user: sysConfig.postgres_user,
                    password: sysConfig.postgres_password,
                    database: sysConfig.postgres_db
                },
                cache: sysConfig.cache_provider === 'memory' ? { provider: 'memory' } : {
                    provider: 'redict',
                    host: sysConfig.redict_host,
                    port: sysConfig.redict_port,
                    db: sysConfig.redict_db,
                    password: sysConfig.redict_password
                },
                livekit: {
                    url: sysConfig.livekit_url,
                    api_key: sysConfig.livekit_api_key,
                    api_secret: sysConfig.livekit_api_secret
                }
            };
            const res = await updateSystemServices(data);
            notify.success(res.message);
            await loadInfraStatus(); // Refresh both UI statuses
            await loadSystemSettings();
        } catch(e: any) {
            notify.error("Error al guardar config del sistema: " + (e?.response?.data?.detail || e.message));
        } finally {
            sysSaving = false;
        }
    }

    async function testDbConnection() {
        dbTesting = true;
        try {
            const data: any = { provider: sysConfig.db_provider };
            if (data.provider === 'postgres') {
                data.host = sysConfig.postgres_host;
                data.port = sysConfig.postgres_port;
                data.user = sysConfig.postgres_user;
                data.password = sysConfig.postgres_password;
                data.database = sysConfig.postgres_db;
            }
            const res = await testServiceConnection(data);
            if (res.ok) notify.success(`✅ Conexión OK (${res.latency_ms}ms)`);
            else notify.error(`❌ Fallo: ${res.error}`);
        } catch (e: any) {
            notify.error("Error en test de BD");
        } finally {
            dbTesting = false;
        }
    }

    async function testCacheConnection() {
        cacheTesting = true;
        try {
            const data: any = { provider: sysConfig.cache_provider };
            if (data.provider === 'redict') {
                data.host = sysConfig.redict_host;
                data.port = sysConfig.redict_port;
                data.db = sysConfig.redict_db;
                data.password = sysConfig.redict_password;
            }
            const res = await testServiceConnection(data);
            if (res.ok) notify.success(`✅ Conexión OK (${res.latency_ms}ms)`);
            else notify.error(`❌ Fallo: ${res.error}`);
        } catch (e: any) {
            notify.error("Error en test de Caché");
        } finally {
            cacheTesting = false;
        }
    }

    // ═══════════════════════════════════════════════════════════════════
    // TAB 5: APARIENCIA
    // ═══════════════════════════════════════════════════════════════════
    const availableThemes = [
        { id: "light", label: "Claro", desc: "Modo claro estándar" },
        { id: "dark", label: "Oscuro", desc: "Modo oscuro clásico" },
        { id: "corporate", label: "Corporate", desc: "Claro profesional" },
        { id: "dracula", label: "Dracula", desc: "Púrpura y rosa" },
        { id: "cyberpunk", label: "Cyberpunk", desc: "Amarillo neón" },
        { id: "dim", label: "Dim", desc: "Oscuro suave" },
        { id: "synthwave", label: "Synthwave", desc: "Retro neón 80s" },
        { id: "night", label: "Noche", desc: "Azul oscuro profundo" },
        { id: "forest", label: "Forest", desc: "Oscuro y ecológico" },
        { id: "garden", label: "Garden", desc: "Claro y floral" },
        { id: "business", label: "Business", desc: "Oscuro y elegante" },
    ];

    function setTheme(themeId: any) {
        theme.setTheme(themeId);
    }

    function toggleLavaLamp() {
        theme.setLavaLamp(!$theme.lavaLampActive);
    }

    // ═══════════════════════════════════════════════════════════════════
    // TAB 6: INFRAESTRUCTURA (DOCKER)
    // ═══════════════════════════════════════════════════════════════════
    import { getInfraStatus, deployInfraStack, type InfraStatusResponse, type DeployActions, type DeployResult } from "$lib/api/infra";

    let infraStatus = $state<InfraStatusResponse | null>(null);
    let infraLoading = $state(true);
    let infraDeploying = $state(false);
    let infraDeployResult = $state<DeployResult | null>(null);

    let infraDeployActions = $state<DeployActions>({ postgres: 'create', redict: 'create' });
    let lastGeneratedPostgresPassword = $state("");

    async function loadInfraStatus() {
        infraLoading = true;
        try {
            infraStatus = await getInfraStatus();
            // Auto-seleccionar "reuse" si hay conflicto detectado
            if (infraStatus?.services?.postgres?.conflict) {
                infraDeployActions.postgres = 'reuse';
            }
            if (infraStatus?.services?.redict?.conflict) {
                infraDeployActions.redict = 'reuse';
            }
        } catch {
            notify.error("No se pudo cargar el estado de la infraestructura.");
        } finally {
            infraLoading = false;
        }
    }

    // Funciones de autocompletado
    function fillPostgresLocal() {
        if (!infraStatus?.services?.postgres || infraStatus.services.postgres.omniwisp_container !== 'running') {
            notify.warning("El contenedor local no está corriendo.");
            return;
        }
        sysConfig.postgres_host = 'localhost';
        sysConfig.postgres_port = infraStatus.services.postgres.port;
        // El backend nos da la sugerencia en infraStatus si ya está corriendo o en el deploy result
        const suggested = infraStatus.services.postgres.suggested || {};
        sysConfig.postgres_user = suggested.user || 'umanager';
        sysConfig.postgres_db = suggested.db || 'umanager_db';
        if (suggested.password) {
            sysConfig.postgres_password = suggested.password;
        } else if (lastGeneratedPostgresPassword) {
            sysConfig.postgres_password = lastGeneratedPostgresPassword;
        }
        notify.info("Datos de Postgres local cargados.");
    }

    function fillRedictLocal() {
        if (!infraStatus?.services?.redict || infraStatus.services.redict.omniwisp_container !== 'running') {
            notify.warning("El servicio local no está activo.");
            return;
        }
        sysConfig.redict_host = 'localhost';
        sysConfig.redict_port = infraStatus.services.redict.port;
        sysConfig.redict_db = 0;
        notify.info("Datos de Redict local cargados.");
    }

    async function onDeployInfra() {
        infraDeploying = true;
        infraDeployResult = null;
        try {
            const res = await deployInfraStack({
                actions: infraDeployActions,
            });
            infraDeployResult = res;
            notify.success(res.message || "Acciones completadas.");
            
            // Si el despliegue devolvió una contraseña, sugerirla para el formulario
            if (res.postgres_password) {
                lastGeneratedPostgresPassword = res.postgres_password;
                sysConfig.postgres_password = res.postgres_password;
                notify.info("Se ha sugerido la contraseña generada en el formulario.");
            }

            await loadInfraStatus();
        } catch (err: any) {
            notify.error("Falló el despliegue: " + (err?.response?.data?.detail || err.message || "Error desconocido"));
        } finally {
            infraDeploying = false;
        }
    }


    // ═══════════════════════════════════════════════════════════════════
    // INIT
    // ═══════════════════════════════════════════════════════════════════
    onMount(async () => {
        await Promise.all([loadGeneralSettings(), loadSystemSettings()]);
    });

    // Cargar audit logs / infra logs solo cuando se active esa tab
    $effect(() => {
        if (activeTab === "auditoria") {
            loadAuditFilters();
            loadAuditLogs();
        } else if (activeTab === "infraestructura") {
            loadInfraStatus();
        }
    });
</script>

<svelte:head>
    <title>Configuración Global — OmniWISP</title>
</svelte:head>


<!-- ── HEADER ─────────────────────────────────────────────────────────── -->
<div
    class="glass-card-flat mb-6"
    style="border-radius:1rem;display:flex;flex-direction:column;overflow:hidden;"
>
    <!-- Título y descripción -->
    <div
        style="padding:1.25rem 1.5rem;display:flex;flex-direction:column;gap:0.75rem;"
    >
        <div
            style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:0.75rem;"
        >
            <div>
                <h1 style="margin:0;font-size:1.5rem;font-weight:800;">
                    Configuración Global
                </h1>
                <p style="margin:0.25rem 0 0;font-size:0.85rem;opacity:0.5;">
                    Ajustes del sistema, facturación, bots e infraestructura.
                </p>
            </div>
        </div>
    </div>

    <!-- Pestañas de Navegación integradas al header -->
    <div
        style="background:oklch(from var(--color-base-content) l c h / 0.02);border-top:1px solid oklch(from var(--color-base-content) l c h / 0.08);padding:0 1.5rem;display:flex;gap:1.5rem;"
        role="tablist"
    >
        <button
            role="tab"
            aria-selected={activeTab === "general"}
            onclick={() => (activeTab = "general")}
            style="padding:0.85rem 0;font-size:0.85rem;font-weight:{activeTab ===
            'general'
                ? '800'
                : '600'};color:{activeTab === 'general'
                ? 'oklch(from var(--color-primary) l c h)'
                : 'inherit'};opacity:{activeTab === 'general'
                ? '1'
                : '0.5'};border-bottom:3px solid {activeTab === 'general'
                ? 'oklch(from var(--color-primary) l c h)'
                : 'transparent'};background:none;cursor:pointer;transition:all 0.2s;"
        >
            ⚙️ General
        </button>
        <button
            role="tab"
            aria-selected={activeTab === "auditoria"}
            onclick={() => (activeTab = "auditoria")}
            style="padding:0.85rem 0;font-size:0.85rem;font-weight:{activeTab ===
            'auditoria'
                ? '800'
                : '600'};color:{activeTab === 'auditoria'
                ? 'oklch(from var(--color-primary) l c h)'
                : 'inherit'};opacity:{activeTab === 'auditoria'
                ? '1'
                : '0.5'};border-bottom:3px solid {activeTab === 'auditoria'
                ? 'oklch(from var(--color-primary) l c h)'
                : 'transparent'};background:none;cursor:pointer;transition:all 0.2s;"
        >
            🛡️ Auditoría
        </button>
        <button
            role="tab"
            aria-selected={activeTab === "bots"}
            onclick={() => (activeTab = "bots")}
            style="padding:0.85rem 0;font-size:0.85rem;font-weight:{activeTab ===
            'bots'
                ? '800'
                : '600'};color:{activeTab === 'bots'
                ? 'oklch(from var(--color-primary) l c h)'
                : 'inherit'};opacity:{activeTab === 'bots'
                ? '1'
                : '0.5'};border-bottom:3px solid {activeTab === 'bots'
                ? 'oklch(from var(--color-primary) l c h)'
                : 'transparent'};background:none;cursor:pointer;transition:all 0.2s;"
        >
            🤖 Bots
        </button>
        <button
            role="tab"
            aria-selected={activeTab === "apariencia"}
            onclick={() => (activeTab = "apariencia")}
            style="padding:0.85rem 0;font-size:0.85rem;font-weight:{activeTab ===
            'apariencia'
                ? '800'
                : '600'};color:{activeTab === 'apariencia'
                ? 'oklch(from var(--color-primary) l c h)'
                : 'inherit'};opacity:{activeTab === 'apariencia'
                ? '1'
                : '0.5'};border-bottom:3px solid {activeTab === 'apariencia'
                ? 'oklch(from var(--color-primary) l c h)'
                : 'transparent'};background:none;cursor:pointer;transition:all 0.2s;"
        >
            🎨 Apariencia
        </button>
        <button
            role="tab"
            aria-selected={activeTab === "infraestructura"}
            onclick={() => (activeTab = "infraestructura")}
            style="padding:0.85rem 0;font-size:0.85rem;font-weight:{activeTab ===
            'infraestructura'
                ? '800'
                : '600'};color:{activeTab === 'infraestructura'
                ? 'oklch(from var(--color-primary) l c h)'
                : 'inherit'};opacity:{activeTab === 'infraestructura'
                ? '1'
                : '0.5'};border-bottom:3px solid {activeTab === 'infraestructura'
                ? 'oklch(from var(--color-primary) l c h)'
                : 'transparent'};background:none;cursor:pointer;transition:all 0.2s;"
        >
            ⛴️ Infraestructura
        </button>
        <button
            role="tab"
            aria-selected={activeTab === "videollamadas"}
            onclick={() => (activeTab = "videollamadas")}
            style="padding:0.85rem 0;font-size:0.85rem;font-weight:{activeTab ===
            'videollamadas'
                ? '800'
                : '600'};color:{activeTab === 'videollamadas'
                ? 'oklch(from var(--color-primary) l c h)'
                : 'inherit'};opacity:{activeTab === 'videollamadas'
                ? '1'
                : '0.5'};border-bottom:3px solid {activeTab === 'videollamadas'
                ? 'oklch(from var(--color-primary) l c h)'
                : 'transparent'};background:none;cursor:pointer;transition:all 0.2s;"
        >
            🎥 Videollamadas
        </button>
    </div>
</div>

<!-- ══════════════════ TAB 1: GENERAL ══════════════════ -->
{#if activeTab === "general"}
    {#if generalLoading}
        <div class="flex justify-center py-16">
            <span class="loading loading-spinner loading-lg"></span>
        </div>
    {:else}
        <div class="card bg-base-100 shadow-xl border border-base-200">
            <div class="card-body space-y-8">
                <!-- INFORMACIÓN DE LA ISP -->
                <section>
                    <h2 class="text-lg font-semibold mb-1">
                        Información General
                    </h2>
                    <p class="text-sm text-base-content/60 mb-4">
                        Datos básicos de tu organización.
                    </p>
                    <div
                        class="grid grid-cols-1 md:grid-cols-2 gap-4 divider-y pt-2"
                    >
                        <div class="form-control">
                            <label class="label" for="company_name"
                                ><span class="label-text"
                                    >Nombre de Empresa</span
                                ></label
                            >
                            <input
                                id="company_name"
                                type="text"
                                class="input input-bordered"
                                placeholder="Mi ISP S.A."
                                value={getS("company_name")}
                                oninput={(e) =>
                                    setS(
                                        "company_name",
                                        (e.target as HTMLInputElement).value,
                                    )}
                            />
                        </div>
                        <div class="form-control">
                            <label class="label" for="notification_email"
                                ><span class="label-text">Email Admin</span
                                ></label
                            >
                            <input
                                id="notification_email"
                                type="email"
                                class="input input-bordered"
                                placeholder="admin@example.com"
                                value={getS("notification_email")}
                                oninput={(e) =>
                                    setS(
                                        "notification_email",
                                        (e.target as HTMLInputElement).value,
                                    )}
                            />
                        </div>
                        <div class="form-control">
                            <label class="label" for="currency_symbol"
                                ><span class="label-text"
                                    >Símbolo de Moneda</span
                                ></label
                            >
                            <input
                                id="currency_symbol"
                                type="text"
                                class="input input-bordered w-24"
                                placeholder="$"
                                value={getS("currency_symbol")}
                                oninput={(e) =>
                                    setS(
                                        "currency_symbol",
                                        (e.target as HTMLInputElement).value,
                                    )}
                            />
                        </div>
                    </div>
                </section>

                <div class="divider"></div>

                <!-- PERSONALIZACIÓN DE TICKETS -->
                <section>
                    <h2 class="text-lg font-semibold mb-1">
                        Personalización de Tickets
                    </h2>
                    <p class="text-sm text-base-content/60 mb-4">
                        Logo y textos para documentos y facturas.
                    </p>
                    <div class="grid grid-cols-1 gap-4">
                        <div class="form-control">
                            <label class="label" for="company_logo_url"
                                ><span class="label-text">URL del Logo</span
                                ></label
                            >
                            <input
                                id="company_logo_url"
                                type="text"
                                class="input input-bordered"
                                placeholder="/static/logo.png o https://..."
                                value={getS("company_logo_url")}
                                oninput={(e) =>
                                    setS(
                                        "company_logo_url",
                                        (e.target as HTMLInputElement).value,
                                    )}
                            />
                        </div>
                        <div class="form-control">
                            <label class="label" for="billing_address"
                                ><span class="label-text">Dirección Fiscal</span
                                ></label
                            >
                            <textarea
                                id="billing_address"
                                class="textarea textarea-bordered"
                                rows="2"
                                value={getS("billing_address")}
                                oninput={(e) =>
                                    setS(
                                        "billing_address",
                                        (e.target as HTMLTextAreaElement).value,
                                    )}
                            ></textarea>
                        </div>
                        <div class="form-control">
                            <label class="label" for="ticket_footer_message"
                                ><span class="label-text"
                                    >Mensaje al Pie del Ticket</span
                                ></label
                            >
                            <textarea
                                id="ticket_footer_message"
                                class="textarea textarea-bordered"
                                rows="3"
                                placeholder="Gracias por su preferencia..."
                                value={getS("ticket_footer_message")}
                                oninput={(e) =>
                                    setS(
                                        "ticket_footer_message",
                                        (e.target as HTMLTextAreaElement).value,
                                    )}
                            ></textarea>
                        </div>
                    </div>
                </section>

                <div class="divider"></div>

                <!-- MONITOREO Y BACKUPS -->
                <section>
                    <h2 class="text-lg font-semibold mb-1">
                        Monitoreo y Backups
                    </h2>
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
                        <div class="form-control">
                            <label class="label" for="default_monitor_interval"
                                ><span class="label-text"
                                    >Intervalo Monitor (seg)</span
                                ></label
                            >
                            <input
                                id="default_monitor_interval"
                                type="number"
                                class="input input-bordered"
                                value={getS("default_monitor_interval")}
                                oninput={(e) =>
                                    setS(
                                        "default_monitor_interval",
                                        (e.target as HTMLInputElement).value,
                                    )}
                            />
                        </div>
                        <div class="form-control">
                            <label
                                class="label"
                                for="dashboard_refresh_interval"
                                ><span class="label-text"
                                    >Intervalo Live (seg)</span
                                ></label
                            >
                            <input
                                id="dashboard_refresh_interval"
                                type="number"
                                class="input input-bordered"
                                value={getS("dashboard_refresh_interval")}
                                oninput={(e) =>
                                    setS(
                                        "dashboard_refresh_interval",
                                        (e.target as HTMLInputElement).value,
                                    )}
                            />
                        </div>
                        <div class="form-control">
                            <label class="label" for="monitor_max_workers"
                                ><span class="label-text"
                                    >Concurrencia de Monitor</span
                                ></label
                            >
                            <input
                                id="monitor_max_workers"
                                type="number"
                                min="1"
                                max="50"
                                class="input input-bordered"
                                placeholder="10"
                                value={getS("monitor_max_workers")}
                                oninput={(e) =>
                                    setS(
                                        "monitor_max_workers",
                                        (e.target as HTMLInputElement).value,
                                    )}
                            />
                        </div>
                        <div class="form-control">
                            <label class="label" for="backup_frequency"
                                ><span class="label-text"
                                    >Backup de Routers</span
                                ></label
                            >
                            <select
                                id="backup_frequency"
                                class="select select-bordered"
                                value={getS("backup_frequency")}
                                onchange={(e) =>
                                    setS(
                                        "backup_frequency",
                                        (e.target as HTMLSelectElement).value,
                                    )}
                            >
                                <option value="daily">Diario</option>
                                <option value="weekly">Semanal</option>
                            </select>
                        </div>
                        <div class="form-control">
                            <label class="label" for="backup_run_hour"
                                ><span class="label-text"
                                    >Hora de Backup (Routers)</span
                                ></label
                            >
                            <input
                                id="backup_run_hour"
                                type="time"
                                class="input input-bordered"
                                value={getS("backup_run_hour")}
                                oninput={(e) =>
                                    setS(
                                        "backup_run_hour",
                                        (e.target as HTMLInputElement).value,
                                    )}
                            />
                        </div>
                        <div class="form-control">
                            <label class="label" for="db_backup_run_hour"
                                ><span class="label-text"
                                    >Hora de Backup (BD)</span
                                ></label
                            >
                            <input
                                id="db_backup_run_hour"
                                type="time"
                                class="input input-bordered"
                                value={getS("db_backup_run_hour")}
                                oninput={(e) =>
                                    setS(
                                        "db_backup_run_hour",
                                        (e.target as HTMLInputElement).value,
                                    )}
                            />
                        </div>
                    </div>
                </section>

                <div class="divider"></div>

                <!-- SEÑAL CPE -->
                <section>
                    <h2 class="text-lg font-semibold mb-4">
                        Umbrales de Señal CPE
                    </h2>
                    <p class="text-sm text-base-content/60 mb-4">
                        Configura los valores para determinar la calidad de
                        señal de los CPEs.
                    </p>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div class="form-control">
                            <label
                                class="label"
                                for="cpe_signal_warning_threshold"
                                ><span class="label-text"
                                    >Baja / Advertencia (dBm)</span
                                ></label
                            >
                            <input
                                id="cpe_signal_warning_threshold"
                                type="number"
                                class="input input-bordered"
                                placeholder="-62"
                                value={getS("cpe_signal_warning_threshold")}
                                oninput={(e) =>
                                    setS(
                                        "cpe_signal_warning_threshold",
                                        (e.target as HTMLInputElement).value,
                                    )}
                            />
                        </div>
                        <div class="form-control">
                            <label
                                class="label"
                                for="cpe_signal_danger_threshold"
                                ><span class="label-text"
                                    >Mala / Peligro (dBm)</span
                                ></label
                            >
                            <input
                                id="cpe_signal_danger_threshold"
                                type="number"
                                class="input input-bordered"
                                placeholder="-71"
                                value={getS("cpe_signal_danger_threshold")}
                                oninput={(e) =>
                                    setS(
                                        "cpe_signal_danger_threshold",
                                        (e.target as HTMLInputElement).value,
                                    )}
                            />
                        </div>
                    </div>
                </section>

                <div class="divider"></div>

                <!-- FACTURACIÓN -->
                <section>
                    <h2 class="text-lg font-semibold mb-4">
                        Facturación (Billing)
                    </h2>
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div class="form-control">
                            <label class="label" for="days_before_due"
                                ><span class="label-text"
                                    >Días Antes del Vencimiento</span
                                ></label
                            >
                            <input
                                id="days_before_due"
                                type="number"
                                class="input input-bordered"
                                value={getS("days_before_due")}
                                oninput={(e) =>
                                    setS(
                                        "days_before_due",
                                        (e.target as HTMLInputElement).value,
                                    )}
                            />
                        </div>
                        <div class="form-control">
                            <label class="label" for="billing_alert_days"
                                ><span class="label-text">Días de Alerta</span
                                ></label
                            >
                            <input
                                id="billing_alert_days"
                                type="number"
                                class="input input-bordered"
                                value={getS("billing_alert_days")}
                                oninput={(e) =>
                                    setS(
                                        "billing_alert_days",
                                        (e.target as HTMLInputElement).value,
                                    )}
                            />
                        </div>
                        <div class="form-control">
                            <label class="label" for="suspension_run_hour"
                                ><span class="label-text"
                                    >Hora de Suspensión</span
                                ></label
                            >
                            <input
                                id="suspension_run_hour"
                                type="time"
                                class="input input-bordered"
                                value={getS("suspension_run_hour")}
                                oninput={(e) =>
                                    setS(
                                        "suspension_run_hour",
                                        (e.target as HTMLInputElement).value,
                                    )}
                            />
                        </div>
                    </div>
                </section>
            </div>

            <!-- Footer del card con botón de guardar -->
            <div class="border-t border-base-200 px-6 py-4 flex justify-end">
                <button
                    class="btn btn-primary"
                    onclick={saveGeneralSettings}
                    disabled={generalSaving}
                >
                    {#if generalSaving}<span
                            class="loading loading-spinner loading-sm"
                        ></span>{/if}
                    Guardar Cambios
                </button>
            </div>
        </div>

        <!-- ZONA DE PELIGRO -->
        <div class="card bg-base-100 shadow border border-error/30 mt-6">
            <div class="card-body">
                <h2 class="text-lg font-semibold text-error">
                    ⚠️ Zona de Peligro
                </h2>
                <p class="text-sm text-base-content/60">
                    Acciones administrativas inmediatas.
                </p>
                <div class="flex flex-wrap gap-3 mt-3">
                    <button
                        class="btn btn-warning gap-2"
                        onclick={onForceBilling}
                    >
                        🔄 Forzar Actualización de Suspensiones
                    </button>
                    <button class="btn btn-primary gap-2" onclick={onBackupNow}>
                        💾 Backup de BD Ahora
                    </button>
                </div>
            </div>
        </div>
    {/if}
{/if}

<!-- ══════════════════ TAB 2: AUDITORÍA ══════════════════ -->
{#if activeTab === "auditoria"}
    <div class="card bg-base-100 shadow-xl border border-base-200">
        <div class="card-body">
            <div
                class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4"
            >
                <div>
                    <h2 class="text-lg font-semibold">Logs de Auditoría</h2>
                    <p class="text-sm text-base-content/60">
                        Registro de acciones críticas realizadas en el sistema.
                    </p>
                </div>
                <button
                    class="btn btn-outline btn-sm gap-1"
                    onclick={loadAuditLogs}
                >
                    🔄 Actualizar
                </button>
            </div>

            <!-- Filtros -->
            <div class="flex flex-wrap gap-4 mb-4 p-3 bg-base-200 rounded-lg">
                <div class="flex items-center gap-2">
                    <label
                        for="audit-action"
                        class="text-xs font-bold uppercase">Acción:</label
                    >
                    <select
                        id="audit-action"
                        class="select select-sm select-bordered"
                        value={auditActionFilter}
                        onchange={(e) => {
                            auditActionFilter = (e.target as HTMLSelectElement)
                                .value;
                            auditPage = 1;
                            loadAuditLogs();
                        }}
                    >
                        <option value="all">Todas</option>
                        {#each auditFilters.actions as action}
                            <option value={action}>{action}</option>
                        {/each}
                    </select>
                </div>
                <div class="flex items-center gap-2">
                    <label for="audit-user" class="text-xs font-bold uppercase"
                        >Usuario:</label
                    >
                    <select
                        id="audit-user"
                        class="select select-sm select-bordered"
                        value={auditUserFilter}
                        onchange={(e) => {
                            auditUserFilter = (e.target as HTMLSelectElement)
                                .value;
                            auditPage = 1;
                            loadAuditLogs();
                        }}
                    >
                        <option value="all">Todos</option>
                        {#each auditFilters.usernames as u}
                            <option value={u}>{u}</option>
                        {/each}
                    </select>
                </div>
            </div>

            <!-- Tabla -->
            <div class="overflow-x-auto rounded-lg border border-base-200">
                {#if auditLoading}
                    <div class="flex justify-center py-12">
                        <span class="loading loading-spinner loading-md"></span>
                    </div>
                {:else if auditLogs.length === 0}
                    <div class="text-center py-12 text-base-content/50">
                        No hay logs de auditoría registrados.
                    </div>
                {:else}
                    <table class="table table-sm">
                        <thead class="bg-base-200">
                            <tr>
                                <th>Fecha / Hora</th>
                                <th>Usuario</th>
                                <th>Acción</th>
                                <th>Recurso</th>
                                <th>IP</th>
                                <th>Estado</th>
                            </tr>
                        </thead>
                        <tbody>
                            {#each auditLogs as log (log.id)}
                                <tr class="hover">
                                    <td class="whitespace-nowrap">
                                        <span class="block font-medium"
                                            >{fmtTime(log.timestamp)}</span
                                        >
                                        <span
                                            class="text-xs text-base-content/50"
                                            >{fmtDate(log.timestamp)}</span
                                        >
                                    </td>
                                    <td>
                                        <span class="font-medium"
                                            >{log.username}</span
                                        >
                                        {#if log.user_role}<span
                                                class="block text-xs text-base-content/50"
                                                >{log.user_role}</span
                                            >{/if}
                                    </td>
                                    <td>
                                        <span
                                            class="badge {actionBadge(
                                                log.action,
                                            )} badge-sm font-mono"
                                            >{log.action}</span
                                        >
                                    </td>
                                    <td
                                        class="font-mono text-xs text-base-content/70"
                                        >{log.resource_type}/{log.resource_id}</td
                                    >
                                    <td class="font-mono text-xs"
                                        >{log.ip_address ?? "N/A"}</td
                                    >
                                    <td>
                                        {#if log.status === "success"}
                                            <span
                                                class="badge badge-success badge-sm"
                                                >✓ OK</span
                                            >
                                        {:else}
                                            <span
                                                class="badge badge-error badge-sm"
                                                >✗ Error</span
                                            >
                                        {/if}
                                    </td>
                                </tr>
                            {/each}
                        </tbody>
                    </table>
                {/if}
            </div>

            <!-- Paginación -->
            <div
                class="flex flex-col sm:flex-row items-center justify-between gap-3 mt-4"
            >
                <div
                    class="flex items-center gap-2 text-sm text-base-content/60"
                >
                    <span>Mostrar</span>
                    <select
                        class="select select-sm select-bordered"
                        onchange={(e) => {
                            auditPageSize = parseInt(
                                (e.target as HTMLSelectElement).value,
                            );
                            auditPage = 1;
                            loadAuditLogs();
                        }}
                    >
                        <option value="10">10</option>
                        <option value="20" selected>20</option>
                        <option value="50">50</option>
                    </select>
                    <span>por pág. — Total: <strong>{auditTotal}</strong></span>
                </div>
                <div class="join">
                    <button
                        class="join-item btn btn-sm"
                        disabled={auditPage <= 1}
                        onclick={() => {
                            auditPage--;
                            loadAuditLogs();
                        }}>‹</button
                    >
                    <button class="join-item btn btn-sm btn-disabled"
                        >{auditPage} / {auditTotalPages}</button
                    >
                    <button
                        class="join-item btn btn-sm"
                        disabled={auditPage >= auditTotalPages}
                        onclick={() => {
                            auditPage++;
                            loadAuditLogs();
                        }}>›</button
                    >
                </div>
            </div>
        </div>
    </div>
{/if}

<!-- ══════════════════ TAB 3: BOTS ══════════════════ -->
{#if activeTab === "bots"}
    {#if generalLoading}
        <div class="flex justify-center py-16">
            <span class="loading loading-spinner loading-lg"></span>
        </div>
    {:else}
        <div class="card bg-base-100 shadow-xl border border-base-200">
            <div class="card-body space-y-8">
                <!-- TOKENS Y MODO -->
                <section>
                    <h2
                        class="text-lg font-semibold mb-1 flex items-center gap-2"
                    >
                        🔑 Tokens y Modo de Ejecución
                    </h2>
                    <p class="text-sm text-base-content/60 mb-4">
                        Configura los tokens de Telegram y el modo de operación.
                    </p>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div class="form-control">
                            <label class="label" for="bot_execution_mode"
                                ><span class="label-text"
                                    >Modo de Ejecución</span
                                ></label
                            >
                            <select
                                id="bot_execution_mode"
                                class="select select-bordered"
                                value={getS("bot_execution_mode")}
                                onchange={(e) =>
                                    setS(
                                        "bot_execution_mode",
                                        (e.target as HTMLSelectElement).value,
                                    )}
                            >
                                <option value="auto"
                                    >⚡ Auto (Recomendado)</option
                                >
                                <option value="polling"
                                    >🔄 Polling (Interno)</option
                                >
                                <option value="webhook"
                                    >🌐 Webhook (Dominio/Túnel)</option
                                >
                            </select>
                        </div>
                        <div class="form-control">
                            <label class="label" for="bot_external_url"
                                ><span class="label-text"
                                    >URL Externa (para Webhook)</span
                                ></label
                            >
                            <input
                                id="bot_external_url"
                                type="text"
                                class="input input-bordered"
                                placeholder="https://mi-dominio.com"
                                value={getS("bot_external_url")}
                                oninput={(e) =>
                                    setS(
                                        "bot_external_url",
                                        (e.target as HTMLInputElement).value,
                                    )}
                            />
                        </div>
                        <div class="form-control">
                            <label class="label" for="telegram_bot_token"
                                ><span class="label-text"
                                    >Token Bot Técnicos/Alertas</span
                                ></label
                            >
                            <input
                                id="telegram_bot_token"
                                type="password"
                                class="input input-bordered"
                                placeholder="123456:ABC-DEF..."
                                value={getS("telegram_bot_token")}
                                oninput={(e) =>
                                    setS(
                                        "telegram_bot_token",
                                        (e.target as HTMLInputElement).value,
                                    )}
                            />
                        </div>
                        <div class="form-control">
                            <label class="label" for="client_bot_token"
                                ><span class="label-text"
                                    >Token Bot Clientes</span
                                ></label
                            >
                            <input
                                id="client_bot_token"
                                type="password"
                                class="input input-bordered"
                                placeholder="123456:ABC-DEF..."
                                value={getS("client_bot_token")}
                                oninput={(e) =>
                                    setS(
                                        "client_bot_token",
                                        (e.target as HTMLInputElement).value,
                                    )}
                            />
                        </div>
                        <div class="form-control">
                            <label class="label" for="telegram_chat_id"
                                ><span class="label-text"
                                    >Chat ID de Alertas</span
                                ></label
                            >
                            <input
                                id="telegram_chat_id"
                                type="text"
                                class="input input-bordered"
                                placeholder="-123456789"
                                value={getS("telegram_chat_id")}
                                oninput={(e) =>
                                    setS(
                                        "telegram_chat_id",
                                        (e.target as HTMLInputElement).value,
                                    )}
                            />
                        </div>
                    </div>
                </section>

                <div class="divider"></div>

                <!-- MENSAJES DE BIENVENIDA -->
                <section>
                    <h2 class="text-lg font-semibold mb-1">
                        💬 Mensajes de Bienvenida
                    </h2>
                    <p class="text-sm text-base-content/60 mb-4">
                        Personaliza los mensajes iniciales del bot.
                    </p>
                    <div class="grid grid-cols-1 gap-4">
                        <div class="form-control">
                            <label class="label" for="bot_welcome_msg_client"
                                ><span class="label-text"
                                    >Saludo (Cliente vinculado)</span
                                ></label
                            >
                            <textarea
                                id="bot_welcome_msg_client"
                                class="textarea textarea-bordered font-mono text-sm"
                                rows="3"
                                value={getS("bot_welcome_msg_client")}
                                oninput={(e) =>
                                    setS(
                                        "bot_welcome_msg_client",
                                        (e.target as HTMLTextAreaElement).value,
                                    )}
                            ></textarea>
                        </div>
                        <div class="form-control">
                            <label class="label" for="bot_welcome_msg_guest"
                                ><span class="label-text"
                                    >Saludo (Invitado — debe incluir {"{user_id}"})</span
                                ></label
                            >
                            <textarea
                                id="bot_welcome_msg_guest"
                                class="textarea textarea-bordered font-mono text-sm"
                                rows="4"
                                value={getS("bot_welcome_msg_guest")}
                                oninput={(e) =>
                                    setS(
                                        "bot_welcome_msg_guest",
                                        (e.target as HTMLTextAreaElement).value,
                                    )}
                            ></textarea>
                        </div>
                        <div class="form-control">
                            <label class="label" for="bot_auto_reply_msg"
                                ><span class="label-text"
                                    >Mensaje Automático (sin sesión activa)</span
                                ></label
                            >
                            <textarea
                                id="bot_auto_reply_msg"
                                class="textarea textarea-bordered font-mono text-sm"
                                rows="3"
                                value={getS("bot_auto_reply_msg")}
                                oninput={(e) =>
                                    setS(
                                        "bot_auto_reply_msg",
                                        (e.target as HTMLTextAreaElement).value,
                                    )}
                            ></textarea>
                        </div>
                    </div>
                </section>

                <div class="divider"></div>

                <!-- BOTONES DEL MENÚ -->
                <section>
                    <h2 class="text-lg font-semibold mb-1">
                        🎛️ Botones del Menú Principal
                    </h2>
                    <p class="text-sm text-base-content/60 mb-4">
                        Activa/desactiva y personaliza el texto de cada botón.
                    </p>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {#each [{ label: "Reportar Falla", enableKey: "bot_enable_btn_report", valueKey: "bot_val_btn_report" }, { label: "Ver Tickets", enableKey: "bot_enable_btn_status", valueKey: "bot_val_btn_status" }, { label: "Clave WiFi", enableKey: "bot_enable_btn_wifi", valueKey: "bot_val_btn_wifi" }, { label: "Agente Humano", enableKey: "bot_enable_btn_agent", valueKey: "bot_val_btn_agent" }] as btn}
                            <div class="p-3 border border-base-200 rounded-lg">
                                <div
                                    class="flex items-center justify-between mb-2"
                                >
                                    <span class="text-sm font-medium"
                                        >{btn.label}</span
                                    >
                                    <input
                                        type="checkbox"
                                        class="toggle toggle-primary toggle-sm"
                                        checked={getS(btn.enableKey) === "true"}
                                        onchange={(e) =>
                                            setS(
                                                btn.enableKey,
                                                String(
                                                    (
                                                        e.target as HTMLInputElement
                                                    ).checked,
                                                ),
                                            )}
                                    />
                                </div>
                                <input
                                    type="text"
                                    class="input input-bordered input-sm w-full"
                                    disabled={getS(btn.enableKey) !== "true"}
                                    value={getS(btn.valueKey)}
                                    oninput={(e) =>
                                        setS(
                                            btn.valueKey,
                                            (e.target as HTMLInputElement)
                                                .value,
                                        )}
                                />
                            </div>
                        {/each}
                    </div>
                </section>
            </div>

            <div
                class="border-t border-base-200 px-6 py-4 flex justify-between items-center"
            >
                <button
                    class="btn btn-warning gap-2"
                    onclick={onRestartBots}
                    disabled={botRestarting || botSaving}
                >
                    {#if botRestarting}<span
                            class="loading loading-spinner loading-sm"
                        ></span>{:else}🔁{/if}
                    {botRestarting
                        ? "Reiniciando..."
                        : "Aplicar y Reiniciar Bots"}
                </button>
                <button
                    class="btn btn-primary"
                    onclick={saveBotSettings}
                    disabled={botSaving}
                >
                    {#if botSaving}<span
                            class="loading loading-spinner loading-sm"
                        ></span>{/if}
                    Guardar Cambios
                </button>
            </div>
        </div>
    {/if}
{/if}




<!-- ══════════════════ TAB 5: APARIENCIA ══════════════════ -->
{#if activeTab === "apariencia"}
    <div class="card bg-base-100 shadow-xl border border-base-200">
        <div class="card-body">
            <h2 class="text-lg font-semibold mb-1 flex items-center gap-2">
                🎨 Tema Visual
            </h2>
            <p class="text-sm text-base-content/60 mb-6">
                Personaliza la apariencia. El cambio es inmediato y se guarda en
                este navegador.
            </p>

            <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
                {#each availableThemes as t}
                    <button
                        class="relative rounded-xl border-2 p-5 text-left transition-all duration-200 cursor-pointer
                            {$theme.id === t.id
                            ? 'border-primary bg-primary/10 shadow-lg'
                            : 'border-base-300 hover:border-base-content/40 bg-base-200/50'}"
                        onclick={() => setTheme(t.id)}
                    >
                        <!-- Preview color strip -->
                        <div
                            data-theme={t.id}
                            class="rounded-lg h-14 mb-3 overflow-hidden flex gap-1 p-2 bg-base-100"
                        >
                            <div class="flex-1 rounded bg-primary"></div>
                            <div class="flex-1 rounded bg-secondary"></div>
                            <div class="flex-1 rounded bg-accent"></div>
                        </div>
                        <p class="font-bold text-sm">{t.label}</p>
                        <p class="text-xs text-base-content/60">{t.desc}</p>
                        {#if $theme.id === t.id}
                            <span
                                class="absolute top-2 right-2 text-primary text-lg"
                                >✓</span
                            >
                        {/if}
                    </button>
                {/each}
            </div>

            <div class="divider"></div>

            <div
                class="flex items-center justify-between p-4 bg-base-200 rounded-lg border border-base-300"
            >
                <div>
                    <h3 class="font-bold text-lg">
                        🌋 Fondo Animado Lava Lamp
                    </h3>
                    <p class="text-sm text-base-content/60">
                        Activa círculos abstractos flotantes que reaccionan a
                        los colores del tema actual.
                    </p>
                </div>
                <div>
                    <input
                        type="checkbox"
                        class="toggle toggle-primary toggle-lg"
                        checked={$theme.lavaLampActive}
                        onchange={toggleLavaLamp}
                    />
                </div>
            </div>
        </div>
    </div>
{/if}

<!-- ══════════════════ TAB 6: INFRAESTRUCTURA ══════════════════ -->
{#if activeTab === "infraestructura"}
    <div class="card bg-base-100 shadow-xl border border-base-200">
        <div class="card-body gap-8">
            <div>
            <!-- Cabecera de Infraestructura -->
            <div class="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-4">
                <div>
                    <h2 class="text-3xl font-black flex items-center gap-3">
                        <span class="text-4xl">🏢</span> Infraestructura
                    </h2>
                    <p class="text-sm opacity-60">Gestione contenedores Docker y proveedores de datos del sistema.</p>
                </div>
                <button 
                    class="btn btn-primary px-10 shadow-lg shadow-primary/20 w-full md:w-auto" 
                    onclick={async () => {
                        sysSaving = true;
                        try {
                            await updateSystemServices(sysConfig);
                            notify.success("¡Configuración global aplicada!");
                            await loadInfraStatus();
                        } catch(e) {
                            notify.error("Error al guardar proveedores.");
                        } finally {
                            sysSaving = false;
                        }
                    }}
                    disabled={sysSaving}
                >
                    {#if sysSaving}<span class="loading loading-spinner loading-sm"></span>{/if}
                    💾 Guardar y Reiniciar
                </button>
            </div>
            </div>

            {#if infraLoading}
                <div class="flex flex-col items-center justify-center py-24 gap-3">
                    <span class="loading loading-spinner loading-lg text-primary"></span>
                    <p class="text-sm font-medium animate-pulse">Cargando estado del sistema...</p>
                </div>
            {:else if !infraStatus || infraStatus.status === 'error'}
                <div class="alert alert-warning shadow-lg">
                    <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-8 w-8" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
                    <div class="flex-1">
                        <h3 class="font-bold">Modo de Configuración Manual</h3>
                        <p class="text-xs">No se detectó Docker. Puede configurar servidores externos manualmente abajo.</p>
                    </div>
                </div>
            {/if}

            <div class="space-y-12">
                
                <!-- 🐘 SECCIÓN BASE DE DATOS -->
                <section class="space-y-6">
                    <div class="flex items-center justify-between border-b border-base-300 pb-3">
                        <h3 class="text-lg font-bold flex items-center gap-3">
                            🐘 Almacenamiento de Datos
                        </h3>
                        {#if sysStatus && sysStatus.db}
                            <div class="badge badge-lg gap-2 text-xs font-bold {sysStatus.db.online ? 'badge-success text-success-content' : 'badge-error text-error-content'}">
                                <span class="w-2 h-2 rounded-full {sysStatus.db.online ? 'bg-success-content' : 'bg-error-content'}"></span>
                                {sysStatus.db.online ? 'En Línea' : 'Desconectado'}
                            </div>
                        {/if}
                    </div>

                    <!-- Selector de Proveedor -->
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                        <button 
                            class="relative flex items-start gap-4 p-5 rounded-2xl border-2 transition-all text-left {sysConfig.db_provider === 'sqlite' ? 'border-primary bg-primary/5' : 'border-base-300 hover:border-base-content/20'}"
                            onclick={() => sysConfig.db_provider = 'sqlite'}
                        >
                            <div class="text-4xl">📁</div>
                            <div>
                                <div class="font-bold text-lg">SQLite (Archivo Local)</div>
                                <p class="text-xs opacity-60">Ideal para entornos pequeños y simplicidad total.</p>
                            </div>
                            {#if sysConfig.db_provider === 'sqlite'}
                                <div class="absolute top-3 right-3 badge badge-primary badge-sm font-bold">SELECCIONADO</div>
                            {/if}
                        </button>

                        <button 
                            class="relative flex items-start gap-4 p-5 rounded-2xl border-2 transition-all text-left {sysConfig.db_provider === 'postgres' ? 'border-primary bg-primary/5' : 'border-base-300 hover:border-base-content/20'}"
                            onclick={() => sysConfig.db_provider = 'postgres'}
                        >
                            <div class="text-4xl">🐘</div>
                            <div>
                                <div class="font-bold text-lg">PostgreSQL</div>
                                <p class="text-xs opacity-60">Alta disponibilidad, escalabilidad y robustez.</p>
                            </div>
                            {#if sysConfig.db_provider === 'postgres'}
                                <div class="absolute top-3 right-3 badge badge-primary badge-sm font-bold">SELECCIONADO</div>
                            {/if}
                        </button>
                    </div>

                    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                        <!-- Lado 1: Configuración de Credenciales (Siempre visible si es Postgres) -->
                        <div class="space-y-4">
                            {#if sysConfig.db_provider === 'postgres'}
                                <div class="bg-base-200/50 p-6 rounded-2xl border border-base-300 space-y-4">
                                    <div class="flex items-center justify-between">
                                        <p class="text-xs font-bold uppercase opacity-50 tracking-wider">Conexión PostgreSQL</p>
                                        <div class="flex items-center gap-2">
                                            <button class="btn btn-xs btn-outline btn-info gap-1" onclick={testDbConnection} disabled={dbTesting}>
                                                {#if dbTesting}<span class="loading loading-spinner loading-xs"></span>{/if}
                                                <span>🔌</span> Probar Conexión
                                            </button>
                                            {#if infraStatus?.services?.postgres?.omniwisp_container === 'running'}
                                                <button class="btn btn-xs btn-outline btn-primary gap-1" onclick={fillPostgresLocal}>
                                                    <span>🪄</span> Autocompletar Local
                                                </button>
                                            {/if}
                                        </div>
                                    </div>
                                    <div class="form-control">
                                        <label class="label p-1" for="db_host"><span class="label-text font-bold">Host</span></label>
                                        <input id="db_host" type="text" class="input input-bordered" bind:value={sysConfig.postgres_host} placeholder="localhost o IP" />
                                    </div>
                                    <div class="grid grid-cols-2 gap-4">
                                        <div class="form-control">
                                            <label class="label p-1" for="db_port"><span class="label-text font-bold">Puerto</span></label>
                                            <input id="db_port" type="number" class="input input-bordered" bind:value={sysConfig.postgres_port} />
                                        </div>
                                        <div class="form-control">
                                            <label class="label p-1" for="db_name"><span class="label-text font-bold">Base de Datos</span></label>
                                            <input id="db_name" type="text" class="input input-bordered" bind:value={sysConfig.postgres_db} />
                                        </div>
                                    </div>
                                    <div class="grid grid-cols-2 gap-4 text-xs">
                                        <div class="form-control">
                                            <label class="label p-1" for="db_user"><span class="label-text font-bold">Usuario</span></label>
                                            <input id="db_user" type="text" class="input input-bordered" bind:value={sysConfig.postgres_user} />
                                        </div>
                                        <div class="form-control">
                                            <label class="label p-1" for="db_pass"><span class="label-text font-bold">Contraseña</span></label>
                                            <input id="db_pass" type="password" class="input input-bordered" bind:value={sysConfig.postgres_password} />
                                        </div>
                                    </div>

                                    {#if infraStatus?.services?.postgres?.suggested?.password}
                                        <div class="mt-4 p-3 bg-primary/10 border border-primary/20 rounded-xl text-[11px] space-y-2">
                                            <div class="flex items-center justify-between font-bold text-primary">
                                                <span>📍 Credenciales Locales Detectadas</span>
                                                <button class="btn btn-xs btn-primary btn-ghost h-auto min-h-0 py-0" onclick={fillPostgresLocal}>Aplicar Todo 🪄</button>
                                            </div>
                                            <div class="grid grid-cols-1 gap-1 opacity-80">
                                                <p><strong>DB:</strong> {infraStatus.services.postgres.suggested.db}</p>
                                                <p><strong>Usuario:</strong> {infraStatus.services.postgres.suggested.user}</p>
                                                <div class="flex items-center gap-2">
                                                    <strong>Password:</strong> 
                                                    <code class="bg-base-100 px-1 rounded">{infraStatus.services.postgres.suggested.password}</code>
                                                    <button class="hover:text-primary" onclick={() => { navigator.clipboard.writeText(infraStatus?.services?.postgres?.suggested?.password || ''); notify.success("Copiado"); }}>📋</button>
                                                </div>
                                            </div>
                                        </div>
                                    {/if}
                                </div>
                            {:else}
                                <div class="bg-primary/5 p-8 rounded-2xl border border-dashed border-primary/30 flex flex-col items-center text-center gap-3">
                                    <span class="text-4xl text-primary">📦</span>
                                    <div>
                                        <p class="font-bold text-primary">Modo Independiente (SQLite)</p>
                                        <p class="text-xs opacity-70">Los datos se almacenan en un solo archivo plano. Sin dependencias externas.</p>
                                    </div>
                                </div>
                            {/if}
                        </div>

                        <!-- Lado 2: Gestión de Infraestructura (Solo si Docker está disponible) -->
                        <div class="space-y-4">
                            <p class="text-xs font-bold uppercase opacity-50 tracking-wider">Control de Infraestructura</p>
                            {#if !infraStatus || infraStatus.status === 'error'}
                                <div class="p-6 rounded-2xl bg-base-200 border border-base-300 text-center">
                                    <p class="text-xs opacity-60">Docker no disponible para gestión automática.</p>
                                </div>
                            {:else}
                                <div class="flex flex-col gap-3">
                                    {#if infraStatus.services?.postgres?.omniwisp_container === 'running'}
                                        <div class="alert alert-success py-3 flex gap-2">
                                            <span class="text-xl">✓</span>
                                            <div>
                                                <div class="text-sm font-bold">OmniWISP_postgres activo</div>
                                                <div class="text-[10px] opacity-70">Puerto: {infraStatus.services.postgres.port}</div>
                                            </div>
                                        </div>
                                        <div class="flex gap-2">
                                            <button class="btn btn-warning btn-sm flex-1" onclick={() => { infraDeployActions.postgres = 'stop'; onDeployInfra(); }}>Detener</button>
                                            <button class="btn btn-error btn-sm flex-1" onclick={() => { if(confirm('¿Eliminar y perder datos no persistidos?')) { infraDeployActions.postgres = 'delete'; onDeployInfra(); } }}>Eliminar</button>
                                        </div>
                                    {:else}
                                        <div class="bg-base-200 p-4 rounded-xl border border-base-300 space-y-3">
                                            <p class="text-xs italic opacity-60">Contenedor local no detectado o detenido.</p>
                                            {#if infraStatus.services?.postgres?.conflict}
                                                <button class="btn btn-info btn-sm btn-block" onclick={() => { infraDeployActions.postgres = 'reuse'; onDeployInfra(); }}>Reutilizar {infraStatus.services.postgres.conflict.name}</button>
                                            {/if}
                                            <button class="btn btn-primary btn-sm btn-block" onclick={() => { infraDeployActions.postgres = 'create'; onDeployInfra(); }}>
                                                {infraStatus.services?.postgres?.omniwisp_container === 'missing' ? 'Desplegar PostgreSQL (Docker)' : 'Iniciar PostgreSQL'}
                                            </button>
                                        </div>
                                    {/if}

                                    {#if infraDeployResult?.postgres_password}
                                        <div class="bg-primary/20 p-4 rounded-xl border border-primary/30 mt-2">
                                            <p class="text-[10px] font-bold uppercase opacity-70">🔑 Contraseña Generada</p>
                                            <div class="flex items-center gap-2 mt-1">
                                                <code class="bg-base-100 px-2 py-1 rounded text-xs flex-1 select-all font-mono">{infraDeployResult.postgres_password}</code>
                                                <button class="btn btn-xs btn-ghost" onclick={() => { navigator.clipboard.writeText(infraDeployResult?.postgres_password || ''); notify.success("Copiado"); }}>📋</button>
                                            </div>
                                            <p class="text-[9px] mt-2 opacity-60">Guárdala o usa el botón de autocompletar.</p>
                                        </div>
                                    {/if}
                                </div>
                            {/if}
                        </div>
                    </div>
                </section>

                <div class="divider"></div>

                <!-- ⚡ SECCIÓN CACHÉ -->
                <section class="space-y-6">
                    <div class="flex items-center justify-between border-b border-base-300 pb-3">
                        <h3 class="text-lg font-bold flex items-center gap-3">
                            ⚡ Cache y Mensajería
                        </h3>
                        {#if sysStatus && sysStatus.cache}
                            <div class="badge badge-lg gap-2 text-xs font-bold {sysStatus.cache.online ? 'badge-success text-success-content' : 'badge-error text-error-content'}">
                                <span class="w-2 h-2 rounded-full {sysStatus.cache.online ? 'bg-success-content' : 'bg-error-content'}"></span>
                                {sysStatus.cache.online ? 'En Línea' : 'Desconectado'}
                            </div>
                        {/if}
                    </div>

                    <!-- Selector de Proveedor -->
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                        <button 
                            class="relative flex items-start gap-4 p-5 rounded-2xl border-2 transition-all text-left {sysConfig.cache_provider === 'memory' ? 'border-secondary bg-secondary/5' : 'border-base-300 hover:border-base-content/20'}"
                            onclick={() => sysConfig.cache_provider = 'memory'}
                        >
                            <div class="text-4xl">🧠</div>
                            <div>
                                <div class="font-bold text-lg">RAM (Local)</div>
                                <p class="text-xs opacity-60">Memoria del proceso principal. Muy rápido pero volátil.</p>
                            </div>
                            {#if sysConfig.cache_provider === 'memory'}
                                <div class="absolute top-3 right-3 badge badge-secondary badge-sm font-bold">SELECCIONADO</div>
                            {/if}
                        </button>

                        <button 
                            class="relative flex items-start gap-4 p-5 rounded-2xl border-2 transition-all text-left {sysConfig.cache_provider === 'redict' ? 'border-secondary bg-secondary/5' : 'border-base-300 hover:border-base-content/20'}"
                            onclick={() => sysConfig.cache_provider = 'redict'}
                        >
                            <div class="text-4xl">⚡</div>
                            <div>
                                <div class="font-bold text-lg">Redict / Redis</div>
                                <p class="text-xs opacity-60">Persistencia y comunicación rápida entre servicios.</p>
                            </div>
                            {#if sysConfig.cache_provider === 'redict'}
                                <div class="absolute top-3 right-3 badge badge-secondary badge-sm font-bold">SELECCIONADO</div>
                            {/if}
                        </button>
                    </div>

                    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                        <!-- Lado 1: Configuración -->
                        <div class="space-y-4">
                            {#if sysConfig.cache_provider === 'redict'}
                                <div class="bg-base-200/50 p-6 rounded-2xl border border-base-300 space-y-4">
                                    <div class="flex items-center justify-between">
                                        <p class="text-xs font-bold uppercase opacity-50 tracking-wider">Conexión Redict</p>
                                        <div class="flex items-center gap-2">
                                            <button class="btn btn-xs btn-outline btn-info gap-1" onclick={testCacheConnection} disabled={cacheTesting}>
                                                {#if cacheTesting}<span class="loading loading-spinner loading-xs"></span>{/if}
                                                <span>🔌</span> Probar Conexión
                                            </button>
                                            {#if infraStatus?.services?.redict?.omniwisp_container === 'running'}
                                                <button class="btn btn-xs btn-outline btn-secondary gap-1" onclick={fillRedictLocal}>
                                                    <span>🪄</span> Autocompletar Local
                                                </button>
                                            {/if}
                                        </div>
                                    </div>
                                    <div class="grid grid-cols-2 gap-4">
                                        <div class="form-control">
                                            <label class="label p-1" for="cache_host"><span class="label-text font-bold">Host</span></label>
                                            <input id="cache_host" type="text" class="input input-bordered" bind:value={sysConfig.redict_host} />
                                        </div>
                                        <div class="form-control">
                                            <label class="label p-1" for="cache_port"><span class="label-text font-bold">Puerto</span></label>
                                            <input id="cache_port" type="number" class="input input-bordered" bind:value={sysConfig.redict_port} />
                                        </div>
                                    </div>
                                    <div class="grid grid-cols-2 gap-4">
                                        <div class="form-control">
                                            <label class="label p-1" for="cache_db"><span class="label-text font-bold">DB index</span></label>
                                            <input id="cache_db" type="number" class="input input-bordered" bind:value={sysConfig.redict_db} />
                                        </div>
                                        <div class="form-control">
                                            <label class="label p-1" for="cache_pass"><span class="label-text font-bold">Password</span></label>
                                            <input id="cache_pass" type="password" class="input input-bordered" bind:value={sysConfig.redict_password} />
                                        </div>
                                    </div>
                                </div>
                            {:else}
                                <div class="bg-secondary/5 p-8 rounded-2xl border border-dashed border-secondary/30 flex flex-col items-center text-center gap-3">
                                    <span class="text-4xl">🧠</span>
                                    <div>
                                        <p class="font-bold text-secondary">Caché en Memoria Local</p>
                                        <p class="text-xs opacity-70">Usa RAM del proceso. No apto para múltiples nodos o alta carga.</p>
                                    </div>
                                </div>
                            {/if}
                        </div>

                        <!-- Lado 2: Gestión de Infraestructura -->
                        <div class="space-y-4">
                            <p class="text-xs font-bold uppercase opacity-50 tracking-wider">Control de Infraestructura</p>
                            {#if !infraStatus || infraStatus.status === 'error'}
                                <div class="p-6 rounded-2xl bg-base-200 border border-base-300 text-center">
                                    <p class="text-xs opacity-60">Gestión automática no disponible.</p>
                                </div>
                            {:else}
                                <div class="flex flex-col gap-3">
                                    {#if infraStatus.services?.redict?.omniwisp_container === 'running'}
                                        <div class="alert alert-info py-3 flex gap-2">
                                            <span class="text-xl">⚡</span>
                                            <div>
                                                <div class="text-sm font-bold">OmniWISP_redict activo</div>
                                                <div class="text-[10px] opacity-70">Redis-compatible, Puerto {infraStatus.services.redict.port}</div>
                                            </div>
                                        </div>
                                        <div class="flex gap-2">
                                            <button class="btn btn-warning btn-sm flex-1" onclick={() => { infraDeployActions.redict = 'stop'; onDeployInfra(); }}>Detener</button>
                                            <button class="btn btn-error btn-sm flex-1" onclick={() => { if(confirm('¿Eliminar?')) { infraDeployActions.redict = 'delete'; onDeployInfra(); } }}>Eliminar</button>
                                        </div>
                                    {:else}
                                        <div class="bg-base-200 p-4 rounded-xl border border-base-300 space-y-3">
                                            <p class="text-xs italic opacity-60">Servicio local no iniciado.</p>
                                            {#if infraStatus.services?.redict?.conflict}
                                                <button class="btn btn-info btn-sm btn-block" onclick={() => { infraDeployActions.redict = 'reuse'; onDeployInfra(); }}>Reutilizar {infraStatus.services.redict.conflict.name}</button>
                                            {/if}
                                            <button class="btn btn-primary btn-sm btn-block" onclick={() => { infraDeployActions.redict = 'create'; onDeployInfra(); }}>Desplegar Redict Server</button>
                                        </div>
                                    {/if}
                                </div>
                            {/if}
                        </div>
                    </div>
                </section>
            </div>

            <!-- ESPACIO FINAL -->
            <div class="h-20"></div>
        </div>
    </div>
{/if}

<!-- ══════════════════ TAB 7: VIDEOLLAMADAS ══════════════════ -->
{#if activeTab === "videollamadas"}
    <div class="card bg-base-100 shadow-xl border border-base-200">
        <div class="card-body gap-8">
            <div class="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                <div>
                    <h2 class="text-3xl font-black flex items-center gap-3">
                        <span class="text-4xl">🎥</span> Videollamadas
                    </h2>
                    <p class="text-sm opacity-60">Configuración del servidor de señalización LiveKit.</p>
                </div>
                <button 
                    class="btn btn-primary px-10 shadow-lg shadow-primary/20 w-full md:w-auto" 
                    onclick={saveSystemSettings}
                    disabled={sysSaving}
                >
                    {#if sysSaving}<span class="loading loading-spinner loading-sm"></span>{/if}
                    💾 Guardar Cambios
                </button>
            </div>

            <div class="alert alert-info shadow-sm py-3">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                <div class="text-xs">
                    <p class="font-bold">Nota de Seguridad</p>
                    <p>Las credenciales se almacenan cifradas en el servidor. Después de guardar, los cambios se aplican inmediatamente para nuevas llamadas.</p>
                </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div class="space-y-6">
                    <div class="form-control">
                        <label class="label" for="lk_url">
                            <span class="label-text font-bold">URL del Servidor LiveKit</span>
                        </label>
                        <input 
                            id="lk_url"
                            type="text" 
                            class="input input-bordered focus:input-primary" 
                            placeholder="ws://mi-servidor:7880"
                            bind:value={sysConfig.livekit_url}
                        />
                        <label class="label">
                            <span class="label-text-alt opacity-50 text-[10px]">Ejemplo: wss://livekit.mi-dominio.com</span>
                        </label>
                    </div>

                    <div class="form-control">
                        <label class="label" for="lk_key">
                            <span class="label-text font-bold">API Key (Clave Pública)</span>
                        </label>
                        <input 
                            id="lk_key"
                            type="text" 
                            class="input input-bordered focus:input-primary font-mono text-sm" 
                            placeholder="devkey"
                            bind:value={sysConfig.livekit_api_key}
                        />
                    </div>

                    <div class="form-control">
                        <label class="label" for="lk_secret">
                            <span class="label-text font-bold">API Secret (Clave Privada)</span>
                        </label>
                        <input 
                            id="lk_secret"
                            type="password" 
                            class="input input-bordered focus:input-primary" 
                            placeholder="••••••••••••••••"
                            bind:value={sysConfig.livekit_api_secret}
                        />
                        <label class="label">
                            <span class="label-text-alt opacity-50 text-[10px]">Nunca compartas esta clave. Se guardará de forma cifrada.</span>
                        </label>
                    </div>
                </div>

                <div class="bg-base-200/50 p-6 rounded-2xl border border-dashed border-base-300 flex flex-col items-center justify-center text-center gap-4">
                    <div class="w-16 h-16 bg-primary/10 text-primary rounded-full flex items-center justify-center text-2xl">
                        💡
                    </div>
                    <div class="max-w-xs">
                        <h4 class="font-bold">¿Cómo funciona?</h4>
                        <p class="text-[11px] opacity-70 leading-relaxed mt-2">
                            LiveKit es el motor que permite las videollamadas entre técnicos y clientes. 
                            Una vez configurado, OmniWISP generará automáticamente tokens seguros para cada sesión de soporte.
                        </p>
                    </div>
                    <div class="flex flex-wrap justify-center gap-2 mt-2">
                        <a href="https://docs.livekit.io" target="_blank" class="btn btn-xs btn-ghost text-primary uppercase tracking-tighter">Documentación ↗</a>
                        <a href="/difusion/videollamadas" class="btn btn-xs btn-ghost text-primary uppercase tracking-tighter">Ir al Panel 🎥</a>
                    </div>
                </div>
            </div>
            
            <div class="h-20"></div>
        </div>
    </div>
{/if}


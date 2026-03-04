<script lang="ts">
    import { onMount } from "svelte";
    import {
        getSettings,
        updateSettings,
        getSystemSettings,
        updateSystemSettings,
        getAuditLogs,
        getAuditLogFilters,
        forceBilling,
        backupNow,
        restartBots,
        type AuditLog,
        type SystemSettingsPayload,
    } from "$lib/api";

    // ─── Estado de tabs ────────────────────────────────────────────────
    let activeTab = $state<
        "general" | "auditoria" | "bots" | "sistema" | "apariencia"
    >("general");

    // ─── Toast ─────────────────────────────────────────────────────────
    let toast = $state<{ msg: string; type: "success" | "error" } | null>(null);
    function showToast(msg: string, type: "success" | "error" = "success") {
        toast = { msg, type };
        setTimeout(() => (toast = null), 3500);
    }

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
            showToast("Error al cargar configuración", "error");
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
            showToast("✅ Configuración guardada correctamente");
        } catch {
            showToast("Error al guardar configuración", "error");
        } finally {
            generalSaving = false;
        }
    }

    async function onForceBilling() {
        try {
            const res = await forceBilling();
            showToast(`✅ ${res.message}`);
        } catch {
            showToast("Error al forzar actualización", "error");
        }
    }

    async function onBackupNow() {
        try {
            await backupNow();
            showToast("✅ Backup completado");
        } catch {
            showToast("Error al realizar backup", "error");
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
            showToast("Error al cargar logs de auditoría", "error");
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
            showToast("✅ Configuración de bots guardada");
        } catch {
            showToast("Error al guardar bots", "error");
        } finally {
            botSaving = false;
        }
    }

    async function onRestartBots() {
        botRestarting = true;
        try {
            await updateSettings(generalSettings);
            const res = await restartBots();
            showToast(`✅ ${res.message}`);
        } catch {
            showToast("Error al reiniciar bots", "error");
        } finally {
            botRestarting = false;
        }
    }

    // ═══════════════════════════════════════════════════════════════════
    // TAB 4: SISTEMA
    // ═══════════════════════════════════════════════════════════════════
    let sysConfig = $state<SystemSettingsPayload>({
        db_provider: "sqlite",
        postgres_host: "",
        postgres_port: 5432,
        postgres_db: "umanager",
        postgres_user: "postgres",
        postgres_password: "",
        cache_provider: "memory",
        redict_url: "",
    });
    let sysLoading = $state(true);
    let sysSaving = $state(false);

    async function loadSystemSettings() {
        try {
            const env = await getSystemSettings();
            const dbUrl = env["DATABASE_URL_SYNC"] ?? "";
            sysConfig.db_provider = dbUrl.startsWith("postgresql")
                ? "postgres"
                : "sqlite";
            if (sysConfig.db_provider === "postgres") {
                try {
                    const match = dbUrl.match(
                        /postgresql\+psycopg:\/\/([^:]+):([^@]+)@([^:]+):(\d+)\/(.+)/,
                    );
                    if (match) {
                        sysConfig.postgres_user = match[1];
                        sysConfig.postgres_password = match[2];
                        sysConfig.postgres_host = match[3];
                        sysConfig.postgres_port = parseInt(match[4]);
                        sysConfig.postgres_db = match[5];
                    }
                } catch {}
            }
            sysConfig.cache_provider =
                env["CACHE_BACKEND"] === "redict" ? "redict" : "memory";
            sysConfig.redict_url = env["REDICT_URL"] ?? "";
        } catch {
            showToast("Error al cargar config del sistema", "error");
        } finally {
            sysLoading = false;
        }
    }

    async function saveSystemSettings() {
        sysSaving = true;
        try {
            const res = await updateSystemSettings(sysConfig);
            showToast(`✅ ${res.message}`);
        } catch {
            showToast("Error al guardar config del sistema", "error");
        } finally {
            sysSaving = false;
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
    let currentTheme = $state("dark");

    function setTheme(theme: string) {
        currentTheme = theme;
        document.documentElement.setAttribute("data-theme", theme);
        localStorage.setItem("umanager-theme", theme);
    }

    // ═══════════════════════════════════════════════════════════════════
    // INIT
    // ═══════════════════════════════════════════════════════════════════
    onMount(async () => {
        currentTheme = localStorage.getItem("umanager-theme") || "dark";
        await Promise.all([loadGeneralSettings(), loadSystemSettings()]);
    });

    // Cargar audit logs solo cuando se active esa tab
    $effect(() => {
        if (activeTab === "auditoria") {
            loadAuditFilters();
            loadAuditLogs();
        }
    });
</script>

<svelte:head>
    <title>Configuración Global — UManager</title>
</svelte:head>

<!-- Toast global -->
{#if toast}
    <div class="toast toast-top toast-center z-50">
        <div
            class="alert {toast.type === 'success'
                ? 'alert-success'
                : 'alert-error'} shadow-lg"
        >
            <span>{toast.msg}</span>
        </div>
    </div>
{/if}

<div class="mb-6">
    <h1 class="text-3xl font-bold">Configuración Global</h1>
    <p class="text-base-content/60 mt-1">
        Ajustes del sistema, facturación, bots e infraestructura.
    </p>
</div>

<!-- Tabs DaisyUI (role=tablist) -->
<div role="tablist" class="tabs tabs-bordered tabs-lg mb-6 flex-wrap gap-1">
    <button
        role="tab"
        class="tab {activeTab === 'general' ? 'tab-active font-bold' : ''}"
        onclick={() => (activeTab = "general")}
    >
        ⚙️ General
    </button>
    <button
        role="tab"
        class="tab {activeTab === 'auditoria' ? 'tab-active font-bold' : ''}"
        onclick={() => (activeTab = "auditoria")}
    >
        🛡️ Auditoría
    </button>
    <button
        role="tab"
        class="tab {activeTab === 'bots' ? 'tab-active font-bold' : ''}"
        onclick={() => (activeTab = "bots")}
    >
        🤖 Bots
    </button>
    <button
        role="tab"
        class="tab {activeTab === 'sistema' ? 'tab-active font-bold' : ''}"
        onclick={() => (activeTab = "sistema")}
    >
        🗄️ Sistema
    </button>
    <button
        role="tab"
        class="tab {activeTab === 'apariencia' ? 'tab-active font-bold' : ''}"
        onclick={() => (activeTab = "apariencia")}
    >
        🎨 Apariencia
    </button>
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

<!-- ══════════════════ TAB 4: SISTEMA ══════════════════ -->
{#if activeTab === "sistema"}
    {#if sysLoading}
        <div class="flex justify-center py-16">
            <span class="loading loading-spinner loading-lg"></span>
        </div>
    {:else}
        <div class="alert alert-warning mb-4">
            <span
                >⚠️ <strong>Atención:</strong> Cambiar estos ajustes requiere reiniciar
                el servidor backend para que tengan efecto.</span
            >
        </div>
        <div class="card bg-base-100 shadow-xl border border-base-200">
            <div class="card-body space-y-8">
                <!-- BASE DE DATOS -->
                <section>
                    <h2
                        class="text-lg font-semibold mb-4 flex items-center gap-2"
                    >
                        🗄️ Base de Datos
                    </h2>
                    <div class="flex gap-6 mb-4">
                        <label class="flex items-center gap-2 cursor-pointer">
                            <input
                                type="radio"
                                name="db_provider"
                                class="radio radio-primary"
                                value="sqlite"
                                checked={sysConfig.db_provider === "sqlite"}
                                onchange={() =>
                                    (sysConfig.db_provider = "sqlite")}
                            />
                            <span>SQLite (Archivo Local)</span>
                        </label>
                        <label class="flex items-center gap-2 cursor-pointer">
                            <input
                                type="radio"
                                name="db_provider"
                                class="radio radio-primary"
                                value="postgres"
                                checked={sysConfig.db_provider === "postgres"}
                                onchange={() =>
                                    (sysConfig.db_provider = "postgres")}
                            />
                            <span>PostgreSQL (Remoto/Docker)</span>
                        </label>
                    </div>

                    {#if sysConfig.db_provider === "postgres"}
                        <div
                            class="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 bg-base-200 rounded-lg"
                        >
                            <div class="md:col-span-2 form-control">
                                <label class="label"
                                    ><span class="label-text">Host</span></label
                                >
                                <input
                                    type="text"
                                    class="input input-bordered"
                                    placeholder="localhost"
                                    bind:value={sysConfig.postgres_host}
                                />
                            </div>
                            <div class="form-control">
                                <label class="label"
                                    ><span class="label-text">Puerto</span
                                    ></label
                                >
                                <input
                                    type="number"
                                    class="input input-bordered"
                                    placeholder="5432"
                                    bind:value={sysConfig.postgres_port}
                                />
                            </div>
                            <div class="form-control">
                                <label class="label"
                                    ><span class="label-text"
                                        >Base de Datos</span
                                    ></label
                                >
                                <input
                                    type="text"
                                    class="input input-bordered"
                                    placeholder="umanager"
                                    bind:value={sysConfig.postgres_db}
                                />
                            </div>
                            <div class="form-control">
                                <label class="label"
                                    ><span class="label-text">Usuario</span
                                    ></label
                                >
                                <input
                                    type="text"
                                    class="input input-bordered"
                                    placeholder="postgres"
                                    bind:value={sysConfig.postgres_user}
                                />
                            </div>
                            <div class="form-control">
                                <label class="label"
                                    ><span class="label-text">Contraseña</span
                                    ></label
                                >
                                <input
                                    type="password"
                                    class="input input-bordered"
                                    placeholder="••••••"
                                    bind:value={sysConfig.postgres_password}
                                />
                            </div>
                        </div>
                    {:else}
                        <div
                            class="p-4 bg-base-200 rounded-lg text-sm text-base-content/70"
                        >
                            Se usará el archivo SQLite en <code
                                class="font-mono">data/db/inventory.sqlite</code
                            >
                        </div>
                    {/if}
                </section>

                <div class="divider"></div>

                <!-- CACHÉ -->
                <section>
                    <h2 class="text-lg font-semibold mb-4">
                        ⚡ Cache / Cola de Mensajes
                    </h2>
                    <div class="flex gap-6 mb-4">
                        <label class="flex items-center gap-2 cursor-pointer">
                            <input
                                type="radio"
                                name="cache_provider"
                                class="radio radio-primary"
                                value="memory"
                                checked={sysConfig.cache_provider === "memory"}
                                onchange={() =>
                                    (sysConfig.cache_provider = "memory")}
                            />
                            <span>Memoria (Solo Dev)</span>
                        </label>
                        <label class="flex items-center gap-2 cursor-pointer">
                            <input
                                type="radio"
                                name="cache_provider"
                                class="radio radio-primary"
                                value="redict"
                                checked={sysConfig.cache_provider === "redict"}
                                onchange={() =>
                                    (sysConfig.cache_provider = "redict")}
                            />
                            <span>Redict / Redis (Producción)</span>
                        </label>
                    </div>

                    {#if sysConfig.cache_provider === "redict"}
                        <div class="p-4 bg-base-200 rounded-lg">
                            <div class="form-control">
                                <label class="label"
                                    ><span class="label-text"
                                        >URL de Conexión</span
                                    ></label
                                >
                                <input
                                    type="text"
                                    class="input input-bordered"
                                    placeholder="redis://localhost:6379/0"
                                    bind:value={sysConfig.redict_url}
                                />
                                <label class="label"
                                    ><span
                                        class="label-text-alt text-base-content/50"
                                        >Formato:
                                        redis://[:password@]host:port/db</span
                                    ></label
                                >
                            </div>
                        </div>
                    {/if}
                </section>
            </div>

            <div class="border-t border-base-200 px-6 py-4 flex justify-end">
                <button
                    class="btn btn-warning"
                    onclick={saveSystemSettings}
                    disabled={sysSaving}
                >
                    {#if sysSaving}<span
                            class="loading loading-spinner loading-sm"
                        ></span>{/if}
                    Guardar y Solicitar Reinicio
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
                {#each availableThemes as theme}
                    <button
                        class="relative rounded-xl border-2 p-5 text-left transition-all duration-200 cursor-pointer
                            {currentTheme === theme.id
                            ? 'border-primary bg-primary/10 shadow-lg'
                            : 'border-base-300 hover:border-base-content/40 bg-base-200/50'}"
                        onclick={() => setTheme(theme.id)}
                    >
                        <!-- Preview color strip -->
                        <div
                            data-theme={theme.id}
                            class="rounded-lg h-14 mb-3 overflow-hidden flex gap-1 p-2 bg-base-100"
                        >
                            <div class="flex-1 rounded bg-primary"></div>
                            <div class="flex-1 rounded bg-secondary"></div>
                            <div class="flex-1 rounded bg-accent"></div>
                        </div>
                        <p class="font-bold text-sm">{theme.label}</p>
                        <p class="text-xs text-base-content/60">{theme.desc}</p>
                        {#if currentTheme === theme.id}
                            <span
                                class="absolute top-2 right-2 text-primary text-lg"
                                >✓</span
                            >
                        {/if}
                    </button>
                {/each}
            </div>
        </div>
    </div>
{/if}

<script lang="ts">
    import { notify } from "$lib/stores/notifications";
    import { forceBilling, backupNow, updateSettings } from "$lib/api";

    // Propiedades usando runas de Svelte 5
    let {
        generalSettings = $bindable({}),
    } = $props<{
        generalSettings: Record<string, string>;
    }>();

    let generalSaving = $state(false);

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
</script>

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

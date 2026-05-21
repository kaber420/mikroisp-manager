<script lang="ts">
    import { onMount } from "svelte";
    import { getAuditLogs, getAuditLogFilters } from "$lib/api";
    import { notify } from "$lib/stores/notifications";

    interface AuditLog {
        id: string | number;
        timestamp: string;
        username: string;
        user_role?: string;
        action: string;
        resource_type: string;
        resource_id: string | number;
        ip_address?: string;
        status: string;
    }

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

    onMount(async () => {
        await Promise.all([loadAuditFilters(), loadAuditLogs()]);
    });
</script>

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
                        auditActionFilter = (e.target as HTMLSelectElement).value;
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
                        auditUserFilter = (e.target as HTMLSelectElement).value;
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

<script lang="ts">
    import type { PageData } from "./$types";
    import { getCPEs } from "$lib/api";
    import DataTable from "$lib/components/DataTable.svelte";
    import type { CPEGlobalInfo } from "$lib/types/cpe";
    import CPEEditModal from "$lib/components/cpes/CPEEditModal.svelte";
    import CPEDisableModal from "$lib/components/cpes/CPEDisableModal.svelte";
    import CPEDeleteModal from "$lib/components/cpes/CPEDeleteModal.svelte";

    let { data }: { data: PageData } = $props();

    // --- Filtros ---
    let filterStatus = $state<string>("all");

    let tableComponent: any = $state();
    function applyFilter() {
        tableComponent?.refresh();
    }

    // --- Carga dinámica para DataTable ---
    async function loadCPEs(page: number, pageSize: number, search: string) {
        const params: Record<string, any> = { page, page_size: pageSize };
        if (search) params.search = search;
        if (filterStatus !== "all") params.status = filterStatus;
        const res = await getCPEs(params);
        return {
            items: res.items,
            total: res.total,
            total_pages: Math.max(1, Math.ceil(res.total / pageSize)),
        };
    }

    // --- Modales ---
    let editModal = $state(false);
    let editTarget = $state<CPEGlobalInfo | null>(null);

    let disableModal = $state(false);
    let disableTarget = $state<CPEGlobalInfo | null>(null);

    let deleteModal = $state(false);
    let deleteTarget = $state<CPEGlobalInfo | null>(null);

    function openEdit(cpe: CPEGlobalInfo) {
        editTarget = cpe;
        editModal = true;
    }
    function openDisable(cpe: CPEGlobalInfo) {
        disableTarget = cpe;
        disableModal = true;
    }
    function openDelete(cpe: CPEGlobalInfo) {
        deleteTarget = cpe;
        deleteModal = true;
    }

    // --- Helpers (usados en snippets de DataTable) ---
    function statusLabel(s: string | null) {
        return (
            { active: "Activo", offline: "Caído", disabled: "Deshabilitado" }[s ?? ""] ??
            s ??
            "—"
        );
    }
    function statusClass(s: string | null) {
        return (
            {
                active: "badge-success",
                offline: "badge-error",
                disabled: "badge-ghost",
            }[s ?? ""] ?? "badge-ghost"
        );
    }
    let warningLevel = $derived(
        data.publicSettings?.cpe_signal_warning_threshold
            ? parseFloat(data.publicSettings.cpe_signal_warning_threshold)
            : -62,
    );
    let dangerLevel = $derived(
        data.publicSettings?.cpe_signal_danger_threshold
            ? parseFloat(data.publicSettings.cpe_signal_danger_threshold)
            : -71,
    );
    function signalClass(sig: number | null): string {
        if (sig === null) return "text-base-content opacity-40";
        if (sig <= dangerLevel) return "text-error font-semibold";
        if (sig <= warningLevel) return "text-warning font-semibold";
        return "text-success font-semibold";
    }
    function displayName(cpe: CPEGlobalInfo): string {
        return cpe.cpe_hostname ?? cpe.cpe_mac;
    }
</script>

<div style="display:flex;flex-direction:column;gap:1.5rem;">
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
                <div>
                    <h1 style="margin:0;font-size:1.5rem;font-weight:800;">
                        Network CPEs
                    </h1>
                    <p style="margin:0.25rem 0 0;font-size:0.85rem;opacity:0.5;">
                        {data.cpes.total} CPE{data.cpes.total !== 1 ? "s" : ""} registrados
                    </p>
                </div>
            </div>
        </div>
    </div>

    <!-- Tabla dinámica -->
    <DataTable
        bind:this={tableComponent}
        loadData={loadCPEs}
        initialItems={data.cpes.items}
        initialTotal={data.cpes.total}
        initialPage={1}
        initialTotalPages={Math.max(1, Math.ceil(data.cpes.total / 20))}
    >
        {#snippet filters()}
            <select
                class="select select-bordered select-sm"
                bind:value={filterStatus}
                onchange={applyFilter}
                style="border-radius:0.5rem;font-size:0.875rem;"
            >
                <option value="all">Todos los estados</option>
                <option value="active">Activos</option>
                <option value="offline">Caídos</option>
                <option value="disabled">Deshabilitados</option>
            </select>
        {/snippet}

        {#snippet header()}
            <tr>
                <th class="dt-th">Estado</th>
                <th class="dt-th">CPE / Hostname</th>
                <th class="dt-th">AP Conectado</th>
                <th class="dt-th">SSID / Banda</th>
                <th class="dt-th">Señal</th>
                <th class="dt-th">MAC</th>
                <th class="dt-th">IP</th>
                <th class="dt-th" style="text-align:center;width:80px;"></th>
            </tr>
        {/snippet}

        {#snippet row(cpe: CPEGlobalInfo)}
            <tr>
                <td class="dt-td">
                    <span class="badge badge-sm {statusClass(cpe.status)}">
                        {statusLabel(cpe.status)}
                    </span>
                </td>
                <td class="dt-td">
                    <p style="font-weight:500;margin:0;">{displayName(cpe)}</p>
                    {#if cpe.cpe_hostname}
                        <p style="font-family:monospace;font-size:0.7rem;opacity:0.4;margin:0;">
                            {cpe.cpe_mac}
                        </p>
                    {/if}
                </td>
                <td class="dt-td">
                    {#if cpe.ap_hostname || cpe.ap_host}
                        <p style="font-weight:500;margin:0;">{cpe.ap_hostname ?? ""}</p>
                        <p style="font-family:monospace;font-size:0.7rem;opacity:0.4;margin:0;">
                            {cpe.ap_host ?? ""}
                        </p>
                    {:else}
                        <span style="opacity:0.35;">—</span>
                    {/if}
                </td>
                <td class="dt-td">
                    {#if cpe.ssid}
                        <p style="font-weight:500;margin:0;">{cpe.ssid}</p>
                        {#if cpe.band}
                            <span class="badge badge-xs badge-outline">{cpe.band}</span>
                        {/if}
                    {:else}
                        <span style="opacity:0.35;">—</span>
                    {/if}
                </td>
                <td class="dt-td">
                    {#if cpe.signal !== null}
                        <span class={signalClass(cpe.signal)}>{cpe.signal} dBm</span>
                    {:else}
                        <span style="opacity:0.35;">—</span>
                    {/if}
                </td>
                <td
                    class="dt-td"
                    style="font-family:monospace;font-size:0.75rem;opacity:0.65;"
                >
                    {cpe.cpe_mac}
                </td>
                <td
                    class="dt-td"
                    style="font-family:monospace;font-size:0.75rem;opacity:0.65;"
                >
                    {cpe.ip_address ?? "—"}
                </td>
                <td class="dt-td" style="text-align:center;">
                    <div class="flex gap-1 justify-center">
                        <!-- Editar -->
                        <button
                            class="btn btn-ghost btn-xs btn-square"
                            title="Editar alias"
                            onclick={() => openEdit(cpe)}
                        >
                            <svg
                                xmlns="http://www.w3.org/2000/svg"
                                class="w-3.5 h-3.5"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                                stroke-width="2"
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                ><path
                                    d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"
                                /><path
                                    d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4Z"
                                /></svg
                            >
                        </button>
                        <!-- Deshabilitar (solo si está activo u offline) -->
                        {#if cpe.is_enabled !== false}
                            <button
                                class="btn btn-ghost btn-xs btn-square text-warning"
                                title="Deshabilitar CPE"
                                onclick={() => openDisable(cpe)}
                            >
                                <svg
                                    xmlns="http://www.w3.org/2000/svg"
                                    class="w-3.5 h-3.5"
                                    viewBox="0 0 24 24"
                                    fill="none"
                                    stroke="currentColor"
                                    stroke-width="2"
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    ><circle cx="12" cy="12" r="10" /><line
                                        x1="4.93"
                                        y1="4.93"
                                        x2="19.07"
                                        y2="19.07"
                                    /></svg
                                >
                            </button>
                        {/if}
                        <!-- Eliminar (solo si está deshabilitado) -->
                        {#if cpe.is_enabled === false}
                            <button
                                class="btn btn-ghost btn-xs btn-square text-error"
                                title="Eliminar CPE"
                                onclick={() => openDelete(cpe)}
                            >
                                <svg
                                    xmlns="http://www.w3.org/2000/svg"
                                    class="w-3.5 h-3.5"
                                    viewBox="0 0 24 24"
                                    fill="none"
                                    stroke="currentColor"
                                    stroke-width="2"
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    ><polyline points="3 6 5 6 21 6" /><path
                                        d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"
                                    /><path d="M10 11v6" /><path d="M14 11v6" /><path
                                        d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"
                                    /></svg
                                >
                            </button>
                        {/if}
                    </div>
                </td>
            </tr>
        {/snippet}
    </DataTable>
</div>

<CPEEditModal bind:show={editModal} cpe={editTarget} onsave={applyFilter} />
<CPEDisableModal bind:show={disableModal} cpe={disableTarget} onconfirm={applyFilter} />
<CPEDeleteModal bind:show={deleteModal} cpe={deleteTarget} onconfirm={applyFilter} />

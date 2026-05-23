<script lang="ts">
    import { updateZonaInfra } from "$lib/api";
    import { notify } from "$lib/stores/notifications";
    import type { ZonaDetail, ZonaInfra } from "$lib/types/zona";

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

    // ── Estado de edición ──────────────────────────────────────────────────
    let isEditing = $state(false);
    let fIpGestion = $state(zona.infraestructura?.direccion_ip_gestion ?? "");
    let fGateway = $state(zona.infraestructura?.gateway_predeterminado ?? "");
    let fDns = $state(zona.infraestructura?.servidores_dns ?? "");
    let fVlans = $state(zona.infraestructura?.vlans_utilizadas ?? "");
    let fEquipos = $state(zona.infraestructura?.equipos_criticos ?? "");
    let fMantenimiento = $state(zona.infraestructura?.proximo_mantenimiento ?? "");
    let saving = $state(false);
    let errorMsg = $state<string | null>(null);

    $effect(() => {
        const infra = zona.infraestructura;
        fIpGestion = infra?.direccion_ip_gestion ?? "";
        fGateway = infra?.gateway_predeterminado ?? "";
        fDns = infra?.servidores_dns ?? "";
        fVlans = infra?.vlans_utilizadas ?? "";
        fEquipos = infra?.equipos_criticos ?? "";
        fMantenimiento = infra?.proximo_mantenimiento ?? "";
    });

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
</script>

<div class="glass-card-flat" style="border-radius:1rem;padding:1.5rem;">
    {#if isEditing}
        <!-- ── MODO EDICIÓN ──────────────────────────────────────────── -->
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1.5rem;">
            <h3 style="margin:0;font-size:1.1rem;font-weight:700;opacity:0.9;">🔌 Editar Infraestructura de Red</h3>
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
        <!-- ── MODO LECTURA ──────────────────────────────────────────── -->
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1.5rem;">
            <h3 style="margin:0;font-size:1.1rem;font-weight:700;opacity:0.9;">🔌 Infraestructura de Red</h3>
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
        <!-- ── VACÍO ──────────────────────────────────────────────────── -->
        <div style="text-align:center;padding:2.5rem;opacity:0.5;">
            <p style="font-size:2rem;margin:0 0 0.5rem;">🔌</p>
            <p style="margin:0;font-size:0.9rem;">Sin datos de infraestructura configurados.</p>
            {#if canEdit}
                <button class="btn btn-sm btn-outline mt-4" onclick={() => (isEditing = true)}>Configurar infraestructura</button>
            {/if}
        </div>
    {/if}
</div>

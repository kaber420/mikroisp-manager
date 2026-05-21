<script lang="ts">
    import { updateZonaInfra } from "$lib/api";
    import { notify } from "$lib/stores/notifications";
    import type { ZonaDetail, ZonaInfra } from "$lib/types/zona";

    let { zona, zonaId, onsave } = $props<{
        zona: ZonaDetail;
        zonaId: number;
        onsave?: () => void;
    }>();

    const i = zona.infraestructura;
    let fIpGestion = $state(i?.direccion_ip_gestion ?? "");
    let fGateway = $state(i?.gateway_predeterminado ?? "");
    let fDns = $state(i?.servidores_dns ?? "");
    let fVlans = $state(i?.vlans_utilizadas ?? "");
    let fEquipos = $state(i?.equipos_criticos ?? "");
    let fMantenimiento = $state(i?.proximo_mantenimiento ?? "");
    let savingInfra = $state(false);
    let errorInfra = $state<string | null>(null);

    // Sync when zona prop changes (parent reload)
    $effect(() => {
        const infra = zona.infraestructura;
        fIpGestion = infra?.direccion_ip_gestion ?? "";
        fGateway = infra?.gateway_predeterminado ?? "";
        fDns = infra?.servidores_dns ?? "";
        fVlans = infra?.vlans_utilizadas ?? "";
        fEquipos = infra?.equipos_criticos ?? "";
        fMantenimiento = infra?.proximo_mantenimiento ?? "";
    });

    async function saveInfra() {
        savingInfra = true;
        errorInfra = null;
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
            if (onsave) onsave();
        } catch (e: any) {
            errorInfra = e?.response?.data?.detail ?? "Error al guardar infraestructura.";
        } finally {
            savingInfra = false;
        }
    }
</script>

<div class="glass-card-flat" style="border-radius:1rem;padding:1.5rem;">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1.5rem;">
        <h3 style="margin:0;font-size:1.1rem;font-weight:700;opacity:0.9;">🔌 Infraestructura de Red</h3>
        {#if savingInfra}
            <span class="loading loading-spinner loading-sm text-primary"></span>
        {/if}
    </div>

    <form
        onsubmit={(e) => { e.preventDefault(); saveInfra(); }}
        style="display:flex;flex-direction:column;gap:1.25rem;"
    >
        {#if errorInfra}
            <div class="alert alert-error py-2">
                <span style="font-size:0.85rem;">{errorInfra}</span>
            </div>
        {/if}

        <div
            style="display:grid;grid-template-columns:repeat(auto-fit, minmax(220px, 1fr));gap:1rem;"
        >
            <label class="form-control">
                <div class="label">
                    <span class="label-text font-semibold opacity-70">IP de Gestión</span>
                </div>
                <input
                    class="input input-bordered input-sm font-mono bg-base-100"
                    type="text"
                    bind:value={fIpGestion}
                    placeholder="192.168.X.X"
                />
            </label>
            <label class="form-control">
                <div class="label">
                    <span class="label-text font-semibold opacity-70">Gateway</span>
                </div>
                <input
                    class="input input-bordered input-sm font-mono bg-base-100"
                    type="text"
                    bind:value={fGateway}
                    placeholder="192.168.X.1"
                />
            </label>
            <label class="form-control">
                <div class="label">
                    <span class="label-text font-semibold opacity-70">Servidores DNS</span>
                </div>
                <input
                    class="input input-bordered input-sm font-mono bg-base-100"
                    type="text"
                    bind:value={fDns}
                    placeholder="8.8.8.8, 1.1.1.1"
                />
            </label>
            <label class="form-control">
                <div class="label">
                    <span class="label-text font-semibold opacity-70">VLANs Utilizadas</span>
                </div>
                <input
                    class="input input-bordered input-sm font-mono bg-base-100"
                    type="text"
                    bind:value={fVlans}
                    placeholder="10, 20..."
                />
            </label>
        </div>

        <div
            style="display:grid;grid-template-columns:repeat(auto-fit, minmax(250px, 1fr));gap:1rem;"
        >
            <label class="form-control">
                <div class="label">
                    <span class="label-text font-semibold opacity-70">Equipos Críticos</span>
                </div>
                <textarea
                    class="textarea textarea-bordered textarea-sm bg-base-100"
                    bind:value={fEquipos}
                    rows="2"
                    placeholder="ej: Core switch principal..."
                ></textarea>
            </label>
            <label class="form-control">
                <div class="label">
                    <span class="label-text font-semibold opacity-70">Próximo Mantenimiento</span>
                </div>
                <input
                    class="input input-bordered input-sm bg-base-100"
                    type="date"
                    bind:value={fMantenimiento}
                />
            </label>
        </div>

        <div style="text-align:right;">
            <button
                type="submit"
                class="btn btn-primary btn-sm px-6"
                disabled={savingInfra}>Guardar</button
            >
        </div>
    </form>
</div>

<script lang="ts">
    import { updateZona } from "$lib/api";
    import { notify } from "$lib/stores/notifications";
    import type { ZonaDetail } from "$lib/types/zona";

    let { zona, zonaId, onsave } = $props<{
        zona: ZonaDetail;
        zonaId: number;
        onsave?: () => void;
    }>();

    let fNombre = $state(zona.nombre);
    let fDireccion = $state(zona.direccion ?? "");
    let fCoordenadas = $state(zona.coordenadas_gps ?? "");
    let fRackJson = $state(zona.rack_layout ? JSON.stringify(zona.rack_layout, null, 2) : "");
    let savingGeneral = $state(false);
    let errorGeneral = $state<string | null>(null);
    let saveOk = $state(false);

    // Sync field values when zona prop changes (parent reloads)
    $effect(() => {
        fNombre = zona.nombre;
        fDireccion = zona.direccion ?? "";
        fCoordenadas = zona.coordenadas_gps ?? "";
        fRackJson = zona.rack_layout ? JSON.stringify(zona.rack_layout, null, 2) : "";
    });

    async function saveGeneral() {
        savingGeneral = true;
        errorGeneral = null;
        saveOk = false;
        try {
            let rack: Record<string, unknown> | null = null;
            if (fRackJson.trim()) {
                rack = JSON.parse(fRackJson);
            }
            await updateZona(zonaId, {
                nombre: fNombre.trim(),
                direccion: fDireccion.trim() || null,
                coordenadas_gps: fCoordenadas.trim() || null,
                rack_layout: rack,
            });
            saveOk = true;
            notify.success("Datos generales guardados.");
            if (onsave) onsave();
        } catch (e: any) {
            errorGeneral =
                e instanceof SyntaxError
                    ? "JSON del Virtual Rack inválido."
                    : (e?.response?.data?.detail ?? "Error al guardar.");
        } finally {
            savingGeneral = false;
        }
    }
</script>

<div class="glass-card-flat" style="border-radius:1rem;padding:1.5rem;">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1.5rem;">
        <h3 style="margin:0;font-size:1.1rem;font-weight:700;opacity:0.9;">📋 Datos Generales</h3>
        {#if savingGeneral}
            <span class="loading loading-spinner loading-sm text-primary"></span>
        {/if}
    </div>

    <form
        onsubmit={(e) => { e.preventDefault(); saveGeneral(); }}
        style="display:flex;flex-direction:column;gap:1.25rem;"
    >
        {#if errorGeneral}
            <div class="alert alert-error py-2">
                <span style="font-size:0.85rem;">{errorGeneral}</span>
            </div>
        {/if}

        <div
            style="display:grid;grid-template-columns:repeat(auto-fit, minmax(250px, 1fr));gap:1rem;"
        >
            <label class="form-control">
                <div class="label">
                    <span class="label-text font-semibold opacity-70">Nombre *</span>
                </div>
                <input
                    class="input input-bordered input-sm bg-base-100"
                    type="text"
                    bind:value={fNombre}
                    required
                />
            </label>
            <label class="form-control">
                <div class="label">
                    <span class="label-text font-semibold opacity-70">Dirección</span>
                </div>
                <input
                    class="input input-bordered input-sm bg-base-100"
                    type="text"
                    bind:value={fDireccion}
                    placeholder="ej: Av. Principal 123"
                />
            </label>
            <label class="form-control">
                <div class="label">
                    <span class="label-text font-semibold opacity-70">Coordenadas GPS</span>
                </div>
                <input
                    class="input input-bordered input-sm bg-base-100"
                    type="text"
                    bind:value={fCoordenadas}
                    placeholder="ej: -12.0464, -77.0428"
                />
            </label>
        </div>

        <label class="form-control">
            <div class="label">
                <span class="label-text font-semibold opacity-70">Virtual Rack (JSON)</span>
                <span class="label-text-alt opacity-40">Opcional</span>
            </div>
            <textarea
                class="textarea textarea-bordered textarea-sm font-mono bg-base-100"
                bind:value={fRackJson}
                rows="3"
                placeholder="Formato JSON estructural del rack"
            ></textarea>
        </label>

        <div style="text-align:right;">
            <button
                type="submit"
                class="btn btn-primary btn-sm px-6"
                disabled={savingGeneral}>Guardar</button
            >
        </div>
    </form>
</div>

<script lang="ts">
    import { updateZona } from "$lib/api";
    import { notify } from "$lib/stores/notifications";
    import type { ZonaDetail } from "$lib/types/zona";

    let { zona, zonaId, canEdit = false, onsave } = $props<{
        zona: ZonaDetail;
        zonaId: number;
        canEdit?: boolean;
        onsave?: () => void;
    }>();

    function fmt(val: string | null | undefined): string {
        return val?.trim() ? val : "—";
    }

    // ── Estado de edición ──────────────────────────────────────────────────
    let isEditing = $state(false);
    let fNombre = $state(zona.nombre);
    let fDireccion = $state(zona.direccion ?? "");
    let fCoordenadas = $state(zona.coordenadas_gps ?? "");
    let fRackJson = $state(zona.rack_layout ? JSON.stringify(zona.rack_layout, null, 2) : "");
    let saving = $state(false);
    let errorMsg = $state<string | null>(null);

    $effect(() => {
        fNombre = zona.nombre;
        fDireccion = zona.direccion ?? "";
        fCoordenadas = zona.coordenadas_gps ?? "";
        fRackJson = zona.rack_layout ? JSON.stringify(zona.rack_layout, null, 2) : "";
    });

    async function save() {
        saving = true;
        errorMsg = null;
        try {
            let rack: Record<string, unknown> | null = null;
            if (fRackJson.trim()) rack = JSON.parse(fRackJson);
            await updateZona(zonaId, {
                nombre: fNombre.trim(),
                direccion: fDireccion.trim() || null,
                coordenadas_gps: fCoordenadas.trim() || null,
                rack_layout: rack,
            });
            notify.success("Datos generales guardados.");
            isEditing = false;
            if (onsave) onsave();
        } catch (e: any) {
            errorMsg = e instanceof SyntaxError
                ? "JSON del Virtual Rack inválido."
                : (e?.response?.data?.detail ?? "Error al guardar.");
        } finally {
            saving = false;
        }
    }
</script>

<div class="glass-card-flat" style="border-radius:1rem;padding:1.5rem;">
    {#if isEditing}
        <!-- ── MODO EDICIÓN ──────────────────────────────────────────── -->
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1.5rem;">
            <h3 style="margin:0;font-size:1.1rem;font-weight:700;opacity:0.9;">📋 Editar Datos Generales</h3>
            <div style="display:flex;align-items:center;gap:0.5rem;">
                {#if saving}<span class="loading loading-spinner loading-sm text-primary"></span>{/if}
                <button type="button" class="btn btn-xs btn-neutral" onclick={() => (isEditing = false)}>Cancelar</button>
            </div>
        </div>

        <form onsubmit={(e) => { e.preventDefault(); save(); }} style="display:flex;flex-direction:column;gap:1.25rem;">
            {#if errorMsg}
                <div class="alert alert-error py-2">
                    <span style="font-size:0.85rem;">{errorMsg}</span>
                </div>
            {/if}

            <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(250px, 1fr));gap:1rem;">
                <label class="form-control">
                    <div class="label"><span class="label-text font-semibold opacity-70">Nombre *</span></div>
                    <input class="input input-bordered input-sm bg-base-100" type="text" bind:value={fNombre} required />
                </label>
                <label class="form-control">
                    <div class="label"><span class="label-text font-semibold opacity-70">Dirección</span></div>
                    <input class="input input-bordered input-sm bg-base-100" type="text" bind:value={fDireccion} placeholder="ej: Av. Principal 123" />
                </label>
                <label class="form-control">
                    <div class="label"><span class="label-text font-semibold opacity-70">Coordenadas GPS</span></div>
                    <input class="input input-bordered input-sm bg-base-100" type="text" bind:value={fCoordenadas} placeholder="ej: -12.0464, -77.0428" />
                </label>
            </div>

            <label class="form-control">
                <div class="label">
                    <span class="label-text font-semibold opacity-70">Virtual Rack (JSON)</span>
                    <span class="label-text-alt opacity-40">Opcional</span>
                </div>
                <textarea class="textarea textarea-bordered textarea-sm font-mono bg-base-100" bind:value={fRackJson} rows="3" placeholder="Formato JSON estructural del rack"></textarea>
            </label>

            <div style="text-align:right;">
                <button type="submit" class="btn btn-primary btn-sm px-6" disabled={saving}>Guardar</button>
            </div>
        </form>

    {:else}
        <!-- ── MODO LECTURA ──────────────────────────────────────────── -->
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1.5rem;">
            <h3 style="margin:0;font-size:1.1rem;font-weight:700;opacity:0.9;">📋 Datos Generales</h3>
            {#if canEdit}
                <button type="button" class="btn btn-xs btn-outline btn-primary" onclick={() => (isEditing = true)}>✏️ Editar</button>
            {/if}
        </div>

        <table style="width:100%;border-collapse:collapse;">
            <tbody>
                {#each [
                    { label: "Nombre", value: zona.nombre },
                    { label: "Dirección", value: fmt(zona.direccion) },
                    { label: "Coordenadas GPS", value: fmt(zona.coordenadas_gps) },
                ] as row}
                    <tr style="border-bottom:1px solid oklch(from var(--color-base-content) l c h / 0.07);">
                        <td style="padding:0.75rem 1rem 0.75rem 0;font-size:0.78rem;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;opacity:0.4;width:11rem;vertical-align:top;">{row.label}</td>
                        <td style="padding:0.75rem 0;font-size:0.9rem;">{row.value}</td>
                    </tr>
                {/each}
            </tbody>
        </table>

        {#if zona.rack_layout && Object.keys(zona.rack_layout).length > 0}
            <div style="margin-top:1.25rem;">
                <p style="font-size:0.73rem;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;opacity:0.4;margin:0 0 0.5rem;">Virtual Rack (JSON)</p>
                <pre style="background:oklch(from var(--color-base-content) l c h / 0.05);padding:1rem;border-radius:0.5rem;font-size:0.75rem;overflow:auto;max-height:200px;">{JSON.stringify(zona.rack_layout, null, 2)}</pre>
            </div>
        {/if}
    {/if}
</div>

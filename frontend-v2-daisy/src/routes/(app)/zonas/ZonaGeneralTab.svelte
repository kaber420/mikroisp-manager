<script lang="ts">
    import type { ZonaDetail } from "$lib/types/zona";

    let { zona } = $props<{ zona: ZonaDetail }>();

    function fmt(val: string | null | undefined): string {
        return val?.trim() ? val : "—";
    }
</script>

<div class="glass-card-flat" style="padding:1.5rem;border-radius:1rem;">
    <table style="width:100%;border-collapse:collapse;">
        <tbody>
            {#each [
                { label: "Nombre", value: zona.nombre },
                { label: "Dirección", value: fmt(zona.direccion) },
                { label: "Coordenadas GPS", value: fmt(zona.coordenadas_gps) },
            ] as row}
                <tr style="border-bottom:1px solid oklch(from var(--color-base-content) l c h / 0.07);">
                    <td
                        style="padding:0.75rem 1rem 0.75rem 0;font-size:0.78rem;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;opacity:0.4;width:11rem;vertical-align:top;"
                        >{row.label}</td
                    >
                    <td style="padding:0.75rem 0;font-size:0.9rem;">{row.value}</td>
                </tr>
            {/each}
        </tbody>
    </table>

    {#if zona.rack_layout && Object.keys(zona.rack_layout).length > 0}
        <div style="margin-top:1.25rem;">
            <p
                style="font-size:0.73rem;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;opacity:0.4;margin:0 0 0.5rem;"
            >
                Virtual Rack (JSON)
            </p>
            <pre
                style="background:oklch(from var(--color-base-content) l c h / 0.05);padding:1rem;border-radius:0.5rem;font-size:0.75rem;overflow:auto;max-height:200px;"
                >{JSON.stringify(zona.rack_layout, null, 2)}</pre
            >
        </div>
    {/if}
</div>

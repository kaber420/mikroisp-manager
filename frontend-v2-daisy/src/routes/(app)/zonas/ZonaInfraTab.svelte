<script lang="ts">
    import type { ZonaDetail } from "$lib/types/zona";

    let { zona, zonaId } = $props<{ zona: ZonaDetail; zonaId: number }>();

    function fmt(val: string | null | undefined): string {
        return val?.trim() ? val : "—";
    }

    function fmtDate(val: string | null | undefined): string {
        if (!val) return "—";
        try {
            return new Date(val).toLocaleDateString("es", {
                day: "2-digit",
                month: "short",
                year: "numeric",
            });
        } catch {
            return val;
        }
    }
</script>

<div class="glass-card-flat" style="padding:1.5rem;border-radius:1rem;">
    {#if zona.infraestructura}
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
                        <td
                            style="padding:0.75rem 1rem 0.75rem 0;font-size:0.78rem;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;opacity:0.4;width:13rem;vertical-align:top;"
                            >{row.label}</td
                        >
                        <td
                            style="padding:0.75rem 0;font-size:0.9rem;font-family:{row.mono ? 'monospace' : 'inherit'};"
                            >{row.value}</td
                        >
                    </tr>
                {/each}
            </tbody>
        </table>
    {:else}
        <div style="text-align:center;padding:2.5rem;opacity:0.5;">
            <p style="font-size:2rem;margin:0 0 0.5rem;">🔌</p>
            <p style="margin:0;font-size:0.9rem;">Sin datos de infraestructura configurados.</p>
            <a href="/zonas/{zonaId}/editar" class="btn btn-sm btn-outline mt-4"
                >Configurar infraestructura</a
            >
        </div>
    {/if}
</div>

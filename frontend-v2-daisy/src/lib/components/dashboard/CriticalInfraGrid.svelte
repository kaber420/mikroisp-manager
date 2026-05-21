<script lang="ts">
    // Propiedades usando runas de Svelte 5
    let { stats } = $props<{
        stats: {
            cpes: { total_cpes: number; active: number };
            routers: { total_routers: number; online: number };
            aps: { total_aps: number; online: number };
            switches: { total_switches: number; online: number };
        };
    }>();

    // --- Infraestructura Crítica (Grid Superior - 4 cards) ---
    let infraStats = $derived([
        {
            label: "CPEs",
            value: stats?.cpes?.total_cpes ?? 0,
            active: stats?.cpes?.active ?? 0,
            offline:
                (stats?.cpes?.total_cpes ?? 0) -
                (stats?.cpes?.active ?? 0),
            percent:
                (stats?.cpes?.total_cpes ?? 0) > 0
                    ? Math.round(
                          ((stats?.cpes?.active ?? 0) /
                              (stats?.cpes?.total_cpes ?? 1)) *
                              100,
                      )
                    : 0,
            icon: "📡",
            color: "blue",
        },
        {
            label: "Routers",
            value: stats?.routers?.total_routers ?? 0,
            active: stats?.routers?.online ?? 0,
            offline:
                (stats?.routers?.total_routers ?? 0) -
                (stats?.routers?.online ?? 0),
            percent:
                (stats?.routers?.total_routers ?? 0) > 0
                    ? Math.round(
                          ((stats?.routers?.online ?? 0) /
                              (stats?.routers?.total_routers ?? 1)) *
                              100,
                      )
                    : 0,
            icon: "🔀",
            color: "violet",
        },
        {
            label: "Access Points",
            value: stats?.aps?.total_aps ?? 0,
            active: stats?.aps?.online ?? 0,
            offline:
                (stats?.aps?.total_aps ?? 0) - (stats?.aps?.online ?? 0),
            percent:
                (stats?.aps?.total_aps ?? 0) > 0
                    ? Math.round(
                          ((stats?.aps?.online ?? 0) /
                              (stats?.aps?.total_aps ?? 1)) *
                              100,
                      )
                    : 0,
            icon: "📶",
            color: "sky",
        },
        {
            label: "Switches",
            value: stats?.switches?.total_switches ?? 0,
            active: stats?.switches?.online ?? 0,
            offline:
                (stats?.switches?.total_switches ?? 0) -
                (stats?.switches?.online ?? 0),
            percent:
                (stats?.switches?.total_switches ?? 0) > 0
                    ? Math.round(
                          ((stats?.switches?.online ?? 0) /
                              (stats?.switches?.total_switches ?? 1)) *
                              100,
                      )
                    : 0,
            icon: "🔌",
            color: "emerald",
        },
    ]);

    const colorMap: Record<string, any> = {
        blue: {
            text: "text-blue-400",
            bgLight: "bg-blue-500/10",
            borderLight: "border-blue-500/20",
            glow: "drop-shadow-[0_0_8px_rgba(59,130,246,0.3)]",
            blob: "bg-blue-500/10 group-hover:bg-blue-500/15",
        },
        violet: {
            text: "text-purple-400",
            bgLight: "bg-purple-500/10",
            borderLight: "border-purple-500/20",
            glow: "drop-shadow-[0_0_8px_rgba(168,85,247,0.3)]",
            blob: "bg-purple-500/10 group-hover:bg-purple-500/15",
        },
        sky: {
            text: "text-sky-400",
            bgLight: "bg-sky-500/10",
            borderLight: "border-sky-500/20",
            glow: "drop-shadow-[0_0_8px_rgba(14,165,233,0.3)]",
            blob: "bg-sky-500/10 group-hover:bg-sky-500/15",
        },
        emerald: {
            text: "text-emerald-400",
            bgLight: "bg-emerald-500/10",
            borderLight: "border-emerald-500/20",
            glow: "drop-shadow-[0_0_8px_rgba(16,185,129,0.3)]",
            blob: "bg-emerald-500/10 group-hover:bg-emerald-500/15",
        },
    };
</script>

<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
    {#each infraStats as stat}
        {@const theme = colorMap[stat.color] || colorMap.blue}
        <div
            class="glass-panel-dona p-5 flex items-center justify-between group relative overflow-hidden"
        >
            <!-- Columna izquierda: Datos -->
            <div class="flex flex-col z-10">
                <span
                    class="text-[11px] font-bold tracking-[0.15em] text-slate-400 uppercase mb-1"
                >
                    {stat.label}
                </span>
                <span
                    class="text-3xl font-extrabold text-white leading-none"
                >
                    {stat.value}
                </span>
                <!-- Badges de Up / Down -->
                <div class="mt-3 flex gap-2 text-xs">
                    <span
                        class="bg-emerald-500/10 text-emerald-400 border-emerald-500/20 px-2 py-0.5 rounded border font-medium"
                    >
                        {stat.active}
                    </span>
                    <span
                        class="bg-rose-500/10 text-rose-400 border-rose-500/20 px-2 py-0.5 rounded border font-medium"
                    >
                        {stat.offline}
                    </span>
                </div>
            </div>

            <!-- Columna derecha: Dona (Radial Progress) -->
            <div
                class="z-10 {theme.text} radial-progress donut-sm {theme.glow}"
                style="--value:{stat.percent};"
                role="progressbar"
            >
                <span class="text-white text-xs font-bold"
                    >{stat.percent}%</span
                >
            </div>

            <!-- Fondo mancha -->
            <div
                class="absolute right-0 top-0 w-32 h-32 blur-[40px] rounded-full pointer-events-none transition-colors {theme.blob}"
            ></div>
        </div>
    {/each}
</div>

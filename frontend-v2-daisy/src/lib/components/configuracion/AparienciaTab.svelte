<script lang="ts">
    import { theme } from "$lib/stores/theme";

    const availableThemes = [
        { id: "light", label: "Claro", desc: "Modo claro estándar" },
        { id: "dark", label: "Oscuro", desc: "Modo oscuro clásico" },
        { id: "corporate", label: "Corporate", desc: "Claro profesional" },
        { id: "dracula", label: "Dracula", desc: "Púrpura y rosa" },
        { id: "cyberpunk", label: "Cyberpunk", desc: "Amarillo neón" },
        { id: "dim", label: "Dim", desc: "Oscuro suave" },
        { id: "synthwave", label: "Synthwave", desc: "Retro neón 80s" },
        { id: "night", label: "Noche", desc: "Azul oscuro profundo" },
        { id: "forest", label: "Forest", desc: "Oscuro y ecológico" },
        { id: "garden", label: "Garden", desc: "Claro y floral" },
        { id: "business", label: "Business", desc: "Oscuro y elegante" },
    ];

    function setTheme(themeId: any) {
        theme.setTheme(themeId);
    }

    function toggleLavaLamp() {
        theme.toggleLavaLamp();
    }
</script>

<div class="card bg-base-100 shadow-xl border border-base-200">
    <div class="card-body">
        <h2 class="text-lg font-semibold mb-1 flex items-center gap-2">
            🎨 Tema Visual
        </h2>
        <p class="text-sm text-base-content/60 mb-6">
            Personaliza la apariencia. El cambio es inmediato y se guarda en
            este navegador.
        </p>

        <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
            {#each availableThemes as t}
                <button
                    class="relative rounded-xl border-2 p-5 text-left transition-all duration-200 cursor-pointer
                        {$theme.current === t.id
                        ? 'border-primary bg-primary/10 shadow-lg'
                        : 'border-base-300 hover:border-base-content/40 bg-base-200/50'}"
                    onclick={() => setTheme(t.id)}
                >
                    <!-- Preview color strip -->
                    <div
                        data-theme={t.id}
                        class="rounded-lg h-14 mb-3 overflow-hidden flex gap-1 p-2 bg-base-100"
                    >
                        <div class="flex-1 rounded bg-primary"></div>
                        <div class="flex-1 rounded bg-secondary"></div>
                        <div class="flex-1 rounded bg-accent"></div>
                    </div>
                    <p class="font-bold text-sm">{t.label}</p>
                    <p class="text-xs text-base-content/60">{t.desc}</p>
                    {#if $theme.current === t.id}
                        <span
                            class="absolute top-2 right-2 text-primary text-lg"
                            >✓</span
                        >
                    {/if}
                </button>
            {/each}
        </div>

        <div class="divider"></div>

        <div
            class="flex items-center justify-between p-4 bg-base-200 rounded-lg border border-base-300"
        >
            <div>
                <h3 class="font-bold text-lg">
                    🌋 Fondo Animado Lava Lamp
                </h3>
                <p class="text-sm text-base-content/60">
                    Activa círculos abstractos flotantes que reaccionan a
                    los colores del tema actual.
                </p>
            </div>
            <div>
                <input
                    type="checkbox"
                    class="toggle toggle-primary toggle-lg"
                    checked={$theme.lavaLampActive}
                    onchange={toggleLavaLamp}
                />
            </div>
        </div>
    </div>
</div>

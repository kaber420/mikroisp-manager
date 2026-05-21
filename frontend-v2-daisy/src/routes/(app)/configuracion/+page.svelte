<script lang="ts">
    import { onMount } from "svelte";
    import { getSettings } from "$lib/api";
    import { notify } from "$lib/stores/notifications";

    // Subcomponentes de cada pestaña
    import GeneralTab from "$lib/components/configuracion/GeneralTab.svelte";
    import AuditoriaTab from "$lib/components/configuracion/AuditoriaTab.svelte";
    import BotsTab from "$lib/components/configuracion/BotsTab.svelte";
    import AparienciaTab from "$lib/components/configuracion/AparienciaTab.svelte";
    import InfraestructuraTab from "$lib/components/configuracion/InfraestructuraTab.svelte";

    // ─── Estado de tabs ────────────────────────────────────────────────
    let activeTab = $state<
        "general" | "auditoria" | "bots" | "apariencia" | "infraestructura" | "videollamadas"
    >("general");

    // ─── Estado compartido ─────────────────────────────────────────────
    let generalSettings = $state<Record<string, string>>({});
    let generalLoading = $state(true);

    async function loadGeneralSettings() {
        try {
            generalSettings = await getSettings();
        } catch {
            notify.error("Error al cargar configuración");
        } finally {
            generalLoading = false;
        }
    }

    onMount(async () => {
        await loadGeneralSettings();
    });
</script>

<svelte:head>
    <title>Configuración Global — OmniWISP</title>
</svelte:head>

<!-- ── HEADER ─────────────────────────────────────────────────────────── -->
<div
    class="glass-card-flat mb-6"
    style="border-radius:1rem;display:flex;flex-direction:column;overflow:hidden;"
>
    <!-- Título y descripción -->
    <div
        style="padding:1.25rem 1.5rem;display:flex;flex-direction:column;gap:0.75rem;"
    >
        <div
            style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:0.75rem;"
        >
            <div>
                <h1 style="margin:0;font-size:1.5rem;font-weight:800;">
                    Configuración Global
                </h1>
                <p style="margin:0.25rem 0 0;font-size:0.85rem;opacity:0.5;">
                    Ajustes del sistema, facturación, bots e infraestructura.
                </p>
            </div>
        </div>
    </div>

    <!-- Pestañas de Navegación integradas al header -->
    <div
        style="background:oklch(from var(--color-base-content) l c h / 0.02);border-top:1px solid oklch(from var(--color-base-content) l c h / 0.08);padding:0 1.5rem;display:flex;gap:1.5rem;"
        role="tablist"
    >
        <button
            role="tab"
            aria-selected={activeTab === "general"}
            onclick={() => (activeTab = "general")}
            style="padding:0.85rem 0;font-size:0.85rem;font-weight:{activeTab ===
            'general'
                ? '800'
                : '600'};color:{activeTab === 'general'
                ? 'oklch(from var(--color-primary) l c h)'
                : 'inherit'};opacity:{activeTab === 'general'
                ? '1'
                : '0.5'};border-bottom:3px solid {activeTab === 'general'
                ? 'oklch(from var(--color-primary) l c h)'
                : 'transparent'};background:none;cursor:pointer;transition:all 0.2s;"
        >
            ⚙️ General
        </button>
        <button
            role="tab"
            aria-selected={activeTab === "auditoria"}
            onclick={() => (activeTab = "auditoria")}
            style="padding:0.85rem 0;font-size:0.85rem;font-weight:{activeTab ===
            'auditoria'
                ? '800'
                : '600'};color:{activeTab === 'auditoria'
                ? 'oklch(from var(--color-primary) l c h)'
                : 'inherit'};opacity:{activeTab === 'auditoria'
                ? '1'
                : '0.5'};border-bottom:3px solid {activeTab === 'auditoria'
                ? 'oklch(from var(--color-primary) l c h)'
                : 'transparent'};background:none;cursor:pointer;transition:all 0.2s;"
        >
            🛡️ Auditoría
        </button>
        <button
            role="tab"
            aria-selected={activeTab === "bots"}
            onclick={() => (activeTab = "bots")}
            style="padding:0.85rem 0;font-size:0.85rem;font-weight:{activeTab ===
            'bots'
                ? '800'
                : '600'};color:{activeTab === 'bots'
                ? 'oklch(from var(--color-primary) l c h)'
                : 'inherit'};opacity:{activeTab === 'bots'
                ? '1'
                : '0.5'};border-bottom:3px solid {activeTab === 'bots'
                ? 'oklch(from var(--color-primary) l c h)'
                : 'transparent'};background:none;cursor:pointer;transition:all 0.2s;"
        >
            🤖 Bots
        </button>
        <button
            role="tab"
            aria-selected={activeTab === "apariencia"}
            onclick={() => (activeTab = "apariencia")}
            style="padding:0.85rem 0;font-size:0.85rem;font-weight:{activeTab ===
            'apariencia'
                ? '800'
                : '600'};color:{activeTab === 'apariencia'
                ? 'oklch(from var(--color-primary) l c h)'
                : 'inherit'};opacity:{activeTab === 'apariencia'
                ? '1'
                : '0.5'};border-bottom:3px solid {activeTab === 'apariencia'
                ? 'oklch(from var(--color-primary) l c h)'
                : 'transparent'};background:none;cursor:pointer;transition:all 0.2s;"
        >
            🎨 Apariencia
        </button>
        <button
            role="tab"
            aria-selected={activeTab === "infraestructura"}
            onclick={() => (activeTab = "infraestructura")}
            style="padding:0.85rem 0;font-size:0.85rem;font-weight:{activeTab ===
            'infraestructura'
                ? '800'
                : '600'};color:{activeTab === 'infraestructura'
                ? 'oklch(from var(--color-primary) l c h)'
                : 'inherit'};opacity:{activeTab === 'infraestructura'
                ? '1'
                : '0.5'};border-bottom:3px solid {activeTab === 'infraestructura'
                ? 'oklch(from var(--color-primary) l c h)'
                : 'transparent'};background:none;cursor:pointer;transition:all 0.2s;"
        >
            ⛴️ Infraestructura
        </button>
        <button
            role="tab"
            aria-selected={activeTab === "videollamadas"}
            onclick={() => (activeTab = "videollamadas")}
            style="padding:0.85rem 0;font-size:0.85rem;font-weight:{activeTab ===
            'videollamadas'
                ? '800'
                : '600'};color:{activeTab === 'videollamadas'
                ? 'oklch(from var(--color-primary) l c h)'
                : 'inherit'};opacity:{activeTab === 'videollamadas'
                ? '1'
                : '0.5'};border-bottom:3px solid {activeTab === 'videollamadas'
                ? 'oklch(from var(--color-primary) l c h)'
                : 'transparent'};background:none;cursor:pointer;transition:all 0.2s;"
        >
            🎥 Videollamadas
        </button>
    </div>
</div>

<!-- ─── CONTENIDOS DE LAS PESTAÑAS ──────────────────────────────────── -->

<!-- TAB 1: GENERAL -->
{#if activeTab === "general"}
    {#if generalLoading}
        <div class="flex justify-center py-16">
            <span class="loading loading-spinner loading-lg"></span>
        </div>
    {:else}
        <GeneralTab bind:generalSettings />
    {/if}
{/if}

<!-- TAB 2: AUDITORÍA -->
{#if activeTab === "auditoria"}
    <AuditoriaTab />
{/if}

<!-- TAB 3: BOTS -->
{#if activeTab === "bots"}
    {#if generalLoading}
        <div class="flex justify-center py-16">
            <span class="loading loading-spinner loading-lg"></span>
        </div>
    {:else}
        <BotsTab bind:generalSettings />
    {/if}
{/if}

<!-- TAB 4: APARIENCIA -->
{#if activeTab === "apariencia"}
    <AparienciaTab />
{/if}

<!-- TAB 5: INFRAESTRUCTURA -->
{#if activeTab === "infraestructura"}
    <InfraestructuraTab />
{/if}

<!-- TAB 6: VIDEOLLAMADAS (REDIRECCIÓN) -->
{#if activeTab === "videollamadas"}
    <div class="card bg-base-100 shadow-xl border border-base-200">
        <div class="card-body items-center text-center py-20">
            <span class="text-6xl mb-6">🚀</span>
            <h2 class="text-2xl font-bold">Panel Unificado</h2>
            <p class="max-w-md opacity-60">
                La configuración de videollamadas ahora forma parte del centro de infraestructura para una gestión más intuitiva.
            </p>
            <button class="btn btn-primary mt-6" onclick={() => activeTab = "infraestructura"}>
                Ir a Infraestructura
            </button>
        </div>
    </div>
{/if}

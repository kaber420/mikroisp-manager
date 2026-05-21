<script lang="ts">
    import { onMount } from "svelte";
    import { page } from "$app/stores";
    import { getZonaDetails } from "$lib/api";
    import type { ZonaDetail } from "$lib/types/zona";
    import ZonaEditGeneralTab from "../../ZonaEditGeneralTab.svelte";
    import ZonaEditInfraTab from "../../ZonaEditInfraTab.svelte";
    import ZonaEditNotasTab from "../../ZonaEditNotasTab.svelte";
    import ZonaEditDocsTab from "../../ZonaEditDocsTab.svelte";

    const zonaId = Number($page.params.id);

    let activeTab = $state<"general" | "infra" | "notas" | "documentos">("general");
    let zona = $state<ZonaDetail | null>(null);
    let loading = $state(true);
    let pageError = $state<string | null>(null);

    async function loadDetalle() {
        loading = true;
        pageError = null;
        try {
            const res = await getZonaDetails(zonaId);
            zona = { notes: [], documentos: [], ...res };
        } catch (e: any) {
            pageError = e?.response?.data?.detail ?? "Error al cargar la zona.";
        } finally {
            loading = false;
        }
    }

    onMount(loadDetalle);
</script>

<!-- ── CABECERA ──────────────────────────────────────────────────────────── -->
<div class="mb-6" style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:1rem;">
    <div style="display:flex;align-items:center;">
        <h2 style="font-size:1.5rem;font-weight:700;margin:0;display:flex;align-items:center;gap:0.5rem;">
            ✏️ {zona ? `Editar: ${zona.nombre}` : "Cargando..."}
        </h2>
    </div>
    <div style="display:flex;align-items:center;gap:0.5rem;">
        <a href="/zonas" class="btn btn-ghost btn-sm">← Zonas</a>
        {#if zona}
            <a href="/zonas/{zonaId}" class="btn btn-primary btn-sm">Ver Detalle</a>
        {/if}
    </div>
</div>

{#if loading}
    <div class="glass-card-flat" style="padding:2rem;border-radius:1rem;">
        {#each Array(5) as _}
            <div style="height:1.1rem;border-radius:0.3rem;background:oklch(from var(--color-base-content) l c h / 0.08);margin-bottom:0.75rem;animation:pulseSkel 1.5s infinite;"></div>
        {/each}
    </div>

{:else if pageError}
    <div class="alert alert-error shadow-sm">
        <span>{pageError}</span>
        <a href="/zonas" class="btn btn-xs btn-ghost">← Volver</a>
    </div>

{:else if zona}
    <!-- ── TABS ─────────────────────────────────────────────────────────────── -->
    <div role="tablist" class="tabs tabs-lifted tabs-lg mb-6">
        <button role="tab" class="tab {activeTab === 'general' ? 'tab-active font-bold' : ''}" onclick={() => (activeTab = "general")}>Generales</button>
        <button role="tab" class="tab {activeTab === 'infra' ? 'tab-active font-bold' : ''}" onclick={() => (activeTab = "infra")}>Infraestructura</button>
        <button role="tab" class="tab {activeTab === 'notas' ? 'tab-active font-bold' : ''}" onclick={() => (activeTab = "notas")}>Notas ({zona.notes.length})</button>
        <button role="tab" class="tab {activeTab === 'documentos' ? 'tab-active font-bold' : ''}" onclick={() => (activeTab = "documentos")}>Documentos ({zona.documentos.length})</button>
    </div>

    <!-- ── TAB CONTENT ────────────────────────────────────────────────────── -->
    <div style="display:flex;flex-direction:column;gap:1.5rem;">
        {#if activeTab === "general"}
            <ZonaEditGeneralTab {zona} {zonaId} onsave={loadDetalle} />
        {:else if activeTab === "infra"}
            <ZonaEditInfraTab {zona} {zonaId} onsave={loadDetalle} />
        {:else if activeTab === "notas"}
            <ZonaEditNotasTab {zona} onsave={loadDetalle} />
        {:else if activeTab === "documentos"}
            <ZonaEditDocsTab {zona} {zonaId} onsave={loadDetalle} />
        {/if}
    </div>
{/if}

<style>
    @keyframes pulseSkel {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
    }
</style>

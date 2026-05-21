<script lang="ts">
    import { onMount } from "svelte";
    import { page } from "$app/stores";
    import { getZonaDetails } from "$lib/api";
    import type { ZonaDetail } from "$lib/types/zona";
    import ZonaGeneralTab from "../ZonaGeneralTab.svelte";
    import ZonaInfraTab from "../ZonaInfraTab.svelte";
    import ZonaNotasTab from "../ZonaNotasTab.svelte";
    import ZonaDocsTab from "../ZonaDocsTab.svelte";

    const zonaId = Number($page.params.id);

    let zona = $state<ZonaDetail | null>(null);
    let loading = $state(true);
    let pageError = $state<string | null>(null);
    let activeTab = $state<"general" | "infra" | "notas" | "docs">("general");
    let editMode = $state(false);

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

    function activateEdit() {
        editMode = true;
    }

    onMount(loadDetalle);
</script>

<!-- ── BREADCRUMB ──────────────────────────────────────────────────────── -->
<div class="breadcrumbs text-sm mb-4 opacity-60">
    <ul>
        <li><a href="/zonas">Zonas</a></li>
        <li>{loading ? "…" : (zona?.nombre ?? "Zona")}</li>
    </ul>
</div>

{#if loading}
    <!-- Skeleton -->
    <div class="flex flex-col gap-4">
        <div class="glass-card-flat" style="padding:1.5rem;border-radius:1rem;">
            <div class="h-6 rounded-lg mb-3" style="background:oklch(from var(--color-base-content) l c h / 0.07);animation:pulseSkel 1.4s infinite;width:40%;"></div>
            <div class="h-4 rounded-lg mb-2" style="background:oklch(from var(--color-base-content) l c h / 0.05);animation:pulseSkel 1.4s infinite;width:25%;"></div>
        </div>
        <div class="glass-card-flat" style="padding:1.5rem;border-radius:1rem;">
            {#each Array(5) as _}
                <div style="height:1.1rem;border-radius:0.3rem;background:oklch(from var(--color-base-content) l c h / 0.07);margin-bottom:0.75rem;animation:pulseSkel 1.4s infinite;"></div>
            {/each}
        </div>
    </div>

{:else if pageError}
    <div class="alert alert-error shadow-sm">
        <span>{pageError}</span>
        <a href="/zonas" class="btn btn-xs btn-ghost">← Volver</a>
    </div>

{:else if zona}
    <!-- ── ENCABEZADO ────────────────────────────────────────────────────── -->
    <div class="glass-card-flat" style="padding:1.25rem 1.5rem;border-radius:1rem;margin-bottom:1.25rem;display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:1rem;">
        <div>
            <h2 style="font-size:1.4rem;font-weight:800;margin:0;display:flex;align-items:center;gap:0.5rem;">
                🗺️ {zona.nombre}
                {#if editMode}
                    <span class="badge badge-warning badge-sm">✏️ Editando</span>
                {/if}
            </h2>
            {#if zona.direccion}
                <p style="margin:0.3rem 0 0;font-size:0.85rem;opacity:0.5;">📍 {zona.direccion}</p>
            {/if}
            <div style="display:flex;gap:0.75rem;margin-top:0.6rem;flex-wrap:wrap;">
                <span class="badge badge-neutral badge-sm">📝 {zona.notes.length} nota{zona.notes.length !== 1 ? 's' : ''}</span>
                <span class="badge badge-neutral badge-sm">📄 {zona.documentos.length} doc{zona.documentos.length !== 1 ? 's' : ''}</span>
            </div>
        </div>
        <div style="display:flex;gap:0.5rem;align-items:center;">
            <a href="/zonas" class="btn btn-ghost btn-sm">← Volver</a>
            {#if editMode}
                <button class="btn btn-sm btn-neutral" onclick={() => (editMode = false)}>👁 Solo lectura</button>
            {:else}
                <button class="btn btn-primary btn-sm" onclick={() => (editMode = true)}>✏️ Editar</button>
            {/if}
        </div>
    </div>

    <!-- ── TABS ──────────────────────────────────────────────────────────── -->
    <div class="tabs tabs-bordered mb-5">
        <button class="tab {activeTab === 'general' ? 'tab-active font-semibold' : ''}" onclick={() => (activeTab = "general")}>📋 General</button>
        <button class="tab {activeTab === 'infra' ? 'tab-active font-semibold' : ''}" onclick={() => (activeTab = "infra")}>🔌 Infraestructura</button>
        <button class="tab {activeTab === 'notas' ? 'tab-active font-semibold' : ''}" onclick={() => (activeTab = "notas")}>
            📝 Notas
            {#if zona.notes.length > 0}<span class="badge badge-primary badge-xs ml-1">{zona.notes.length}</span>{/if}
        </button>
        <button class="tab {activeTab === 'docs' ? 'tab-active font-semibold' : ''}" onclick={() => (activeTab = "docs")}>
            📄 Documentos
            {#if zona.documentos.length > 0}<span class="badge badge-neutral badge-xs ml-1">{zona.documentos.length}</span>{/if}
        </button>
    </div>

    <!-- ── TAB CONTENT ───────────────────────────────────────────────────── -->
    {#if activeTab === "general"}
        <ZonaGeneralTab {zona} {zonaId} {editMode} onsave={loadDetalle} />
    {:else if activeTab === "infra"}
        <ZonaInfraTab {zona} {zonaId} {editMode} onsave={loadDetalle} onedit={activateEdit} />
    {:else if activeTab === "notas"}
        <ZonaNotasTab {zona} {zonaId} {editMode} onsave={loadDetalle} onedit={activateEdit} />
    {:else if activeTab === "docs"}
        <ZonaDocsTab {zona} {zonaId} {editMode} onsave={loadDetalle} onedit={activateEdit} />
    {/if}
{/if}

<style>
    @keyframes pulseSkel {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.35; }
    }
</style>

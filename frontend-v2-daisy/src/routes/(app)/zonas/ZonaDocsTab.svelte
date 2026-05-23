<script lang="ts">
    import { uploadZonaDocumento, deleteZonaDocumento } from "$lib/api";
    import type { ZonaDetail, ZonaDocumento } from "$lib/types/zona";

    let { zona, zonaId, canEdit = false, onsave } = $props<{
        zona: ZonaDetail;
        zonaId: number;
        canEdit?: boolean;
        onsave?: () => void;
    }>();

    // ── Estado lectura ─────────────────────────────────────────────────────
    let selectedDoc = $state<ZonaDocumento | null>(null);

    // ── Estado edición ─────────────────────────────────────────────────────
    let showDeleteDocModal = $state(false);
    let deleteDocTarget = $state<ZonaDocumento | null>(null);
    let deletingDoc = $state(false);
    let uploadingDoc = $state(false);
    let fileInput = $state<HTMLInputElement | null>(null);

    function isImage(tipo: string): boolean { return tipo === "image"; }

    function getDocIcon(tipo: string): string {
        if (isImage(tipo)) return "🖼️";
        if (tipo === "pdf") return "📕";
        return "📄";
    }

    function docUrl(doc: ZonaDocumento): string {
        return `/uploads/zonas/${zonaId}/${doc.nombre_guardado}`;
    }

    function fmtDate(val: string | null | undefined): string {
        if (!val) return "—";
        try {
            return new Date(val).toLocaleDateString("es", { day: "2-digit", month: "short", year: "numeric" });
        } catch { return val; }
    }

    async function uploadDoc(e: Event) {
        const target = e.target as HTMLInputElement;
        if (!target.files || target.files.length === 0) return;
        uploadingDoc = true;
        try {
            await uploadZonaDocumento(zonaId, target.files[0]);
            if (onsave) onsave();
        } catch { /* parent handles */ } finally {
            uploadingDoc = false;
            if (fileInput) fileInput.value = "";
        }
    }

    async function confirmDeleteDoc() {
        if (!deleteDocTarget) return;
        deletingDoc = true;
        try {
            await deleteZonaDocumento(deleteDocTarget.id.toString());
            showDeleteDocModal = false; deleteDocTarget = null;
            if (onsave) onsave();
        } catch { showDeleteDocModal = false; }
        finally { deletingDoc = false; }
    }
</script>

<div class="glass-card-flat" style="border-radius:1rem;padding:1.5rem;display:flex;flex-direction:column;gap:1.25rem;">
    <!-- ── CABECERA ────────────────────────────────────────────────────── -->
    <div style="display:flex;align-items:center;justify-content:space-between;">
        <h3 style="margin:0;font-size:1.1rem;font-weight:700;opacity:0.9;">
            📄 Documentos e Imágenes
            {#if zona.documentos.length > 0}
                <span class="badge badge-neutral ml-1">{zona.documentos.length}</span>
            {/if}
        </h3>
        {#if canEdit}
            <div style="display:flex;align-items:center;gap:0.5rem;">
                {#if uploadingDoc}<span class="loading loading-spinner loading-sm text-primary"></span>{/if}
                <input type="file" bind:this={fileInput} onchange={uploadDoc} style="display:none;"
                    accept="image/*,.pdf,.doc,.docx,.xls,.xlsx,.txt" />
                <button class="btn btn-xs btn-primary" disabled={uploadingDoc} onclick={() => fileInput?.click()}>
                    + Subir Documento
                </button>
            </div>
        {/if}
    </div>

    <!-- ── CONTENIDO ───────────────────────────────────────────────────── -->
    {#if zona.documentos.length === 0}
        <div style="text-align:center;padding:3rem 1.5rem;opacity:0.5;">
            <p style="font-size:2.5rem;margin:0 0 0.5rem;">📄</p>
            <p style="margin:0;font-size:0.9rem;">Sin documentos ni imágenes adjuntos.</p>
            {#if canEdit}
                <button class="btn btn-sm btn-outline mt-4" disabled={uploadingDoc} onclick={() => fileInput?.click()}>
                    Subir primer documento
                </button>
            {/if}
        </div>
    {:else}
        <div class="doc-grid">
            {#each zona.documentos as doc}
                <!-- svelte-ignore a11y_click_events_have_key_events -->
                <!-- svelte-ignore a11y_no_static_element_interactions -->
                <div class="doc-card glass-card" onclick={() => { selectedDoc = doc; }} title={doc.nombre_original}>
                    <div class="doc-thumb">
                        {#if isImage(doc.tipo)}
                            <img src={docUrl(doc)} alt={doc.nombre_original} class="doc-thumb-img" loading="lazy" />
                            <div class="doc-thumb-overlay"><span style="font-size:1.5rem;">🔍</span></div>
                        {:else}
                            <div class="doc-icon-bg"><span class="doc-icon-emoji">{getDocIcon(doc.tipo)}</span></div>
                            <div class="doc-thumb-overlay"><span style="font-size:1.5rem;">⬇️</span></div>
                        {/if}

                        <span class="badge badge-sm badge-neutral"
                            style="position:absolute;top:0.5rem;right:0.5rem;opacity:0.9;text-transform:uppercase;font-size:0.6rem;letter-spacing:0.04em;">
                            {doc.tipo}
                        </span>

                        {#if canEdit}
                            <button
                                class="btn btn-xs btn-circle btn-error shadow-sm"
                                style="position:absolute;top:0.5rem;left:0.5rem;z-index:10;opacity:0.9;font-size:0.75rem;padding:0;width:1.55rem;height:1.55rem;min-height:1.55rem;"
                                title="Eliminar documento"
                                onclick={(e) => { e.stopPropagation(); deleteDocTarget = doc; showDeleteDocModal = true; }}
                            >
                                🗑️
                            </button>
                        {/if}
                    </div>
                    <div class="doc-info">
                        <p class="doc-name" title={doc.nombre_original}>{doc.nombre_original}</p>
                        {#if doc.descripcion}<p class="doc-desc" title={doc.descripcion}>{doc.descripcion}</p>{/if}
                        <p class="doc-date">{fmtDate(doc.creado_en)}</p>
                    </div>
                </div>
            {/each}
        </div>
    {/if}
</div>

<!-- ── MODAL Preview Documento (lectura) ─────────────────────────────── -->
{#if selectedDoc}
    <div class="modal modal-open">
        <div class="modal-box w-11/12 max-w-5xl" style="padding:0;overflow:hidden;">
            <div style="padding:1.25rem 1.5rem;border-bottom:1px solid oklch(from var(--color-base-content) l c h / 0.1);display:flex;align-items:center;justify-content:space-between;">
                <h3 style="font-weight:800;font-size:1.05rem;margin:0;">{getDocIcon(selectedDoc.tipo)} {selectedDoc.nombre_original}</h3>
                <button class="btn btn-ghost btn-sm btn-circle" onclick={() => { selectedDoc = null; }}>✕</button>
            </div>
            <div style="padding:1.25rem;display:flex;flex-direction:column;align-items:center;gap:1rem;min-height:40vh;background:oklch(from var(--color-base-200) l c h / 0.5);">
                {#if isImage(selectedDoc.tipo)}
                    <img src={docUrl(selectedDoc)} alt={selectedDoc.nombre_original}
                        style="max-width:100%;max-height:65vh;object-fit:contain;border-radius:0.75rem;box-shadow:0 8px 30px rgba(0,0,0,0.25);" />
                {:else}
                    <div style="text-align:center;padding:2rem;">
                        <span style="font-size:4rem;display:block;margin-bottom:1rem;opacity:0.3;">{getDocIcon(selectedDoc.tipo)}</span>
                        <h4 style="font-weight:700;margin:0 0 0.5rem;">Archivo no previsualizable en línea</h4>
                        <p style="opacity:0.6;font-size:0.9rem;margin:0 0 1.5rem;max-width:30rem;">
                            El formato <strong>{selectedDoc.tipo.toUpperCase()}</strong> no se puede mostrar directamente. Descárgalo para abrirlo.
                        </p>
                        <a href={`/api/zonas/${zonaId}/documentos/${selectedDoc.id}/descargar`}
                            target="_blank" rel="noopener noreferrer" class="btn btn-primary">⬇️ Ver / Descargar</a>
                    </div>
                {/if}
                {#if selectedDoc.descripcion}
                    <div style="padding:0.75rem 1rem;background:oklch(from var(--color-base-100) l c h / 0.8);border-radius:0.5rem;width:100%;font-size:0.85rem;border:1px solid oklch(from var(--color-base-300) l c h / 0.5);">
                        <strong>Descripción:</strong> {selectedDoc.descripcion}
                    </div>
                {/if}
            </div>
            <div style="padding:0.875rem 1.5rem;border-top:1px solid oklch(from var(--color-base-content) l c h / 0.08);display:flex;justify-content:flex-end;gap:0.5rem;">
                {#if isImage(selectedDoc.tipo)}
                    <a href={docUrl(selectedDoc)} target="_blank" rel="noopener noreferrer" class="btn btn-ghost btn-sm">⬇️ Descargar</a>
                {/if}
                <button class="btn btn-neutral btn-sm" onclick={() => { selectedDoc = null; }}>Cerrar</button>
            </div>
        </div>
        <div class="modal-backdrop" onclick={() => { selectedDoc = null; }}
            onkeydown={(e) => { if (e.key === "Escape") selectedDoc = null; }}
            role="button" tabindex="0"><span class="sr-only">Cerrar</span></div>
    </div>
{/if}

<!-- ── MODAL Eliminar Documento (edición) ────────────────────────────── -->
{#if showDeleteDocModal && deleteDocTarget}
    <div style="position:fixed;inset:0;z-index:200;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;padding:1rem;" role="dialog" aria-modal="true">
        <div style="background:var(--color-base-100);border-radius:1rem;width:100%;max-width:380px;box-shadow:0 25px 50px -12px rgba(0,0,0,0.4);padding:1.5rem;display:flex;flex-direction:column;gap:1rem;">
            <h3 style="margin:0;font-size:1.1rem;font-weight:700;color:var(--color-error);">🗑️ Eliminar Documento</h3>
            <p style="margin:0;font-size:0.9rem;opacity:0.8;">¿Eliminar <strong>{deleteDocTarget.nombre_original}</strong>? Se eliminará permanentemente.</p>
            <div style="display:flex;gap:0.5rem;justify-content:flex-end;">
                <button class="btn btn-ghost btn-sm" onclick={() => (showDeleteDocModal = false)}>Cancelar</button>
                <button class="btn btn-error btn-sm" onclick={confirmDeleteDoc} disabled={deletingDoc}>
                    {#if deletingDoc}<span class="loading loading-spinner loading-xs"></span>{/if}
                    Eliminar
                </button>
            </div>
        </div>
    </div>
{/if}

<style>
    .doc-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 1rem; }
    .doc-card { cursor: pointer; display: flex; flex-direction: column; overflow: hidden; border-radius: 0.875rem !important; transition: box-shadow 0.18s ease, transform 0.18s ease; }
    .doc-card:hover { transform: translateY(-3px); }
    .doc-card:hover .doc-thumb-overlay { opacity: 1; }
    .doc-thumb { position: relative; height: 130px; background: oklch(from var(--color-base-200) l c h / 0.7); display: flex; align-items: center; justify-content: center; overflow: hidden; flex-shrink: 0; border-bottom: 1px solid oklch(from var(--color-base-300) l c h / 0.4); }
    .doc-thumb-img { width: 100%; height: 100%; object-fit: cover; }
    .doc-icon-bg { display: flex; align-items: center; justify-content: center; width: 100%; height: 100%; }
    .doc-icon-emoji { font-size: 3rem; opacity: 0.35; }
    .doc-thumb-overlay { position: absolute; inset: 0; background: oklch(from var(--color-base-content) l c h / 0.55); display: flex; align-items: center; justify-content: center; opacity: 0; transition: opacity 0.2s ease; backdrop-filter: blur(2px); }
    .doc-info { padding: 0.75rem; display: flex; flex-direction: column; gap: 0.25rem; }
    .doc-name { font-size: 0.82rem; font-weight: 600; margin: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .doc-desc { font-size: 0.72rem; opacity: 0.55; margin: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .doc-date { font-size: 0.68rem; opacity: 0.38; margin: 0; text-align: right; margin-top: auto; padding-top: 0.25rem; }
</style>

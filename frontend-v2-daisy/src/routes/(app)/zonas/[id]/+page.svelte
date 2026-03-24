<script lang="ts">
    import { onMount } from "svelte";
    import { page } from "$app/stores";
    import { getZonaDetails } from "$lib/api";
    import type { ZonaDetail, ZonaDocumento } from "$lib/types/zona";
    import MarkdownViewer from "$lib/components/MarkdownViewer.svelte";

    const zonaId = Number($page.params.id);

    let zona = $state<ZonaDetail | null>(null);
    let loading = $state(true);
    let pageError = $state<string | null>(null);
    let activeTab = $state<"general" | "infra" | "notas" | "docs">("general");

    let selectedNote = $state<{ title: string; content: string } | null>(null);
    let selectedDoc = $state<ZonaDocumento | null>(null);

    async function loadDetalle() {
        loading = true;
        pageError = null;
        try {
            const res = await getZonaDetails(zonaId);
            // Normalize: ensure arrays always exist even if backend omits them
            zona = {
                notes: [],
                documentos: [],
                ...res,
            };
        } catch (e: any) {
            pageError = e?.response?.data?.detail ?? "Error al cargar la zona.";
        } finally {
            loading = false;
        }
    }

    onMount(loadDetalle);

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

    function isImage(tipo: string): boolean {
        return tipo === "image";
    }

    function getDocIcon(tipo: string): string {
        if (isImage(tipo)) return "🖼️";
        if (tipo === "pdf") return "📕";
        return "📄";
    }

    function docUrl(doc: ZonaDocumento): string {
        // Backend stores files at data/uploads/zonas/{zona_id}/{nombre_guardado}
        // FastAPI mounts /uploads → data/uploads
        return `/uploads/zonas/${zonaId}/${doc.nombre_guardado}`;
    }
</script>

<!-- ── BREADCRUMB ─────────────────────────────────────────────── -->
<div class="breadcrumbs text-sm mb-4 opacity-60">
    <ul>
        <li><a href="/zonas">Zonas</a></li>
        <li>{loading ? "…" : (zona?.nombre ?? "Zona")}</li>
    </ul>
</div>

{#if loading}
    <!-- Skeleton animado -->
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
    <!-- ── ENCABEZADO ─────────────────────────────────────────────── -->
    <div class="glass-card-flat" style="padding:1.25rem 1.5rem;border-radius:1rem;margin-bottom:1.25rem;display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:1rem;">
        <div>
            <h2 style="font-size:1.4rem;font-weight:800;margin:0;display:flex;align-items:center;gap:0.5rem;">
                🗺️ {zona.nombre}
            </h2>
            {#if zona.direccion}
                <p style="margin:0.3rem 0 0;font-size:0.85rem;opacity:0.5;">📍 {zona.direccion}</p>
            {/if}
            <!-- Stats rápidas -->
            <div style="display:flex;gap:0.75rem;margin-top:0.6rem;flex-wrap:wrap;">
                <span class="badge badge-neutral badge-sm">📝 {zona.notes.length} nota{zona.notes.length !== 1 ? 's' : ''}</span>
                <span class="badge badge-neutral badge-sm">📄 {zona.documentos.length} doc{zona.documentos.length !== 1 ? 's' : ''}</span>
            </div>
        </div>
        <div style="display:flex;gap:0.5rem;align-items:center;">
            <a href="/zonas" class="btn btn-ghost btn-sm">← Volver</a>
            <a href="/zonas/{zonaId}/editar" class="btn btn-primary btn-sm">✏️ Editar</a>
        </div>
    </div>

    <!-- ── TABS ───────────────────────────────────────────────────── -->
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

    <!-- ─── TAB GENERAL ─────────────────────────────────────────── -->
    {#if activeTab === "general"}
        <div class="glass-card-flat" style="padding:1.5rem;border-radius:1rem;">
            <table style="width:100%;border-collapse:collapse;">
                <tbody>
                    {#each [{ label: "Nombre", value: zona.nombre }, { label: "Dirección", value: fmt(zona.direccion) }, { label: "Coordenadas GPS", value: fmt(zona.coordenadas_gps) }] as row}
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
        </div>

    <!-- ─── TAB INFRAESTRUCTURA ─────────────────────────────────── -->
    {:else if activeTab === "infra"}
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
                                <td style="padding:0.75rem 1rem 0.75rem 0;font-size:0.78rem;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;opacity:0.4;width:13rem;vertical-align:top;">{row.label}</td>
                                <td style="padding:0.75rem 0;font-size:0.9rem;font-family:{row.mono ? 'monospace' : 'inherit'};">{row.value}</td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            {:else}
                <div style="text-align:center;padding:2.5rem;opacity:0.5;">
                    <p style="font-size:2rem;margin:0 0 0.5rem;">🔌</p>
                    <p style="margin:0;font-size:0.9rem;">Sin datos de infraestructura configurados.</p>
                    <a href="/zonas/{zonaId}/editar" class="btn btn-sm btn-outline mt-4">Configurar infraestructura</a>
                </div>
            {/if}
        </div>

    <!-- ─── TAB NOTAS ────────────────────────────────────────────── -->
    {:else if activeTab === "notas"}
        <div style="display:flex;flex-direction:column;gap:0.875rem;">
            {#if zona.notes.length === 0}
                <div class="glass-card-flat" style="padding:3rem;border-radius:1rem;text-align:center;opacity:0.55;">
                    <p style="font-size:2rem;margin:0 0 0.5rem;">📝</p>
                    <p style="margin:0 0 1rem;font-size:0.9rem;">Sin notas. Añade notas desde la vista de edición.</p>
                    <a href="/zonas/{zonaId}/editar" class="btn btn-sm btn-outline">Gestionar notas</a>
                </div>
            {:else}
                {#each zona.notes as note}
                    <!-- svelte-ignore a11y_click_events_have_key_events -->
                    <!-- svelte-ignore a11y_no_static_element_interactions -->
                    <div
                        class="note-card glass-card"
                        style="padding:1.25rem 1.5rem;border-radius:0.875rem;cursor:pointer;"
                        onclick={() => { selectedNote = { title: note.title, content: note.content || "" }; }}
                        title="Haz clic para leer la nota completa"
                    >
                        <!-- Cabecera de nota -->
                        <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:1rem;margin-bottom:0.625rem;">
                            <span style="font-weight:700;font-size:0.95rem;line-height:1.3;">{note.title}</span>
                            <div style="display:flex;align-items:center;gap:0.4rem;flex-shrink:0;">
                                {#if note.is_encrypted}
                                    <span class="badge badge-warning badge-xs">🔒</span>
                                {/if}
                                <span style="font-size:0.72rem;opacity:0.4;">{fmtDate(note.updated_at)}</span>
                            </div>
                        </div>

                        <!-- Preview de contenido en markdown -->
                        {#if note.content && !note.is_encrypted}
                            <div style="pointer-events:none;">
                                <MarkdownViewer content={note.content} preview={true} previewLength={200} />
                            </div>
                            <div class="read-more-hint" style="margin-top:0.6rem;display:flex;align-items:center;gap:0.3rem;font-size:0.75rem;opacity:0.45;font-style:italic;">
                                <span>↗</span> Leer nota completa
                            </div>
                        {:else if note.is_encrypted}
                            <p style="font-size:0.82rem;opacity:0.45;margin:0;font-style:italic;">🔒 Contenido encriptado — Haz clic para ver.</p>
                        {:else}
                            <p style="font-size:0.82rem;opacity:0.4;margin:0;font-style:italic;">Sin contenido.</p>
                        {/if}
                    </div>
                {/each}

                <div style="text-align:right;margin-top:0.25rem;">
                    <a href="/zonas/{zonaId}/editar" class="btn btn-sm btn-ghost">Gestionar notas →</a>
                </div>
            {/if}
        </div>

    <!-- ─── TAB DOCUMENTOS ───────────────────────────────────────── -->
    {:else if activeTab === "docs"}
        <div style="display:flex;flex-direction:column;gap:1rem;">
            {#if zona.documentos.length === 0}
                <div class="glass-card-flat" style="padding:3rem;border-radius:1rem;text-align:center;opacity:0.55;">
                    <p style="font-size:2rem;margin:0 0 0.5rem;">📄</p>
                    <p style="margin:0 0 1rem;font-size:0.9rem;">Sin documentos adjuntos.</p>
                    <a href="/zonas/{zonaId}/editar" class="btn btn-sm btn-outline">Subir documentos</a>
                </div>
            {:else}
                <div class="doc-grid">
                    {#each zona.documentos as doc}
                        <!-- svelte-ignore a11y_click_events_have_key_events -->
                        <!-- svelte-ignore a11y_no_static_element_interactions -->
                        <div
                            class="doc-card glass-card"
                            onclick={() => { selectedDoc = doc; }}
                            title={doc.nombre_original}
                        >
                            <!-- Miniatura / Ícono -->
                            <div class="doc-thumb">
                                {#if isImage(doc.tipo)}
                                    <img
                                        src={docUrl(doc)}
                                        alt={doc.nombre_original}
                                        class="doc-thumb-img"
                                        loading="lazy"
                                    />
                                    <!-- Overlay suave al hover -->
                                    <div class="doc-thumb-overlay">
                                        <span style="font-size:1.5rem;">🔍</span>
                                    </div>
                                {:else}
                                    <div class="doc-icon-bg">
                                        <span class="doc-icon-emoji">{getDocIcon(doc.tipo)}</span>
                                    </div>
                                    <div class="doc-thumb-overlay">
                                        <span style="font-size:1.5rem;">⬇️</span>
                                    </div>
                                {/if}
                                <span class="badge badge-sm badge-neutral" style="position:absolute;top:0.5rem;right:0.5rem;opacity:0.9;text-transform:uppercase;font-size:0.6rem;letter-spacing:0.04em;">
                                    {doc.tipo}
                                </span>
                            </div>

                            <!-- Info -->
                            <div class="doc-info">
                                <p class="doc-name" title={doc.nombre_original}>{doc.nombre_original}</p>
                                {#if doc.descripcion}
                                    <p class="doc-desc" title={doc.descripcion}>{doc.descripcion}</p>
                                {/if}
                                <p class="doc-date">{fmtDate(doc.creado_en)}</p>
                            </div>
                        </div>
                    {/each}
                </div>

                <div style="text-align:right;">
                    <a href="/zonas/{zonaId}/editar" class="btn btn-sm btn-ghost">Gestionar documentos →</a>
                </div>
            {/if}
        </div>
    {/if}
{/if}

<!-- ══════════════════════════════════════════════════════════════
     MODAL — Nota Completa (Markdown)
══════════════════════════════════════════════════════════════ -->
{#if selectedNote}
    <div class="modal modal-open">
        <div class="modal-box w-11/12 max-w-4xl" style="padding:0;overflow:hidden;">
            <!-- Header del modal -->
            <div style="padding:1.25rem 1.5rem;border-bottom:1px solid oklch(from var(--color-base-content) l c h / 0.1);display:flex;align-items:center;justify-content:space-between;">
                <h3 style="font-weight:800;font-size:1.05rem;margin:0;">📄 {selectedNote.title}</h3>
                <button class="btn btn-ghost btn-sm btn-circle" onclick={() => { selectedNote = null; }}>✕</button>
            </div>
            <!-- Cuerpo con markdown renderizado -->
            <div style="padding:1.5rem;overflow-y:auto;max-height:68vh;">
                <MarkdownViewer content={selectedNote.content} />
            </div>
        </div>
        <div
            class="modal-backdrop"
            onclick={() => { selectedNote = null; }}
            onkeydown={(e) => { if (e.key === "Escape") selectedNote = null; }}
            role="button"
            tabindex="0"
        ><span class="sr-only">Cerrar</span></div>
    </div>
{/if}

<!-- ══════════════════════════════════════════════════════════════
     MODAL — Documento / Imagen
══════════════════════════════════════════════════════════════ -->
{#if selectedDoc}
    <div class="modal modal-open">
        <div class="modal-box w-11/12 max-w-5xl" style="padding:0;overflow:hidden;">
            <!-- Header -->
            <div style="padding:1.25rem 1.5rem;border-bottom:1px solid oklch(from var(--color-base-content) l c h / 0.1);display:flex;align-items:center;justify-content:space-between;">
                <h3 style="font-weight:800;font-size:1.05rem;margin:0;">
                    {getDocIcon(selectedDoc.tipo)}
                    {selectedDoc.nombre_original}
                </h3>
                <button class="btn btn-ghost btn-sm btn-circle" onclick={() => { selectedDoc = null; }}>✕</button>
            </div>

            <!-- Cuerpo -->
            <div style="padding:1.25rem;display:flex;flex-direction:column;align-items:center;gap:1rem;min-height:40vh;background:oklch(from var(--color-base-200) l c h / 0.5);">
                {#if isImage(selectedDoc.tipo)}
                    <img
                        src={docUrl(selectedDoc)}
                        alt={selectedDoc.nombre_original}
                        style="max-width:100%;max-height:65vh;object-fit:contain;border-radius:0.75rem;box-shadow:0 8px 30px rgba(0,0,0,0.25);"
                    />
                {:else}
                    <div style="text-align:center;padding:2rem;">
                        <span style="font-size:4rem;display:block;margin-bottom:1rem;opacity:0.3;">{getDocIcon(selectedDoc.tipo)}</span>
                        <h4 style="font-weight:700;margin:0 0 0.5rem;">Archivo no previsualizable en línea</h4>
                        <p style="opacity:0.6;font-size:0.9rem;margin:0 0 1.5rem;max-width:30rem;">
                            El formato <strong>{selectedDoc.tipo.toUpperCase()}</strong> no se puede mostrar directamente. Descárgalo para abrirlo.
                        </p>
                        <a
                            href={`/api/zonas/${zonaId}/documentos/${selectedDoc.id}/descargar`}
                            target="_blank"
                            rel="noopener noreferrer"
                            class="btn btn-primary"
                        >⬇️ Ver / Descargar</a>
                    </div>
                {/if}

                {#if selectedDoc.descripcion}
                    <div style="padding:0.75rem 1rem;background:oklch(from var(--color-base-100) l c h / 0.8);border-radius:0.5rem;width:100%;font-size:0.85rem;border:1px solid oklch(from var(--color-base-300) l c h / 0.5);">
                        <strong>Descripción:</strong> {selectedDoc.descripcion}
                    </div>
                {/if}
            </div>

            <!-- Footer -->
            <div style="padding:0.875rem 1.5rem;border-top:1px solid oklch(from var(--color-base-content) l c h / 0.08);display:flex;justify-content:flex-end;gap:0.5rem;">
                {#if isImage(selectedDoc.tipo)}
                    <a
                        href={docUrl(selectedDoc)}
                        target="_blank"
                        rel="noopener noreferrer"
                        class="btn btn-ghost btn-sm"
                    >⬇️ Descargar</a>
                {/if}
                <button class="btn btn-neutral btn-sm" onclick={() => { selectedDoc = null; }}>Cerrar</button>
            </div>
        </div>
        <div
            class="modal-backdrop"
            onclick={() => { selectedDoc = null; }}
            onkeydown={(e) => { if (e.key === "Escape") selectedDoc = null; }}
            role="button"
            tabindex="0"
        ><span class="sr-only">Cerrar</span></div>
    </div>
{/if}

<style>
    /* ─── Note Cards ─── */
    .note-card {
        transition: box-shadow 0.18s ease, transform 0.18s ease, border-color 0.18s ease;
    }
    .note-card:hover {
        transform: translateY(-2px);
        border-color: oklch(from var(--color-primary) l c h / 0.3) !important;
    }
    .read-more-hint {
        transition: opacity 0.15s ease;
    }
    .note-card:hover .read-more-hint {
        opacity: 0.75 !important;
    }

    /* ─── Doc Grid ─── */
    .doc-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
        gap: 1rem;
    }

    .doc-card {
        cursor: pointer;
        display: flex;
        flex-direction: column;
        overflow: hidden;
        border-radius: 0.875rem !important;
        transition: box-shadow 0.18s ease, transform 0.18s ease;
    }
    .doc-card:hover {
        transform: translateY(-3px);
    }
    .doc-card:hover .doc-thumb-overlay {
        opacity: 1;
    }

    .doc-thumb {
        position: relative;
        height: 130px;
        background: oklch(from var(--color-base-200) l c h / 0.7);
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
        flex-shrink: 0;
        border-bottom: 1px solid oklch(from var(--color-base-300) l c h / 0.4);
    }

    .doc-thumb-img {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }

    .doc-icon-bg {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        height: 100%;
    }

    .doc-icon-emoji {
        font-size: 3rem;
        opacity: 0.35;
    }

    .doc-thumb-overlay {
        position: absolute;
        inset: 0;
        background: oklch(from var(--color-base-content) l c h / 0.55);
        display: flex;
        align-items: center;
        justify-content: center;
        opacity: 0;
        transition: opacity 0.2s ease;
        backdrop-filter: blur(2px);
    }

    .doc-info {
        padding: 0.75rem;
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
    }

    .doc-name {
        font-size: 0.82rem;
        font-weight: 600;
        margin: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .doc-desc {
        font-size: 0.72rem;
        opacity: 0.55;
        margin: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .doc-date {
        font-size: 0.68rem;
        opacity: 0.38;
        margin: 0;
        text-align: right;
        margin-top: auto;
        padding-top: 0.25rem;
    }

    /* ─── Skeleton ─── */
    @keyframes pulseSkel {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.35; }
    }
</style>

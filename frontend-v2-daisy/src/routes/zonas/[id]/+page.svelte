<script lang="ts">
    import { onMount } from "svelte";
    import { page } from "$app/stores";
    import { api } from "$lib/api";
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
            const res = await api.get<ZonaDetail>(`/zonas/${zonaId}/details`);
            zona = res.data;
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
</script>

<!-- Breadcrumb -->
<div class="breadcrumbs text-sm mb-4 opacity-60">
    <ul>
        <li><a href="/zonas">Zonas</a></li>
        <li>{loading ? "…" : (zona?.nombre ?? "Zona")}</li>
    </ul>
</div>

{#if loading}
    <!-- Skeleton -->
    <div class="glass-card-flat" style="padding:2rem;border-radius:1rem;">
        {#each Array(6) as _}
            <div
                style="height:1.1rem;border-radius:0.3rem;background:oklch(from var(--color-base-content) l c h / 0.08);margin-bottom:0.75rem;animation:pulseSkel 1.5s infinite;"
            ></div>
        {/each}
    </div>
{:else if pageError}
    <div class="alert alert-error shadow-sm">
        <span>{pageError}</span>
        <a href="/zonas" class="btn btn-xs btn-ghost">← Volver</a>
    </div>
{:else if zona}
    <!-- Encabezado -->
    <div
        style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:1rem;margin-bottom:1.5rem;"
    >
        <div>
            <h2 style="font-size:1.375rem;font-weight:700;margin:0;">
                🗺️ {zona.nombre}
            </h2>
            {#if zona.direccion}
                <p style="margin:0.25rem 0 0;font-size:0.85rem;opacity:0.55;">
                    📍 {zona.direccion}
                </p>
            {/if}
        </div>
        <div style="display:flex;gap:0.5rem;">
            <a href="/zonas" class="btn btn-ghost btn-sm">← Volver</a>
            <a href="/zonas/{zonaId}/editar" class="btn btn-primary btn-sm"
                >✏️ Editar Zona</a
            >
        </div>
    </div>

    <!-- Tabs -->
    <div class="tabs tabs-bordered mb-4">
        <button
            class="tab {activeTab === 'general' ? 'tab-active' : ''}"
            onclick={() => (activeTab = "general")}>General</button
        >
        <button
            class="tab {activeTab === 'infra' ? 'tab-active' : ''}"
            onclick={() => (activeTab = "infra")}>🔌 Infraestructura</button
        >
        <button
            class="tab {activeTab === 'notas' ? 'tab-active' : ''}"
            onclick={() => (activeTab = "notas")}
            >📝 Notas ({zona.notes.length})</button
        >
        <button
            class="tab {activeTab === 'docs' ? 'tab-active' : ''}"
            onclick={() => (activeTab = "docs")}
            >📄 Documentos ({zona.documentos.length})</button
        >
    </div>

    <!-- ─── TAB GENERAL ──────────────────────────────────────────────── -->
    {#if activeTab === "general"}
        <div class="glass-card-flat" style="padding:1.5rem;border-radius:1rem;">
            <table style="width:100%;border-collapse:collapse;">
                <tbody>
                    {#each [{ label: "Nombre", value: zona.nombre }, { label: "Dirección", value: fmt(zona.direccion) }, { label: "Coordenadas GPS", value: fmt(zona.coordenadas_gps) }] as row}
                        <tr
                            style="border-bottom:1px solid oklch(from var(--color-base-content) l c h / 0.08);"
                        >
                            <td
                                style="padding:0.75rem 1rem 0.75rem 0;font-size:0.8rem;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;opacity:0.45;width:11rem;vertical-align:top;"
                                >{row.label}</td
                            >
                            <td style="padding:0.75rem 0;font-size:0.9rem;"
                                >{row.value}</td
                            >
                        </tr>
                    {/each}
                </tbody>
            </table>

            {#if zona.rack_layout && Object.keys(zona.rack_layout).length > 0}
                <div style="margin-top:1.25rem;">
                    <p
                        style="font-size:0.75rem;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;opacity:0.45;margin:0 0 0.5rem;"
                    >
                        Virtual Rack (JSON)
                    </p>
                    <pre
                        style="background:oklch(from var(--color-base-content) l c h / 0.05);padding:1rem;border-radius:0.5rem;font-size:0.75rem;overflow:auto;max-height:200px;">{JSON.stringify(
                            zona.rack_layout,
                            null,
                            2,
                        )}</pre>
                </div>
            {/if}
        </div>

        <!-- ─── TAB INFRAESTRUCTURA ─────────────────────────────────────── -->
    {:else if activeTab === "infra"}
        <div class="glass-card-flat" style="padding:1.5rem;border-radius:1rem;">
            {#if zona.infraestructura}
                {@const infra = zona.infraestructura}
                <table style="width:100%;border-collapse:collapse;">
                    <tbody>
                        {#each [{ label: "IP Gestión", value: fmt(infra.direccion_ip_gestion) }, { label: "Gateway", value: fmt(infra.gateway_predeterminado) }, { label: "Servidores DNS", value: fmt(infra.servidores_dns) }, { label: "VLANs Utilizadas", value: fmt(infra.vlans_utilizadas) }, { label: "Equipos Críticos", value: fmt(infra.equipos_criticos) }, { label: "Próx. Mantenimiento", value: fmtDate(infra.proximo_mantenimiento) }] as row}
                            <tr
                                style="border-bottom:1px solid oklch(from var(--color-base-content) l c h / 0.08);"
                            >
                                <td
                                    style="padding:0.75rem 1rem 0.75rem 0;font-size:0.8rem;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;opacity:0.45;width:13rem;vertical-align:top;"
                                    >{row.label}</td
                                >
                                <td
                                    style="padding:0.75rem 0;font-size:0.9rem;font-family:{row.label ===
                                        'VLANs Utilizadas' ||
                                    row.label === 'IP Gestión'
                                        ? 'monospace'
                                        : 'inherit'};">{row.value}</td
                                >
                            </tr>
                        {/each}
                    </tbody>
                </table>
            {:else}
                <div style="text-align:center;padding:2rem;opacity:0.5;">
                    <p style="font-size:1.5rem;margin:0 0 0.5rem;">🔌</p>
                    <p style="margin:0;font-size:0.9rem;">
                        Sin datos de infraestructura configurados.
                    </p>
                    <a
                        href="/zonas/{zonaId}/editar"
                        class="btn btn-sm btn-outline mt-3"
                        >Configurar infraestructura</a
                    >
                </div>
            {/if}
        </div>

        <!-- ─── TAB NOTAS ───────────────────────────────────────────────── -->
    {:else if activeTab === "notas"}
        <div style="display:flex;flex-direction:column;gap:0.75rem;">
            {#if zona.notes.length === 0}
                <div
                    class="glass-card-flat"
                    style="padding:2.5rem;border-radius:1rem;text-align:center;opacity:0.55;"
                >
                    <p style="font-size:1.5rem;margin:0 0 0.5rem;">📝</p>
                    <p style="margin:0;font-size:0.9rem;">
                        Sin notas. Añade notas desde la vista de edición.
                    </p>
                    <a
                        href="/zonas/{zonaId}/editar"
                        class="btn btn-sm btn-outline mt-3">Gestionar notas</a
                    >
                </div>
            {:else}
                {#each zona.notes as note}
                    <div
                        class="glass-card-flat"
                        style="padding:1.25rem;border-radius:0.75rem;"
                    >
                        <div
                            style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.5rem;"
                        >
                            <span style="font-weight:600;font-size:0.95rem;"
                                >{note.title}</span
                            >
                            <div
                                style="display:flex;align-items:center;gap:0.5rem;"
                            >
                                {#if note.is_encrypted}
                                    <span class="badge badge-warning badge-xs"
                                        >🔒 Encriptada</span
                                    >
                                {/if}
                                <span style="font-size:0.75rem;opacity:0.45;"
                                    >{fmtDate(note.updated_at)}</span
                                >
                            </div>
                        </div>
                        {#if note.content}
                            <button
                                class="btn btn-sm btn-outline mt-3"
                                onclick={() => {
                                    selectedNote = {
                                        title: note.title,
                                        content: note.content || "",
                                    };
                                }}
                            >
                                📄 Ver Nota Completa
                            </button>
                        {/if}
                    </div>
                {/each}
                <div style="text-align:right;">
                    <a
                        href="/zonas/{zonaId}/editar"
                        class="btn btn-sm btn-ghost">Gestionar notas →</a
                    >
                </div>
            {/if}
        </div>

        <!-- ─── TAB DOCUMENTOS ──────────────────────────────────────────── -->
    {:else if activeTab === "docs"}
        <div style="display:flex;flex-direction:column;gap:0.75rem;">
            {#if zona.documentos.length === 0}
                <div
                    class="glass-card-flat"
                    style="padding:2.5rem;border-radius:1rem;text-align:center;opacity:0.55;"
                >
                    <p style="font-size:1.5rem;margin:0 0 0.5rem;">📄</p>
                    <p style="margin:0;font-size:0.9rem;">
                        Sin documentos adjuntos.
                    </p>
                    <a
                        href="/zonas/{zonaId}/editar"
                        class="btn btn-sm btn-outline mt-3">Subir documentos</a
                    >
                </div>
            {:else}
                <div
                    class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4"
                >
                    {#each zona.documentos as doc}
                        <!-- svelte-ignore a11y_click_events_have_key_events -->
                        <!-- svelte-ignore a11y_no_static_element_interactions -->
                        <div
                            class="glass-card-flat flex flex-col cursor-pointer hover:shadow-md transition-all duration-200 overflow-hidden"
                            style="border-radius: 0.75rem;"
                            onclick={() => {
                                selectedDoc = doc;
                            }}
                        >
                            <!-- Miniatura -->
                            <div
                                class="h-32 bg-base-200 flex items-center justify-center border-b border-base-300 relative"
                            >
                                {#if doc.tipo === "imagen"}
                                    <img
                                        src={`/api/zonas/${zonaId}/documentos/${doc.id}/descargar`}
                                        alt={doc.nombre_original}
                                        class="w-full h-full object-cover"
                                        loading="lazy"
                                    />
                                {:else}
                                    <span class="text-4xl opacity-50">
                                        {doc.tipo === "pdf" ? "📕" : "📄"}
                                    </span>
                                {/if}
                                <span
                                    class="badge badge-sm badge-neutral absolute top-2 right-2 opacity-90 shadow-sm"
                                >
                                    {doc.tipo}
                                </span>
                            </div>

                            <!-- Info -->
                            <div
                                class="p-3 flex-1 flex flex-col justify-between"
                            >
                                <div>
                                    <p
                                        class="font-semibold text-sm mb-1 line-clamp-2"
                                        title={doc.nombre_original}
                                    >
                                        {doc.nombre_original}
                                    </p>
                                    {#if doc.descripcion}
                                        <p
                                            class="text-xs opacity-60 line-clamp-1"
                                            title={doc.descripcion}
                                        >
                                            {doc.descripcion}
                                        </p>
                                    {/if}
                                </div>
                                <p
                                    class="text-[0.7rem] opacity-45 mt-2 text-right"
                                >
                                    {fmtDate(doc.creado_en)}
                                </p>
                            </div>
                        </div>
                    {/each}
                </div>
                <div style="text-align:right;">
                    <a
                        href="/zonas/{zonaId}/editar"
                        class="btn btn-sm btn-ghost">Gestionar documentos →</a
                    >
                </div>
            {/if}
        </div>
    {/if}
{/if}

<!-- Notas Modal -->
{#if selectedNote}
    <div class="modal modal-open">
        <div class="modal-box w-11/12 max-w-5xl">
            <h3 class="font-bold text-lg mb-4 pb-2 border-b border-base-300">
                📄 {selectedNote.title}
            </h3>
            <div class="overflow-y-auto max-h-[60vh]">
                <MarkdownViewer content={selectedNote.content} />
            </div>
            <div class="modal-action">
                <button
                    class="btn"
                    onclick={() => {
                        selectedNote = null;
                    }}>Cerrar</button
                >
            </div>
        </div>
        <div
            class="modal-backdrop"
            onclick={() => {
                selectedNote = null;
            }}
            onkeydown={(e) => {
                if (e.key === "Escape") selectedNote = null;
            }}
            role="button"
            tabindex="0"
        >
            <span class="sr-only">Cerrar modal</span>
        </div>
    </div>
{/if}

<!-- Documento Modal -->
{#if selectedDoc}
    <div class="modal modal-open">
        <div class="modal-box w-11/12 max-w-5xl">
            <h3
                class="font-bold text-lg mb-4 pb-2 border-b border-base-300 pr-8"
            >
                {selectedDoc.tipo === "pdf"
                    ? "📕"
                    : selectedDoc.tipo === "imagen"
                      ? "🖼️"
                      : "📄"}
                {selectedDoc.nombre_original}
            </h3>

            <div
                class="flex flex-col items-center justify-center p-4 min-h-[40vh] bg-base-200/50 rounded-xl relative"
            >
                {#if selectedDoc.tipo === "imagen"}
                    <img
                        src={`/api/zonas/${zonaId}/documentos/${selectedDoc.id}/descargar`}
                        alt={selectedDoc.nombre_original}
                        class="max-w-full max-h-[60vh] object-contain rounded-lg shadow-sm"
                    />
                {:else}
                    <div class="text-center">
                        <span class="text-6xl mb-4 block opacity-30">
                            {selectedDoc.tipo === "pdf" ? "📕" : "📄"}
                        </span>
                        <h4 class="font-semibold text-lg mb-2">
                            Archivo no previsualizable en línea
                        </h4>
                        <p class="opacity-60 text-sm mb-6 max-w-md mx-auto">
                            Debido al formato ({selectedDoc.tipo}), recomendamos
                            abrirlo o descargarlo directamente para una mejor
                            experiencia.
                        </p>
                        <a
                            href={`/api/zonas/${zonaId}/documentos/${selectedDoc.id}/descargar`}
                            target="_blank"
                            rel="noopener noreferrer"
                            class="btn btn-primary"
                        >
                            ⬇️ Ver / Descargar ({selectedDoc.tipo.toUpperCase()})
                        </a>
                    </div>
                {/if}

                {#if selectedDoc.descripcion}
                    <div
                        class="mt-4 p-3 bg-base-100 rounded-lg w-full text-sm opacity-80 border border-base-300"
                    >
                        <strong>Descripción:</strong>
                        {selectedDoc.descripcion}
                    </div>
                {/if}
            </div>

            <div class="modal-action">
                <button
                    class="btn"
                    onclick={() => {
                        selectedDoc = null;
                    }}>Cerrar</button
                >
            </div>
        </div>
        <div
            class="modal-backdrop"
            onclick={() => {
                selectedDoc = null;
            }}
            onkeydown={(e) => {
                if (e.key === "Escape") selectedDoc = null;
            }}
            role="button"
            tabindex="0"
        >
            <span class="sr-only">Cerrar modal</span>
        </div>
    </div>
{/if}

<style>
    @keyframes pulseSkel {
        0%,
        100% {
            opacity: 1;
        }
        50% {
            opacity: 0.4;
        }
    }
</style>

<script lang="ts">
    import { onMount } from "svelte";
    import { page } from "$app/stores";
    import { api } from "$lib/api";
    import type { ZonaDetail } from "$lib/types/zona";

    const zonaId = Number($page.params.id);

    let zona = $state<ZonaDetail | null>(null);
    let loading = $state(true);
    let pageError = $state<string | null>(null);
    let activeTab = $state<"general" | "infra" | "notas" | "docs">("general");

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
                            <p
                                style="margin:0;font-size:0.875rem;opacity:0.75;white-space:pre-wrap;"
                            >
                                {note.content}
                            </p>
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
                {#each zona.documentos as doc}
                    <div
                        class="glass-card-flat"
                        style="padding:1rem 1.25rem;border-radius:0.75rem;display:flex;align-items:center;gap:0.75rem;"
                    >
                        <span style="font-size:1.5rem;flex-shrink:0;">
                            {doc.tipo === "pdf"
                                ? "📕"
                                : doc.tipo === "imagen"
                                  ? "🖼️"
                                  : "📎"}
                        </span>
                        <div style="flex:1;min-width:0;">
                            <p
                                style="margin:0;font-weight:600;font-size:0.9rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"
                            >
                                {doc.nombre_original}
                            </p>
                            {#if doc.descripcion}
                                <p
                                    style="margin:0;font-size:0.8rem;opacity:0.6;"
                                >
                                    {doc.descripcion}
                                </p>
                            {/if}
                        </div>
                        <div style="text-align:right;flex-shrink:0;">
                            <span class="badge badge-ghost badge-sm"
                                >{doc.tipo}</span
                            >
                            <p
                                style="margin:0.25rem 0 0;font-size:0.72rem;opacity:0.45;"
                            >
                                {fmtDate(doc.creado_en)}
                            </p>
                        </div>
                    </div>
                {/each}
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

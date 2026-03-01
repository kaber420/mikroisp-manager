<script lang="ts">
    import { onMount } from "svelte";
    import { page } from "$app/stores";
    import { goto } from "$app/navigation";
    import {
        api,
        updateZona,
        updateZonaInfra,
        createZonaNote,
        updateZonaNote,
        deleteZonaNote,
        deleteZonaDocumento,
        uploadZonaDocumento,
    } from "$lib/api";
    import type {
        ZonaDetail,
        ZonaInfra,
        ZonaNote,
        ZonaNoteCreate,
    } from "$lib/types/zona";

    const zonaId = Number($page.params.id);

    // ── Pestañas (Tabs) ──────────────────────────────────────────────────
    let activeTab = $state<"general" | "infra" | "notas" | "documentos">(
        "general",
    );

    let zona = $state<ZonaDetail | null>(null);
    let loading = $state(true);
    let pageError = $state<string | null>(null);
    let saveOk = $state<string | null>(null);

    // ── Campos Generales ─────────────────────────────────────────────────
    let fNombre = $state("");
    let fDireccion = $state("");
    let fCoordenadas = $state("");
    let fRackJson = $state("");
    let savingGeneral = $state(false);
    let errorGeneral = $state<string | null>(null);

    // ── Campos Infraestructura ───────────────────────────────────────────
    let fIpGestion = $state("");
    let fGateway = $state("");
    let fDns = $state("");
    let fVlans = $state("");
    let fEquipos = $state("");
    let fMantenimiento = $state("");
    let savingInfra = $state(false);
    let errorInfra = $state<string | null>(null);

    // ── Notas ────────────────────────────────────────────────────────────
    let showNoteModal = $state(false);
    let noteModalMode = $state<"create" | "edit">("create");
    let editNoteTarget = $state<ZonaNote | null>(null);
    let fNoteTitle = $state("");
    let fNoteContent = $state("");
    let fNoteEncrypted = $state(false);
    let savingNote = $state(false);
    let errorNote = $state<string | null>(null);

    let showDeleteNoteModal = $state(false);
    let deleteNoteTarget = $state<ZonaNote | null>(null);
    let deletingNote = $state(false);

    // ── Documentos ───────────────────────────────────────────────────────
    let showDeleteDocModal = $state(false);
    let deleteDocTarget = $state<
        import("$lib/types/zona").ZonaDocumento | null
    >(null);
    let deletingDoc = $state(false);

    let uploadingDoc = $state(false);
    let fileInput = $state<HTMLInputElement | null>(null);

    // ── Carga ─────────────────────────────────────────────────────────────
    async function loadDetalle() {
        loading = true;
        try {
            const res = await api.get<ZonaDetail>(`/zonas/${zonaId}/details`);
            zona = res.data;
            fNombre = zona.nombre;
            fDireccion = zona.direccion ?? "";
            fCoordenadas = zona.coordenadas_gps ?? "";
            fRackJson = zona.rack_layout
                ? JSON.stringify(zona.rack_layout, null, 2)
                : "";
            const i = zona.infraestructura;
            if (i) {
                fIpGestion = i.direccion_ip_gestion ?? "";
                fGateway = i.gateway_predeterminado ?? "";
                fDns = i.servidores_dns ?? "";
                fVlans = i.vlans_utilizadas ?? "";
                fEquipos = i.equipos_criticos ?? "";
                fMantenimiento = i.proximo_mantenimiento ?? "";
            }
        } catch (e: any) {
            pageError = e?.response?.data?.detail ?? "Error al cargar la zona.";
        } finally {
            loading = false;
        }
    }

    onMount(loadDetalle);

    // ── Guardar Generales ─────────────────────────────────────────────────
    async function saveGeneral() {
        savingGeneral = true;
        errorGeneral = null;
        try {
            let rack: Record<string, unknown> | null = null;
            if (fRackJson.trim()) {
                rack = JSON.parse(fRackJson);
            }
            await updateZona(zonaId, {
                nombre: fNombre.trim(),
                direccion: fDireccion.trim() || null,
                coordenadas_gps: fCoordenadas.trim() || null,
                rack_layout: rack,
            });
            saveOk = "Datos generales guardados.";
            await loadDetalle();
        } catch (e: any) {
            errorGeneral =
                e instanceof SyntaxError
                    ? "JSON del Virtual Rack inválido."
                    : (e?.response?.data?.detail ?? "Error al guardar.");
        } finally {
            savingGeneral = false;
        }
    }

    // ── Guardar Infraestructura ───────────────────────────────────────────
    async function saveInfra() {
        savingInfra = true;
        errorInfra = null;
        try {
            const payload: Partial<ZonaInfra> = {
                direccion_ip_gestion: fIpGestion.trim() || null,
                gateway_predeterminado: fGateway.trim() || null,
                servidores_dns: fDns.trim() || null,
                vlans_utilizadas: fVlans.trim() || null,
                equipos_criticos: fEquipos.trim() || null,
                proximo_mantenimiento: fMantenimiento || null,
            };
            await updateZonaInfra(zonaId, payload);
            saveOk = "Infraestructura guardada.";
            await loadDetalle();
        } catch (e: any) {
            errorInfra =
                e?.response?.data?.detail ??
                "Error al guardar infraestructura.";
        } finally {
            savingInfra = false;
        }
    }

    // ── Notas: abrir modales ───────────────────────────────────────────────
    function openCreateNote() {
        noteModalMode = "create";
        editNoteTarget = null;
        fNoteTitle = "";
        fNoteContent = "";
        fNoteEncrypted = false;
        errorNote = null;
        showNoteModal = true;
    }

    function openEditNote(n: ZonaNote) {
        noteModalMode = "edit";
        editNoteTarget = n;
        fNoteTitle = n.title;
        fNoteContent = n.content ?? "";
        fNoteEncrypted = n.is_encrypted;
        errorNote = null;
        showNoteModal = true;
    }

    async function saveNote() {
        savingNote = true;
        errorNote = null;
        try {
            const data: ZonaNoteCreate = {
                title: fNoteTitle.trim(),
                content: fNoteContent.trim() || null,
                is_encrypted: fNoteEncrypted,
            };
            if (noteModalMode === "create") {
                await createZonaNote(zonaId, data);
            } else if (editNoteTarget) {
                await updateZonaNote(editNoteTarget.id, data);
            }
            showNoteModal = false;
            await loadDetalle();
        } catch (e: any) {
            errorNote = e?.response?.data?.detail ?? "Error al guardar nota.";
        } finally {
            savingNote = false;
        }
    }

    async function confirmDeleteNote() {
        if (!deleteNoteTarget) return;
        deletingNote = true;
        try {
            await deleteZonaNote(deleteNoteTarget.id);
            showDeleteNoteModal = false;
            deleteNoteTarget = null;
            await loadDetalle();
        } catch (e: any) {
            pageError =
                e?.response?.data?.detail ?? "Error al eliminar la nota.";
            showDeleteNoteModal = false;
        } finally {
            deletingNote = false;
        }
    }

    async function confirmDeleteDoc() {
        if (!deleteDocTarget) return;
        deletingDoc = true;
        try {
            await deleteZonaDocumento(deleteDocTarget.id);
            showDeleteDocModal = false;
            deleteDocTarget = null;
            await loadDetalle();
        } catch (e: any) {
            pageError =
                e?.response?.data?.detail ?? "Error al eliminar el documento.";
            showDeleteDocModal = false;
        } finally {
            deletingDoc = false;
        }
    }

    async function uploadDoc(e: Event) {
        const target = e.target as HTMLInputElement;
        if (!target.files || target.files.length === 0) return;
        const file = target.files[0];

        uploadingDoc = true;
        try {
            await uploadZonaDocumento(zonaId, file);
            saveOk = "Documento subido con éxito.";
            await loadDetalle();
        } catch (e: any) {
            pageError =
                e?.response?.data?.detail ?? "Error al subir el documento.";
        } finally {
            uploadingDoc = false;
            if (fileInput) fileInput.value = "";
        }
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

<!-- Cabecera simple con Breadcrumbs -->
<div
    class="mb-6"
    style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:1rem;"
>
    <div style="display:flex;align-items:center;">
        <h2
            style="font-size:1.5rem;font-weight:700;margin:0;display:flex;align-items:center;gap:0.5rem;"
        >
            ✏️ {zona ? `Editar: ${zona.nombre}` : "Cargando..."}
        </h2>
    </div>
    <div style="display:flex;align-items:center;gap:0.5rem;">
        <a href="/zonas" class="btn btn-ghost btn-sm">← Zonas</a>
        {#if zona}
            <a href="/zonas/{zonaId}" class="btn btn-primary btn-sm"
                >Ver Detalle</a
            >
        {/if}
    </div>
</div>

{#if loading}
    <div class="glass-card-flat" style="padding:2rem;border-radius:1rem;">
        {#each Array(5) as _}
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
    {#if saveOk}
        <div
            class="alert alert-success shadow-sm mb-4"
            style="margin-bottom:1rem;"
        >
            <span>{saveOk}</span>
            <button class="btn btn-xs btn-ghost" onclick={() => (saveOk = null)}
                >✕</button
            >
        </div>
    {/if}

    <!-- ─── SELECTOR DE PESTAÑAS (TABS) ────────────────────────────────────── -->
    <div role="tablist" class="tabs tabs-lifted tabs-lg mb-6">
        <button
            role="tab"
            class="tab {activeTab === 'general' ? 'tab-active font-bold' : ''}"
            onclick={() => (activeTab = "general")}>Generales</button
        >
        <button
            role="tab"
            class="tab {activeTab === 'infra' ? 'tab-active font-bold' : ''}"
            onclick={() => (activeTab = "infra")}>Infraestructura</button
        >
        <button
            role="tab"
            class="tab {activeTab === 'notas' ? 'tab-active font-bold' : ''}"
            onclick={() => (activeTab = "notas")}
            >Notas ({zona.notes.length})</button
        >
        <button
            role="tab"
            class="tab {activeTab === 'documentos'
                ? 'tab-active font-bold'
                : ''}"
            onclick={() => (activeTab = "documentos")}
            >Documentos ({zona.documentos.length})</button
        >
    </div>

    <div style="display:flex;flex-direction:column;gap:1.5rem;">
        <!-- ─── SECCIÓN 1: DATOS GENERALES ─────────────────────────────── -->
        {#if activeTab === "general"}
            <div
                class="glass-card-flat"
                style="border-radius:1rem;padding:1.5rem;"
            >
                <div
                    style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1.5rem;"
                >
                    <h3
                        style="margin:0;font-size:1.1rem;font-weight:700;opacity:0.9;"
                    >
                        📋 Datos Generales
                    </h3>
                    {#if savingGeneral}<span
                            class="loading loading-spinner loading-sm text-primary"
                        ></span>{/if}
                </div>
                <form
                    onsubmit={(e) => {
                        e.preventDefault();
                        saveGeneral();
                    }}
                    style="display:flex;flex-direction:column;gap:1.25rem;"
                >
                    {#if errorGeneral}<div class="alert alert-error py-2">
                            <span style="font-size:0.85rem;"
                                >{errorGeneral}</span
                            >
                        </div>{/if}

                    <div
                        style="display:grid;grid-template-columns:repeat(auto-fit, minmax(250px, 1fr));gap:1rem;"
                    >
                        <label class="form-control">
                            <div class="label">
                                <span
                                    class="label-text font-semibold opacity-70"
                                    >Nombre *</span
                                >
                            </div>
                            <input
                                class="input input-bordered input-sm bg-base-100"
                                type="text"
                                bind:value={fNombre}
                                required
                            />
                        </label>
                        <label class="form-control">
                            <div class="label">
                                <span
                                    class="label-text font-semibold opacity-70"
                                    >Dirección</span
                                >
                            </div>
                            <input
                                class="input input-bordered input-sm bg-base-100"
                                type="text"
                                bind:value={fDireccion}
                                placeholder="ej: Av. Principal 123"
                            />
                        </label>
                        <label class="form-control">
                            <div class="label">
                                <span
                                    class="label-text font-semibold opacity-70"
                                    >Coordenadas GPS</span
                                >
                            </div>
                            <input
                                class="input input-bordered input-sm bg-base-100"
                                type="text"
                                bind:value={fCoordenadas}
                                placeholder="ej: -12.0464, -77.0428"
                            />
                        </label>
                    </div>

                    <label class="form-control">
                        <div class="label">
                            <span class="label-text font-semibold opacity-70"
                                >Virtual Rack (JSON)</span
                            >
                            <span class="label-text-alt opacity-40"
                                >Opcional</span
                            >
                        </div>
                        <textarea
                            class="textarea textarea-bordered textarea-sm font-mono bg-base-100"
                            bind:value={fRackJson}
                            rows="3"
                            placeholder="Formato JSON estructural del rack"
                        ></textarea>
                    </label>

                    <div style="text-align:right;">
                        <button
                            type="submit"
                            class="btn btn-primary btn-sm px-6"
                            disabled={savingGeneral}>Guardar</button
                        >
                    </div>
                </form>
            </div>
        {/if}

        <!-- ─── SECCIÓN 2: INFRAESTRUCTURA ─────────────────────────────── -->
        {#if activeTab === "infra"}
            <div
                class="glass-card-flat"
                style="border-radius:1rem;padding:1.5rem;"
            >
                <div
                    style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1.5rem;"
                >
                    <h3
                        style="margin:0;font-size:1.1rem;font-weight:700;opacity:0.9;"
                    >
                        🔌 Infraestructura de Red
                    </h3>
                    {#if savingInfra}<span
                            class="loading loading-spinner loading-sm text-primary"
                        ></span>{/if}
                </div>
                <form
                    onsubmit={(e) => {
                        e.preventDefault();
                        saveInfra();
                    }}
                    style="display:flex;flex-direction:column;gap:1.25rem;"
                >
                    {#if errorInfra}<div class="alert alert-error py-2">
                            <span style="font-size:0.85rem;">{errorInfra}</span>
                        </div>{/if}

                    <div
                        style="display:grid;grid-template-columns:repeat(auto-fit, minmax(220px, 1fr));gap:1rem;"
                    >
                        <label class="form-control">
                            <div class="label">
                                <span
                                    class="label-text font-semibold opacity-70"
                                    >IP de Gestión</span
                                >
                            </div>
                            <input
                                class="input input-bordered input-sm font-mono bg-base-100"
                                type="text"
                                bind:value={fIpGestion}
                                placeholder="192.168.X.X"
                            />
                        </label>
                        <label class="form-control">
                            <div class="label">
                                <span
                                    class="label-text font-semibold opacity-70"
                                    >Gateway</span
                                >
                            </div>
                            <input
                                class="input input-bordered input-sm font-mono bg-base-100"
                                type="text"
                                bind:value={fGateway}
                                placeholder="192.168.X.1"
                            />
                        </label>
                        <label class="form-control">
                            <div class="label">
                                <span
                                    class="label-text font-semibold opacity-70"
                                    >Servidores DNS</span
                                >
                            </div>
                            <input
                                class="input input-bordered input-sm font-mono bg-base-100"
                                type="text"
                                bind:value={fDns}
                                placeholder="8.8.8.8, 1.1.1.1"
                            />
                        </label>
                        <label class="form-control">
                            <div class="label">
                                <span
                                    class="label-text font-semibold opacity-70"
                                    >VLANs Utilizadas</span
                                >
                            </div>
                            <input
                                class="input input-bordered input-sm font-mono bg-base-100"
                                type="text"
                                bind:value={fVlans}
                                placeholder="10, 20..."
                            />
                        </label>
                    </div>

                    <div
                        style="display:grid;grid-template-columns:repeat(auto-fit, minmax(250px, 1fr));gap:1rem;"
                    >
                        <label class="form-control">
                            <div class="label">
                                <span
                                    class="label-text font-semibold opacity-70"
                                    >Equipos Críticos</span
                                >
                            </div>
                            <textarea
                                class="textarea textarea-bordered textarea-sm bg-base-100"
                                bind:value={fEquipos}
                                rows="2"
                                placeholder="ej: Core switch principal..."
                            ></textarea>
                        </label>

                        <label class="form-control">
                            <div class="label">
                                <span
                                    class="label-text font-semibold opacity-70"
                                    >Próximo Mantenimiento</span
                                >
                            </div>
                            <input
                                class="input input-bordered input-sm bg-base-100"
                                type="date"
                                bind:value={fMantenimiento}
                            />
                        </label>
                    </div>

                    <div style="text-align:right;">
                        <button
                            type="submit"
                            class="btn btn-primary btn-sm px-6"
                            disabled={savingInfra}>Guardar</button
                        >
                    </div>
                </form>
            </div>
        {/if}

        <!-- ─── SECCIÓN 3: NOTAS ────────────────────────────────────────── -->
        {#if activeTab === "notas"}
            <div
                class="glass-card-flat"
                style="border-radius:1rem;padding:1.5rem;"
            >
                <div
                    style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem;"
                >
                    <h3
                        style="margin:0;font-size:1.1rem;font-weight:700;opacity:0.9;"
                    >
                        📝 Notas ({zona.notes.length})
                    </h3>
                    <button
                        class="btn btn-xs btn-outline"
                        onclick={openCreateNote}>+ Añadir</button
                    >
                </div>

                <div style="display:flex;flex-direction:column;gap:0.75rem;">
                    {#if zona.notes.length === 0}
                        <p
                            style="opacity:0.4;font-size:0.875rem;text-align:center;padding:1rem 0;margin:0;"
                        >
                            Sin notas adjuntas
                        </p>
                    {:else}
                        <div
                            style="display:grid;grid-template-columns:repeat(auto-fill, minmax(280px, 1fr));gap:1rem;"
                        >
                            {#each zona.notes as note}
                                <div
                                    style="background:var(--color-base-100);padding:1rem;border-radius:0.75rem;border:1px solid oklch(from var(--color-base-content) l c h / 0.08);position:relative;"
                                >
                                    <div
                                        style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:0.5rem;padding-right:2rem;"
                                    >
                                        <span
                                            style="font-weight:600;font-size:0.9rem;opacity:0.9;"
                                            >{note.title}</span
                                        >
                                        {#if note.is_encrypted}<span
                                                class="badge badge-warning badge-xs"
                                                style="position:absolute;top:1rem;right:1rem;"
                                                title="Nota encriptada">🔒</span
                                            >{/if}
                                    </div>
                                    {#if note.content}
                                        <p
                                            style="margin:0 0 0.75rem;font-size:0.82rem;opacity:0.65;white-space:pre-wrap;"
                                        >
                                            {note.content}
                                        </p>
                                    {/if}
                                    <div
                                        style="display:flex;align-items:center;justify-content:space-between;border-top:1px solid oklch(from var(--color-base-content) l c h / 0.08);padding-top:0.5rem;margin-top:auto;"
                                    >
                                        <span
                                            style="font-size:0.7rem;opacity:0.4;"
                                            >{fmtDate(note.updated_at)}</span
                                        >
                                        <div style="display:flex;gap:0.25rem;">
                                            <button
                                                class="btn btn-xs btn-ghost px-2"
                                                onclick={() =>
                                                    openEditNote(note)}
                                                >✏️</button
                                            >
                                            <button
                                                class="btn btn-xs btn-ghost text-error px-2"
                                                onclick={() => {
                                                    deleteNoteTarget = note;
                                                    showDeleteNoteModal = true;
                                                }}>🗑️</button
                                            >
                                        </div>
                                    </div>
                                </div>
                            {/each}
                        </div>
                    {/if}
                </div>
            </div>
        {/if}

        <!-- ─── SECCIÓN 4: DOCUMENTOS ──────────────────────────────────── -->
        {#if activeTab === "documentos"}
            <div
                class="glass-card-flat"
                style="border-radius:1rem;padding:1.5rem;"
            >
                <div
                    style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem;"
                >
                    <h3
                        style="margin:0;font-size:1.1rem;font-weight:700;opacity:0.9;"
                    >
                        📄 Documentos ({zona.documentos.length})
                    </h3>
                    <div style="display:flex;align-items:center;gap:0.5rem;">
                        {#if uploadingDoc}
                            <span
                                class="loading loading-spinner loading-sm text-primary"
                            ></span>
                        {/if}
                        <input
                            type="file"
                            bind:this={fileInput}
                            onchange={uploadDoc}
                            style="display:none;"
                            accept="image/*,.pdf,.doc,.docx,.xls,.xlsx,.txt"
                        />
                        <button
                            class="btn btn-xs btn-outline"
                            disabled={uploadingDoc}
                            onclick={() => fileInput?.click()}
                        >
                            Subir
                        </button>
                    </div>
                </div>

                <div style="display:flex;flex-direction:column;gap:0.5rem;">
                    {#if zona.documentos.length === 0}
                        <p
                            style="opacity:0.4;font-size:0.875rem;text-align:center;padding:1rem 0;margin:0;"
                        >
                            Sin documentos adjuntos
                        </p>
                    {:else}
                        <div
                            style="display:grid;grid-template-columns:repeat(auto-fill, minmax(300px, 1fr));gap:0.75rem;"
                        >
                            {#each zona.documentos as doc}
                                <div
                                    style="display:flex;align-items:center;gap:0.75rem;background:var(--color-base-100);padding:0.75rem 1rem;border-radius:0.75rem;border:1px solid oklch(from var(--color-base-content) l c h / 0.08);"
                                >
                                    <span style="font-size:1.25rem;opacity:0.7;"
                                        >{doc.tipo === "pdf"
                                            ? "📕"
                                            : doc.tipo === "imagen"
                                              ? "🖼️"
                                              : "📎"}</span
                                    >
                                    <div style="flex:1;min-width:0;">
                                        <p
                                            style="margin:0;font-weight:600;font-size:0.85rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;opacity:0.9;"
                                        >
                                            {doc.nombre_original}
                                        </p>
                                        <p
                                            style="margin:0;font-size:0.7rem;opacity:0.5;"
                                        >
                                            {doc.tipo.toUpperCase()} • {fmtDate(
                                                doc.creado_en,
                                            )}
                                        </p>
                                    </div>
                                    <button
                                        class="btn btn-xs btn-square btn-ghost text-error"
                                        onclick={() => {
                                            deleteDocTarget = doc;
                                            showDeleteDocModal = true;
                                        }}>🗑️</button
                                    >
                                </div>
                            {/each}
                        </div>
                    {/if}
                </div>
            </div>
        {/if}
    </div>
{/if}

<!-- ═══ MODAL: Crear/Editar Nota ═══════════════════════════════════════════ -->
{#if showNoteModal}
    <div
        style="position:fixed;inset:0;z-index:200;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;padding:1rem;"
        role="dialog"
        aria-modal="true"
    >
        <div
            style="background:var(--color-base-100);border-radius:1rem;width:100%;max-width:480px;box-shadow:0 25px 50px -12px rgba(0,0,0,0.4);overflow:hidden;"
        >
            <div
                style="padding:1.25rem 1.5rem;border-bottom:1px solid oklch(from var(--color-base-content) l c h / 0.12);display:flex;align-items:center;justify-content:space-between;"
            >
                <h3 style="margin:0;font-size:1.1rem;font-weight:700;">
                    {noteModalMode === "create"
                        ? "➕ Nueva Nota"
                        : "✏️ Editar Nota"}
                </h3>
                <button
                    class="btn btn-ghost btn-sm btn-circle"
                    onclick={() => (showNoteModal = false)}>✕</button
                >
            </div>
            <form
                onsubmit={(e) => {
                    e.preventDefault();
                    saveNote();
                }}
                style="padding:1.5rem;display:flex;flex-direction:column;gap:1rem;"
            >
                {#if errorNote}
                    <div class="alert alert-error py-2">
                        <span style="font-size:0.85rem;">{errorNote}</span>
                    </div>
                {/if}

                <label class="form-control">
                    <div class="label">
                        <span class="label-text font-semibold">Título *</span>
                    </div>
                    <input
                        class="input input-bordered input-sm"
                        type="text"
                        bind:value={fNoteTitle}
                        required
                    />
                </label>

                <label class="form-control">
                    <div class="label">
                        <span class="label-text font-semibold">Contenido</span>
                        <span class="label-text-alt opacity-50">Opcional</span>
                    </div>
                    <textarea
                        class="textarea textarea-bordered textarea-sm"
                        bind:value={fNoteContent}
                        rows="5"
                        placeholder="Escribe la nota aquí..."
                    ></textarea>
                </label>

                <div
                    style="display:flex;align-items:center;justify-content:space-between;"
                >
                    <span class="label-text font-semibold"
                        >🔒 Nota Encriptada</span
                    >
                    <input
                        type="checkbox"
                        class="toggle toggle-warning toggle-sm"
                        bind:checked={fNoteEncrypted}
                    />
                </div>

                <div style="display:flex;gap:0.5rem;justify-content:flex-end;">
                    <button
                        type="button"
                        class="btn btn-ghost btn-sm"
                        onclick={() => (showNoteModal = false)}>Cancelar</button
                    >
                    <button
                        type="submit"
                        class="btn btn-primary btn-sm"
                        disabled={savingNote}
                    >
                        {#if savingNote}<span
                                class="loading loading-spinner loading-xs"
                            ></span>{/if}
                        {noteModalMode === "create" ? "Crear" : "Guardar"}
                    </button>
                </div>
            </form>
        </div>
    </div>
{/if}

<!-- ═══ MODAL: Confirmar Eliminar Nota ════════════════════════════════════ -->
{#if showDeleteNoteModal && deleteNoteTarget}
    <div
        style="position:fixed;inset:0;z-index:200;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;padding:1rem;"
        role="dialog"
        aria-modal="true"
    >
        <div
            style="background:var(--color-base-100);border-radius:1rem;width:100%;max-width:380px;box-shadow:0 25px 50px -12px rgba(0,0,0,0.4);padding:1.5rem;display:flex;flex-direction:column;gap:1rem;"
        >
            <h3
                style="margin:0;font-size:1.1rem;font-weight:700;color:var(--color-error);"
            >
                🗑️ Eliminar Nota
            </h3>
            <p style="margin:0;font-size:0.9rem;opacity:0.8;">
                ¿Eliminar la nota <strong>{deleteNoteTarget.title}</strong>?
                Esta acción no se puede deshacer.
            </p>
            <div style="display:flex;gap:0.5rem;justify-content:flex-end;">
                <button
                    class="btn btn-ghost btn-sm"
                    onclick={() => (showDeleteNoteModal = false)}
                    >Cancelar</button
                >
                <button
                    class="btn btn-error btn-sm"
                    onclick={confirmDeleteNote}
                    disabled={deletingNote}
                >
                    {#if deletingNote}<span
                            class="loading loading-spinner loading-xs"
                        ></span>{/if}
                    Eliminar
                </button>
            </div>
        </div>
    </div>
{/if}

<!-- ═══ MODAL: Confirmar Eliminar Documento ══════════════════════════════ -->
{#if showDeleteDocModal && deleteDocTarget}
    <div
        style="position:fixed;inset:0;z-index:200;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;padding:1rem;"
        role="dialog"
        aria-modal="true"
    >
        <div
            style="background:var(--color-base-100);border-radius:1rem;width:100%;max-width:380px;box-shadow:0 25px 50px -12px rgba(0,0,0,0.4);padding:1.5rem;display:flex;flex-direction:column;gap:1rem;"
        >
            <h3
                style="margin:0;font-size:1.1rem;font-weight:700;color:var(--color-error);"
            >
                🗑️ Eliminar Documento
            </h3>
            <p style="margin:0;font-size:0.9rem;opacity:0.8;">
                ¿Eliminar el documento <strong
                    >{deleteDocTarget.nombre_original}</strong
                >? Se eliminará permanentemente.
            </p>
            <div style="display:flex;gap:0.5rem;justify-content:flex-end;">
                <button
                    class="btn btn-ghost btn-sm"
                    onclick={() => (showDeleteDocModal = false)}
                    >Cancelar</button
                >
                <button
                    class="btn btn-error btn-sm"
                    onclick={confirmDeleteDoc}
                    disabled={deletingDoc}
                >
                    {#if deletingDoc}<span
                            class="loading loading-spinner loading-xs"
                        ></span>{/if}
                    Eliminar
                </button>
            </div>
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

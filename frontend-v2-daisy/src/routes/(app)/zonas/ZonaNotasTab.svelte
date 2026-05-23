<script lang="ts">
    import { createZonaNote, updateZonaNote, deleteZonaNote } from "$lib/api";
    import type { ZonaDetail, ZonaNote, ZonaNoteCreate } from "$lib/types/zona";
    import MarkdownViewer from "$lib/components/MarkdownViewer.svelte";

    let { zona, zonaId, canEdit = false, onsave } = $props<{
        zona: ZonaDetail;
        zonaId: number;
        canEdit?: boolean;
        onsave?: () => void;
    }>();

    // ── Estado lectura ─────────────────────────────────────────────────────
    let selectedNote = $state<{ title: string; content: string } | null>(null);

    // ── Estado edición ─────────────────────────────────────────────────────
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

    function fmtDate(v: string | null | undefined): string {
        if (!v) return "—";
        try { return new Date(v).toLocaleDateString("es", { day: "2-digit", month: "short", year: "numeric" }); }
        catch { return v; }
    }

    function openCreateNote() {
        noteModalMode = "create"; editNoteTarget = null;
        fNoteTitle = ""; fNoteContent = ""; fNoteEncrypted = false;
        errorNote = null; showNoteModal = true;
    }

    function openEditNote(n: ZonaNote) {
        noteModalMode = "edit"; editNoteTarget = n;
        fNoteTitle = n.title; fNoteContent = n.content ?? "";
        fNoteEncrypted = n.is_encrypted; errorNote = null; showNoteModal = true;
    }

    async function saveNote() {
        savingNote = true; errorNote = null;
        try {
            const data: ZonaNoteCreate = {
                title: fNoteTitle.trim(),
                content: fNoteContent.trim() || null,
                is_encrypted: fNoteEncrypted,
            };
            if (noteModalMode === "create") { await createZonaNote(zonaId, data); }
            else if (editNoteTarget) { await updateZonaNote(editNoteTarget.id, data); }
            showNoteModal = false;
            if (onsave) onsave();
        } catch (e: any) {
            errorNote = e?.response?.data?.detail ?? "Error al guardar nota.";
        } finally { savingNote = false; }
    }

    async function confirmDeleteNote() {
        if (!deleteNoteTarget) return;
        deletingNote = true;
        try {
            await deleteZonaNote(deleteNoteTarget.id);
            showDeleteNoteModal = false; deleteNoteTarget = null;
            if (onsave) onsave();
        } catch { showDeleteNoteModal = false; }
        finally { deletingNote = false; }
    }
</script>

<div class="glass-card-flat" style="border-radius:1rem;padding:1.5rem;display:flex;flex-direction:column;gap:1.25rem;">
    <!-- ── CABECERA ────────────────────────────────────────────────────── -->
    <div style="display:flex;align-items:center;justify-content:space-between;">
        <h3 style="margin:0;font-size:1.1rem;font-weight:700;opacity:0.9;">
            📝 Notas de la Zona
            {#if zona.notes.length > 0}
                <span class="badge badge-neutral ml-1">{zona.notes.length}</span>
            {/if}
        </h3>
        {#if canEdit}
            <button class="btn btn-xs btn-primary" onclick={openCreateNote}>
                + Nueva Nota
            </button>
        {/if}
    </div>

    <!-- ── CONTENIDO ───────────────────────────────────────────────────── -->
    {#if zona.notes.length === 0}
        <div style="text-align:center;padding:3rem 1.5rem;opacity:0.5;">
            <p style="font-size:2.5rem;margin:0 0 0.5rem;">📝</p>
            <p style="margin:0;font-size:0.9rem;">Sin notas adjuntas en esta zona.</p>
            {#if canEdit}
                <button class="btn btn-sm btn-outline mt-4" onclick={openCreateNote}>
                    Crear primera nota
                </button>
            {/if}
        </div>
    {:else}
        <div style="display:flex;flex-direction:column;gap:1rem;">
            {#each zona.notes as note}
                <!-- svelte-ignore a11y_click_events_have_key_events -->
                <!-- svelte-ignore a11y_no_static_element_interactions -->
                <div
                    class="note-card glass-card"
                    style="padding:1.25rem 1.5rem;border-radius:0.875rem;cursor:pointer;position:relative;"
                    onclick={() => { selectedNote = { title: note.title, content: note.content || "" }; }}
                    title="Haz clic para leer la nota completa"
                >
                    <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:1rem;margin-bottom:0.625rem;padding-right:4.5rem;">
                        <span style="font-weight:700;font-size:0.95rem;line-height:1.3;">{note.title}</span>
                        <div style="display:flex;align-items:center;gap:0.4rem;flex-shrink:0;">
                            {#if note.is_encrypted}
                                <span class="badge badge-warning badge-xs">🔒</span>
                            {/if}
                            <span style="font-size:0.72rem;opacity:0.4;">{fmtDate(note.updated_at)}</span>
                        </div>
                    </div>

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

                    {#if canEdit}
                        <div style="position:absolute;top:0.8rem;right:0.8rem;display:flex;gap:0.25rem;z-index:10;">
                            <button
                                class="btn btn-xs btn-square btn-ghost hover:bg-base-200"
                                title="Editar nota"
                                onclick={(e) => { e.stopPropagation(); openEditNote(note); }}
                            >
                                ✏️
                            </button>
                            <button
                                class="btn btn-xs btn-square btn-ghost text-error hover:bg-error/10"
                                title="Eliminar nota"
                                onclick={(e) => { e.stopPropagation(); deleteNoteTarget = note; showDeleteNoteModal = true; }}
                            >
                                🗑️
                            </button>
                        </div>
                    {/if}
                </div>
            {/each}
        </div>
    {/if}
</div>

<!-- ── MODAL Nota Completa (lectura) ──────────────────────────────────── -->
{#if selectedNote}
    <div class="modal modal-open">
        <div class="modal-box w-11/12 max-w-4xl" style="padding:0;overflow:hidden;">
            <div style="padding:1.25rem 1.5rem;border-bottom:1px solid oklch(from var(--color-base-content) l c h / 0.1);display:flex;align-items:center;justify-content:space-between;">
                <h3 style="font-weight:800;font-size:1.05rem;margin:0;">📄 {selectedNote.title}</h3>
                <button class="btn btn-ghost btn-sm btn-circle" onclick={() => { selectedNote = null; }}>✕</button>
            </div>
            <div style="padding:1.5rem;overflow-y:auto;max-height:68vh;">
                <MarkdownViewer content={selectedNote.content} />
            </div>
        </div>
        <div class="modal-backdrop" onclick={() => { selectedNote = null; }}
            onkeydown={(e) => { if (e.key === "Escape") selectedNote = null; }}
            role="button" tabindex="0"><span class="sr-only">Cerrar</span></div>
    </div>
{/if}

<!-- ── MODAL Crear/Editar Nota (edición) ──────────────────────────────── -->
{#if showNoteModal}
    <div style="position:fixed;inset:0;z-index:200;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;padding:1rem;" role="dialog" aria-modal="true">
        <div style="background:var(--color-base-100);border-radius:1rem;width:100%;max-width:480px;box-shadow:0 25px 50px -12px rgba(0,0,0,0.4);overflow:hidden;">
            <div style="padding:1.25rem 1.5rem;border-bottom:1px solid oklch(from var(--color-base-content) l c h / 0.12);display:flex;align-items:center;justify-content:space-between;">
                <h3 style="margin:0;font-size:1.1rem;font-weight:700;">{noteModalMode === "create" ? "➕ Nueva Nota" : "✏️ Editar Nota"}</h3>
                <button class="btn btn-ghost btn-sm btn-circle" onclick={() => (showNoteModal = false)}>✕</button>
            </div>
            <form onsubmit={(e) => { e.preventDefault(); saveNote(); }} style="padding:1.5rem;display:flex;flex-direction:column;gap:1rem;">
                {#if errorNote}<div class="alert alert-error py-2"><span style="font-size:0.85rem;">{errorNote}</span></div>{/if}
                <label class="form-control">
                    <div class="label"><span class="label-text font-semibold">Título *</span></div>
                    <input class="input input-bordered input-sm" type="text" bind:value={fNoteTitle} required />
                </label>
                <label class="form-control">
                    <div class="label">
                        <span class="label-text font-semibold">Contenido</span>
                        <span class="label-text-alt opacity-50">Opcional</span>
                    </div>
                    <textarea class="textarea textarea-bordered textarea-sm" bind:value={fNoteContent} rows="5" placeholder="Escribe la nota aquí..."></textarea>
                </label>
                <div style="display:flex;align-items:center;justify-content:space-between;">
                    <span class="label-text font-semibold">🔒 Nota Encriptada</span>
                    <input type="checkbox" class="toggle toggle-warning toggle-sm" bind:checked={fNoteEncrypted} />
                </div>
                <div style="display:flex;gap:0.5rem;justify-content:flex-end;">
                    <button type="button" class="btn btn-ghost btn-sm" onclick={() => (showNoteModal = false)}>Cancelar</button>
                    <button type="submit" class="btn btn-primary btn-sm" disabled={savingNote}>
                        {#if savingNote}<span class="loading loading-spinner loading-xs"></span>{/if}
                        {noteModalMode === "create" ? "Crear" : "Guardar"}
                    </button>
                </div>
            </form>
        </div>
    </div>
{/if}

<!-- ── MODAL Eliminar Nota ────────────────────────────────────────────── -->
{#if showDeleteNoteModal && deleteNoteTarget}
    <div style="position:fixed;inset:0;z-index:200;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;padding:1rem;" role="dialog" aria-modal="true">
        <div style="background:var(--color-base-100);border-radius:1rem;width:100%;max-width:380px;box-shadow:0 25px 50px -12px rgba(0,0,0,0.4);padding:1.5rem;display:flex;flex-direction:column;gap:1rem;">
            <h3 style="margin:0;font-size:1.1rem;font-weight:700;color:var(--color-error);">🗑️ Eliminar Nota</h3>
            <p style="margin:0;font-size:0.9rem;opacity:0.8;">¿Eliminar la nota <strong>{deleteNoteTarget.title}</strong>? Esta acción no se puede deshacer.</p>
            <div style="display:flex;gap:0.5rem;justify-content:flex-end;">
                <button class="btn btn-ghost btn-sm" onclick={() => (showDeleteNoteModal = false)}>Cancelar</button>
                <button class="btn btn-error btn-sm" onclick={confirmDeleteNote} disabled={deletingNote}>
                    {#if deletingNote}<span class="loading loading-spinner loading-xs"></span>{/if}
                    Eliminar
                </button>
            </div>
        </div>
    </div>
{/if}

<style>
    .note-card { transition: box-shadow 0.18s ease, transform 0.18s ease, border-color 0.18s ease; }
    .note-card:hover { transform: translateY(-2px); border-color: oklch(from var(--color-primary) l c h / 0.3) !important; }
    .read-more-hint { transition: opacity 0.15s ease; }
    .note-card:hover .read-more-hint { opacity: 0.75 !important; }
</style>

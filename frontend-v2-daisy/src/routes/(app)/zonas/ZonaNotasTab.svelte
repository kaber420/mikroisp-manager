<script lang="ts">
    import { createZonaNote, updateZonaNote, deleteZonaNote } from "$lib/api";
    import type { ZonaDetail, ZonaNote, ZonaNoteCreate } from "$lib/types/zona";
    import MarkdownViewer from "$lib/components/MarkdownViewer.svelte";

    let { zona, zonaId, editMode = false, onsave, onedit } = $props<{
        zona: ZonaDetail;
        zonaId: number;
        editMode?: boolean;
        onsave?: () => void;
        onedit?: () => void;
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
            if (noteModalMode === "create") { await createZonaNote(zona.id, data); }
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

{#if editMode}
    <!-- ── MODO EDICIÓN ──────────────────────────────────────────────────── -->
    <div class="glass-card-flat" style="border-radius:1rem;padding:1.5rem;">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem;">
            <h3 style="margin:0;font-size:1.1rem;font-weight:700;opacity:0.9;">📝 Notas ({zona.notes.length})</h3>
            <button class="btn btn-xs btn-outline" onclick={openCreateNote}>+ Añadir</button>
        </div>

        <div style="display:flex;flex-direction:column;gap:0.75rem;">
            {#if zona.notes.length === 0}
                <p style="opacity:0.4;font-size:0.875rem;text-align:center;padding:1rem 0;margin:0;">Sin notas adjuntas</p>
            {:else}
                <div style="display:grid;grid-template-columns:repeat(auto-fill, minmax(280px, 1fr));gap:1rem;">
                    {#each zona.notes as note}
                        <div style="background:var(--color-base-100);padding:1rem;border-radius:0.75rem;border:1px solid oklch(from var(--color-base-content) l c h / 0.08);position:relative;">
                            <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:0.5rem;padding-right:2rem;">
                                <span style="font-weight:600;font-size:0.9rem;opacity:0.9;">{note.title}</span>
                                {#if note.is_encrypted}
                                    <span class="badge badge-warning badge-xs" style="position:absolute;top:1rem;right:1rem;" title="Nota encriptada">🔒</span>
                                {/if}
                            </div>
                            {#if note.content}
                                <p style="margin:0 0 0.75rem;font-size:0.82rem;opacity:0.65;white-space:pre-wrap;">{note.content}</p>
                            {/if}
                            <div style="display:flex;align-items:center;justify-content:space-between;border-top:1px solid oklch(from var(--color-base-content) l c h / 0.08);padding-top:0.5rem;">
                                <span style="font-size:0.7rem;opacity:0.4;">{fmtDate(note.updated_at)}</span>
                                <div style="display:flex;gap:0.25rem;">
                                    <button class="btn btn-xs btn-ghost px-2" onclick={() => openEditNote(note)}>✏️</button>
                                    <button class="btn btn-xs btn-ghost text-error px-2"
                                        onclick={() => { deleteNoteTarget = note; showDeleteNoteModal = true; }}>🗑️</button>
                                </div>
                            </div>
                        </div>
                    {/each}
                </div>
            {/if}
        </div>
    </div>

{:else}
    <!-- ── MODO LECTURA ──────────────────────────────────────────────────── -->
    <div style="display:flex;flex-direction:column;gap:0.875rem;">
        {#if zona.notes.length === 0}
            <div class="glass-card-flat" style="padding:3rem;border-radius:1rem;text-align:center;opacity:0.55;">
                <p style="font-size:2rem;margin:0 0 0.5rem;">📝</p>
                <p style="margin:0 0 1rem;font-size:0.9rem;">Sin notas. Activa el modo edición para añadir.</p>
                {#if onedit}
                    <button class="btn btn-sm btn-outline" onclick={onedit}>Gestionar notas</button>
                {/if}
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
                    <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:1rem;margin-bottom:0.625rem;">
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
                </div>
            {/each}

            {#if onedit}
                <div style="text-align:right;margin-top:0.25rem;">
                    <button class="btn btn-sm btn-ghost" onclick={onedit}>Gestionar notas →</button>
                </div>
            {/if}
        {/if}
    </div>
{/if}

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

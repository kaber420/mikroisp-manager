<script lang="ts">
    import type { ZonaDetail } from "$lib/types/zona";
    import MarkdownViewer from "$lib/components/MarkdownViewer.svelte";

    let { zona, zonaId } = $props<{ zona: ZonaDetail; zonaId: number }>();

    let selectedNote = $state<{ title: string; content: string } | null>(null);

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
                <div
                    style="display:flex;align-items:flex-start;justify-content:space-between;gap:1rem;margin-bottom:0.625rem;"
                >
                    <span style="font-weight:700;font-size:0.95rem;line-height:1.3;">{note.title}</span>
                    <div style="display:flex;align-items:center;gap:0.4rem;flex-shrink:0;">
                        {#if note.is_encrypted}
                            <span class="badge badge-warning badge-xs">🔒</span>
                        {/if}
                        <span style="font-size:0.72rem;opacity:0.4;">{fmtDate(note.updated_at)}</span>
                    </div>
                </div>

                <!-- Preview -->
                {#if note.content && !note.is_encrypted}
                    <div style="pointer-events:none;">
                        <MarkdownViewer content={note.content} preview={true} previewLength={200} />
                    </div>
                    <div
                        class="read-more-hint"
                        style="margin-top:0.6rem;display:flex;align-items:center;gap:0.3rem;font-size:0.75rem;opacity:0.45;font-style:italic;"
                    >
                        <span>↗</span> Leer nota completa
                    </div>
                {:else if note.is_encrypted}
                    <p style="font-size:0.82rem;opacity:0.45;margin:0;font-style:italic;">
                        🔒 Contenido encriptado — Haz clic para ver.
                    </p>
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

<!-- MODAL — Nota Completa -->
{#if selectedNote}
    <div class="modal modal-open">
        <div class="modal-box w-11/12 max-w-4xl" style="padding:0;overflow:hidden;">
            <div
                style="padding:1.25rem 1.5rem;border-bottom:1px solid oklch(from var(--color-base-content) l c h / 0.1);display:flex;align-items:center;justify-content:space-between;"
            >
                <h3 style="font-weight:800;font-size:1.05rem;margin:0;">📄 {selectedNote.title}</h3>
                <button
                    class="btn btn-ghost btn-sm btn-circle"
                    onclick={() => { selectedNote = null; }}>✕</button
                >
            </div>
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

<style>
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
</style>

<script lang="ts">
    import { uploadZonaDocumento, deleteZonaDocumento } from "$lib/api";
    import type { ZonaDetail, ZonaDocumento } from "$lib/types/zona";

    let { zona, zonaId, onsave } = $props<{
        zona: ZonaDetail;
        zonaId: number;
        onsave?: () => void;
    }>();

    let showDeleteDocModal = $state(false);
    let deleteDocTarget = $state<ZonaDocumento | null>(null);
    let deletingDoc = $state(false);
    let uploadingDoc = $state(false);
    let fileInput = $state<HTMLInputElement | null>(null);

    async function uploadDoc(e: Event) {
        const target = e.target as HTMLInputElement;
        if (!target.files || target.files.length === 0) return;
        const file = target.files[0];
        uploadingDoc = true;
        try {
            await uploadZonaDocumento(zonaId, file);
            if (onsave) onsave();
        } catch (e: any) {
            // Parent handles error notifications
        } finally {
            uploadingDoc = false;
            if (fileInput) fileInput.value = "";
        }
    }

    async function confirmDeleteDoc() {
        if (!deleteDocTarget) return;
        deletingDoc = true;
        try {
            await deleteZonaDocumento(deleteDocTarget.id);
            showDeleteDocModal = false;
            deleteDocTarget = null;
            if (onsave) onsave();
        } catch { showDeleteDocModal = false; }
        finally { deletingDoc = false; }
    }

    function fmtDate(v: string | null | undefined): string {
        if (!v) return "—";
        try { return new Date(v).toLocaleDateString("es", { day:"2-digit", month:"short", year:"numeric" }); }
        catch { return v; }
    }
</script>

<div class="glass-card-flat" style="border-radius:1rem;padding:1.5rem;">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem;">
        <h3 style="margin:0;font-size:1.1rem;font-weight:700;opacity:0.9;">📄 Documentos ({zona.documentos.length})</h3>
        <div style="display:flex;align-items:center;gap:0.5rem;">
            {#if uploadingDoc}
                <span class="loading loading-spinner loading-sm text-primary"></span>
            {/if}
            <input
                type="file"
                bind:this={fileInput}
                onchange={uploadDoc}
                style="display:none;"
                accept="image/*,.pdf,.doc,.docx,.xls,.xlsx,.txt"
            />
            <button class="btn btn-xs btn-outline" disabled={uploadingDoc} onclick={() => fileInput?.click()}>
                Subir
            </button>
        </div>
    </div>

    <div style="display:flex;flex-direction:column;gap:0.5rem;">
        {#if zona.documentos.length === 0}
            <p style="opacity:0.4;font-size:0.875rem;text-align:center;padding:1rem 0;margin:0;">Sin documentos adjuntos</p>
        {:else}
            <div style="display:grid;grid-template-columns:repeat(auto-fill, minmax(300px, 1fr));gap:0.75rem;">
                {#each zona.documentos as doc}
                    <div style="display:flex;align-items:center;gap:0.75rem;background:var(--color-base-100);padding:0.75rem 1rem;border-radius:0.75rem;border:1px solid oklch(from var(--color-base-content) l c h / 0.08);">
                        <span style="font-size:1.25rem;opacity:0.7;">
                            {doc.tipo === "pdf" ? "📕" : doc.tipo === "image" ? "🖼️" : "📎"}
                        </span>
                        <div style="flex:1;min-width:0;">
                            <p style="margin:0;font-weight:600;font-size:0.85rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;opacity:0.9;">{doc.nombre_original}</p>
                            <p style="margin:0;font-size:0.7rem;opacity:0.5;">{doc.tipo.toUpperCase()} • {fmtDate(doc.creado_en)}</p>
                        </div>
                        <button
                            class="btn btn-xs btn-square btn-ghost text-error"
                            onclick={() => { deleteDocTarget = doc; showDeleteDocModal = true; }}>🗑️</button>
                    </div>
                {/each}
            </div>
        {/if}
    </div>
</div>

{#if showDeleteDocModal && deleteDocTarget}
    <div style="position:fixed;inset:0;z-index:200;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;padding:1rem;" role="dialog" aria-modal="true">
        <div style="background:var(--color-base-100);border-radius:1rem;width:100%;max-width:380px;box-shadow:0 25px 50px -12px rgba(0,0,0,0.4);padding:1.5rem;display:flex;flex-direction:column;gap:1rem;">
            <h3 style="margin:0;font-size:1.1rem;font-weight:700;color:var(--color-error);">🗑️ Eliminar Documento</h3>
            <p style="margin:0;font-size:0.9rem;opacity:0.8;">¿Eliminar el documento <strong>{deleteDocTarget.nombre_original}</strong>? Se eliminará permanentemente.</p>
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

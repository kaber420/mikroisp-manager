<script lang="ts">
    let { isOpen = $bindable(false), onclose = () => {} } = $props<{
        isOpen: boolean;
        onclose?: () => void;
    }>();
</script>

{#if isOpen}
<div class="modal modal-open">
    <div class="modal-box max-w-4xl h-[80vh] flex flex-col p-0 overflow-hidden bg-neutral-900 border border-white/10">
        <div class="bg-black/40 p-4 border-b border-white/5 flex items-center justify-between">
            <div class="flex items-center gap-3">
                <span class="w-3 h-3 rounded-full bg-error animate-pulse"></span>
                <span class="text-white font-bold text-sm tracking-widest uppercase">Videoasistencia en vivo</span>
            </div>
            <button class="btn btn-circle btn-ghost btn-sm text-white/50 hover:text-white" onclick={onclose}>✕</button>
        </div>

        <div class="flex-1 relative bg-black flex items-center justify-center text-white/10">
            <span class="text-6xl">📹</span>
            <div class="absolute bottom-6 right-6 w-48 h-32 bg-neutral-800 rounded-2xl border-2 border-primary shadow-2xl overflow-hidden">
                <!-- Mi cámara -->
                <div class="w-full h-full flex items-center justify-center text-xs opacity-30 italic">Mi cámara</div>
            </div>
        </div>

        <div class="p-6 bg-black/80 flex items-center justify-center gap-4">
            <button class="btn btn-circle btn-lg btn-ghost border border-white/10 text-white">🎤</button>
            <button class="btn btn-circle btn-lg btn-error shadow-2xl shadow-error/20" onclick={onclose}>📞</button>
            <button class="btn btn-circle btn-lg btn-ghost border border-white/10 text-white">⚙️</button>
        </div>
    </div>
</div>
{/if}

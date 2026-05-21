<script lang="ts">
    let {
        selectedFile = $bindable<File | null>(null),
        imageUrl = $bindable(""),
        imageError = $bindable(false),
        localPreviewUrl = $bindable<string | null>(null),
        onfileselect,
        onclearfile,
    }: {
        selectedFile: File | null;
        imageUrl: string;
        imageError: boolean;
        localPreviewUrl: string | null;
        onfileselect?: (event: Event) => void;
        onclearfile?: () => void;
    } = $props();
</script>

<div class="card bg-base-100 shadow-sm">
    <div class="card-body gap-3">
        <h2 class="card-title text-base">
            <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-5 w-5 text-primary"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
            >
                <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                />
            </svg>
            Imagen
            <span class="badge badge-ghost badge-sm ml-1 font-normal">Opcional</span>
        </h2>

        <input
            type="file"
            id="broadcastFileInput"
            accept=".jpg,.jpeg,.png,.webp"
            class="hidden"
            onchange={onfileselect}
        />

        {#if !selectedFile}
            <!-- Zona de subida -->
            <button
                type="button"
                onclick={() => document.getElementById("broadcastFileInput")?.click()}
                class="border-base-300 hover:border-primary/50 hover:bg-base-200 flex flex-col items-center gap-2 rounded-xl border-2 border-dashed py-8 transition-all"
            >
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    class="text-base-content/30 h-10 w-10"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="1.5"
                        d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                    />
                </svg>
                <span class="text-sm font-medium">Haz clic para subir una imagen</span>
                <span class="text-base-content/40 text-xs">JPG, PNG, WebP · Máx 5 MB</span>
            </button>

            <!-- O usa URL -->
            <div class="flex items-center gap-2">
                <div class="divider flex-1 text-xs">o usa URL</div>
            </div>
            <label class="input input-bordered flex items-center gap-2">
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    class="text-base-content/40 h-4 w-4 shrink-0"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"
                    />
                </svg>
                <input
                    type="url"
                    bind:value={imageUrl}
                    oninput={() => (imageError = false)}
                    placeholder="https://ejemplo.com/imagen.jpg"
                    class="grow text-sm"
                />
            </label>
        {:else}
            <!-- Archivo seleccionado -->
            <div
                class="flex items-center gap-3 rounded-xl border border-success/30 bg-success/10 px-4 py-3"
            >
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    class="h-5 w-5 text-success"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                    />
                </svg>
                <span class="min-w-0 flex-1 truncate text-sm font-medium text-success"
                    >{selectedFile.name}</span
                >
                <button
                    onclick={onclearfile}
                    class="btn btn-ghost btn-xs btn-circle text-error"
                    title="Quitar imagen"
                >
                    <svg
                        xmlns="http://www.w3.org/2000/svg"
                        class="h-4 w-4"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M6 18L18 6M6 6l12 12"
                        />
                    </svg>
                </button>
            </div>
        {/if}

        <!-- Preview de imagen -->
        {#if localPreviewUrl || (imageUrl && !imageError)}
            <div class="overflow-hidden rounded-xl border border-base-300 bg-black/10">
                <img
                    src={localPreviewUrl ?? imageUrl}
                    alt="Vista previa"
                    class="h-48 w-full object-cover opacity-80 transition-opacity hover:opacity-100"
                    onerror={() => (imageError = true)}
                />
            </div>
        {/if}
        {#if imageError && imageUrl}
            <p class="text-error text-xs">La URL no es válida o no es accesible.</p>
        {/if}
    </div>
</div>

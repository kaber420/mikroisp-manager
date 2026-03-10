<script lang="ts">
    import { uploadBroadcastImage, sendBroadcast } from "$lib/api";
    import type { PageData } from "./$types";
    import type { BroadcastTargetType } from "$lib/types/broadcast";

    let { data }: { data: PageData } = $props();

    // --- Estado del formulario ---
    let targetType: BroadcastTargetType = $state("clients");
    let allZones = $state(true);
    let selectedZoneIds = $state<number[]>([]);
    let staffRoles = $state({ admin: true, technician: true, billing: true });

    let message = $state("");
    let imageUrl = $state("");
    let selectedFile = $state<File | null>(null);
    let localPreviewUrl = $state<string | null>(null);
    let imageError = $state(false);

    // --- Estado de la operación ---
    let sending = $state(false);
    let uploading = $state(false);
    let lastResult = $state<{ recipient_count: number; target: string } | null>(
        null,
    );
    let errorMessage = $state("");

    // --- Modal de confirmación ---
    let confirmModal: HTMLDialogElement;

    // --- Computed ---
    let targetLabel = $derived(() => {
        if (targetType === "technicians") {
            const roles = Object.entries(staffRoles)
                .filter(([, v]) => v)
                .map(
                    ([k]) =>
                        ({
                            admin: "Admin",
                            technician: "Técnicos",
                            billing: "Cobranza",
                        })[k] ?? k,
                );
            if (roles.length === 0) return "Ningún rol seleccionado";
            if (roles.length === 3)
                return "Todo el Personal (Admin, Técnicos, Cobranza)";
            return `Personal: ${roles.join(", ")}`;
        }
        if (allZones) return "Todos los Clientes (Multizona)";
        return `${selectedZoneIds.length} zona(s) seleccionada(s)`;
    });

    let canSend = $derived(
        message.trim().length > 0 &&
            (targetType === "clients"
                ? allZones || selectedZoneIds.length > 0
                : Object.values(staffRoles).some(Boolean)),
    );

    // --- Gestión de imagen ---
    function handleFileSelect(event: Event) {
        const input = event.target as HTMLInputElement;
        const file = input.files?.[0];
        if (!file) return;

        const validTypes = ["image/jpeg", "image/png", "image/webp"];
        if (!validTypes.includes(file.type)) {
            errorMessage = "Tipo no permitido: usa JPG, PNG o WebP.";
            return;
        }
        if (file.size > 5 * 1024 * 1024) {
            errorMessage = "Imagen demasiado grande (máximo 5 MB).";
            return;
        }

        errorMessage = "";
        selectedFile = file;
        imageUrl = "";
        imageError = false;
        if (localPreviewUrl) URL.revokeObjectURL(localPreviewUrl);
        localPreviewUrl = URL.createObjectURL(file);
    }

    function clearFile() {
        selectedFile = null;
        if (localPreviewUrl) {
            URL.revokeObjectURL(localPreviewUrl);
            localPreviewUrl = null;
        }
        const input = document.getElementById(
            "broadcastFileInput",
        ) as HTMLInputElement | null;
        if (input) input.value = "";
    }

    // --- Envío ---
    function openConfirmModal() {
        if (!canSend) return;
        errorMessage = "";
        confirmModal?.showModal();
    }

    async function handleSend() {
        confirmModal?.close();
        sending = true;
        lastResult = null;
        errorMessage = "";

        try {
            let localImagePath: string | null = null;

            if (selectedFile) {
                uploading = true;
                try {
                    const uploaded = await uploadBroadcastImage(selectedFile);
                    localImagePath = uploaded.temp_path;
                } finally {
                    uploading = false;
                }
            }

            const payload: import("$lib/types/broadcast").BroadcastRequest = {
                message: message.trim(),
                target_type: targetType,
                image_url: imageUrl || null,
                local_image_path: localImagePath,
            };

            if (targetType === "clients" && !allZones) {
                payload.zone_ids = [...selectedZoneIds];
            }

            if (targetType === "technicians") {
                payload.staff_roles = Object.entries(staffRoles)
                    .filter(([, v]) => v)
                    .map(([k]) => k);
            }

            const result = await sendBroadcast(payload);
            lastResult = result;

            // Limpiar formulario
            message = "";
            imageUrl = "";
            clearFile();
        } catch (e: any) {
            errorMessage =
                e?.response?.data?.detail ||
                e?.message ||
                "Error desconocido al enviar.";
        } finally {
            sending = false;
        }
    }

    function toggleZone(id: number) {
        if (selectedZoneIds.includes(id)) {
            selectedZoneIds = selectedZoneIds.filter((z) => z !== id);
        } else {
            selectedZoneIds = [...selectedZoneIds, id];
        }
    }
</script>

<svelte:head>
    <title>Difusión — UManager v2</title>
</svelte:head>

<!-- ===== ENCABEZADO ===== -->
<div class="mb-6 flex items-center gap-3">
    <div class="bg-warning/10 text-warning rounded-xl p-3">
        <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-7 w-7"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
        >
            <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M11 5.882V19.24a1.76 1.76 0 01-3.417.592l-2.147-6.15M18 13a3 3 0 100-6M5.436 13.683A4.001 4.001 0 017 6h1.832c4.1 0 7.625-1.234 9.168-3v14c-1.543-1.766-5.067-3-9.168-3H7a3.988 3.988 0 01-1.564-.317z"
            />
        </svg>
    </div>
    <div>
        <h1 class="text-2xl font-bold">Difusión Masiva</h1>
        <p class="text-base-content/60 text-sm">
            Envía mensajes por Telegram a clientes o personal
        </p>
    </div>
</div>

<div class="grid grid-cols-1 gap-6 lg:grid-cols-3">
    <!-- ===== COLUMNA PRINCIPAL ===== -->
    <div class="space-y-5 lg:col-span-2">
        <!-- 1. DESTINATARIOS -->
        <div class="card bg-base-100 shadow-sm">
            <div class="card-body gap-4">
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
                            d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"
                        />
                    </svg>
                    Destinatarios
                </h2>

                <!-- Tabs de tipo -->
                <div class="grid grid-cols-2 gap-3">
                    <!-- Clientes -->
                    <button
                        onclick={() => (targetType = "clients")}
                        class="flex flex-col items-start gap-1 rounded-xl border-2 p-4 text-left transition-all
                               {targetType === 'clients'
                            ? 'border-primary bg-primary/10'
                            : 'border-base-300 hover:border-primary/40'}"
                    >
                        <span class="text-2xl">👥</span>
                        <span class="font-semibold">Clientes</span>
                        <span class="text-base-content/50 text-xs"
                            >Usuarios del servicio con Telegram</span
                        >
                    </button>

                    <!-- Personal -->
                    <button
                        onclick={() => (targetType = "technicians")}
                        class="flex flex-col items-start gap-1 rounded-xl border-2 p-4 text-left transition-all
                               {targetType === 'technicians'
                            ? 'border-primary bg-primary/10'
                            : 'border-base-300 hover:border-primary/40'}"
                    >
                        <span class="text-2xl">🏷️</span>
                        <span class="font-semibold">Personal (Staff)</span>
                        <span class="text-base-content/50 text-xs"
                            >Técnicos, Cobranza y Admins</span
                        >
                    </button>
                </div>

                <!-- Opciones de Clientes -->
                {#if targetType === "clients"}
                    <div class="bg-base-200 rounded-xl p-4 transition-all">
                        <label class="flex cursor-pointer items-center gap-3">
                            <input
                                type="checkbox"
                                class="checkbox checkbox-primary checkbox-sm"
                                bind:checked={allZones}
                            />
                            <span class="font-medium">Todas las Zonas</span>
                        </label>

                        {#if !allZones}
                            <div class="mt-4">
                                {#if data.zones.length === 0}
                                    <div
                                        class="text-base-content/50 flex flex-col items-center gap-2 py-6 text-sm"
                                    >
                                        <svg
                                            xmlns="http://www.w3.org/2000/svg"
                                            class="h-8 w-8 opacity-40"
                                            fill="none"
                                            viewBox="0 0 24 24"
                                            stroke="currentColor"
                                        >
                                            <path
                                                stroke-linecap="round"
                                                stroke-linejoin="round"
                                                stroke-width="2"
                                                d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064"
                                            />
                                        </svg>
                                        No hay zonas con clientes de Telegram
                                    </div>
                                {:else}
                                    <div
                                        class="mt-2 grid max-h-48 grid-cols-1 gap-2 overflow-y-auto pr-1 sm:grid-cols-2"
                                    >
                                        {#each data.zones as zone (zone.id)}
                                            <label
                                                class="flex cursor-pointer items-center gap-3 rounded-lg p-3 transition-all
                                                   {selectedZoneIds.includes(
                                                    zone.id,
                                                )
                                                    ? 'bg-primary/10 border-primary border'
                                                    : 'border-base-300 bg-base-100 hover:border-primary/40 border'}"
                                            >
                                                <input
                                                    type="checkbox"
                                                    class="checkbox checkbox-primary checkbox-sm"
                                                    checked={selectedZoneIds.includes(
                                                        zone.id,
                                                    )}
                                                    onchange={() =>
                                                        toggleZone(zone.id)}
                                                />
                                                <span
                                                    class="text-sm font-medium"
                                                    >{zone.name}</span
                                                >
                                            </label>
                                        {/each}
                                    </div>
                                {/if}
                            </div>
                        {/if}
                    </div>
                {/if}

                <!-- Opciones de Personal -->
                {#if targetType === "technicians"}
                    <div
                        class="bg-primary/5 border-primary/20 rounded-xl border p-4 transition-all"
                    >
                        <p
                            class="text-primary mb-3 text-xs font-semibold uppercase tracking-wider"
                        >
                            Filtrar por rol
                        </p>
                        <div class="flex flex-wrap gap-3">
                            <!-- Admin -->
                            <label
                                class="flex cursor-pointer items-center gap-2 rounded-lg border-2 px-4 py-2 transition-all
                                   {staffRoles.admin
                                    ? 'border-error bg-error/10 text-error'
                                    : 'border-base-300 hover:border-error/50'}"
                            >
                                <input
                                    type="checkbox"
                                    class="checkbox checkbox-error checkbox-sm"
                                    bind:checked={staffRoles.admin}
                                />
                                <span class="text-sm font-medium">Admin</span>
                            </label>

                            <!-- Técnico -->
                            <label
                                class="flex cursor-pointer items-center gap-2 rounded-lg border-2 px-4 py-2 transition-all
                                   {staffRoles.technician
                                    ? 'border-info bg-info/10 text-info'
                                    : 'border-base-300 hover:border-info/50'}"
                            >
                                <input
                                    type="checkbox"
                                    class="checkbox checkbox-info checkbox-sm"
                                    bind:checked={staffRoles.technician}
                                />
                                <span class="text-sm font-medium">Técnico</span>
                            </label>

                            <!-- Cobranza -->
                            <label
                                class="flex cursor-pointer items-center gap-2 rounded-lg border-2 px-4 py-2 transition-all
                                   {staffRoles.billing
                                    ? 'border-success bg-success/10 text-success'
                                    : 'border-base-300 hover:border-success/50'}"
                            >
                                <input
                                    type="checkbox"
                                    class="checkbox checkbox-success checkbox-sm"
                                    bind:checked={staffRoles.billing}
                                />
                                <span class="text-sm font-medium">Cobranza</span
                                >
                            </label>
                        </div>
                    </div>
                {/if}
            </div>
        </div>

        <!-- 2. MENSAJE -->
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
                            d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                        />
                    </svg>
                    Mensaje
                </h2>

                <div class="relative">
                    <textarea
                        bind:value={message}
                        rows="7"
                        placeholder="Escribe el mensaje que recibirán tus destinatarios..."
                        class="textarea textarea-bordered w-full resize-none pr-16 font-mono text-sm leading-relaxed"
                    ></textarea>
                    <span
                        class="text-base-content/40 absolute right-3 bottom-3 select-none text-xs tabular-nums"
                    >
                        {message.length} car.
                    </span>
                </div>

                <div class="text-base-content/40 flex gap-1 text-xs">
                    <svg
                        xmlns="http://www.w3.org/2000/svg"
                        class="h-3.5 w-3.5 shrink-0 mt-0.5"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                    </svg>
                    Telegram admite <strong>Markdown</strong>: *negrita*,
                    _cursiva_, `código`
                </div>
            </div>
        </div>

        <!-- 3. IMAGEN OPCIONAL -->
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
                    <span class="badge badge-ghost badge-sm ml-1 font-normal"
                        >Opcional</span
                    >
                </h2>

                <input
                    type="file"
                    id="broadcastFileInput"
                    accept=".jpg,.jpeg,.png,.webp"
                    class="hidden"
                    onchange={handleFileSelect}
                />

                {#if !selectedFile}
                    <!-- Zona de subida -->
                    <button
                        type="button"
                        onclick={() =>
                            document
                                .getElementById("broadcastFileInput")
                                ?.click()}
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
                        <span class="text-sm font-medium"
                            >Haz clic para subir una imagen</span
                        >
                        <span class="text-base-content/40 text-xs"
                            >JPG, PNG, WebP · Máx 5 MB</span
                        >
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
                        <span
                            class="min-w-0 flex-1 truncate text-sm font-medium text-success"
                            >{selectedFile.name}</span
                        >
                        <button
                            onclick={clearFile}
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
                    <div
                        class="overflow-hidden rounded-xl border border-base-300 bg-black/10"
                    >
                        <img
                            src={localPreviewUrl ?? imageUrl}
                            alt="Vista previa"
                            class="h-48 w-full object-cover opacity-80 transition-opacity hover:opacity-100"
                            onerror={() => (imageError = true)}
                        />
                    </div>
                {/if}
                {#if imageError && imageUrl}
                    <p class="text-error text-xs">
                        La URL no es válida o no es accesible.
                    </p>
                {/if}
            </div>
        </div>
    </div>

    <!-- ===== COLUMNA LATERAL ===== -->
    <div class="space-y-4">
        <!-- Resumen del envío -->
        <div class="card bg-base-100 shadow-sm">
            <div class="card-body gap-4">
                <h2 class="card-title text-base">Resumen</h2>

                <div class="space-y-3">
                    <!-- Target -->
                    <div
                        class="bg-base-200 flex items-start gap-3 rounded-xl p-3"
                    >
                        <span class="mt-0.5 text-xl"
                            >{targetType === "clients" ? "👥" : "🏷️"}</span
                        >
                        <div>
                            <p
                                class="text-xs font-semibold uppercase tracking-wider text-primary"
                            >
                                Destinatarios
                            </p>
                            <p class="mt-0.5 text-sm">{targetLabel()}</p>
                        </div>
                    </div>

                    <!-- Mensaje -->
                    <div
                        class="bg-base-200 flex items-start gap-3 rounded-xl p-3"
                    >
                        <span class="mt-0.5 text-xl">💬</span>
                        <div class="min-w-0">
                            <p
                                class="text-xs font-semibold uppercase tracking-wider text-primary"
                            >
                                Mensaje
                            </p>
                            {#if message.trim()}
                                <p class="mt-0.5 line-clamp-3 text-sm">
                                    {message.trim()}
                                </p>
                            {:else}
                                <p
                                    class="text-base-content/40 mt-0.5 text-sm italic"
                                >
                                    Sin mensaje…
                                </p>
                            {/if}
                        </div>
                    </div>

                    <!-- Imagen -->
                    <div
                        class="bg-base-200 flex items-start gap-3 rounded-xl p-3"
                    >
                        <span class="mt-0.5 text-xl">🖼️</span>
                        <div>
                            <p
                                class="text-xs font-semibold uppercase tracking-wider text-primary"
                            >
                                Imagen
                            </p>
                            {#if selectedFile}
                                <p class="mt-0.5 truncate text-sm">
                                    {selectedFile.name}
                                </p>
                            {:else if imageUrl}
                                <p class="mt-0.5 truncate text-sm text-info">
                                    URL adjunta
                                </p>
                            {:else}
                                <p
                                    class="text-base-content/40 mt-0.5 text-sm italic"
                                >
                                    Sin imagen
                                </p>
                            {/if}
                        </div>
                    </div>
                </div>

                <!-- Error -->
                {#if errorMessage}
                    <div class="alert alert-error text-sm">
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            class="h-5 w-5 shrink-0"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                stroke-width="2"
                                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                            />
                        </svg>
                        <span>{errorMessage}</span>
                    </div>
                {/if}

                <!-- Último resultado -->
                {#if lastResult}
                    <div class="alert alert-success text-sm">
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            class="h-5 w-5 shrink-0"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                stroke-width="2"
                                d="M5 13l4 4L19 7"
                            />
                        </svg>
                        <span>
                            Enviado a <strong
                                >{lastResult.recipient_count}</strong
                            > destinatarios
                        </span>
                    </div>
                {/if}

                <!-- Botón principal -->
                <button
                    onclick={openConfirmModal}
                    disabled={!canSend || sending}
                    class="btn btn-warning btn-block gap-2"
                >
                    {#if sending}
                        <span class="loading loading-spinner loading-sm"></span>
                        {uploading ? "Subiendo imagen…" : "Enviando…"}
                    {:else}
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            class="h-5 w-5"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                stroke-width="2"
                                d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                            />
                        </svg>
                        Enviar Broadcast
                    {/if}
                </button>

                {#if !canSend && !sending}
                    <p class="text-center text-xs text-base-content/40">
                        {#if !message.trim()}
                            Escribe un mensaje para continuar
                        {:else if targetType === "clients" && !allZones && selectedZoneIds.length === 0}
                            Selecciona al menos una zona
                        {:else if targetType === "technicians" && !Object.values(staffRoles).some(Boolean)}
                            Selecciona al menos un rol
                        {/if}
                    </p>
                {/if}
            </div>
        </div>

        <!-- Tips -->
        <div class="card bg-warning/5 border border-warning/20 shadow-sm">
            <div class="card-body gap-2 p-4">
                <h3
                    class="text-xs font-bold uppercase tracking-wider text-warning"
                >
                    📌 Tips
                </h3>
                <ul class="space-y-1.5 text-xs text-base-content/70">
                    <li>
                        • Solo se incluyen clientes/staff con Telegram vinculado
                    </li>
                    <li>• El envío es inmediato y no reversible</li>
                    <li>
                        • Límite Telegram: ~20 mensajes/segundo (gestionado
                        automáticamente)
                    </li>
                    <li>• El mensaje admite formato Markdown de Telegram</li>
                </ul>
            </div>
        </div>
    </div>
</div>

<!-- ===== MODAL DE CONFIRMACIÓN ===== -->
<dialog bind:this={confirmModal} class="modal modal-bottom sm:modal-middle">
    <div class="modal-box">
        <h3 class="mb-1 text-lg font-bold">Confirmar Broadcast</h3>
        <p class="text-base-content/60 mb-4 text-sm">
            Estás a punto de enviar a:
        </p>

        <div
            class="bg-warning/10 border border-warning/30 rounded-xl px-4 py-3 text-center"
        >
            <p class="text-lg font-semibold">{targetLabel()}</p>
        </div>

        {#if message.trim()}
            <div class="mt-4 rounded-xl border border-base-300 bg-base-200 p-3">
                <p class="line-clamp-4 text-sm">{message.trim()}</p>
            </div>
        {/if}

        <p class="text-base-content/50 mt-4 text-xs">
            ⚠️ Esta acción no se puede deshacer. Los mensajes se enviarán
            inmediatamente.
        </p>

        <div class="modal-action">
            <form method="dialog">
                <button class="btn">Cancelar</button>
            </form>
            <button onclick={handleSend} class="btn btn-warning gap-2">
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
                        d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                    />
                </svg>
                Sí, enviar ahora
            </button>
        </div>
    </div>
    <form method="dialog" class="modal-backdrop">
        <button>cerrar</button>
    </form>
</dialog>

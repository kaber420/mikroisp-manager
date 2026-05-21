<script lang="ts">
    import type { BroadcastTargetType } from "$lib/types/broadcast";

    let {
        targetType,
        message,
        selectedFile,
        imageUrl,
        canSend,
        sending,
        uploading,
        lastResult,
        errorMessage,
        targetLabel,
        onsend,
        staffRoles,
        allZones,
        selectedZoneIds,
    }: {
        targetType: BroadcastTargetType;
        message: string;
        selectedFile: File | null;
        imageUrl: string;
        canSend: boolean;
        sending: boolean;
        uploading: boolean;
        lastResult: { recipient_count: number; target: string } | null;
        errorMessage: string;
        targetLabel: () => string;
        onsend?: () => void;
        staffRoles: { admin: boolean; technician: boolean; billing: boolean };
        allZones: boolean;
        selectedZoneIds: number[];
    } = $props();
</script>

<div class="space-y-4">
    <!-- Resumen del envío -->
    <div class="card bg-base-100 shadow-sm">
        <div class="card-body gap-4">
            <h2 class="card-title text-base">Resumen</h2>

            <div class="space-y-3">
                <!-- Target -->
                <div class="bg-base-200 flex items-start gap-3 rounded-xl p-3">
                    <span class="mt-0.5 text-xl"
                        >{targetType === "clients" ? "👥" : "🏷️"}</span
                    >
                    <div>
                        <p class="text-xs font-semibold uppercase tracking-wider text-primary">
                            Destinatarios
                        </p>
                        <p class="mt-0.5 text-sm">{targetLabel()}</p>
                    </div>
                </div>

                <!-- Mensaje -->
                <div class="bg-base-200 flex items-start gap-3 rounded-xl p-3">
                    <span class="mt-0.5 text-xl">💬</span>
                    <div class="min-w-0">
                        <p class="text-xs font-semibold uppercase tracking-wider text-primary">
                            Mensaje
                        </p>
                        {#if message.trim()}
                            <p class="mt-0.5 line-clamp-3 text-sm">{message.trim()}</p>
                        {:else}
                            <p class="text-base-content/40 mt-0.5 text-sm italic">Sin mensaje…</p>
                        {/if}
                    </div>
                </div>

                <!-- Imagen -->
                <div class="bg-base-200 flex items-start gap-3 rounded-xl p-3">
                    <span class="mt-0.5 text-xl">🖼️</span>
                    <div>
                        <p class="text-xs font-semibold uppercase tracking-wider text-primary">
                            Imagen
                        </p>
                        {#if selectedFile}
                            <p class="mt-0.5 truncate text-sm">{selectedFile.name}</p>
                        {:else if imageUrl}
                            <p class="mt-0.5 truncate text-sm text-info">URL adjunta</p>
                        {:else}
                            <p class="text-base-content/40 mt-0.5 text-sm italic">Sin imagen</p>
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
                        Enviado a <strong>{lastResult.recipient_count}</strong> destinatarios
                    </span>
                </div>
            {/if}

            <!-- Botón principal -->
            <button
                onclick={onsend}
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
            <h3 class="text-xs font-bold uppercase tracking-wider text-warning">
                📌 Tips
            </h3>
            <ul class="space-y-1.5 text-xs text-base-content/70">
                <li>• Solo se incluyen clientes/staff con Telegram vinculado</li>
                <li>• El envío es inmediato y no reversible</li>
                <li>
                    • Límite Telegram: ~20 mensajes/segundo (gestionado automáticamente)
                </li>
                <li>• El mensaje admite formato Markdown de Telegram</li>
            </ul>
        </div>
    </div>
</div>

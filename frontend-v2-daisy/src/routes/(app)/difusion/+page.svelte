<script lang="ts">
    import { uploadBroadcastImage, sendBroadcast } from "$lib/api";
    import type { PageData } from "./$types";
    import type { BroadcastTargetType } from "$lib/types/broadcast";

    import DifusionHeader from "$lib/components/difusion/DifusionHeader.svelte";
    import DifusionDestinatariosCard from "$lib/components/difusion/DifusionDestinatariosCard.svelte";
    import DifusionMensajeCard from "$lib/components/difusion/DifusionMensajeCard.svelte";
    import DifusionImagenCard from "$lib/components/difusion/DifusionImagenCard.svelte";
    import DifusionResumenCard from "$lib/components/difusion/DifusionResumenCard.svelte";
    import DifusionConfirmModal from "$lib/components/difusion/DifusionConfirmModal.svelte";

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
    let lastResult = $state<{ recipient_count: number; target: string } | null>(null);
    let errorMessage = $state("");

    // --- Modal de confirmación ---
    let confirmModalEl: HTMLDialogElement | undefined = $state();

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
        confirmModalEl?.showModal();
    }

    async function handleSend() {
        confirmModalEl?.close();
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
    <title>Difusión — OmniWISP</title>
</svelte:head>

<DifusionHeader />

<div class="grid grid-cols-1 gap-6 lg:grid-cols-3">
    <!-- Columna principal -->
    <div class="space-y-5 lg:col-span-2">
        <DifusionDestinatariosCard
            zones={data.zones}
            bind:targetType
            bind:allZones
            bind:selectedZoneIds
            bind:staffRoles
            ontogglezone={toggleZone}
        />
        <DifusionMensajeCard bind:message />
        <DifusionImagenCard
            bind:selectedFile
            bind:imageUrl
            bind:imageError
            bind:localPreviewUrl
            onfileselect={handleFileSelect}
            onclearfile={clearFile}
        />
    </div>

    <!-- Columna lateral -->
    <div>
        <DifusionResumenCard
            {targetType}
            {message}
            {selectedFile}
            {imageUrl}
            {canSend}
            {sending}
            {uploading}
            {lastResult}
            {errorMessage}
            {targetLabel}
            {staffRoles}
            {allZones}
            {selectedZoneIds}
            onsend={openConfirmModal}
        />
    </div>
</div>

<DifusionConfirmModal
    bind:dialogRef={confirmModalEl}
    {targetLabel}
    {message}
    onconfirm={handleSend}
/>

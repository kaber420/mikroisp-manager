<script lang="ts">
    import {
        getRouterFiles,
        createRouterBackup,
        deleteRouterFile,
        saveBackupToServer,
        getLocalBackups,
        deleteLocalBackup,
        getLocalBackupDownloadUrl,
        type BackupCreatePayload,
    } from "$lib/api";
    import { onMount } from "svelte";

    let { host }: { host: string } = $props();

    // ── Estado Backups en Router ──────────────────────────────────────────────
    let routerFiles = $state<any[]>([]);
    let filesLoading = $state(true);
    let filesError = $state<string | null>(null);

    // ── Estado Backups Servidor ───────────────────────────────────────────────
    let localFiles = $state<any[]>([]);
    let localLoading = $state(true);
    let localError = $state<string | null>(null);

    // ── Estado Modal Crear Backup ─────────────────────────────────────────────
    let showCreateModal = $state(false);
    let newBackupName = $state("");
    let newBackupType = $state<"backup" | "export">("backup");
    let creating = $state(false);
    let createError = $state<string | null>(null);
    let createSuccess = $state<string | null>(null);

    // ── Acciones en curso ────────────────────────────────────────────────────
    let actionInProgress = $state<string | null>(null);
    let actionMsg = $state<{ type: "ok" | "err"; text: string } | null>(null);

    onMount(() => {
        loadRouterFiles();
        loadLocalFiles();
    });

    async function loadRouterFiles() {
        filesLoading = true;
        filesError = null;
        try {
            routerFiles = await getRouterFiles(host);
        } catch (e: any) {
            filesError =
                e?.response?.data?.detail ??
                "Error al cargar archivos del router.";
        } finally {
            filesLoading = false;
        }
    }

    async function loadLocalFiles() {
        localLoading = true;
        localError = null;
        try {
            localFiles = await getLocalBackups(host);
        } catch (e: any) {
            localError =
                e?.response?.data?.detail ?? "Error al cargar backups locales.";
        } finally {
            localLoading = false;
        }
    }

    async function handleCreateBackup() {
        if (!newBackupName.trim()) return;
        creating = true;
        createError = null;
        createSuccess = null;
        try {
            const payload: BackupCreatePayload = {
                backup_name: newBackupName.trim(),
                backup_type: newBackupType,
                overwrite: false,
            };
            const result = await createRouterBackup(host, payload);
            createSuccess = result.message;
            newBackupName = "";
            await loadRouterFiles();
            setTimeout(() => {
                showCreateModal = false;
                createSuccess = null;
            }, 1500);
        } catch (e: any) {
            if (e?.response?.status === 409) {
                createError =
                    e?.response?.data?.detail ?? "El archivo ya existe.";
            } else {
                createError =
                    e?.response?.data?.detail ?? "Error al crear el backup.";
            }
        } finally {
            creating = false;
        }
    }

    async function handleDeleteRouterFile(fileId: string) {
        if (!confirm(`¿Eliminar "${fileId}" del router?`)) return;
        actionInProgress = "del_" + fileId;
        actionMsg = null;
        try {
            await deleteRouterFile(host, fileId);
            actionMsg = {
                type: "ok",
                text: `"${fileId}" eliminado del router.`,
            };
            routerFiles = routerFiles.filter((f) => f.name !== fileId);
        } catch (e: any) {
            actionMsg = {
                type: "err",
                text: e?.response?.data?.detail ?? "Error al eliminar.",
            };
        } finally {
            actionInProgress = null;
            setTimeout(() => (actionMsg = null), 3000);
        }
    }

    async function handleSaveToServer(filename: string) {
        actionInProgress = "save_" + filename;
        actionMsg = null;
        try {
            const result = await saveBackupToServer(host, filename);
            actionMsg = {
                type: "ok",
                text:
                    result?.message ?? `"${filename}" guardado en el servidor.`,
            };
            await loadLocalFiles();
        } catch (e: any) {
            actionMsg = {
                type: "err",
                text:
                    e?.response?.data?.detail ??
                    "Error al guardar en servidor.",
            };
        } finally {
            actionInProgress = null;
            setTimeout(() => (actionMsg = null), 4000);
        }
    }

    async function handleDeleteLocalFile(filename: string) {
        if (!confirm(`¿Eliminar "${filename}" del servidor?`)) return;
        actionInProgress = "ldel_" + filename;
        actionMsg = null;
        try {
            await deleteLocalBackup(host, filename);
            actionMsg = {
                type: "ok",
                text: `"${filename}" eliminado del servidor.`,
            };
            localFiles = localFiles.filter((f) => f.name !== filename);
        } catch (e: any) {
            actionMsg = {
                type: "err",
                text: e?.response?.data?.detail ?? "Error al eliminar local.",
            };
        } finally {
            actionInProgress = null;
            setTimeout(() => (actionMsg = null), 3000);
        }
    }

    function fmtSize(bytes: number): string {
        if (bytes == null) return "--";
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / 1048576).toFixed(2)} MB`;
    }

    function fmtDate(ts: number | string): string {
        const d = typeof ts === "number" ? new Date(ts * 1000) : new Date(ts);
        return d.toLocaleString("es", {
            dateStyle: "short",
            timeStyle: "short",
        });
    }
</script>

<div style="display:flex;flex-direction:column;gap:1.25rem;">
    <!-- Toast de acción -->
    {#if actionMsg}
        <div
            class="alert {actionMsg.type === 'ok'
                ? 'alert-success'
                : 'alert-error'} py-2"
            style="font-size:0.85rem;border-radius:0.75rem;"
        >
            {actionMsg.type === "ok" ? "✅" : "⚠️"}
            {actionMsg.text}
        </div>
    {/if}

    <!-- ── Card 1: Backups en el Router ──────────────────────────────────── -->
    <div class="glass-card-flat" style="border-radius:1rem;padding:1.25rem;">
        <div
            style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem;gap:0.75rem;flex-wrap:wrap;"
        >
            <div style="display:flex;align-items:center;gap:0.5rem;">
                <span style="font-size:1.2rem;">📦</span>
                <h3 style="margin:0;font-size:0.95rem;font-weight:800;">
                    Backups en el Router
                </h3>
                <span style="font-size:0.7rem;opacity:0.4;"
                    >Almacenados en el dispositivo MikroTik</span
                >
            </div>
            <div style="display:flex;gap:0.5rem;">
                <button
                    class="btn btn-ghost btn-xs"
                    onclick={loadRouterFiles}
                    disabled={filesLoading}
                >
                    {#if filesLoading}
                        <span class="loading loading-spinner loading-xs"></span>
                    {:else}
                        🔄
                    {/if}
                </button>
                <button
                    class="btn btn-primary btn-xs"
                    onclick={() => {
                        showCreateModal = true;
                        createError = null;
                        createSuccess = null;
                    }}
                >
                    + Crear Backup
                </button>
            </div>
        </div>

        {#if filesLoading}
            <div style="text-align:center;padding:2rem;opacity:0.5;">
                <span class="loading loading-spinner loading-md"></span>
                <p style="margin:0.5rem 0 0;font-size:0.85rem;">
                    Cargando archivos del router...
                </p>
            </div>
        {:else if filesError}
            <div class="alert alert-warning py-2" style="font-size:0.8rem;">
                {filesError}
            </div>
        {:else if routerFiles.length === 0}
            <p
                style="text-align:center;opacity:0.4;font-size:0.85rem;padding:1.5rem 0;"
            >
                Sin archivos de backup en el router.
            </p>
        {:else}
            <div
                style="overflow-x:auto;border-radius:0.5rem;border:1px solid oklch(from var(--color-base-content) l c h / 0.08);"
            >
                <table
                    style="width:100%;font-size:0.82rem;border-collapse:collapse;"
                >
                    <thead>
                        <tr
                            style="background:oklch(from var(--color-base-content) l c h / 0.04);"
                        >
                            <th
                                style="padding:0.5rem 0.75rem;text-align:left;font-weight:700;opacity:0.6;text-transform:uppercase;font-size:0.7rem;"
                                >Nombre</th
                            >
                            <th
                                style="padding:0.5rem 0.75rem;text-align:left;font-weight:700;opacity:0.6;text-transform:uppercase;font-size:0.7rem;"
                                >Tipo</th
                            >
                            <th
                                style="padding:0.5rem 0.75rem;text-align:left;font-weight:700;opacity:0.6;text-transform:uppercase;font-size:0.7rem;"
                                >Tamaño</th
                            >
                            <th
                                style="padding:0.5rem 0.75rem;text-align:right;font-weight:700;opacity:0.6;text-transform:uppercase;font-size:0.7rem;"
                                >Acciones</th
                            >
                        </tr>
                    </thead>
                    <tbody>
                        {#each routerFiles as file}
                            {@const isBackup = file.name?.endsWith(".backup")}
                            <tr
                                style="border-top:1px solid oklch(from var(--color-base-content) l c h / 0.06);"
                            >
                                <td
                                    style="padding:0.5rem 0.75rem;font-family:monospace;font-size:0.8rem;"
                                    >{file.name}</td
                                >
                                <td style="padding:0.5rem 0.75rem;">
                                    <span
                                        class="badge badge-xs {isBackup
                                            ? 'badge-info'
                                            : 'badge-warning'} font-bold"
                                    >
                                        {isBackup ? ".backup" : ".rsc"}
                                    </span>
                                </td>
                                <td style="padding:0.5rem 0.75rem;opacity:0.6;"
                                    >{fmtSize(file.size)}</td
                                >
                                <td
                                    style="padding:0.5rem 0.75rem;text-align:right;"
                                >
                                    <div
                                        style="display:flex;gap:0.4rem;justify-content:flex-end;"
                                    >
                                        <button
                                            class="btn btn-xs btn-ghost"
                                            onclick={() =>
                                                handleSaveToServer(file.name)}
                                            disabled={actionInProgress ===
                                                "save_" + file.name}
                                            title="Guardar copia en servidor"
                                        >
                                            {#if actionInProgress === "save_" + file.name}
                                                <span
                                                    class="loading loading-spinner loading-xs"
                                                ></span>
                                            {:else}
                                                ☁️ Servidor
                                            {/if}
                                        </button>
                                        <button
                                            class="btn btn-xs btn-error btn-ghost"
                                            onclick={() =>
                                                handleDeleteRouterFile(
                                                    file.name,
                                                )}
                                            disabled={actionInProgress ===
                                                "del_" + file.name}
                                            title="Eliminar del router"
                                        >
                                            {#if actionInProgress === "del_" + file.name}
                                                <span
                                                    class="loading loading-spinner loading-xs"
                                                ></span>
                                            {:else}
                                                🗑️
                                            {/if}
                                        </button>
                                    </div>
                                </td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>
        {/if}
    </div>

    <!-- ── Card 2: Respaldos en Servidor ─────────────────────────────────── -->
    <div class="glass-card-flat" style="border-radius:1rem;padding:1.25rem;">
        <div
            style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem;gap:0.75rem;flex-wrap:wrap;"
        >
            <div style="display:flex;align-items:center;gap:0.5rem;">
                <span style="font-size:1.2rem;">🖥️</span>
                <h3 style="margin:0;font-size:0.95rem;font-weight:800;">
                    Respaldos en Servidor
                </h3>
                <span style="font-size:0.7rem;opacity:0.4;"
                    >Copias descargadas al servidor local</span
                >
            </div>
            <button
                class="btn btn-ghost btn-xs"
                onclick={loadLocalFiles}
                disabled={localLoading}
            >
                {#if localLoading}
                    <span class="loading loading-spinner loading-xs"></span>
                {:else}
                    🔄
                {/if}
            </button>
        </div>

        {#if localLoading}
            <div style="text-align:center;padding:2rem;opacity:0.5;">
                <span class="loading loading-spinner loading-md"></span>
                <p style="margin:0.5rem 0 0;font-size:0.85rem;">
                    Cargando respaldos en servidor...
                </p>
            </div>
        {:else if localError}
            <div class="alert alert-warning py-2" style="font-size:0.8rem;">
                {localError}
            </div>
        {:else if localFiles.length === 0}
            <p
                style="text-align:center;opacity:0.4;font-size:0.85rem;padding:1.5rem 0;"
            >
                Sin respaldos en el servidor todavía. Usa "☁️ Servidor" en un
                archivo arriba para guardar una copia.
            </p>
        {:else}
            <div
                style="display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:0.75rem;"
            >
                {#each localFiles as file}
                    {@const isBackup = file.name?.endsWith(".backup")}
                    <div
                        style="background:oklch(from var(--color-base-content) l c h / 0.04);border:1px solid oklch(from var(--color-base-content) l c h / 0.1);border-radius:0.75rem;padding:0.85rem;display:flex;flex-direction:column;gap:0.5rem;"
                    >
                        <div
                            style="display:flex;align-items:center;gap:0.5rem;flex-wrap:wrap;"
                        >
                            <span
                                class="badge badge-xs {isBackup
                                    ? 'badge-info'
                                    : 'badge-warning'} font-bold shrink-0"
                            >
                                {isBackup ? ".backup" : ".rsc"}
                            </span>
                            <span
                                style="font-family:monospace;font-size:0.75rem;word-break:break-all;flex:1;"
                                >{file.name}</span
                            >
                        </div>
                        <div
                            style="display:flex;justify-content:space-between;font-size:0.72rem;opacity:0.5;"
                        >
                            <span>{fmtSize(file.size)}</span>
                            <span>{fmtDate(file.modified)}</span>
                        </div>
                        <div
                            style="display:flex;gap:0.4rem;margin-top:0.25rem;"
                        >
                            <a
                                href={getLocalBackupDownloadUrl(
                                    host,
                                    file.name,
                                )}
                                class="btn btn-xs btn-ghost flex-1"
                                download={file.name}
                                title="Descargar al PC"
                            >
                                ⬇️ Descargar
                            </a>
                            <button
                                class="btn btn-xs btn-error btn-ghost"
                                onclick={() => handleDeleteLocalFile(file.name)}
                                disabled={actionInProgress ===
                                    "ldel_" + file.name}
                                title="Eliminar del servidor"
                            >
                                {#if actionInProgress === "ldel_" + file.name}
                                    <span
                                        class="loading loading-spinner loading-xs"
                                    ></span>
                                {:else}
                                    🗑️
                                {/if}
                            </button>
                        </div>
                    </div>
                {/each}
            </div>
        {/if}
    </div>
</div>

<!-- ── Modal: Crear Backup ─────────────────────────────────────────────────── -->
{#if showCreateModal}
    <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
    <div
        style="position:fixed;inset:0;background:rgba(0,0,0,0.55);backdrop-filter:blur(4px);z-index:9000;display:flex;align-items:center;justify-content:center;padding:1rem;"
        onclick={() => (showCreateModal = false)}
        role="none"
    >
        <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
        <div
            class="glass-card-flat"
            style="border-radius:1.25rem;width:100%;max-width:440px;padding:1.5rem;box-shadow:0 20px 60px rgba(0,0,0,0.5);border:1px solid oklch(from var(--color-primary) l c h / 0.2);"
            onclick={(e) => e.stopPropagation()}
            role="none"
        >
            <div
                style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem;"
            >
                <h3 style="margin:0;font-size:1rem;font-weight:800;">
                    📦 Crear Backup en Router
                </h3>
                <button
                    class="btn btn-ghost btn-sm btn-circle"
                    onclick={() => (showCreateModal = false)}>✕</button
                >
            </div>

            {#if createError}
                <div
                    class="alert alert-error py-2 mb-3"
                    style="font-size:0.85rem;"
                >
                    ⚠️ {createError}
                </div>
            {/if}
            {#if createSuccess}
                <div
                    class="alert alert-success py-2 mb-3"
                    style="font-size:0.85rem;"
                >
                    ✅ {createSuccess}
                </div>
            {/if}

            <form
                onsubmit={(e) => {
                    e.preventDefault();
                    handleCreateBackup();
                }}
                style="display:flex;flex-direction:column;gap:1rem;"
            >
                <div>
                    <label
                        for="backup-name-input"
                        style="font-size:0.75rem;font-weight:700;opacity:0.6;text-transform:uppercase;display:block;margin-bottom:0.35rem;"
                    >
                        Nombre del archivo
                    </label>
                    <input
                        id="backup-name-input"
                        type="text"
                        class="input input-bordered w-full input-sm"
                        bind:value={newBackupName}
                        required
                        placeholder="backup-{new Date()
                            .toISOString()
                            .slice(0, 10)}"
                    />
                    <p style="margin:0.3rem 0 0;font-size:0.7rem;opacity:0.5;">
                        La extensión se añade automáticamente.
                    </p>
                </div>

                <div>
                    <p
                        style="font-size:0.75rem;font-weight:700;opacity:0.6;text-transform:uppercase;display:block;margin-bottom:0.5rem;"
                    >
                        Tipo de Backup
                    </p>
                    <div style="display:flex;gap:1rem;">
                        <label class="flex gap-2 items-center cursor-pointer">
                            <input
                                type="radio"
                                class="radio radio-primary radio-sm"
                                bind:group={newBackupType}
                                value="backup"
                            />
                            <span style="font-size:0.85rem;"
                                >.backup <span style="opacity:0.5;"
                                    >(binario)</span
                                ></span
                            >
                        </label>
                        <label class="flex gap-2 items-center cursor-pointer">
                            <input
                                type="radio"
                                class="radio radio-secondary radio-sm"
                                bind:group={newBackupType}
                                value="export"
                            />
                            <span style="font-size:0.85rem;"
                                >.rsc <span style="opacity:0.5;"
                                    >(script texto)</span
                                ></span
                            >
                        </label>
                    </div>
                </div>

                <div
                    style="display:flex;gap:0.75rem;justify-content:flex-end;padding-top:0.75rem;border-top:1px solid oklch(from var(--color-base-content) l c h / 0.1);"
                >
                    <button
                        type="button"
                        class="btn btn-ghost btn-sm"
                        onclick={() => (showCreateModal = false)}
                        >Cancelar</button
                    >
                    <button
                        type="submit"
                        class="btn btn-primary btn-sm"
                        disabled={creating || !newBackupName.trim()}
                    >
                        {#if creating}
                            <span class="loading loading-spinner loading-xs"
                            ></span>
                            Creando...
                        {:else}
                            📦 Crear
                        {/if}
                    </button>
                </div>
            </form>
        </div>
    </div>
{/if}

<script lang="ts">
    import { onMount } from "svelte";
    import { api, createUser, updateUser, deleteUser } from "$lib/api";
    import DataTable from "$lib/components/DataTable.svelte";
    import type { User, UserCreate, UserUpdate } from "$lib/types/user";
    import { user as currentUser } from "$lib/stores/auth";

    // ── Estado principal ──────────────────────────────────────────────────
    let users = $state<User[]>([]);
    let loading = $state(true);
    let pageError = $state<string | null>(null);

    // ── Modal Crear/Editar ────────────────────────────────────────────────
    let showModal = $state(false);
    let modalMode = $state<"create" | "edit">("create");
    let editTarget = $state<User | null>(null);
    let modalError = $state<string | null>(null);
    let modalLoading = $state(false);

    // Campos del formulario
    let fUsername = $state("");
    let fEmail = $state("");
    let fPassword = $state("");
    let fRole = $state("admin");
    let fActive = $state(true);
    let fTelegramId = $state("");
    let fAlerts = $state(false);
    let fDeviceDown = $state(false);
    let fAnnouncements = $state(false);

    // ── Modal Confirmar Eliminar ─────────────────────────────────────────
    let showDeleteModal = $state(false);
    let deleteTarget = $state<User | null>(null);
    let deleteLoading = $state(false);

    // ── Carga inicial ─────────────────────────────────────────────────────
    async function loadUsers() {
        loading = true;
        pageError = null;
        try {
            const res = await api.get<User[]>("/users");
            users = res.data;
        } catch (e: any) {
            pageError =
                e?.response?.data?.detail ?? "Error al cargar usuarios.";
        } finally {
            loading = false;
        }
    }

    onMount(loadUsers);

    // ── Helpers ────────────────────────────────────────────────────────────
    const ROLES = ["admin", "tecnico", "cobranza"];

    function roleBadgeStyle(role: string): string {
        if (role === "admin")
            return "background:#fef3c7;color:#92400e;border:1px solid #fde68a;";
        if (role === "tecnico")
            return "background:#dbeafe;color:#1e40af;border:1px solid #bfdbfe;";
        if (role === "cobranza")
            return "background:#d1fae5;color:#065f46;border:1px solid #a7f3d0;";
        return "background:#f3f4f6;color:#374151;border:1px solid #e5e7eb;";
    }

    function activeStyle(active: boolean): string {
        return active
            ? "background:#d1fae5;color:#065f46;border:1px solid #a7f3d0;"
            : "background:#fee2e2;color:#991b1b;border:1px solid #fecaca;";
    }

    // ── Abrir Modales ──────────────────────────────────────────────────────
    function openCreate() {
        modalMode = "create";
        editTarget = null;
        fUsername = "";
        fEmail = "";
        fPassword = "";
        fRole = "admin";
        fActive = true;
        fTelegramId = "";
        fAlerts = false;
        fDeviceDown = false;
        fAnnouncements = false;
        modalError = null;
        showModal = true;
    }

    function openEdit(u: User) {
        modalMode = "edit";
        editTarget = u;
        fUsername = u.username;
        fEmail = u.email;
        fPassword = "";
        fRole = u.role;
        fActive = u.is_active;
        fTelegramId = u.telegram_chat_id ?? "";
        fAlerts = u.receive_alerts;
        fDeviceDown = u.receive_device_down_alerts;
        fAnnouncements = u.receive_announcements;
        modalError = null;
        showModal = true;
    }

    function openDelete(u: User) {
        deleteTarget = u;
        showDeleteModal = true;
    }

    // ── Guardar Usuario ────────────────────────────────────────────────────
    async function saveUser() {
        modalLoading = true;
        modalError = null;
        try {
            if (modalMode === "create") {
                const payload: UserCreate = {
                    username: fUsername.trim(),
                    email: fEmail.trim(),
                    password: fPassword,
                    role: fRole,
                    is_active: fActive,
                    telegram_chat_id: fTelegramId.trim() || null,
                    receive_alerts: fAlerts,
                    receive_device_down_alerts: fDeviceDown,
                    receive_announcements: fAnnouncements,
                };
                await createUser(payload);
            } else if (editTarget) {
                const payload: UserUpdate = {
                    email: fEmail.trim(),
                    role: fRole,
                    is_active: fActive,
                    telegram_chat_id: fTelegramId.trim() || null,
                    receive_alerts: fAlerts,
                    receive_device_down_alerts: fDeviceDown,
                    receive_announcements: fAnnouncements,
                };
                if (fPassword.trim()) payload.password = fPassword;
                await updateUser(editTarget.username, payload);
            }
            showModal = false;
            await loadUsers();
        } catch (e: any) {
            modalError =
                e?.response?.data?.detail ?? "Error al guardar el usuario.";
        } finally {
            modalLoading = false;
        }
    }

    // ── Eliminar Usuario ───────────────────────────────────────────────────
    async function confirmDelete() {
        if (!deleteTarget) return;
        deleteLoading = true;
        try {
            await deleteUser(deleteTarget.username);
            showDeleteModal = false;
            deleteTarget = null;
            await loadUsers();
        } catch (e: any) {
            // mostrar alerta aunque cerremos el modal
            pageError =
                e?.response?.data?.detail ?? "Error al eliminar el usuario.";
            showDeleteModal = false;
        } finally {
            deleteLoading = false;
        }
    }
</script>

<!-- ── CONTENEDOR PRINCIPAL ───────────────────────────────────────────── -->
<div style="display:flex;flex-direction:column;gap:1.5rem;">
    <!-- Encabezado -->
    <div
        style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:0.5rem;"
    >
        <div>
            <h2 style="font-size:1.375rem;font-weight:700;margin:0;">
                Control de Acceso — Usuarios
            </h2>
            <p style="margin:0.25rem 0 0;font-size:0.85rem;opacity:0.5;">
                {loading
                    ? "Cargando..."
                    : `${users.length} usuario${users.length !== 1 ? "s" : ""} registrados`}
            </p>
        </div>
        <button class="btn btn-primary btn-sm" onclick={openCreate}>
            + Nuevo Usuario
        </button>
    </div>

    <!-- Error de página (ej. no tienes permisos o fallo de red) -->
    {#if pageError}
        <div class="alert alert-error shadow-sm">
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
                    d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
            </svg>
            <span>{pageError}</span>
            <button
                class="btn btn-xs btn-ghost"
                onclick={() => (pageError = null)}>✕</button
            >
        </div>
    {/if}

    <!-- DataTable (modo local — la lista completa viene del onMount) -->
    {#if !loading}
        <DataTable items={users}>
            {#snippet header()}
                <tr>
                    <th class="dt-th">Usuario</th>
                    <th class="dt-th">Email</th>
                    <th class="dt-th">Rol</th>
                    <th class="dt-th" style="text-align:center;">Estado</th>
                    <th class="dt-th" style="text-align:center;"
                        >Notificaciones</th
                    >
                    <th class="dt-th" style="text-align:center;">Acciones</th>
                </tr>
            {/snippet}

            {#snippet row(u: User)}
                <tr>
                    <!-- Usuario -->
                    <td class="dt-td">
                        <div
                            style="display:flex;align-items:center;gap:0.625rem;"
                        >
                            <div
                                style="
                                width:2rem; height:2rem; border-radius:9999px;
                                background:linear-gradient(135deg, var(--color-primary), var(--color-secondary));
                                display:flex; align-items:center; justify-content:center;
                                font-weight:700; font-size:0.8rem; color:white; flex-shrink:0;
                            "
                            >
                                {u.username[0].toUpperCase()}
                            </div>
                            <span style="font-weight:500;">{u.username}</span>
                            {#if u.is_superuser}
                                <span
                                    style="font-size:0.65rem;padding:0.1rem 0.4rem;border-radius:4px;background:#fde68a;color:#92400e;font-weight:700;"
                                    >SUPER</span
                                >
                            {/if}
                        </div>
                    </td>

                    <!-- Email -->
                    <td class="dt-td" style="opacity:0.7;font-size:0.8rem;"
                        >{u.email}</td
                    >

                    <!-- Rol -->
                    <td class="dt-td">
                        <span
                            style="
                            display:inline-block; padding:0.15rem 0.55rem;
                            border-radius:999px; font-size:0.7rem; font-weight:600;
                            {roleBadgeStyle(u.role)}
                        ">{u.role}</span
                        >
                    </td>

                    <!-- Estado activo -->
                    <td class="dt-td" style="text-align:center;">
                        <span
                            style="
                            display:inline-block; padding:0.15rem 0.55rem;
                            border-radius:999px; font-size:0.7rem; font-weight:600;
                            {activeStyle(u.is_active)}
                        ">{u.is_active ? "Activo" : "Inactivo"}</span
                        >
                    </td>

                    <!-- Notificaciones -->
                    <td class="dt-td" style="text-align:center;">
                        <div
                            style="display:flex;gap:0.375rem;justify-content:center;flex-wrap:wrap;"
                        >
                            {#if u.receive_device_down_alerts}
                                <span
                                    class="badge badge-error badge-xs"
                                    title="Alertas de Caídas">🔴 Caídas</span
                                >
                            {/if}
                            {#if u.receive_alerts}
                                <span
                                    class="badge badge-warning badge-xs"
                                    title="Alertas Generales">🔔 Alertas</span
                                >
                            {/if}
                            {#if u.receive_announcements}
                                <span
                                    class="badge badge-info badge-xs"
                                    title="Anuncios">📢 Anuncios</span
                                >
                            {/if}
                            {#if !u.receive_device_down_alerts && !u.receive_alerts && !u.receive_announcements}
                                <span style="opacity:0.35;font-size:0.75rem;"
                                    >Sin notificaciones</span
                                >
                            {/if}
                        </div>
                    </td>

                    <!-- Acciones -->
                    <td class="dt-td" style="text-align:center;">
                        <div
                            style="display:flex;gap:0.375rem;justify-content:center;"
                        >
                            <button
                                class="btn btn-xs btn-ghost"
                                title="Editar usuario"
                                onclick={() => openEdit(u)}>✏️</button
                            >
                            <button
                                class="btn btn-xs btn-ghost text-error"
                                title="Eliminar usuario"
                                disabled={u.username === $currentUser?.username}
                                onclick={() => openDelete(u)}>🗑️</button
                            >
                        </div>
                    </td>
                </tr>
            {/snippet}
        </DataTable>
    {:else}
        <!-- Skeleton -->
        <div class="glass-card-flat" style="padding:2rem;border-radius:1rem;">
            {#each Array(5) as _}
                <div
                    style="height:1.2rem;border-radius:0.3rem;background:oklch(from var(--color-base-content) l c h / 0.08);margin-bottom:0.75rem;animation:pulseSkel 1.5s infinite;"
                ></div>
            {/each}
        </div>
    {/if}
</div>

<!-- ═══════════════════════════════════════════════════
     MODAL — Crear / Editar Usuario
═══════════════════════════════════════════════════ -->
{#if showModal}
    <!-- Overlay -->
    <div
        style="position:fixed;inset:0;z-index:200;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;padding:1rem;"
        role="dialog"
        aria-modal="true"
    >
        <div
            style="background:var(--color-base-100);border-radius:1rem;width:100%;max-width:440px;box-shadow:0 25px 50px -12px rgba(0,0,0,0.4);overflow:hidden;"
        >
            <!-- Header del modal -->
            <div
                style="padding:1.25rem 1.5rem;border-bottom:1px solid oklch(from var(--color-base-content) l c h / 0.12);display:flex;align-items:center;justify-content:space-between;"
            >
                <h3 style="margin:0;font-size:1.1rem;font-weight:700;">
                    {modalMode === "create"
                        ? "➕ Crear Usuario"
                        : "✏️ Editar Usuario"}
                </h3>
                <button
                    class="btn btn-ghost btn-sm btn-circle"
                    onclick={() => (showModal = false)}>✕</button
                >
            </div>

            <!-- Cuerpo del modal -->
            <form
                onsubmit={(e) => {
                    e.preventDefault();
                    saveUser();
                }}
                style="padding:1.5rem;display:flex;flex-direction:column;gap:1rem;"
            >
                {#if modalError}
                    <div class="alert alert-error alert-sm py-2">
                        <span style="font-size:0.85rem;">{modalError}</span>
                    </div>
                {/if}

                <!-- Username -->
                <label class="form-control w-full">
                    <div class="label">
                        <span class="label-text font-semibold"
                            >Nombre de Usuario *</span
                        >
                    </div>
                    <input
                        class="input input-bordered input-sm w-full"
                        type="text"
                        bind:value={fUsername}
                        placeholder="ej: juan_perez"
                        required
                        disabled={modalMode === "edit"}
                    />
                    {#if modalMode === "edit"}
                        <div class="label">
                            <span class="label-text-alt opacity-50"
                                >El username no se puede modificar.</span
                            >
                        </div>
                    {/if}
                </label>

                <!-- Email -->
                <label class="form-control w-full">
                    <div class="label">
                        <span class="label-text font-semibold">Email *</span>
                    </div>
                    <input
                        class="input input-bordered input-sm w-full"
                        type="email"
                        bind:value={fEmail}
                        placeholder="usuario@empresa.com"
                        required
                    />
                </label>

                <!-- Password -->
                <label class="form-control w-full">
                    <div class="label">
                        <span class="label-text font-semibold">
                            Contraseña {modalMode === "edit"
                                ? "(dejar vacío para no cambiar)"
                                : "*"}
                        </span>
                    </div>
                    <input
                        class="input input-bordered input-sm w-full"
                        type="password"
                        bind:value={fPassword}
                        placeholder={modalMode === "edit"
                            ? "••••••••"
                            : "Nueva contraseña"}
                        required={modalMode === "create"}
                    />
                </label>

                <!-- Rol -->
                <label class="form-control w-full">
                    <div class="label">
                        <span class="label-text font-semibold">Rol *</span>
                    </div>
                    <select
                        class="select select-bordered select-sm w-full"
                        bind:value={fRole}
                        required
                    >
                        {#each ROLES as r}
                            <option value={r}
                                >{r.charAt(0).toUpperCase() +
                                    r.slice(1)}</option
                            >
                        {/each}
                    </select>
                </label>

                <!-- Estado activo -->
                <div
                    style="display:flex;align-items:center;justify-content:space-between;"
                >
                    <span class="label-text font-semibold">Cuenta Activa</span>
                    <input
                        type="checkbox"
                        class="toggle toggle-success toggle-sm"
                        bind:checked={fActive}
                    />
                </div>

                <!-- Telegram -->
                <label class="form-control w-full">
                    <div class="label">
                        <span class="label-text font-semibold"
                            >Telegram Chat ID</span
                        >
                    </div>
                    <input
                        class="input input-bordered input-sm w-full"
                        type="text"
                        bind:value={fTelegramId}
                        placeholder="Opcional (ej: 123456789)"
                    />
                </label>

                <!-- Notificaciones -->
                <div
                    style="border:1px solid oklch(from var(--color-base-content) l c h / 0.12);border-radius:0.5rem;padding:0.875rem;"
                >
                    <p
                        style="margin:0 0 0.75rem;font-size:0.8rem;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;opacity:0.6;"
                    >
                        Notificaciones Telegram
                    </p>
                    <div style="display:flex;flex-direction:column;gap:0.5rem;">
                        <label
                            style="display:flex;align-items:center;justify-content:space-between;cursor:pointer;"
                        >
                            <span style="font-size:0.875rem;"
                                >🔴 Alertas de Caídas</span
                            >
                            <input
                                type="checkbox"
                                class="checkbox checkbox-error checkbox-sm"
                                bind:checked={fDeviceDown}
                            />
                        </label>
                        <label
                            style="display:flex;align-items:center;justify-content:space-between;cursor:pointer;"
                        >
                            <span style="font-size:0.875rem;"
                                >🔔 Alertas Generales</span
                            >
                            <input
                                type="checkbox"
                                class="checkbox checkbox-warning checkbox-sm"
                                bind:checked={fAlerts}
                            />
                        </label>
                        <label
                            style="display:flex;align-items:center;justify-content:space-between;cursor:pointer;"
                        >
                            <span style="font-size:0.875rem;">📢 Anuncios</span>
                            <input
                                type="checkbox"
                                class="checkbox checkbox-info checkbox-sm"
                                bind:checked={fAnnouncements}
                            />
                        </label>
                    </div>
                </div>

                <!-- Botones -->
                <div
                    style="display:flex;gap:0.5rem;justify-content:flex-end;padding-top:0.25rem;"
                >
                    <button
                        type="button"
                        class="btn btn-ghost btn-sm"
                        onclick={() => (showModal = false)}>Cancelar</button
                    >
                    <button
                        type="submit"
                        class="btn btn-primary btn-sm"
                        disabled={modalLoading}
                    >
                        {#if modalLoading}
                            <span class="loading loading-spinner loading-xs"
                            ></span>
                        {/if}
                        {modalMode === "create" ? "Crear" : "Guardar cambios"}
                    </button>
                </div>
            </form>
        </div>
    </div>
{/if}

<!-- ═══════════════════════════════════════════════════
     MODAL — Confirmar Eliminación
═══════════════════════════════════════════════════ -->
{#if showDeleteModal && deleteTarget}
    <div
        style="position:fixed;inset:0;z-index:200;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;padding:1rem;"
        role="dialog"
        aria-modal="true"
    >
        <div
            style="background:var(--color-base-100);border-radius:1rem;width:100%;max-width:380px;box-shadow:0 25px 50px -12px rgba(0,0,0,0.4);padding:1.5rem;display:flex;flex-direction:column;gap:1rem;"
        >
            <h3
                style="margin:0;font-size:1.1rem;font-weight:700;color:var(--color-error);"
            >
                🗑️ Eliminar Usuario
            </h3>
            <p style="margin:0;font-size:0.9rem;opacity:0.8;">
                ¿Estás seguro de que quieres eliminar al usuario
                <strong>{deleteTarget.username}</strong>? Esta acción no se
                puede deshacer.
            </p>
            <div style="display:flex;gap:0.5rem;justify-content:flex-end;">
                <button
                    class="btn btn-ghost btn-sm"
                    onclick={() => (showDeleteModal = false)}>Cancelar</button
                >
                <button
                    class="btn btn-error btn-sm"
                    onclick={confirmDelete}
                    disabled={deleteLoading}
                >
                    {#if deleteLoading}
                        <span class="loading loading-spinner loading-xs"></span>
                    {/if}
                    Eliminar
                </button>
            </div>
        </div>
    </div>
{/if}

<style>
    @keyframes pulseSkel {
        0%,
        100% {
            opacity: 1;
        }
        50% {
            opacity: 0.4;
        }
    }
</style>

<script lang="ts">
    import { createUser, updateUser } from "$lib/api";
    import type { User, UserCreate, UserUpdate } from "$lib/types/user";
    import { notify } from "$lib/stores/notifications";

    // Propiedades usando runas de Svelte 5
    let {
        show = $bindable(false),
        mode = "create",
        target = null,
        onsave,
    } = $props<{
        show: boolean;
        mode: "create" | "edit";
        target: User | null;
        onsave?: () => void;
    }>();

    // Campos del formulario locales
    let fUsername = $state("");
    let fEmail = $state("");
    let fPassword = $state("");
    let fRole = $state("admin");
    let fActive = $state(true);
    let fTelegramId = $state("");
    let fAlerts = $state(false);
    let fDeviceDown = $state(false);
    let fAnnouncements = $state(false);

    // Estados de carga e interacción locales
    let modalError = $state<string | null>(null);
    let modalLoading = $state(false);

    const ROLES = ["admin", "tecnico", "cobranza"];

    // Carga de datos / Reset al mostrar el modal
    $effect(() => {
        if (show) {
            if (mode === "edit" && target) {
                fUsername = target.username;
                fEmail = target.email;
                fPassword = "";
                fRole = target.role;
                fActive = target.is_active;
                fTelegramId = target.telegram_chat_id ?? "";
                fAlerts = target.receive_alerts;
                fDeviceDown = target.receive_device_down_alerts;
                fAnnouncements = target.receive_announcements;
                modalError = null;
            } else {
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
            }
        }
    });

    async function saveUser() {
        modalLoading = true;
        modalError = null;
        try {
            if (mode === "create") {
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
                    full_name: fUsername.trim(),
                };
                await createUser(payload);
                show = false;
                notify.success("Usuario creado correctamente.");
                if (onsave) onsave();
            } else if (target) {
                const payload: UserUpdate = {
                    email: fEmail.trim(),
                    role: fRole,
                    is_active: fActive,
                    telegram_chat_id: fTelegramId.trim() || null,
                    receive_alerts: fAlerts,
                    receive_device_down_alerts: fDeviceDown,
                    receive_announcements: fAnnouncements,
                    full_name: target.full_name || target.username,
                };
                if (fPassword.trim()) payload.password = fPassword;
                await updateUser(target.username, payload);
                show = false;
                notify.success("Usuario actualizado.");
                if (onsave) onsave();
            }
        } catch (e: any) {
            modalError = e?.response?.data?.detail ?? "Error al guardar el usuario.";
            notify.error(modalError);
        } finally {
            modalLoading = false;
        }
    }
</script>

{#if show}
    <div
        style="position:fixed;inset:0;z-index:200;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;padding:1rem;overflow-y:auto;"
        role="dialog"
        aria-modal="true"
    >
        <div
            style="background:var(--color-base-100);border-radius:1rem;width:100%;max-width:440px;box-shadow:0 25px 50px -12px rgba(0,0,0,0.4);overflow:hidden;margin:auto;"
        >
            <!-- Header del modal -->
            <div
                style="padding:1.25rem 1.5rem;border-bottom:1px solid oklch(from var(--color-base-content) l c h / 0.12);display:flex;align-items:center;justify-content:space-between;"
            >
                <h3 style="margin:0;font-size:1.1rem;font-weight:700;">
                    {mode === "create"
                        ? "➕ Crear Usuario"
                        : "✏️ Editar Usuario"}
                </h3>
                <button
                    class="btn btn-ghost btn-sm btn-circle"
                    onclick={() => (show = false)}>✕</button
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
                        disabled={mode === "edit"}
                    />
                    {#if mode === "edit"}
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
                            Contraseña {mode === "edit"
                                ? "(dejar vacío para no cambiar)"
                                : "*"}
                        </span>
                    </div>
                    <input
                        class="input input-bordered input-sm w-full"
                        type="password"
                        bind:value={fPassword}
                        placeholder={mode === "edit"
                            ? "••••••••"
                            : "Nueva contraseña"}
                        required={mode === "create"}
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
                    style="display:flex;gap:0.5rem;justify-content:flex-end;padding-top:0.25rem;border-top:1px solid oklch(from var(--color-base-content) l c h / 0.08);"
                >
                    <button
                        type="button"
                        class="btn btn-ghost btn-sm"
                        onclick={() => (show = false)}>Cancelar</button
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
                        {mode === "create" ? "Crear" : "Guardar cambios"}
                    </button>
                </div>
            </form>
        </div>
    </div>
{/if}

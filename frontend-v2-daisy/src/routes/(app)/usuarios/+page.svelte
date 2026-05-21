<script lang="ts">
    import { onMount } from "svelte";
    import { getUsers } from "$lib/api";
    import DataTable from "$lib/components/DataTable.svelte";
    import type { User } from "$lib/types/user";
    import { user as currentUser } from "$lib/stores/auth";
    import { notify } from "$lib/stores/notifications";

    // Subcomponentes refactorizados
    import UserFormModal from "$lib/components/usuarios/UserFormModal.svelte";
    import UserDeleteModal from "$lib/components/usuarios/UserDeleteModal.svelte";

    // ── Estado principal ──────────────────────────────────────────────────
    let users = $state<User[]>([]);
    let loading = $state(true);

    // ── Modal Crear/Editar ────────────────────────────────────────────────
    let showModal = $state(false);
    let modalMode = $state<"create" | "edit">("create");
    let editTarget = $state<User | null>(null);

    // ── Modal Confirmar Eliminar ─────────────────────────────────────────
    let showDeleteModal = $state(false);
    let deleteTarget = $state<User | null>(null);

    // ── Carga inicial ─────────────────────────────────────────────────────
    async function loadUsers() {
        loading = true;
        try {
            const res = await getUsers();
            users = res;
        } catch (e: any) {
            notify.error(e?.response?.data?.detail ?? "Error al cargar usuarios.");
        } finally {
            loading = false;
        }
    }

    onMount(loadUsers);

    // ── Helpers ────────────────────────────────────────────────────────────
    function roleBadgeStyle(role: string): string {
        const map: Record<string, string> = {
            admin: "badge-warning",
            tecnico: "badge-info",
            cobranza: "badge-success",
        };
        return map[role] || "badge-ghost";
    }

    function activeBadgeStyle(active: boolean): string {
        return active ? "badge-success" : "badge-error";
    }

    // ── Abrir Modales ──────────────────────────────────────────────────────
    function openCreate() {
        modalMode = "create";
        editTarget = null;
        showModal = true;
    }

    function openEdit(u: User) {
        modalMode = "edit";
        editTarget = u;
        showModal = true;
    }

    function openDelete(u: User) {
        deleteTarget = u;
        showDeleteModal = true;
    }

    // ── Callbacks de modales ───────────────────────────────────────────────
    async function handleSave() {
        await loadUsers();
    }

    async function handleDeleteConfirm() {
        notify.success("Usuario eliminado correctamente.");
        await loadUsers();
    }
</script>

<!-- ── CONTENEDOR PRINCIPAL ───────────────────────────────────────────── -->
<div style="display:flex;flex-direction:column;gap:1.5rem;">
    <!-- ── HEADER ─────────────────────────────────────────────────────────── -->
    <div
        class="glass-card-flat"
        style="border-radius:1rem;display:flex;flex-direction:column;overflow:hidden;"
    >
        <div
            style="padding:1.25rem 1.5rem;display:flex;flex-direction:column;gap:0.75rem;"
        >
            <div
                style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:0.75rem;"
            >
                <div>
                    <h1 style="margin:0;font-size:1.5rem;font-weight:800;">
                        Control de Acceso — Usuarios
                    </h1>
                    <p
                        style="margin:0.25rem 0 0;font-size:0.85rem;opacity:0.5;"
                    >
                        {loading
                            ? "Cargando..."
                            : `${users.length} usuario${users.length !== 1 ? "s" : ""} registrado${users.length !== 1 ? "s" : ""}`}
                    </p>
                </div>
                <div
                    style="display:flex;align-items:center;gap:0.75rem;flex-wrap:wrap;"
                >
                    <button
                        class="btn btn-primary btn-sm gap-2"
                        onclick={openCreate}
                    >
                        <svg
                            class="w-4 h-4"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                stroke-width="2"
                                d="M12 4v16m8-8H4"
                            />
                        </svg>
                        Nuevo Usuario
                    </button>
                </div>
            </div>
        </div>
    </div>


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
                            class="badge badge-sm {roleBadgeStyle(u.role)} capitalize"
                        >{u.role}</span
                        >
                    </td>

                    <!-- Estado activo -->
                    <td class="dt-td" style="text-align:center;">
                        <span
                            class="badge badge-sm {activeBadgeStyle(u.is_active)}"
                        >{u.is_active ? "Activo" : "Inactivo"}</span
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

<!-- Modales Refactorizados -->
<UserFormModal
    bind:show={showModal}
    mode={modalMode}
    target={editTarget}
    onsave={handleSave}
/>

<UserDeleteModal
    bind:show={showDeleteModal}
    target={deleteTarget}
    onconfirm={handleDeleteConfirm}
/>

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

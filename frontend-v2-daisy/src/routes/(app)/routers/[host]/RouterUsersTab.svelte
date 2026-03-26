<script lang="ts">
    import { onMount } from "svelte";
    import {
        getRouterUsers,
        createRouterUser,
        deleteRouterUser,
    } from "$lib/api";

    export let host: string;

    // Estado
    let users: any[] = [];
    let loading = false;
    let error = "";
    let successMsg = "";
    let notProvisioned = false;

    // Modal
    let showModal = false;
    let saving = false;
    let newUser = { username: "", password: "", group: "read" };
    let formError = "";

    // Confirmación de eliminación
    let deleteTarget: string | null = null;

    async function loadUsers() {
        loading = true;
        error = "";
        try {
            users = await getRouterUsers(host);
        } catch (e: any) {
            if (e?.response?.status === 412) {
                notProvisioned = true;
            } else {
                error =
                    e?.response?.data?.detail ||
                    "Error al cargar los usuarios del router.";
            }
        } finally {
            loading = false;
        }
    }

    async function handleCreate() {
        if (!newUser.username.trim() || !newUser.password.trim()) {
            formError = "El nombre de usuario y la contraseña son requeridos.";
            return;
        }
        saving = true;
        formError = "";
        try {
            await createRouterUser(host, { ...newUser });
            successMsg = `Usuario "${newUser.username}" creado correctamente.`;
            newUser = { username: "", password: "", group: "read" };
            showModal = false;
            await loadUsers();
        } catch (e: any) {
            formError =
                e?.response?.data?.detail || "Error al crear el usuario.";
        } finally {
            saving = false;
        }
    }

    async function handleDelete(userId: string) {
        try {
            await deleteRouterUser(host, userId);
            successMsg = `Usuario eliminado correctamente.`;
            deleteTarget = null;
            await loadUsers();
        } catch (e: any) {
            error =
                e?.response?.data?.detail || "Error al eliminar el usuario.";
        }
    }

    function openModal() {
        newUser = { username: "", password: "", group: "read" };
        formError = "";
        showModal = true;
    }

    function getBadgeClass(group: string): string {
        switch (group.toLowerCase()) {
            case "full":
                return "badge-error";
            case "write":
                return "badge-warning";
            case "read":
                return "badge-info";
            default:
                return "badge-ghost";
        }
    }

    onMount(loadUsers);
</script>

<div class="space-y-4">
    {#if notProvisioned}
        <div class="alert alert-warning shadow-lg">
            <svg
                xmlns="http://www.w3.org/2000/svg"
                class="stroke-current shrink-0 h-6 w-6"
                fill="none"
                viewBox="0 0 24 24"
                ><path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                /></svg
            >
            <div>
                <h3 class="font-bold">Router no aprovisionado</h3>
                <div class="text-xs">
                    Este router no ha sido aprovisionado para acceso seguro.
                    Debes ir a la pestaña <b>Overview</b> y hacer clic en
                    <b>Aprovisionar</b> para activar estas funciones.
                </div>
            </div>
        </div>
    {:else}
        <!-- Header y botón añadir -->
        <div class="flex items-center justify-between">
            <div>
                <h3 class="text-lg font-bold">Usuarios del Router</h3>
                <p class="text-sm text-base-content/60">
                    Cuentas locales del sistema MikroTik.
                </p>
            </div>
            <div class="flex gap-2">
                <button
                    class="btn btn-sm btn-ghost"
                    on:click={loadUsers}
                    disabled={loading}
                >
                    <svg
                        xmlns="http://www.w3.org/2000/svg"
                        class="w-4 h-4 {loading ? 'animate-spin' : ''}"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        ><path d="M23 4v6h-6" /><path d="M1 20v-6h6" /><path
                            d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"
                        /></svg
                    >
                    Actualizar
                </button>
                <button
                    class="btn btn-sm btn-primary gap-2"
                    on:click={openModal}
                >
                    <svg
                        xmlns="http://www.w3.org/2000/svg"
                        class="w-4 h-4"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        ><line x1="12" y1="5" x2="12" y2="19" /><line
                            x1="5"
                            y1="12"
                            x2="19"
                            y2="12"
                        /></svg
                    >
                    Añadir Usuario
                </button>
            </div>
        </div>

        <!-- Mensajes de estado -->
        {#if successMsg}
            <div class="alert alert-success py-2">
                <span class="text-sm">{successMsg}</span>
                <button
                    class="btn btn-xs btn-ghost ml-auto"
                    on:click={() => (successMsg = "")}>✕</button
                >
            </div>
        {/if}
        {#if error}
            <div class="alert alert-error py-2">
                <span class="text-sm">{error}</span>
                <button
                    class="btn btn-xs btn-ghost ml-auto"
                    on:click={() => (error = "")}>✕</button
                >
            </div>
        {/if}

        <!-- Tabla de usuarios -->
        <div class="overflow-x-auto rounded-lg border border-base-300">
            <table class="table table-sm w-full">
                <thead>
                    <tr class="bg-base-200/50">
                        <th>Usuario</th>
                        <th>Grupo</th>
                        <th>Último IP</th>
                        <th>Último Login</th>
                        <th class="text-right">Acciones</th>
                    </tr>
                </thead>
                <tbody>
                    {#if loading}
                        <tr
                            ><td colspan="5" class="text-center py-8">
                                <span class="loading loading-spinner loading-md"
                                ></span>
                            </td></tr
                        >
                    {:else if users.length === 0}
                        <tr
                            ><td
                                colspan="5"
                                class="text-center py-8 text-base-content/50"
                            >
                                No hay usuarios disponibles o no se pudo
                                conectar al router.
                            </td></tr
                        >
                    {:else}
                        {#each users as u}
                            <tr class="hover">
                                <td class="font-mono font-semibold"
                                    >{u.name || u[".id"] || "-"}</td
                                >
                                <td>
                                    <span
                                        class="badge badge-sm {getBadgeClass(
                                            u.group || '',
                                        )}"
                                    >
                                        {u.group || "unknown"}
                                    </span>
                                </td>
                                <td class="font-mono text-xs"
                                    >{u["last-logged-in-from"] || "-"}</td
                                >
                                <td class="text-xs"
                                    >{u["last-logged-in"] || "-"}</td
                                >
                                <td class="text-right">
                                    {#if u.name !== "admin"}
                                        <button
                                            class="btn btn-xs btn-ghost text-error"
                                            on:click={() =>
                                                (deleteTarget =
                                                    u[".id"] || u.name)}
                                            title="Eliminar usuario"
                                        >
                                            <svg
                                                xmlns="http://www.w3.org/2000/svg"
                                                class="w-4 h-4"
                                                viewBox="0 0 24 24"
                                                fill="none"
                                                stroke="currentColor"
                                                stroke-width="2"
                                                ><polyline
                                                    points="3 6 5 6 21 6"
                                                /><path
                                                    d="M19 6l-1 14H6L5 6"
                                                /><path
                                                    d="M10 11v6M14 11v6"
                                                /><path d="M9 6V4h6v2" /></svg
                                            >
                                        </button>
                                    {:else}
                                        <span class="badge badge-xs badge-ghost"
                                            >protegido</span
                                        >
                                    {/if}
                                </td>
                            </tr>
                        {/each}
                    {/if}
                </tbody>
            </table>
        </div>

        <p class="text-xs text-base-content/40">
            Total: {users.length} usuario(s)
        </p>
    {/if}
</div>

<!-- Modal: Crear usuario -->
{#if showModal}
    <dialog class="modal modal-open">
        <div class="modal-box max-w-sm">
            <h3 class="font-bold text-lg mb-4">Nuevo Usuario del Router</h3>
            {#if formError}
                <div class="alert alert-error py-2 mb-3 text-sm">
                    {formError}
                </div>
            {/if}
            <form on:submit|preventDefault={handleCreate} class="space-y-4">
                <label class="form-control">
                    <span class="label-text">Usuario</span>
                    <input
                        class="input input-bordered input-sm"
                        type="text"
                        bind:value={newUser.username}
                        placeholder="ej. operador1"
                        autocomplete="off"
                        required
                    />
                </label>
                <label class="form-control">
                    <span class="label-text">Contraseña</span>
                    <input
                        class="input input-bordered input-sm"
                        type="password"
                        bind:value={newUser.password}
                        placeholder="Contraseña segura"
                        required
                    />
                </label>
                <label class="form-control">
                    <span class="label-text">Grupo / Rol</span>
                    <select
                        class="select select-bordered select-sm"
                        bind:value={newUser.group}
                    >
                        <option value="read">read – Solo lectura</option>
                        <option value="write">write – Escritura</option>
                        <option value="full">full – Acceso completo</option>
                    </select>
                </label>
                <div class="modal-action mt-2">
                    <button
                        type="button"
                        class="btn btn-sm btn-ghost"
                        on:click={() => (showModal = false)}>Cancelar</button
                    >
                    <button
                        type="submit"
                        class="btn btn-sm btn-primary"
                        disabled={saving}
                    >
                        {#if saving}<span
                                class="loading loading-spinner loading-xs"
                            ></span>{/if}
                        Crear Usuario
                    </button>
                </div>
            </form>
        </div>
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div
            class="modal-backdrop"
            role="button"
            tabindex="-1"
            on:click={() => (showModal = false)}
            on:keydown={(e) => e.key === "Escape" && (showModal = false)}
        ></div>
    </dialog>
{/if}

<!-- Modal: Confirmar eliminación -->
{#if deleteTarget !== null}
    <dialog class="modal modal-open">
        <div class="modal-box max-w-sm">
            <h3 class="font-bold text-lg">¿Eliminar usuario?</h3>
            <p class="py-4 text-sm">
                Esta acción eliminará permanentemente el usuario
                <span class="font-mono font-bold">{deleteTarget}</span> del router.
            </p>
            <div class="modal-action">
                <button
                    class="btn btn-sm btn-ghost"
                    on:click={() => (deleteTarget = null)}>Cancelar</button
                >
                <button
                    class="btn btn-sm btn-error"
                    on:click={() => deleteTarget && handleDelete(deleteTarget)}
                >
                    Sí, eliminar
                </button>
            </div>
        </div>
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div
            class="modal-backdrop"
            role="button"
            tabindex="-1"
            on:click={() => (deleteTarget = null)}
            on:keydown={(e) => e.key === "Escape" && (deleteTarget = null)}
        ></div>
    </dialog>
{/if}

<script lang="ts">
    import { onMount } from 'svelte';
    import {
        getPPPoESecrets,
        getPPPoEActive,
        getPPPoEProfiles,
        createPPPoESecret,
        updatePPPoESecret,
        disablePPPoESecret,
        deletePPPoESecret,
        killPPPoEConnection
    } from '$lib/api';

    export let host: string;

    // Sub-tab activo
    let activeTab: 'secrets' | 'active' = 'secrets';

    // Estado común
    let loadingSecrets = false;
    let loadingActive = false;
    let errorMsg = '';
    let successMsg = '';

    // Datos
    let secrets: any[] = [];
    let activeSessions: any[] = [];
    let profiles: any[] = [];

    // Modal: crear/editar secreto
    let showSecretModal = false;
    let editingSecret: any | null = null;
    let secretForm = { username: '', password: '', profile: '', service: 'pppoe', comment: '' };
    let formError = '';
    let savingSecret = false;

    // Confirmación eliminación/desconexión
    let deleteSecretTarget: string | null = null;
    let killSessionTarget: string | null = null;

    // Búsqueda
    let searchSecrets = '';
    let searchActive = '';

    $: filteredSecrets = secrets.filter(s =>
        !searchSecrets || (s.name || '').toLowerCase().includes(searchSecrets.toLowerCase())
    );
    $: filteredSessions = activeSessions.filter(s =>
        !searchActive || (s.name || '').toLowerCase().includes(searchActive.toLowerCase())
    );

    async function loadSecrets() {
        loadingSecrets = true;
        errorMsg = '';
        try {
            secrets = await getPPPoESecrets(host);
        } catch (e: any) {
            errorMsg = e?.response?.data?.detail || 'Error al cargar los secretos PPP.';
        } finally {
            loadingSecrets = false;
        }
    }

    async function loadActive() {
        loadingActive = true;
        errorMsg = '';
        try {
            activeSessions = await getPPPoEActive(host);
        } catch (e: any) {
            errorMsg = e?.response?.data?.detail || 'Error al cargar las sesiones activas.';
        } finally {
            loadingActive = false;
        }
    }

    async function loadProfiles() {
        try {
            profiles = await getPPPoEProfiles(host);
        } catch {
            profiles = [];
        }
    }

    function openCreateModal() {
        editingSecret = null;
        secretForm = { username: '', password: '', profile: profiles[0]?.name || '', service: 'pppoe', comment: '' };
        formError = '';
        showSecretModal = true;
    }

    function openEditModal(s: any) {
        editingSecret = s;
        secretForm = {
            username: s.name || '',
            password: '',
            profile: s.profile || '',
            service: s.service || 'pppoe',
            comment: s.comment || ''
        };
        formError = '';
        showSecretModal = true;
    }

    async function handleSaveSecret() {
        if (!secretForm.username.trim()) {
            formError = 'El nombre de usuario es requerido.';
            return;
        }
        if (!editingSecret && !secretForm.password.trim()) {
            formError = 'La contraseña es requerida al crear un secreto.';
            return;
        }
        savingSecret = true;
        formError = '';
        try {
            if (editingSecret) {
                const update: any = {};
                if (secretForm.password) update.password = secretForm.password;
                if (secretForm.profile) update.profile = secretForm.profile;
                if (secretForm.comment !== undefined) update.comment = secretForm.comment;
                await updatePPPoESecret(host, editingSecret['.id'], update);
                successMsg = `Secreto "${secretForm.username}" actualizado.`;
            } else {
                await createPPPoESecret(host, {
                    username: secretForm.username,
                    password: secretForm.password,
                    profile: secretForm.profile,
                    service: secretForm.service,
                    comment: secretForm.comment
                });
                successMsg = `Secreto "${secretForm.username}" creado correctamente.`;
            }
            showSecretModal = false;
            await loadSecrets();
        } catch (e: any) {
            formError = e?.response?.data?.detail || 'Error al guardar el secreto.';
        } finally {
            savingSecret = false;
        }
    }

    async function toggleSecretStatus(s: any) {
        errorMsg = '';
        const shouldDisable = s.disabled !== 'true' && s.disabled !== true;
        try {
            await disablePPPoESecret(host, s['.id'], shouldDisable);
            successMsg = `Secreto "${s.name}" ${shouldDisable ? 'deshabilitado' : 'habilitado'}.`;
            await loadSecrets();
        } catch (e: any) {
            errorMsg = e?.response?.data?.detail || 'Error al cambiar el estado del secreto.';
        }
    }

    async function handleDeleteSecret(secretId: string) {
        try {
            await deletePPPoESecret(host, secretId);
            successMsg = 'Secreto eliminado correctamente.';
            deleteSecretTarget = null;
            await loadSecrets();
        } catch (e: any) {
            errorMsg = e?.response?.data?.detail || 'Error al eliminar el secreto.';
        }
    }

    async function handleKillSession(username: string) {
        try {
            await killPPPoEConnection(host, username);
            successMsg = `Sesión de "${username}" desconectada.`;
            killSessionTarget = null;
            await loadActive();
        } catch (e: any) {
            errorMsg = e?.response?.data?.detail || 'Error al desconectar la sesión.';
        }
    }

    function formatUptime(uptime: string): string {
        return uptime || '-';
    }

    onMount(async () => {
        await Promise.all([loadSecrets(), loadActive(), loadProfiles()]);
    });
</script>

<div class="space-y-4">
    <!-- Header -->
    <div class="flex items-center justify-between">
        <div>
            <h3 class="text-lg font-bold">Gestión PPP Global</h3>
            <p class="text-sm text-base-content/60">Secretos y sesiones activas PPPoE/PPTP del router.</p>
        </div>
        <div class="flex gap-2">
            <button class="btn btn-sm btn-ghost" on:click={() => { loadSecrets(); loadActive(); }}>
                <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6"/><path d="M1 20v-6h6"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
                Actualizar
            </button>
        </div>
    </div>

    <!-- Alertas -->
    {#if successMsg}
        <div class="alert alert-success py-2">
            <span class="text-sm">{successMsg}</span>
            <button class="btn btn-xs btn-ghost ml-auto" on:click={() => successMsg = ''}>✕</button>
        </div>
    {/if}
    {#if errorMsg}
        <div class="alert alert-error py-2">
            <span class="text-sm">{errorMsg}</span>
            <button class="btn btn-xs btn-ghost ml-auto" on:click={() => errorMsg = ''}>✕</button>
        </div>
    {/if}

    <!-- Sub-tabs -->
    <div class="tabs tabs-boxed w-fit">
        <button
            class="tab {activeTab === 'secrets' ? 'tab-active' : ''}"
            on:click={() => activeTab = 'secrets'}
        >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 mr-2" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/></svg>
            Secretos
            <span class="badge badge-sm ml-2">{secrets.length}</span>
        </button>
        <button
            class="tab {activeTab === 'active' ? 'tab-active' : ''}"
            on:click={() => activeTab = 'active'}
        >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 mr-2" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14"/></svg>
            Sesiones Activas
            <span class="badge badge-sm badge-success ml-2">{activeSessions.length}</span>
        </button>
    </div>

    <!-- === SECRETOS PPP === -->
    {#if activeTab === 'secrets'}
        <div class="space-y-3">
            <div class="flex gap-2 items-center">
                <input
                    class="input input-bordered input-sm flex-1 max-w-xs"
                    type="text"
                    placeholder="Buscar usuario..."
                    bind:value={searchSecrets}
                />
                <button class="btn btn-sm btn-primary gap-1" on:click={openCreateModal}>
                    <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                    Nuevo Secreto
                </button>
            </div>
            <div class="overflow-x-auto rounded-lg border border-base-300">
                <table class="table table-sm w-full">
                    <thead>
                        <tr class="bg-base-200/50">
                            <th>Usuario</th>
                            <th>Perfil</th>
                            <th>Servicio</th>
                            <th>Comentario</th>
                            <th>Estado</th>
                            <th class="text-right">Acciones</th>
                        </tr>
                    </thead>
                    <tbody>
                        {#if loadingSecrets}
                            <tr><td colspan="6" class="text-center py-8">
                                <span class="loading loading-spinner loading-md"></span>
                            </td></tr>
                        {:else if filteredSecrets.length === 0}
                            <tr><td colspan="6" class="text-center py-8 text-base-content/50">
                                {searchSecrets ? 'No se encontraron resultados.' : 'No hay secretos PPP configurados.'}
                            </td></tr>
                        {:else}
                            {#each filteredSecrets as s}
                                <tr class="hover {s.disabled === 'true' || s.disabled === true ? 'opacity-50' : ''}">
                                    <td class="font-mono font-semibold">{s.name || '-'}</td>
                                    <td>
                                        <span class="badge badge-sm badge-outline">{s.profile || '-'}</span>
                                    </td>
                                    <td class="text-xs">{s.service || 'pppoe'}</td>
                                    <td class="text-xs text-base-content/70 max-w-xs truncate">{s.comment || '-'}</td>
                                    <td>
                                        {#if s.disabled === 'true' || s.disabled === true}
                                            <span class="badge badge-sm badge-error">Deshabilitado</span>
                                        {:else}
                                            <span class="badge badge-sm badge-success">Activo</span>
                                        {/if}
                                    </td>
                                    <td class="text-right">
                                        <div class="flex gap-1 justify-end">
                                            <button
                                                class="btn btn-xs btn-ghost"
                                                title="{s.disabled === 'true' || s.disabled === true ? 'Habilitar' : 'Deshabilitar'}"
                                                on:click={() => toggleSecretStatus(s)}
                                            >
                                                {#if s.disabled === 'true' || s.disabled === true}
                                                    <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-success" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 12l2 2 4-4m6 2a9 9 0 1 1-18 0 9 9 0 0 1 18 0z"/></svg>
                                                {:else}
                                                    <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-warning" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg>
                                                {/if}
                                            </button>
                                            <button
                                                class="btn btn-xs btn-ghost"
                                                title="Editar"
                                                on:click={() => openEditModal(s)}
                                            >
                                                <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                                            </button>
                                            <button
                                                class="btn btn-xs btn-ghost text-error"
                                                title="Eliminar"
                                                on:click={() => deleteSecretTarget = s['.id']}
                                            >
                                                <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4h6v2"/></svg>
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            {/each}
                        {/if}
                    </tbody>
                </table>
            </div>
            <p class="text-xs text-base-content/40">Mostrando {filteredSecrets.length} de {secrets.length} secreto(s).</p>
        </div>
    {/if}

    <!-- === SESIONES ACTIVAS === -->
    {#if activeTab === 'active'}
        <div class="space-y-3">
            <input
                class="input input-bordered input-sm max-w-xs"
                type="text"
                placeholder="Buscar sesión..."
                bind:value={searchActive}
            />
            <div class="overflow-x-auto rounded-lg border border-base-300">
                <table class="table table-sm w-full">
                    <thead>
                        <tr class="bg-base-200/50">
                            <th>Usuario</th>
                            <th>Servicio</th>
                            <th>IP Caller</th>
                            <th>IP Remota</th>
                            <th>Sesión activa</th>
                            <th class="text-right">Acciones</th>
                        </tr>
                    </thead>
                    <tbody>
                        {#if loadingActive}
                            <tr><td colspan="6" class="text-center py-8">
                                <span class="loading loading-spinner loading-md"></span>
                            </td></tr>
                        {:else if filteredSessions.length === 0}
                            <tr><td colspan="6" class="text-center py-8 text-base-content/50">
                                {searchActive ? 'No se encontraron resultados.' : 'No hay sesiones activas en este momento.'}
                            </td></tr>
                        {:else}
                            {#each filteredSessions as s}
                                <tr class="hover">
                                    <td class="font-mono font-semibold">{s.name || '-'}</td>
                                    <td class="text-xs">{s.service || '-'}</td>
                                    <td class="font-mono text-xs">{s['caller-id'] || '-'}</td>
                                    <td class="font-mono text-xs">{s['remote-address'] || '-'}</td>
                                    <td class="text-xs">{formatUptime(s.uptime)}</td>
                                    <td class="text-right">
                                        <button
                                            class="btn btn-xs btn-error btn-outline gap-1"
                                            title="Desconectar sesión"
                                            on:click={() => killSessionTarget = s.name}
                                        >
                                            <svg xmlns="http://www.w3.org/2000/svg" class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg>
                                            Desconectar
                                        </button>
                                    </td>
                                </tr>
                            {/each}
                        {/if}
                    </tbody>
                </table>
            </div>
            <p class="text-xs text-base-content/40">{filteredSessions.length} sesión(es) activa(s).</p>
        </div>
    {/if}
</div>

<!-- Modal: Crear / Editar Secreto -->
{#if showSecretModal}
    <dialog class="modal modal-open">
        <div class="modal-box max-w-md">
            <h3 class="font-bold text-lg mb-4">
                {editingSecret ? `Editar Secreto: ${editingSecret.name}` : 'Nuevo Secreto PPP'}
            </h3>
            {#if formError}
                <div class="alert alert-error py-2 mb-3 text-sm">{formError}</div>
            {/if}
            <form on:submit|preventDefault={handleSaveSecret} class="space-y-3">
                {#if !editingSecret}
                    <label class="form-control">
                        <span class="label-text">Usuario PPP</span>
                        <input
                            class="input input-bordered input-sm"
                            type="text"
                            bind:value={secretForm.username}
                            placeholder="ej. cliente001"
                            required
                        />
                    </label>
                {/if}
                <label class="form-control">
                    <span class="label-text">{editingSecret ? 'Nueva contraseña (dejar en blanco para no cambiar)' : 'Contraseña'}</span>
                    <input
                        class="input input-bordered input-sm"
                        type="password"
                        bind:value={secretForm.password}
                        placeholder="{editingSecret ? 'Nueva contraseña...' : 'Contraseña del secreto'}"
                        required={!editingSecret}
                    />
                </label>
                <label class="form-control">
                    <span class="label-text">Perfil</span>
                    {#if profiles.length > 0}
                        <select class="select select-bordered select-sm" bind:value={secretForm.profile}>
                            {#each profiles as p}
                                <option value={p.name}>{p.name}</option>
                            {/each}
                        </select>
                    {:else}
                        <input
                            class="input input-bordered input-sm"
                            type="text"
                            bind:value={secretForm.profile}
                            placeholder="ej. default"
                        />
                    {/if}
                </label>
                {#if !editingSecret}
                    <label class="form-control">
                        <span class="label-text">Servicio</span>
                        <select class="select select-bordered select-sm" bind:value={secretForm.service}>
                            <option value="pppoe">PPPoE</option>
                            <option value="pptp">PPTP</option>
                            <option value="l2tp">L2TP</option>
                            <option value="any">Cualquiera</option>
                        </select>
                    </label>
                {/if}
                <label class="form-control">
                    <span class="label-text">Comentario</span>
                    <input
                        class="input input-bordered input-sm"
                        type="text"
                        bind:value={secretForm.comment}
                        placeholder="Comentario opcional"
                    />
                </label>
                <div class="modal-action mt-2">
                    <button type="button" class="btn btn-sm btn-ghost" on:click={() => showSecretModal = false}>Cancelar</button>
                    <button type="submit" class="btn btn-sm btn-primary" disabled={savingSecret}>
                        {#if savingSecret}<span class="loading loading-spinner loading-xs"></span>{/if}
                        {editingSecret ? 'Guardar cambios' : 'Crear Secreto'}
                    </button>
                </div>
            </form>
        </div>
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div class="modal-backdrop" role="button" tabindex="-1" on:click={() => showSecretModal = false} on:keydown={(e) => e.key === 'Escape' && (showSecretModal = false)}></div>
    </dialog>
{/if}

<!-- Modal: Confirmar eliminación de secreto -->
{#if deleteSecretTarget !== null}
    <dialog class="modal modal-open">
        <div class="modal-box max-w-sm">
            <h3 class="font-bold text-lg">¿Eliminar secreto?</h3>
            <p class="py-4 text-sm">Esta acción eliminará permanentemente el secreto del router. El usuario PPP perderá acceso de inmediato.</p>
            <div class="modal-action">
                <button class="btn btn-sm btn-ghost" on:click={() => deleteSecretTarget = null}>Cancelar</button>
                <button class="btn btn-sm btn-error" on:click={() => deleteSecretTarget && handleDeleteSecret(deleteSecretTarget)}>
                    Sí, eliminar
                </button>
            </div>
        </div>
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div class="modal-backdrop" role="button" tabindex="-1" on:click={() => deleteSecretTarget = null} on:keydown={(e) => e.key === 'Escape' && (deleteSecretTarget = null)}></div>
    </dialog>
{/if}

<!-- Modal: Confirmar desconexión de sesión -->
{#if killSessionTarget !== null}
    <dialog class="modal modal-open">
        <div class="modal-box max-w-sm">
            <h3 class="font-bold text-lg">¿Desconectar sesión?</h3>
            <p class="py-4 text-sm">
                El usuario <span class="font-mono font-bold">{killSessionTarget}</span> será desconectado inmediatamente. 
                Intentará reconectarse si tiene configurado auto-reconexión.
            </p>
            <div class="modal-action">
                <button class="btn btn-sm btn-ghost" on:click={() => killSessionTarget = null}>Cancelar</button>
                <button class="btn btn-sm btn-warning" on:click={() => killSessionTarget && handleKillSession(killSessionTarget)}>
                    Sí, desconectar
                </button>
            </div>
        </div>
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div class="modal-backdrop" role="button" tabindex="-1" on:click={() => killSessionTarget = null} on:keydown={(e) => e.key === 'Escape' && (killSessionTarget = null)}></div>
    </dialog>
{/if}

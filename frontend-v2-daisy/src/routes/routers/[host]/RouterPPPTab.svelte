<script lang="ts">
    import { onMount } from 'svelte';
    import {
        getPPPoESecrets,
        getPPPoEActive,
        getPPPoEProfiles,
        getPPPoEServers,
        createPPPoESecret,
        updatePPPoESecret,
        disablePPPoESecret,
        deletePPPoESecret,
        killPPPoEConnection,
        addPPPoEServer,
        deletePPPoEServer,
        createPPPProfile,
        deletePPPProfile
    } from '$lib/api';

    export let host: string;

    // Sub-tab activo (4 sub-tabs)
    let activeTab: 'secrets' | 'active' | 'servers' | 'profiles' = 'secrets';

    // Estado común
    let loadingSecrets = false;
    let loadingActive = false;
    let loadingServers = false;
    let loadingProfiles = false;
    let errorMsg = '';
    let successMsg = '';

    // Datos
    let secrets: any[] = [];
    let activeSessions: any[] = [];
    let profiles: any[] = [];
    let servers: any[] = [];
    let interfaces: string[] = [];

    // ── SECRETOS ──────────────────────────────────────────────────────────────
    let showSecretModal = false;
    let editingSecret: any | null = null;
    let secretForm = { username: '', password: '', profile: '', service: 'pppoe', comment: '' };
    let formError = '';
    let savingSecret = false;
    let deleteSecretTarget: string | null = null;
    let killSessionTarget: string | null = null;
    let searchSecrets = '';
    let searchActive = '';

    $: filteredSecrets = secrets.filter(s =>
        !searchSecrets || (s.name || '').toLowerCase().includes(searchSecrets.toLowerCase())
    );
    $: filteredSessions = activeSessions.filter(s =>
        !searchActive || (s.name || '').toLowerCase().includes(searchActive.toLowerCase())
    );

    // ── SERVIDORES ────────────────────────────────────────────────────────────
    let showServerModal = false;
    let serverForm = { service_name: 'pppoe-server', interface: '', default_profile: '', one_session_per_host: true, keepalive_timeout: 10 };
    let serverFormError = '';
    let savingServer = false;
    let deleteServerTarget: string | null = null;

    // ── PERFILES ──────────────────────────────────────────────────────────────
    let showProfileModal = false;
    let profileForm = { plan_name: '', rate_limit: '', local_address: '', parent_queue: 'none', comment: '', pool_mode: 'new', pool_range: '', remote_address: '' };
    let profileFormError = '';
    let savingProfile = false;
    let deleteProfileTarget: string | null = null;

    const SYSTEM_PROFILES = ['default', 'default-encryption'];

    // ── CARGA DE DATOS ────────────────────────────────────────────────────────

    async function loadSecrets() {
        loadingSecrets = true; errorMsg = '';
        try { secrets = await getPPPoESecrets(host); }
        catch (e: any) { errorMsg = e?.response?.data?.detail || 'Error al cargar los secretos PPP.'; }
        finally { loadingSecrets = false; }
    }

    async function loadActive() {
        loadingActive = true; errorMsg = '';
        try { activeSessions = await getPPPoEActive(host); }
        catch (e: any) { errorMsg = e?.response?.data?.detail || 'Error al cargar las sesiones activas.'; }
        finally { loadingActive = false; }
    }

    async function loadServers() {
        loadingServers = true; errorMsg = '';
        try { servers = await getPPPoEServers(host); }
        catch (e: any) { errorMsg = e?.response?.data?.detail || 'Error al cargar los servidores PPPoE.'; }
        finally { loadingServers = false; }
    }

    async function loadProfiles() {
        loadingProfiles = true; errorMsg = '';
        try { profiles = await getPPPoEProfiles(host); }
        catch (e: any) { errorMsg = e?.response?.data?.detail || 'Error al cargar los perfiles PPP.'; }
        finally { loadingProfiles = false; }
    }

    // ── SECRETOS: Funciones ───────────────────────────────────────────────────

    function openCreateModal() {
        editingSecret = null;
        secretForm = { username: '', password: '', profile: profiles[0]?.name || '', service: 'pppoe', comment: '' };
        formError = '';
        showSecretModal = true;
    }

    function openEditModal(s: any) {
        editingSecret = s;
        secretForm = { username: s.name || '', password: '', profile: s.profile || '', service: s.service || 'pppoe', comment: s.comment || '' };
        formError = '';
        showSecretModal = true;
    }

    async function handleSaveSecret() {
        if (!secretForm.username.trim()) { formError = 'El nombre de usuario es requerido.'; return; }
        if (!editingSecret && !secretForm.password.trim()) { formError = 'La contraseña es requerida al crear un secreto.'; return; }
        savingSecret = true; formError = '';
        try {
            if (editingSecret) {
                const update: any = {};
                if (secretForm.password) update.password = secretForm.password;
                if (secretForm.profile) update.profile = secretForm.profile;
                if (secretForm.comment !== undefined) update.comment = secretForm.comment;
                await updatePPPoESecret(host, editingSecret['.id'], update);
                successMsg = `Secreto "${secretForm.username}" actualizado.`;
            } else {
                await createPPPoESecret(host, { username: secretForm.username, password: secretForm.password, profile: secretForm.profile, service: secretForm.service, comment: secretForm.comment });
                successMsg = `Secreto "${secretForm.username}" creado correctamente.`;
            }
            showSecretModal = false;
            await loadSecrets();
        } catch (e: any) { formError = e?.response?.data?.detail || 'Error al guardar el secreto.'; }
        finally { savingSecret = false; }
    }

    async function toggleSecretStatus(s: any) {
        const shouldDisable = s.disabled !== 'true' && s.disabled !== true;
        try {
            await disablePPPoESecret(host, s['.id'], shouldDisable);
            successMsg = `Secreto "${s.name}" ${shouldDisable ? 'deshabilitado' : 'habilitado'}.`;
            await loadSecrets();
        } catch (e: any) { errorMsg = e?.response?.data?.detail || 'Error al cambiar el estado del secreto.'; }
    }

    async function handleDeleteSecret(secretId: string) {
        try {
            await deletePPPoESecret(host, secretId);
            successMsg = 'Secreto eliminado correctamente.';
            deleteSecretTarget = null;
            await loadSecrets();
        } catch (e: any) { errorMsg = e?.response?.data?.detail || 'Error al eliminar el secreto.'; }
    }

    async function handleKillSession(username: string) {
        try {
            await killPPPoEConnection(host, username);
            successMsg = `Sesión de "${username}" desconectada.`;
            killSessionTarget = null;
            await loadActive();
        } catch (e: any) { errorMsg = e?.response?.data?.detail || 'Error al desconectar la sesión.'; }
    }

    // ── SERVIDORES: Funciones ─────────────────────────────────────────────────

    function openServerModal() {
        serverForm = { service_name: 'pppoe-server', interface: interfaces[0] || '', default_profile: profiles[0]?.name || '', one_session_per_host: true, keepalive_timeout: 10 };
        serverFormError = '';
        showServerModal = true;
    }

    async function handleSaveServer() {
        if (!serverForm.service_name.trim()) { serverFormError = 'El nombre del servicio es requerido.'; return; }
        if (!serverForm.interface) { serverFormError = 'Debes seleccionar una interfaz.'; return; }
        savingServer = true; serverFormError = '';
        try {
            const result = await addPPPoEServer(host, { ...serverForm });
            if (result?.status === 'warning') {
                serverFormError = result.message;
                return;
            }
            successMsg = `Servidor PPPoE "${serverForm.service_name}" añadido.`;
            showServerModal = false;
            await loadServers();
        } catch (e: any) { serverFormError = e?.response?.data?.detail || 'Error al crear el servidor PPPoE.'; }
        finally { savingServer = false; }
    }

    async function handleDeleteServer(serviceName: string) {
        try {
            await deletePPPoEServer(host, serviceName);
            successMsg = `Servidor "${serviceName}" eliminado.`;
            deleteServerTarget = null;
            await loadServers();
        } catch (e: any) { errorMsg = e?.response?.data?.detail || 'Error al eliminar el servidor PPPoE.'; }
    }

    // ── PERFILES: Funciones ───────────────────────────────────────────────────

    function openProfileModal() {
        profileForm = { plan_name: '', rate_limit: '', local_address: '', parent_queue: 'none', comment: '', pool_mode: 'new', pool_range: '', remote_address: '' };
        profileFormError = '';
        showProfileModal = true;
    }

    async function handleSaveProfile() {
        if (!profileForm.plan_name.trim()) { profileFormError = 'El nombre del plan es requerido.'; return; }
        if (!profileForm.rate_limit.trim()) { profileFormError = 'La velocidad es requerida (ej: 10M/10M).'; return; }
        if (profileForm.pool_mode === 'new' && !profileForm.pool_range.trim()) { profileFormError = 'Debes indicar el rango del pool (ej: 192.168.20.2-192.168.20.200).'; return; }
        if (profileForm.pool_mode === 'existing' && !profileForm.remote_address.trim()) { profileFormError = 'Debes seleccionar un pool existente.'; return; }
        savingProfile = true; profileFormError = '';
        const payload: any = {
            plan_name: profileForm.plan_name,
            rate_limit: profileForm.rate_limit,
            local_address: profileForm.local_address,
            parent_queue: profileForm.parent_queue,
            comment: profileForm.comment,
        };
        if (profileForm.pool_mode === 'new') payload.pool_range = profileForm.pool_range;
        else payload.remote_address = profileForm.remote_address;
        try {
            const result = await createPPPProfile(host, payload);
            if (result?.status === 'error') { profileFormError = result.message; return; }
            successMsg = `Perfil "${profileForm.plan_name}" creado correctamente.`;
            showProfileModal = false;
            await loadProfiles();
        } catch (e: any) { profileFormError = e?.response?.data?.detail || 'Error al crear el perfil.'; }
        finally { savingProfile = false; }
    }

    async function handleDeleteProfile(planName: string) {
        try {
            await deletePPPProfile(host, planName);
            successMsg = `Perfil "${planName}" eliminado.`;
            deleteProfileTarget = null;
            await loadProfiles();
        } catch (e: any) { errorMsg = e?.response?.data?.detail || 'Error al eliminar el perfil.'; }
    }

    onMount(async () => {
        await Promise.all([loadSecrets(), loadActive(), loadProfiles(), loadServers()]);
        // Obtener interfaces disponibles de los perfiles de servidor actuales o del full-details si está disponible
        // Por ahora usamos un método básico: los servidores ya cargados + interfaz manual
    });
</script>

<div class="space-y-4">
    <!-- Header -->
    <div class="flex items-center justify-between">
        <div>
            <h3 class="text-lg font-bold">Gestión PPP Global</h3>
            <p class="text-sm text-base-content/60">Secretos, sesiones, servidores y perfiles PPPoE del router.</p>
        </div>
        <button class="btn btn-sm btn-ghost" on:click={() => { loadSecrets(); loadActive(); loadServers(); loadProfiles(); }}>
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6"/><path d="M1 20v-6h6"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
            Actualizar
        </button>
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
    <div class="tabs tabs-boxed w-fit flex-wrap">
        <button class="tab {activeTab === 'secrets' ? 'tab-active' : ''}" on:click={() => activeTab = 'secrets'}>
            🔑 Secretos
            <span class="badge badge-sm ml-2">{secrets.length}</span>
        </button>
        <button class="tab {activeTab === 'active' ? 'tab-active' : ''}" on:click={() => activeTab = 'active'}>
            📡 Activas
            <span class="badge badge-sm badge-success ml-2">{activeSessions.length}</span>
        </button>
        <button class="tab {activeTab === 'servers' ? 'tab-active' : ''}" on:click={() => activeTab = 'servers'}>
            🖥️ Servidores
            <span class="badge badge-sm badge-info ml-2">{servers.length}</span>
        </button>
        <button class="tab {activeTab === 'profiles' ? 'tab-active' : ''}" on:click={() => activeTab = 'profiles'}>
            📋 Perfiles
            <span class="badge badge-sm badge-neutral ml-2">{profiles.length}</span>
        </button>
    </div>

    <!-- ═══════════════ SECRETOS PPP ═══════════════ -->
    {#if activeTab === 'secrets'}
        <div class="space-y-3">
            <div class="flex gap-2 items-center">
                <input class="input input-bordered input-sm flex-1 max-w-xs" type="text" placeholder="Buscar usuario..." bind:value={searchSecrets} />
                <button class="btn btn-sm btn-primary gap-1" on:click={openCreateModal}>
                    <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                    Nuevo Secreto
                </button>
            </div>
            <div class="overflow-x-auto rounded-lg border border-base-300">
                <table class="table table-sm w-full">
                    <thead><tr class="bg-base-200/50">
                        <th>Usuario</th><th>Perfil</th><th>Servicio</th><th>Comentario</th><th>Estado</th><th class="text-right">Acciones</th>
                    </tr></thead>
                    <tbody>
                        {#if loadingSecrets}
                            <tr><td colspan="6" class="text-center py-8"><span class="loading loading-spinner loading-md"></span></td></tr>
                        {:else if filteredSecrets.length === 0}
                            <tr><td colspan="6" class="text-center py-8 text-base-content/50">{searchSecrets ? 'Sin resultados.' : 'No hay secretos PPP.'}</td></tr>
                        {:else}
                            {#each filteredSecrets as s}
                                <tr class="hover {s.disabled === 'true' || s.disabled === true ? 'opacity-50' : ''}">
                                    <td class="font-mono font-semibold">{s.name || '-'}</td>
                                    <td><span class="badge badge-sm badge-outline">{s.profile || '-'}</span></td>
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
                                            <button class="btn btn-xs btn-ghost" title="{s.disabled === 'true' || s.disabled === true ? 'Habilitar' : 'Deshabilitar'}" on:click={() => toggleSecretStatus(s)}>
                                                {#if s.disabled === 'true' || s.disabled === true}
                                                    <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-success" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 12l2 2 4-4m6 2a9 9 0 1 1-18 0 9 9 0 0 1 18 0z"/></svg>
                                                {:else}
                                                    <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-warning" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg>
                                                {/if}
                                            </button>
                                            <button class="btn btn-xs btn-ghost" title="Editar" on:click={() => openEditModal(s)}>
                                                <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                                            </button>
                                            <button class="btn btn-xs btn-ghost text-error" title="Eliminar" on:click={() => deleteSecretTarget = s['.id']}>
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

    <!-- ═══════════════ SESIONES ACTIVAS ═══════════════ -->
    {#if activeTab === 'active'}
        <div class="space-y-3">
            <input class="input input-bordered input-sm max-w-xs" type="text" placeholder="Buscar sesión..." bind:value={searchActive} />
            <div class="overflow-x-auto rounded-lg border border-base-300">
                <table class="table table-sm w-full">
                    <thead><tr class="bg-base-200/50">
                        <th>Usuario</th><th>Servicio</th><th>IP Caller</th><th>IP Remota</th><th>Uptime</th><th class="text-right">Acciones</th>
                    </tr></thead>
                    <tbody>
                        {#if loadingActive}
                            <tr><td colspan="6" class="text-center py-8"><span class="loading loading-spinner loading-md"></span></td></tr>
                        {:else if filteredSessions.length === 0}
                            <tr><td colspan="6" class="text-center py-8 text-base-content/50">{searchActive ? 'Sin resultados.' : 'No hay sesiones activas.'}</td></tr>
                        {:else}
                            {#each filteredSessions as s}
                                <tr class="hover">
                                    <td class="font-mono font-semibold">{s.name || '-'}</td>
                                    <td class="text-xs">{s.service || '-'}</td>
                                    <td class="font-mono text-xs">{s['caller-id'] || '-'}</td>
                                    <td class="font-mono text-xs">{s['remote-address'] || '-'}</td>
                                    <td class="text-xs">{s.uptime || '-'}</td>
                                    <td class="text-right">
                                        <button class="btn btn-xs btn-error btn-outline gap-1" title="Desconectar sesión" on:click={() => killSessionTarget = s.name}>
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

    <!-- ═══════════════ SERVIDORES PPPOE ═══════════════ -->
    {#if activeTab === 'servers'}
        <div class="space-y-3">
            <div class="flex justify-end">
                <button class="btn btn-sm btn-primary gap-1" on:click={openServerModal}>
                    <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                    Añadir Servidor
                </button>
            </div>
            <div class="overflow-x-auto rounded-lg border border-base-300">
                <table class="table table-sm w-full">
                    <thead><tr class="bg-base-200/50">
                        <th>Nombre Servicio</th><th>Interface</th><th>Perfil Defecto</th><th>1 Sesión/Host</th><th>Keepalive (s)</th><th>Estado</th><th class="text-right">Acciones</th>
                    </tr></thead>
                    <tbody>
                        {#if loadingServers}
                            <tr><td colspan="7" class="text-center py-8"><span class="loading loading-spinner loading-md"></span></td></tr>
                        {:else if servers.length === 0}
                            <tr><td colspan="7" class="text-center py-8 text-base-content/50">No hay servidores PPPoE configurados.</td></tr>
                        {:else}
                            {#each servers as srv}
                                <tr class="hover">
                                    <td class="font-mono font-semibold">{srv['service-name'] || srv.name || '-'}</td>
                                    <td><span class="badge badge-sm badge-outline">{srv.interface || '-'}</span></td>
                                    <td class="text-xs">{srv['default-profile'] || '-'}</td>
                                    <td>
                                        {#if srv['one-session-per-host'] === 'yes' || srv['one-session-per-host'] === true}
                                            <span class="badge badge-xs badge-success">✓ Sí</span>
                                        {:else}
                                            <span class="badge badge-xs badge-ghost">No</span>
                                        {/if}
                                    </td>
                                    <td class="text-xs">{srv['keepalive-timeout'] || '10'}</td>
                                    <td>
                                        {#if srv.disabled === 'false' || srv.disabled === false || !srv.disabled}
                                            <span class="badge badge-sm badge-success">Activo</span>
                                        {:else}
                                            <span class="badge badge-sm badge-error">Deshabilitado</span>
                                        {/if}
                                    </td>
                                    <td class="text-right">
                                        <button class="btn btn-xs btn-ghost text-error" title="Eliminar servidor" on:click={() => deleteServerTarget = srv['service-name'] || srv.name}>
                                            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4h6v2"/></svg>
                                        </button>
                                    </td>
                                </tr>
                            {/each}
                        {/if}
                    </tbody>
                </table>
            </div>
        </div>
    {/if}

    <!-- ═══════════════ PERFILES PPP ═══════════════ -->
    {#if activeTab === 'profiles'}
        <div class="space-y-3">
            <div class="flex justify-end">
                <button class="btn btn-sm btn-primary gap-1" on:click={openProfileModal}>
                    <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                    Nuevo Perfil / Plan
                </button>
            </div>
            <div class="overflow-x-auto rounded-lg border border-base-300">
                <table class="table table-sm w-full">
                    <thead><tr class="bg-base-200/50">
                        <th>Nombre</th><th>Rate Limit</th><th>IP Local</th><th>Pool/Remote</th><th>Cola Padre</th><th class="text-right">Acciones</th>
                    </tr></thead>
                    <tbody>
                        {#if loadingProfiles}
                            <tr><td colspan="6" class="text-center py-8"><span class="loading loading-spinner loading-md"></span></td></tr>
                        {:else if profiles.length === 0}
                            <tr><td colspan="6" class="text-center py-8 text-base-content/50">No hay perfiles PPP configurados.</td></tr>
                        {:else}
                            {#each profiles as p}
                                {@const isSystem = SYSTEM_PROFILES.includes(p.name)}
                                <tr class="hover {isSystem ? 'opacity-60' : ''}">
                                    <td class="font-mono font-semibold">
                                        {p.name || '-'}
                                        {#if isSystem}<span class="badge badge-xs badge-neutral ml-1">sistema</span>{/if}
                                    </td>
                                    <td class="font-mono text-xs">{p['rate-limit'] || '-'}</td>
                                    <td class="font-mono text-xs">{p['local-address'] || '-'}</td>
                                    <td class="font-mono text-xs">{p['remote-address'] || '-'}</td>
                                    <td class="text-xs">{p['parent-queue'] || 'none'}</td>
                                    <td class="text-right">
                                        {#if !isSystem}
                                            <button class="btn btn-xs btn-ghost text-error" title="Eliminar perfil" on:click={() => deleteProfileTarget = p.name}>
                                                <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4h6v2"/></svg>
                                            </button>
                                        {:else}
                                            <span class="text-xs text-base-content/30">Solo lectura</span>
                                        {/if}
                                    </td>
                                </tr>
                            {/each}
                        {/if}
                    </tbody>
                </table>
            </div>
            <p class="text-xs text-base-content/40">{profiles.length} perfil(es) en el router.</p>
        </div>
    {/if}
</div>

<!-- ═══════════════════════════════════════════════════════════
     MODALES — SECRETOS
══════════════════════════════════════════════════════════════ -->

{#if showSecretModal}
    <dialog class="modal modal-open">
        <div class="modal-box max-w-md">
            <h3 class="font-bold text-lg mb-4">
                {editingSecret ? `Editar Secreto: ${editingSecret.name}` : 'Nuevo Secreto PPP'}
            </h3>
            {#if formError}<div class="alert alert-error py-2 mb-3 text-sm">{formError}</div>{/if}
            <form on:submit|preventDefault={handleSaveSecret} class="space-y-3">
                {#if !editingSecret}
                    <label class="form-control">
                        <span class="label-text">Usuario PPP</span>
                        <input class="input input-bordered input-sm" type="text" bind:value={secretForm.username} placeholder="ej. cliente001" required />
                    </label>
                {/if}
                <label class="form-control">
                    <span class="label-text">{editingSecret ? 'Nueva contraseña (dejar en blanco para no cambiar)' : 'Contraseña'}</span>
                    <input class="input input-bordered input-sm" type="password" bind:value={secretForm.password} placeholder="{editingSecret ? 'Nueva contraseña...' : 'Contraseña del secreto'}" required={!editingSecret} />
                </label>
                <label class="form-control">
                    <span class="label-text">Perfil</span>
                    {#if profiles.length > 0}
                        <select class="select select-bordered select-sm" bind:value={secretForm.profile}>
                            {#each profiles as p}<option value={p.name}>{p.name}</option>{/each}
                        </select>
                    {:else}
                        <input class="input input-bordered input-sm" type="text" bind:value={secretForm.profile} placeholder="ej. default" />
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
                    <input class="input input-bordered input-sm" type="text" bind:value={secretForm.comment} placeholder="Comentario opcional" />
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

{#if deleteSecretTarget !== null}
    <dialog class="modal modal-open">
        <div class="modal-box max-w-sm">
            <h3 class="font-bold text-lg">¿Eliminar secreto?</h3>
            <p class="py-4 text-sm">Esta acción eliminará permanentemente el secreto del router.</p>
            <div class="modal-action">
                <button class="btn btn-sm btn-ghost" on:click={() => deleteSecretTarget = null}>Cancelar</button>
                <button class="btn btn-sm btn-error" on:click={() => deleteSecretTarget && handleDeleteSecret(deleteSecretTarget)}>Sí, eliminar</button>
            </div>
        </div>
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div class="modal-backdrop" role="button" tabindex="-1" on:click={() => deleteSecretTarget = null} on:keydown={(e) => e.key === 'Escape' && (deleteSecretTarget = null)}></div>
    </dialog>
{/if}

{#if killSessionTarget !== null}
    <dialog class="modal modal-open">
        <div class="modal-box max-w-sm">
            <h3 class="font-bold text-lg">¿Desconectar sesión?</h3>
            <p class="py-4 text-sm">El usuario <span class="font-mono font-bold">{killSessionTarget}</span> será desconectado inmediatamente.</p>
            <div class="modal-action">
                <button class="btn btn-sm btn-ghost" on:click={() => killSessionTarget = null}>Cancelar</button>
                <button class="btn btn-sm btn-warning" on:click={() => killSessionTarget && handleKillSession(killSessionTarget)}>Sí, desconectar</button>
            </div>
        </div>
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div class="modal-backdrop" role="button" tabindex="-1" on:click={() => killSessionTarget = null} on:keydown={(e) => e.key === 'Escape' && (killSessionTarget = null)}></div>
    </dialog>
{/if}

<!-- ═══════════════════════════════════════════════════════════
     MODALES — SERVIDORES PPPOE
══════════════════════════════════════════════════════════════ -->

{#if showServerModal}
    <dialog class="modal modal-open">
        <div class="modal-box max-w-lg">
            <h3 class="font-bold text-lg mb-4">Añadir Servidor PPPoE</h3>
            {#if serverFormError}<div class="alert alert-error py-2 mb-3 text-sm">{serverFormError}</div>{/if}
            <form on:submit|preventDefault={handleSaveServer} class="space-y-3">
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <label class="form-control">
                        <span class="label-text">Nombre del Servicio</span>
                        <input class="input input-bordered input-sm" type="text" bind:value={serverForm.service_name} placeholder="pppoe-server" required />
                    </label>
                    <label class="form-control">
                        <span class="label-text">Interface</span>
                        <input class="input input-bordered input-sm" type="text" bind:value={serverForm.interface} placeholder="ether1, bridge1, etc." required />
                        <span class="text-xs text-base-content/50 mt-1">Nombre exacto de la interfaz del router</span>
                    </label>
                </div>
                <label class="form-control">
                    <span class="label-text">Perfil por Defecto</span>
                    {#if profiles.length > 0}
                        <select class="select select-bordered select-sm" bind:value={serverForm.default_profile}>
                            {#each profiles as p}<option value={p.name}>{p.name}</option>{/each}
                        </select>
                    {:else}
                        <input class="input input-bordered input-sm" type="text" bind:value={serverForm.default_profile} placeholder="default" />
                    {/if}
                </label>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 items-end">
                    <label class="flex items-center gap-3 cursor-pointer">
                        <input type="checkbox" class="checkbox checkbox-primary checkbox-sm" bind:checked={serverForm.one_session_per_host} />
                        <div>
                            <span class="label-text font-medium">One Session per Host</span>
                            <p class="text-xs text-base-content/50">Evita múltiples sesiones desde el mismo cliente</p>
                        </div>
                    </label>
                    <label class="form-control">
                        <span class="label-text">Keepalive Timeout (seg.)</span>
                        <input class="input input-bordered input-sm" type="number" bind:value={serverForm.keepalive_timeout} min="1" max="120" />
                    </label>
                </div>
                <div class="modal-action mt-2">
                    <button type="button" class="btn btn-sm btn-ghost" on:click={() => showServerModal = false}>Cancelar</button>
                    <button type="submit" class="btn btn-sm btn-primary" disabled={savingServer}>
                        {#if savingServer}<span class="loading loading-spinner loading-xs"></span>{/if}
                        Añadir Servidor
                    </button>
                </div>
            </form>
        </div>
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div class="modal-backdrop" role="button" tabindex="-1" on:click={() => showServerModal = false} on:keydown={(e) => e.key === 'Escape' && (showServerModal = false)}></div>
    </dialog>
{/if}

{#if deleteServerTarget !== null}
    <dialog class="modal modal-open">
        <div class="modal-box max-w-sm">
            <h3 class="font-bold text-lg">¿Eliminar servidor PPPoE?</h3>
            <p class="py-4 text-sm">El servidor <span class="font-mono font-bold">{deleteServerTarget}</span> será eliminado. Los clientes conectados perderán el acceso.</p>
            <div class="modal-action">
                <button class="btn btn-sm btn-ghost" on:click={() => deleteServerTarget = null}>Cancelar</button>
                <button class="btn btn-sm btn-error" on:click={() => deleteServerTarget && handleDeleteServer(deleteServerTarget)}>Sí, eliminar</button>
            </div>
        </div>
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div class="modal-backdrop" role="button" tabindex="-1" on:click={() => deleteServerTarget = null} on:keydown={(e) => e.key === 'Escape' && (deleteServerTarget = null)}></div>
    </dialog>
{/if}

<!-- ═══════════════════════════════════════════════════════════
     MODALES — PERFILES PPP
══════════════════════════════════════════════════════════════ -->

{#if showProfileModal}
    <dialog class="modal modal-open">
        <div class="modal-box max-w-lg">
            <h3 class="font-bold text-lg mb-4">Nuevo Perfil / Plan PPP</h3>
            <p class="text-sm text-base-content/60 mb-4">Crea un perfil PPP con su pool de IPs en el router. El nombre del perfil se generará automáticamente como <code>profile-{profileForm.plan_name.toLowerCase().replace(/\s+/g, '-') || 'nombre'}</code>.</p>
            {#if profileFormError}<div class="alert alert-error py-2 mb-3 text-sm">{profileFormError}</div>{/if}
            <form on:submit|preventDefault={handleSaveProfile} class="space-y-3">
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <label class="form-control">
                        <span class="label-text">Nombre del Plan *</span>
                        <input class="input input-bordered input-sm" type="text" bind:value={profileForm.plan_name} placeholder="ej. Residencial-10M" required />
                        <span class="text-xs text-base-content/50 mt-1">Se creará como: profile-residencial-10m</span>
                    </label>
                    <label class="form-control">
                        <span class="label-text">Velocidad OK (Subida/Bajada) *</span>
                        <input class="input input-bordered input-sm" type="text" bind:value={profileForm.rate_limit} placeholder="ej. 5M/10M" required />
                    </label>
                </div>
                <label class="form-control">
                    <span class="label-text">IP Local (Gateway del Router)</span>
                    <input class="input input-bordered input-sm" type="text" bind:value={profileForm.local_address} placeholder="ej. 192.168.20.1" />
                </label>
                <label class="form-control">
                    <span class="label-text">Cola Padre</span>
                    <input class="input input-bordered input-sm" type="text" bind:value={profileForm.parent_queue} placeholder="none" />
                    <span class="text-xs text-base-content/50 mt-1">Nombre de la cola padre o "none"</span>
                </label>

                <!-- Modo de pool -->
                <div class="border border-base-300 rounded-lg p-3 space-y-3">
                    <p class="text-sm font-semibold">Pool de IPs para Clientes</p>
                    <div class="flex gap-4">
                        <label class="flex items-center gap-2 cursor-pointer">
                            <input type="radio" class="radio radio-primary radio-sm" bind:group={profileForm.pool_mode} value="new" />
                            <span class="text-sm">Crear nuevo pool</span>
                        </label>
                        <label class="flex items-center gap-2 cursor-pointer">
                            <input type="radio" class="radio radio-primary radio-sm" bind:group={profileForm.pool_mode} value="existing" />
                            <span class="text-sm">Usar pool existente</span>
                        </label>
                    </div>
                    {#if profileForm.pool_mode === 'new'}
                        <label class="form-control">
                            <span class="label-text text-xs">Rango del Pool *</span>
                            <input class="input input-bordered input-sm" type="text" bind:value={profileForm.pool_range} placeholder="ej. 192.168.20.2-192.168.20.200" />
                            <span class="text-xs text-base-content/50 mt-1">Se creará pool-residencial-10m con este rango</span>
                        </label>
                    {:else}
                        <label class="form-control">
                            <span class="label-text text-xs">Nombre del Pool Existente *</span>
                            <input class="input input-bordered input-sm" type="text" bind:value={profileForm.remote_address} placeholder="ej. pool-clientes" />
                        </label>
                    {/if}
                </div>

                <label class="form-control">
                    <span class="label-text">Comentario</span>
                    <input class="input input-bordered input-sm" type="text" bind:value={profileForm.comment} placeholder="Descripción opcional del plan" />
                </label>

                <div class="modal-action mt-2">
                    <button type="button" class="btn btn-sm btn-ghost" on:click={() => showProfileModal = false}>Cancelar</button>
                    <button type="submit" class="btn btn-sm btn-primary" disabled={savingProfile}>
                        {#if savingProfile}<span class="loading loading-spinner loading-xs"></span>{/if}
                        Crear Perfil
                    </button>
                </div>
            </form>
        </div>
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div class="modal-backdrop" role="button" tabindex="-1" on:click={() => showProfileModal = false} on:keydown={(e) => e.key === 'Escape' && (showProfileModal = false)}></div>
    </dialog>
{/if}

{#if deleteProfileTarget !== null}
    <dialog class="modal modal-open">
        <div class="modal-box max-w-sm">
            <h3 class="font-bold text-lg">¿Eliminar perfil PPP?</h3>
            <p class="py-4 text-sm">Se eliminarán el perfil y su pool de IPs asociado para <span class="font-mono font-bold">{deleteProfileTarget}</span>. Los clientes con este perfil dejarán de conectarse.</p>
            <div class="modal-action">
                <button class="btn btn-sm btn-ghost" on:click={() => deleteProfileTarget = null}>Cancelar</button>
                <button class="btn btn-sm btn-error" on:click={() => deleteProfileTarget && handleDeleteProfile(deleteProfileTarget)}>Sí, eliminar perfil y pool</button>
            </div>
        </div>
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div class="modal-backdrop" role="button" tabindex="-1" on:click={() => deleteProfileTarget = null} on:keydown={(e) => e.key === 'Escape' && (deleteProfileTarget = null)}></div>
    </dialog>
{/if}

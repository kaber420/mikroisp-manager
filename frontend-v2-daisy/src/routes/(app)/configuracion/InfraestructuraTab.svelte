<script lang="ts">
    import { onMount } from "svelte";
    import { notify } from "$lib/stores/notifications";
    import {
        getSystemServicesStatus,
        getSystemServices,
        updateSystemServices,
        testServiceConnection,
    } from "$lib/api";
    import { 
        deployInfraStack,
        getInfraStatus
    } from "$lib/api/infra";
    import ServiceControlCard from "$lib/components/infra/ServiceControlCard.svelte";

    // Declaraciones de tipos locales para la infraestructura
    type DeployActions = {
        postgres: 'skip' | 'create' | 'reuse' | 'destroy';
        redict: 'skip' | 'create' | 'reuse' | 'destroy';
    };

    type AdvancedConfig = {
        env: Record<string, string>;
        network: string;
        port: number;
    };

    type DeployResult = {
        message?: string;
        postgres_password?: string;
    };

    type InfraStatusResponse = {
        system_state?: {
            active_db: string;
            degraded: boolean;
            db_warning?: string;
        };
        services?: {
            postgres?: {
                omniwisp_container: string;
                port: number;
                suggested?: {
                    user?: string;
                    db?: string;
                    password?: string;
                };
                conflict?: boolean;
                [key: string]: any;
            };
            redict?: {
                omniwisp_container: string;
                port: number;
                conflict?: boolean;
                [key: string]: any;
            };
        };
    };

    let sysConfig = $state<any>({
        db_provider: "sqlite",
        postgres_host: "",
        postgres_port: 5432,
        postgres_db: "umanager",
        postgres_user: "postgres",
        postgres_password: "",
        cache_provider: "memory",
        redict_password: "",
        redict_db: 0,
        livekit_url: "ws://localhost:7880",
        livekit_api_key: "",
        livekit_api_secret: ""
    });
    let sysStatus = $state<any>(null);
    let sysLoading = $state(true);
    let sysSaving = $state(false);

    let dbTesting = $state(false);
    let cacheTesting = $state(false);

    // Docker Infra
    let infraStatus = $state<InfraStatusResponse | null>(null);
    let infraLoading = $state(true);
    let infraDeploying = $state(false);
    let infraDeployResult = $state<DeployResult | null>(null);

    let infraDeployActions = $state<DeployActions>({ postgres: 'skip', redict: 'skip' });
    let infraAdvanced = $state<Record<string, AdvancedConfig>>({ 
        postgres: { env: {}, network: 'bridge', port: 5432 }, 
        redict: { env: {}, network: 'bridge', port: 6379 } 
    });
    let lastGeneratedPostgresPassword = $state("");

    async function loadSystemSettings() {
        try {
            sysStatus = await getSystemServicesStatus();
            sysConfig.db_provider = sysStatus.db?.backend || 'sqlite';
            sysConfig.cache_provider = sysStatus.cache?.backend || 'memory';

            const srv = await getSystemServices();
            if (srv.db) {
                if (srv.db.provider) sysConfig.db_provider = srv.db.provider;
                if (srv.db.host) sysConfig.postgres_host = srv.db.host;
                if (srv.db.port) sysConfig.postgres_port = srv.db.port;
                if (srv.db.database) sysConfig.postgres_db = srv.db.database;
                if (srv.db.user) sysConfig.postgres_user = srv.db.user;
                if (srv.db.password) sysConfig.postgres_password = srv.db.password;
            }
            if (srv.cache) {
                if (srv.cache.provider) sysConfig.cache_provider = srv.cache.provider;
                if (srv.cache.host) sysConfig.redict_host = srv.cache.host;
                if (srv.cache.port) sysConfig.redict_port = srv.cache.port;
                if (srv.cache.db !== undefined) sysConfig.redict_db = srv.cache.db;
                if (srv.cache.password) sysConfig.redict_password = srv.cache.password;
            }
            if (srv.livekit) {
                if (srv.livekit.url) sysConfig.livekit_url = srv.livekit.url;
                if (srv.livekit.api_key) sysConfig.livekit_api_key = srv.livekit.api_key;
                if (srv.livekit.api_secret) sysConfig.livekit_api_secret = srv.livekit.api_secret;
            }
        } catch {
            notify.error("Error al cargar config del sistema");
        } finally {
            sysLoading = false;
        }
    }

    async function saveSystemSettings() {
        sysSaving = true;
        try {
            const data = {
                db: sysConfig.db_provider === 'sqlite' ? { provider: 'sqlite' } : {
                    provider: 'postgres',
                    host: sysConfig.postgres_host,
                    port: sysConfig.postgres_port,
                    user: sysConfig.postgres_user,
                    password: sysConfig.postgres_password,
                    database: sysConfig.postgres_db
                },
                cache: sysConfig.cache_provider === 'memory' ? { provider: 'memory' } : {
                    provider: 'redict',
                    host: sysConfig.redict_host,
                    port: sysConfig.redict_port,
                    db: sysConfig.redict_db,
                    password: sysConfig.redict_password
                },
                livekit: {
                    url: sysConfig.livekit_url,
                    api_key: sysConfig.livekit_api_key,
                    api_secret: sysConfig.livekit_api_secret
                }
            };
            const res = await updateSystemServices(data);
            notify.success(res.message);
            await loadInfraStatus(); // Refresh both UI statuses
            await loadSystemSettings();
        } catch(e: any) {
            notify.error("Error al guardar config del sistema: " + (e?.response?.data?.detail || e.message));
        } finally {
            sysSaving = false;
        }
    }

    async function testDbConnection() {
        dbTesting = true;
        try {
            const data: any = { provider: sysConfig.db_provider };
            if (data.provider === 'postgres') {
                data.host = sysConfig.postgres_host;
                data.port = sysConfig.postgres_port;
                data.user = sysConfig.postgres_user;
                data.password = sysConfig.postgres_password;
                data.database = sysConfig.postgres_db;
            }
            const res = await testServiceConnection(data);
            if (res.ok) notify.success(`✅ Conexión OK (${res.latency_ms}ms)`);
            else notify.error(`❌ Fallo: ${res.error}`);
        } catch (e: any) {
            notify.error("Error en test de BD");
        } finally {
            dbTesting = false;
        }
    }

    async function testCacheConnection() {
        cacheTesting = true;
        try {
            const data: any = { provider: sysConfig.cache_provider };
            if (data.provider === 'redict') {
                data.host = sysConfig.redict_host;
                data.port = sysConfig.redict_port;
                data.db = sysConfig.redict_db;
                data.password = sysConfig.redict_password;
            }
            const res = await testServiceConnection(data);
            if (res.ok) notify.success(`✅ Conexión OK (${res.latency_ms}ms)`);
            else notify.error(`❌ Fallo: ${res.error}`);
        } catch (e: any) {
            notify.error("Error en test de Caché");
        } finally {
            cacheTesting = false;
        }
    }

    async function loadInfraStatus() {
        infraLoading = true;
        try {
            infraStatus = await getInfraStatus();
            // Auto-seleccionar "reuse" si hay conflicto detectado
            if (infraStatus?.services?.postgres?.conflict) {
                infraDeployActions.postgres = 'reuse';
            }
            if (infraStatus?.services?.redict?.conflict) {
                infraDeployActions.redict = 'reuse';
            }
        } catch {
            notify.error("No se pudo cargar el estado de la infraestructura.");
        } finally {
            infraLoading = false;
        }
    }

    // Funciones de autocompletado
    function fillPostgresLocal() {
        if (!infraStatus?.services?.postgres || infraStatus.services.postgres.omniwisp_container !== 'running') {
            notify.warning("El contenedor local no está corriendo.");
            return;
        }
        sysConfig.postgres_host = 'localhost';
        sysConfig.postgres_port = infraStatus.services.postgres.port;
        // El backend nos da la sugerencia en infraStatus si ya está corriendo o en el deploy result
        const suggested = infraStatus.services.postgres.suggested || {};
        sysConfig.postgres_user = suggested.user || 'umanager';
        sysConfig.postgres_db = suggested.db || 'umanager_db';
        if (suggested.password) {
            sysConfig.postgres_password = suggested.password;
        } else if (lastGeneratedPostgresPassword) {
            sysConfig.postgres_password = lastGeneratedPostgresPassword;
        }
        notify.info("Datos de Postgres local cargados.");
    }

    function fillRedictLocal() {
        if (!infraStatus?.services?.redict || infraStatus.services.redict.omniwisp_container !== 'running') {
            notify.warning("El servicio local no está activo.");
            return;
        }
        sysConfig.redict_host = 'localhost';
        sysConfig.redict_port = infraStatus.services.redict.port;
        sysConfig.redict_db = 0;
        notify.info("Datos de Redict local cargados.");
    }

    async function onDeployInfra() {
        infraDeploying = true;
        infraDeployResult = null;
        try {
            const res = await deployInfraStack({
                postgres_password: sysConfig.postgres_password || undefined,
                postgres_user: sysConfig.postgres_user || 'umanager',
                postgres_db: sysConfig.postgres_db || 'umanager_db',
                actions: infraDeployActions,
                advanced: infraAdvanced
            });
            infraDeployResult = res;
            notify.success(res.message || "Acciones completadas.");

            // Si el despliegue devolvió una contraseña, sugerirla para el formulario
            if (res.postgres_password) {
                lastGeneratedPostgresPassword = res.postgres_password;
                sysConfig.postgres_password = res.postgres_password;
                notify.info("Se ha sugerido la contraseña generada en el formulario.");
            }

            await loadInfraStatus();
        } catch (err: any) {
            notify.error("Falló el despliegue: " + (err?.response?.data?.detail || err.message || "Error desconocido"));
        } finally {
            infraDeploying = false;
        }
    }

    onMount(async () => {
        await Promise.all([loadSystemSettings(), loadInfraStatus()]);
    });
</script>

<div class="space-y-6">
    <div class="grid grid-cols-1 xl:grid-cols-2 gap-6">
        
        <!-- TARJETA POSTGRESQL -->
        <div class="card bg-base-100 shadow-xl border border-base-200">
            <div class="card-body">
                <div class="flex justify-between items-center border-b border-base-200 pb-2 mb-4">
                    <h2 class="card-title text-2xl flex items-center gap-2">🐘  PostgreSQL</h2>
                    <div class="badge {sysStatus?.db?.online ? 'badge-success' : 'badge-error'}">{sysStatus?.db?.online ? 'Conectado' : 'Desconectado'}</div>
                </div>

                <!-- Estado real de BD activa -->
                {#if infraStatus?.system_state}
                    <div class="alert {infraStatus.system_state.active_db === 'postgres' ? 'alert-success' : (infraStatus.system_state.degraded ? 'alert-error' : 'alert-info')} py-2 mb-3 text-sm">
                        <span>{infraStatus.system_state.active_db === 'postgres' ? '🐘' : '📁'}</span>
                        <span>
                            <strong>Motor activo: {infraStatus.system_state.active_db.toUpperCase()}</strong>
                            {#if infraStatus.system_state.db_warning}
                                &nbsp;— {infraStatus.system_state.db_warning}
                            {/if}
                        </span>
                    </div>
                {/if}

                <div class="flex flex-col gap-1 mb-6">
                    <label class="px-1" for="db_prov">
                        <span class="text-sm font-semibold opacity-70">Modo de Operación</span>
                    </label>
                    <select id="db_prov" class="select select-bordered w-full" bind:value={sysConfig.db_provider}>
                        <option value="sqlite">Local (SQLite) - Sin contenedor</option>
                        <option value="postgres">Docker (PostgreSQL) - Recomendado</option>
                    </select>
                </div>

                {#if sysConfig.db_provider === 'postgres'}
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4">
                        <div class="flex flex-col gap-1">
                            <label class="px-1" for="db_name">
                                <span class="text-sm font-semibold opacity-70">Base de Datos</span>
                            </label>
                            <input id="db_name" type="text" class="input input-bordered input-sm w-full" bind:value={sysConfig.postgres_db} />
                        </div>
                        <div class="flex flex-col gap-1">
                            <label class="px-1" for="db_user">
                                <span class="text-sm font-semibold opacity-70">Usuario</span>
                            </label>
                            <input id="db_user" type="text" class="input input-bordered input-sm w-full" bind:value={sysConfig.postgres_user} />
                        </div>
                        <div class="flex flex-col gap-1 md:col-span-2">
                            <label class="px-1" for="db_pass">
                                <span class="text-sm font-semibold opacity-70">Contraseña</span>
                            </label>
                            <input id="db_pass" type="text" class="input input-bordered input-sm w-full font-mono" bind:value={sysConfig.postgres_password} placeholder="Mínimo 8 caracteres" />
                        </div>
                    </div>

                    <ServiceControlCard 
                        title="PostgreSQL"
                        serviceKey="postgres"
                        status={infraStatus?.services?.postgres}
                        testing={dbTesting}
                        onTest={testDbConnection}
                        onAction={(act: any, adv: any) => {
                            // Limpiar acciones previas para asegurar aislamiento total
                            infraDeployActions.postgres = 'skip';
                            infraDeployActions.redict = 'skip';
                            
                            infraDeployActions.postgres = act;
                            infraAdvanced.postgres = adv;

                            if (act === 'create') {
                                saveSystemSettings().then(onDeployInfra);
                            } else {
                                onDeployInfra();
                            }
                        }}
                    />
                {:else}
                    <div class="p-6 mt-4 bg-blue-500/5 border border-dashed border-blue-500/30 rounded-2xl flex flex-col items-center gap-3 text-center">
                        <span class="text-4xl text-blue-500">📁</span>
                        <p class="text-sm">SQLite está activo.<br>Los datos se guardan en <code>data/db/inventory.sqlite</code>.</p>
                        <button class="btn btn-sm btn-primary mt-2" onclick={async () => { await saveSystemSettings(); }}>💾 Confirmar Modo Local</button>
                    </div>
                {/if}
            </div>
        </div>

        <!-- TARJETA REDICT & LIVEKIT -->
        <div class="space-y-6">
            <!-- Redict / Redis -->
            <div class="card bg-base-100 shadow-xl border border-base-200">
                <div class="card-body">
                    <div class="flex justify-between items-center border-b border-base-200 pb-2 mb-4">
                        <h2 class="card-title text-xl flex items-center gap-2">⚡ Caché (Redict)</h2>
                        <div class="badge {sysStatus?.cache?.online ? 'badge-success' : 'badge-error'}">{sysStatus?.cache?.online ? 'Online' : 'Offline'}</div>
                    </div>

                    <div class="flex flex-col gap-1 mb-4">
                        <label class="px-1" for="cache_prov_select">
                            <span class="text-sm font-semibold opacity-70">Proveedor de Caché</span>
                        </label>
                        <select id="cache_prov_select" class="select select-bordered select-sm w-full" bind:value={sysConfig.cache_provider}>
                            <option value="memory">Local RAM (Volátil)</option>
                            <option value="redict">Docker Redict (Persistente)</option>
                        </select>
                    </div>

                    {#if sysConfig.cache_provider === 'redict'}
                        <div class="flex flex-col gap-1">
                            <label class="px-1" for="c_pass">
                                <span class="text-sm font-semibold opacity-70">Contraseña</span>
                            </label>
                            <input id="c_pass" type="text" class="input input-bordered input-sm w-full" bind:value={sysConfig.redict_password} />
                        </div>

                        <ServiceControlCard 
                            title="Redict"
                            serviceKey="redict"
                            status={infraStatus?.services?.redict}
                            testing={cacheTesting}
                            onTest={testCacheConnection}
                            onAction={(act: any, adv: any) => {
                                // Limpiar acciones previas para asegurar aislamiento total
                                infraDeployActions.postgres = 'skip';
                                infraDeployActions.redict = 'skip';

                                infraDeployActions.redict = act;
                                infraAdvanced.redict = adv;

                                if (act === 'create') {
                                    saveSystemSettings().then(onDeployInfra);
                                } else {
                                    onDeployInfra();
                                }
                            }}
                        />
                    {:else}
                        <button class="btn btn-sm btn-primary w-full" onclick={saveSystemSettings}>💾 Guardar Configuración</button>
                    {/if}
                </div>
            </div>

            <!-- LiveKit -->
            <div class="card bg-base-100 shadow-xl border border-base-200">
                <div class="card-body">
                     <h2 class="card-title text-xl flex items-center gap-2 border-b border-base-200 pb-2 mb-4">🎥 Servidor LiveKit</h2>
                      <div class="flex flex-col gap-4">
                        <div class="flex flex-col gap-1">
                            <label class="px-1" for="lk_url_inp"><span class="text-sm font-semibold opacity-70">Dsn / Url</span></label>
                            <input id="lk_url_inp" type="text" class="input input-bordered input-sm w-full" bind:value={sysConfig.livekit_url} placeholder="wss://mi-livekit.com" />
                        </div>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div class="flex flex-col gap-1">
                                <label class="px-1" for="lk_key_inp"><span class="text-sm font-semibold opacity-70">API Key</span></label>
                                <input id="lk_key_inp" type="text" class="input input-bordered input-sm w-full" bind:value={sysConfig.livekit_api_key} placeholder="AK..." />
                            </div>
                            <div class="flex flex-col gap-1">
                                <label class="px-1" for="lk_secret_inp"><span class="text-sm font-semibold opacity-70">API Secret</span></label>
                                <input id="lk_secret_inp" type="password" class="input input-bordered input-sm w-full" bind:value={sysConfig.livekit_api_secret} placeholder="🔒 Secret" />
                            </div>
                        </div>
                        <div class="pt-2">
                            <button class="btn btn-sm btn-primary w-full md:w-auto px-8" onclick={saveSystemSettings}>💾 Aplicar LiveKit</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>

    </div>
</div>

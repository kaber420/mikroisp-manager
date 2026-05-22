<script lang="ts">
    import axios from "axios";
    import { goto } from "$app/navigation";
    import { onMount } from "svelte";

    // Setup steps state
    let currentStep = $state(1);
    let errorMsg = $state("");
    let successMsg = $state("");
    let loading = $state(false);

    // Step 1: Inspection states
    let dockerAvailable = $state(false);
    let checkingStatus = $state(false);
    let pgConflict = $state<any>(null);
    let redictConflict = $state<any>(null);
    let systemState = $state<any>({ active_db: "sqlite", active_cache: "memory", degraded: false });

    // Step 2: Config Selector
    let deployMode = $state<"sqlite" | "docker">("docker");
    let pgUser = $state("umanager");
    let pgDb = $state("umanager_db");
    let pgPassword = $state("");
    let showPassword = $state(false);
    
    // Live Terminal Log streaming
    let consoleLogs = $state<string[]>([]);
    let socketPg: WebSocket | null = null;
    let socketRd: WebSocket | null = null;
    let isDeploying = $state(false);

    // Step 3: Admin Creator
    let username = $state("");
    let email = $state("");
    let password = $state("");
    let passwordConfirm = $state("");

    onMount(() => {
        checkSystemStatus();
    });

    async function checkSystemStatus() {
        checkingStatus = true;
        errorMsg = "";
        try {
            const res = await axios.get("/api/setup/status");
            const data = res.data;
            if (data.status === "success") {
                dockerAvailable = true;
                pgConflict = data.services.postgres.conflict;
                redictConflict = data.services.redict.conflict;
                systemState = data.system_state;
            } else {
                dockerAvailable = false;
                errorMsg = data.message || "Docker no está disponible en este servidor.";
            }
        } catch (err: any) {
            dockerAvailable = false;
            errorMsg = err.response?.data?.detail || "No se pudo conectar al servicio Docker del Host.";
        } finally {
            checkingStatus = false;
        }
    }

    function generateSecurePassword() {
        const chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+~|}{[]:;?><,./-=";
        let pass = "";
        for (let i = 0; i < 20; i++) {
            pass += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        pgPassword = pass;
        showPassword = true;
    }

    function startLogStreaming() {
        consoleLogs = ["[SISTEMA] Iniciando transmisión de logs de Docker..."];
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const host = window.location.host;

        // Conectar logs de Postgres
        socketPg = new WebSocket(`${protocol}//${host}/ws/setup/logs/omniwisp_postgres`);
        socketPg.onmessage = (event) => {
            consoleLogs = [...consoleLogs, `[POSTGRESQL] ${event.data.trim()}`];
        };
        socketPg.onerror = () => {
            consoleLogs = [...consoleLogs, "[POSTGRESQL] [ERROR] Falló la conexión de logs."];
        };

        // Conectar logs de Redict
        socketRd = new WebSocket(`${protocol}//${host}/ws/setup/logs/omniwisp_redict`);
        socketRd.onmessage = (event) => {
            consoleLogs = [...consoleLogs, `[REDICT] ${event.data.trim()}`];
        };
        socketRd.onerror = () => {
            consoleLogs = [...consoleLogs, "[REDICT] [ERROR] Falló la conexión de logs."];
        };
    }

    function stopLogStreaming() {
        if (socketPg) socketPg.close();
        if (socketRd) socketRd.close();
    }

    async function handleDeployInfra() {
        loading = true;
        isDeploying = true;
        errorMsg = "";
        successMsg = "";
        consoleLogs = [];

        if (deployMode === "docker") {
            if (!pgPassword) {
                generateSecurePassword();
            }
            startLogStreaming();

            try {
                const res = await axios.post("/api/setup/deploy-infra", {
                    postgres_user: pgUser,
                    postgres_db: pgDb,
                    postgres_password: pgPassword,
                    actions: {
                        postgres: "create",
                        redict: "create"
                    }
                });

                if (res.data.status === "success") {
                    successMsg = "¡Infraestructura Docker Postgres + Redict desplegada con éxito!";
                    consoleLogs = [...consoleLogs, "[SISTEMA] Despliegue de producción completo y sincronizado."];
                    setTimeout(() => {
                        currentStep = 3;
                    }, 1500);
                } else {
                    errorMsg = res.data.message || "Error al desplegar la pila.";
                }
            } catch (err: any) {
                errorMsg = err.response?.data?.detail || "Error fatal de conexión al desplegar contenedores.";
            } finally {
                loading = false;
                isDeploying = false;
                stopLogStreaming();
            }
        } else {
            // SQLite Local Setup
            try {
                consoleLogs = ["[SISTEMA] Configurando almacenamiento local SQLite y caché en memoria..."];
                const res = await axios.post("/api/setup/deploy-infra", {
                    actions: {
                        postgres: "delete",
                        redict: "delete"
                    }
                });

                if (res.data.status === "success") {
                    successMsg = "Almacenamiento SQLite configurado con éxito.";
                    setTimeout(() => {
                        currentStep = 3;
                    }, 1000);
                }
            } catch (err: any) {
                errorMsg = err.response?.data?.detail || "Error al configurar base SQLite.";
            } finally {
                loading = false;
                isDeploying = false;
            }
        }
    }

    async function handleCreateAdmin(e: Event) {
        e.preventDefault();
        loading = true;
        errorMsg = "";
        successMsg = "";

        if (password !== passwordConfirm) {
            errorMsg = "Las contraseñas de administrador no coinciden.";
            loading = false;
            return;
        }

        if (password.length < 6) {
            errorMsg = "La contraseña de administrador debe tener al menos 6 caracteres.";
            loading = false;
            return;
        }

        try {
            const res = await axios.post("/api/setup", {
                username,
                email,
                password
            });

            if (res.status === 200 || res.status === 201) {
                successMsg = "¡Usuario administrador bootstrap creado con éxito!";
                currentStep = 4;
                
                // Redirección al login/dashboard después de 3 segundos
                setTimeout(() => {
                    goto("/login?setup=success");
                }, 3000);
            } else {
                errorMsg = res.data?.detail || "Error al crear administrador.";
            }
        } catch (err: any) {
            errorMsg = err.response?.data?.detail || "Fallo de conexión al crear administrador.";
        } finally {
            loading = false;
        }
    }
</script>

<svelte:head>
    <title>Asistente de Configuración Inicial — OmniWISP</title>
</svelte:head>

<div class="min-h-screen bg-gradient-to-tr from-slate-950 via-slate-900 to-indigo-950 flex flex-col items-center justify-center p-6 text-slate-100 font-sans">
    
    <!-- Premium Header -->
    <div class="flex flex-col items-center mb-8 text-center animate-fade-in">
        <div class="w-16 h-16 rounded-2xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center shadow-lg shadow-indigo-500/10 mb-4 animate-pulse">
            <svg class="h-10 w-10 text-indigo-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z" />
            </svg>
        </div>
        <h1 class="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-indigo-200 via-slate-200 to-indigo-200 bg-clip-text text-transparent">
            OmniWISP
        </h1>
        <p class="text-indigo-300/60 text-sm mt-1">
            Asistente de Instalación y Despliegue de Infraestructura
        </p>
    </div>

    <!-- Container Card (Glassmorphism) -->
    <div class="w-full max-w-3xl bg-slate-900/60 backdrop-blur-xl border border-slate-800 rounded-3xl p-8 shadow-2xl flex flex-col gap-8 transition-all duration-300">
        
        <!-- Premium DaisyUI Stepper -->
        <ul class="steps steps-vertical sm:steps-horizontal w-full text-xs font-semibold select-none border-b border-slate-800/50 pb-6">
            <li class="step {currentStep >= 1 ? 'step-primary text-indigo-400' : 'text-slate-500'}">Bienvenida e Inspección</li>
            <li class="step {currentStep >= 2 ? 'step-primary text-indigo-400' : 'text-slate-500'}">Infraestructura</li>
            <li class="step {currentStep >= 3 ? 'step-primary text-indigo-400' : 'text-slate-500'}">Cuenta Admin</li>
            <li class="step {currentStep >= 4 ? 'step-primary text-indigo-400' : 'text-slate-500'}">¡Completado!</li>
        </ul>

        <!-- Alerts -->
        {#if errorMsg}
            <div class="alert alert-error bg-red-950/40 border-red-500/30 text-red-300 rounded-2xl flex items-start gap-3 text-sm shadow-md animate-shake">
                <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6 text-red-400 mt-0.5" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                <div class="flex-1">
                    <span class="font-bold">Error encontrado</span>
                    <p class="text-xs text-red-300/80 mt-0.5">{errorMsg}</p>
                </div>
            </div>
        {/if}

        {#if successMsg}
            <div class="alert alert-success bg-emerald-950/40 border-emerald-500/30 text-emerald-300 rounded-2xl flex items-start gap-3 text-sm shadow-md animate-fade-in">
                <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6 text-emerald-400 mt-0.5" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                <div>
                    <span class="font-bold">Operación Exitosa</span>
                    <p class="text-xs text-emerald-300/80 mt-0.5">{successMsg}</p>
                </div>
            </div>
        {/if}

        <!-- STEP 1: WELCOME & DIAGNOSTICS -->
        {#if currentStep === 1}
            <div class="space-y-6 animate-fade-in">
                <div class="space-y-2">
                    <h2 class="text-xl font-bold text-slate-100">Paso 1: Diagnóstico de Servidor y Entorno</h2>
                    <p class="text-slate-400 text-sm">
                        OmniWISP está listo para inicializarse. A continuación, revisamos si cuentas con los requisitos del servidor.
                    </p>
                </div>

                <!-- Inspection Panel -->
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <!-- Docker Daemon Status -->
                    <div class="bg-slate-950/50 border border-slate-800/80 rounded-2xl p-5 flex flex-col justify-between h-36">
                        <div class="flex items-center justify-between">
                            <span class="text-xs text-slate-400 uppercase font-semibold">Demonio Docker</span>
                            <span class="indicator-item badge {dockerAvailable ? 'badge-success' : 'badge-error'} badge-xs"></span>
                        </div>
                        <div class="mt-2">
                            <p class="text-lg font-bold">{dockerAvailable ? "Disponible" : "Apagado"}</p>
                            <p class="text-xs text-slate-500 mt-1">{dockerAvailable ? "Motor Docker listo para desplegar" : "No se detecta Docker local"}</p>
                        </div>
                    </div>

                    <!-- Postgres Port Check -->
                    <div class="bg-slate-950/50 border border-slate-800/80 rounded-2xl p-5 flex flex-col justify-between h-36">
                        <div class="flex items-center justify-between">
                            <span class="text-xs text-slate-400 uppercase font-semibold">Puerto Postgres (5432)</span>
                            <span class="indicator-item badge {pgConflict ? 'badge-warning' : 'badge-success'} badge-xs"></span>
                        </div>
                        <div class="mt-2">
                            <p class="text-lg font-bold">{pgConflict ? "Ocupado" : "Libre"}</p>
                            <p class="text-xs text-slate-500 mt-1">{pgConflict ? `Conflicto con: ${pgConflict.name}` : "Puerto listo para recibir base de datos"}</p>
                        </div>
                    </div>

                    <!-- Redict Port Check -->
                    <div class="bg-slate-950/50 border border-slate-800/80 rounded-2xl p-5 flex flex-col justify-between h-36">
                        <div class="flex items-center justify-between">
                            <span class="text-xs text-slate-400 uppercase font-semibold">Puerto Redict (6379)</span>
                            <span class="indicator-item badge {redictConflict ? 'badge-warning' : 'badge-success'} badge-xs"></span>
                        </div>
                        <div class="mt-2">
                            <p class="text-lg font-bold">{redictConflict ? "Ocupado" : "Libre"}</p>
                            <p class="text-xs text-slate-500 mt-1">{redictConflict ? `Conflicto con: ${redictConflict.name}` : "Puerto listo para recibir caché"}</p>
                        </div>
                    </div>
                </div>

                <!-- Guidance Info Box -->
                {#if !dockerAvailable}
                    <div class="bg-amber-950/20 border border-amber-500/20 text-amber-300 rounded-2xl p-4 text-xs leading-relaxed">
                        ⚠️ **Nota:** Al no disponer del servicio Docker de producción, la configuración de infraestructura de base de datos Postgres y caché Redict se deshabilitará. Podrás configurar OmniWISP utilizando SQLite local sin problemas.
                    </div>
                {/if}

                <!-- Actions -->
                <div class="flex justify-between items-center pt-4 border-t border-slate-800/50 mt-6">
                    <button class="btn btn-ghost text-slate-400 hover:text-slate-200" onclick={checkSystemStatus} disabled={checkingStatus}>
                        {checkingStatus ? "Analizando..." : "Re-Inspeccionar"}
                    </button>
                    <button class="btn btn-primary bg-indigo-600 hover:bg-indigo-700 border-none shadow-md shadow-indigo-600/20 px-8" onclick={() => currentStep = 2}>
                        Siguiente Paso
                    </button>
                </div>
            </div>
        {/if}

        <!-- STEP 2: INFRASTRUCTURE CONFIG & SELECTOR -->
        {#if currentStep === 2}
            <div class="space-y-6 animate-fade-in">
                <div class="space-y-2">
                    <h2 class="text-xl font-bold text-slate-100">Paso 2: Selección y Despliegue de Infraestructura</h2>
                    <p class="text-slate-400 text-sm">
                        Elige cómo deseas que OmniWISP almacene tus datos y gestione el caché del sistema.
                    </p>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <!-- Option A: SQLite (Local & Fast) -->
                    <div class="card border-2 cursor-pointer transition-all duration-200 p-6 flex flex-col justify-between h-64 bg-slate-950/40 hover:bg-slate-950/60 {deployMode === 'sqlite' ? 'border-indigo-500/80 shadow-md shadow-indigo-500/10' : 'border-slate-800'}" onclick={() => deployMode = "sqlite"}>
                        <div>
                            <div class="flex items-center justify-between mb-4">
                                <h3 class="text-lg font-bold text-slate-100">Instalación Simple (SQLite)</h3>
                                <input type="radio" name="deployMode" class="radio radio-primary" checked={deployMode === "sqlite"} />
                            </div>
                            <p class="text-xs text-slate-400 leading-relaxed">
                                Ideal para desarrollo, pruebas, o servidores con recursos mínimos. Ejecuta una base de datos local basada en archivos SQLite y utiliza almacenamiento en caché interno de memoria.
                            </p>
                        </div>
                        <span class="badge badge-neutral text-xs py-2 px-3 border border-slate-800 bg-slate-900/60">Cero dependencias</span>
                    </div>

                    <!-- Option B: Docker PostgreSQL + Redict (Scale/Production) -->
                    <div class="card border-2 cursor-pointer transition-all duration-200 p-6 flex flex-col justify-between h-64 bg-slate-950/40 hover:bg-slate-950/60 {!dockerAvailable ? 'opacity-40 cursor-not-allowed' : ''} {deployMode === 'docker' ? 'border-indigo-500/80 shadow-md shadow-indigo-500/10' : 'border-slate-800'}" onclick={() => { if (dockerAvailable) deployMode = 'docker'; }}>
                        <div>
                            <div class="flex items-center justify-between mb-4">
                                <h3 class="text-lg font-bold text-slate-100">Pila de Producción (Docker)</h3>
                                <input type="radio" name="deployMode" class="radio radio-primary" checked={deployMode === "docker"} disabled={!dockerAvailable} />
                            </div>
                            <p class="text-xs text-slate-400 leading-relaxed">
                                Despliega automáticamente contenedores Docker dedicados para PostgreSQL (Base de datos robusta y relacional) y Redict (Caché optimizado en memoria y mensajería en vivo).
                            </p>
                        </div>
                        <span class="badge badge-primary text-xs py-2 px-3 border-none bg-indigo-600/30 text-indigo-300">Recomendado para Producción</span>
                    </div>
                </div>

                <!-- PostgreSQL & Redict Config Drawer (only if docker mode) -->
                {#if deployMode === "docker"}
                    <div class="bg-slate-950/60 border border-slate-800/80 rounded-2xl p-6 space-y-4 animate-fade-in">
                        <h4 class="text-sm font-bold text-indigo-300/80 uppercase tracking-wider mb-2">Credenciales de Base de Datos PostgreSQL</h4>
                        
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label for="pgUser" class="block text-xs font-semibold uppercase text-slate-400 mb-1">Usuario</label>
                                <input id="pgUser" type="text" bind:value={pgUser} class="input input-bordered w-full text-sm bg-slate-900 border-slate-800 text-slate-200 rounded-xl" />
                            </div>
                            <div>
                                <label for="pgDb" class="block text-xs font-semibold uppercase text-slate-400 mb-1">Base de Datos</label>
                                <input id="pgDb" type="text" bind:value={pgDb} class="input input-bordered w-full text-sm bg-slate-900 border-slate-800 text-slate-200 rounded-xl" />
                            </div>
                        </div>

                        <div>
                            <label for="pgPassword" class="block text-xs font-semibold uppercase text-slate-400 mb-1">Contraseña</label>
                            <div class="relative">
                                <input 
                                    id="pgPassword" 
                                    type={showPassword ? "text" : "password"} 
                                    bind:value={pgPassword} 
                                    placeholder="Dejar vacío para autogenerar contraseña fuerte"
                                    class="input input-bordered w-full text-sm bg-slate-900 border-slate-800 text-slate-200 pr-32 rounded-xl" 
                                />
                                <button type="button" class="absolute right-2 top-2 btn btn-xs btn-neutral text-xs rounded-lg" onclick={generateSecurePassword}>
                                    Autogenerar
                                </button>
                            </div>
                        </div>
                    </div>
                {/if}

                <!-- Logging Console Panel -->
                {#if isDeploying || consoleLogs.length > 0}
                    <div class="space-y-2 animate-fade-in">
                        <h4 class="text-sm font-bold text-slate-400">Terminal de Logs de Despliegue (En Vivo)</h4>
                        <div class="h-48 overflow-y-auto bg-black/90 border border-slate-800 rounded-xl p-4 font-mono text-xs text-green-400/90 leading-relaxed shadow-inner">
                            {#each consoleLogs as log}
                                <div class="break-all whitespace-pre-wrap">{log}</div>
                            {/each}
                        </div>
                    </div>
                {/if}

                <!-- Actions -->
                <div class="flex justify-between items-center pt-4 border-t border-slate-800/50 mt-6">
                    <button class="btn btn-ghost text-slate-400 hover:text-slate-200" onclick={() => currentStep = 1} disabled={loading}>
                        Atrás
                    </button>
                    <button class="btn btn-primary bg-indigo-600 hover:bg-indigo-700 border-none shadow-md shadow-indigo-600/20 px-8" onclick={handleDeployInfra} disabled={loading}>
                        {loading ? "Desplegando..." : "Desplegar Stack"}
                    </button>
                </div>
            </div>
        {/if}

        <!-- STEP 3: CREATE ADMIN USER -->
        {#if currentStep === 3}
            <div class="space-y-6 animate-fade-in">
                <div class="space-y-2">
                    <h2 class="text-xl font-bold text-slate-100">Paso 3: Creación de la Cuenta Administrador</h2>
                    <p class="text-slate-400 text-sm">
                        Tu infraestructura está activa. Crea el primer usuario administrador para gestionar el sistema.
                    </p>
                </div>

                <form class="space-y-4" onsubmit={handleCreateAdmin}>
                    <div>
                        <label for="username" class="block text-xs font-semibold uppercase text-slate-400 mb-1">Nombre de Usuario</label>
                        <input id="username" type="text" bind:value={username} required placeholder="ej. administrador" class="input input-bordered w-full text-sm bg-slate-900 border-slate-800 text-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:outline-none transition-all" />
                    </div>

                    <div>
                        <label for="email" class="block text-xs font-semibold uppercase text-slate-400 mb-1">Correo Electrónico</label>
                        <input id="email" type="email" bind:value={email} required placeholder="admin@example.com" class="input input-bordered w-full text-sm bg-slate-900 border-slate-800 text-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:outline-none transition-all" />
                    </div>

                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label for="password" class="block text-xs font-semibold uppercase text-slate-400 mb-1">Contraseña</label>
                            <input id="password" type="password" bind:value={password} required minlength="6" placeholder="••••••••" class="input input-bordered w-full text-sm bg-slate-900 border-slate-800 text-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:outline-none transition-all" />
                        </div>
                        <div>
                            <label for="passwordConfirm" class="block text-xs font-semibold uppercase text-slate-400 mb-1">Confirmar Contraseña</label>
                            <input id="passwordConfirm" type="password" bind:value={passwordConfirm} required minlength="6" placeholder="••••••••" class="input input-bordered w-full text-sm bg-slate-900 border-slate-800 text-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:outline-none transition-all" />
                        </div>
                    </div>

                    <!-- Form Actions -->
                    <div class="flex justify-between items-center pt-6 border-t border-slate-800/50 mt-6">
                        <span class="text-xs text-slate-500">
                            🔒 Los endpoints de configuración se bloquearán al concluir este paso.
                        </span>
                        <button type="submit" class="btn btn-primary bg-indigo-600 hover:bg-indigo-700 border-none shadow-md shadow-indigo-600/20 px-8" disabled={loading}>
                            {loading ? "Creando administrador..." : "Crear Administrador"}
                        </button>
                    </div>
                </form>
            </div>
        {/if}

        <!-- STEP 4: SUCCESS & DONE -->
        {#if currentStep === 4}
            <div class="flex flex-col items-center justify-center space-y-6 text-center py-10 animate-scale-up">
                <!-- Circular success badge with nice check icon -->
                <div class="w-20 h-20 rounded-full bg-emerald-600/10 border border-emerald-500/20 flex items-center justify-center shadow-lg shadow-emerald-500/5 mb-2 animate-bounce">
                    <svg class="h-10 w-10 text-emerald-400 animate-fade-in" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                    </svg>
                </div>

                <div class="space-y-2">
                    <h2 class="text-2xl font-bold text-slate-100">¡Configuración Completada con Éxito!</h2>
                    <p class="text-slate-400 text-sm max-w-md mx-auto leading-relaxed">
                        Tu base de datos e infraestructura se han integrado de forma consistente. OmniWISP está completamente operativo y listo para usarse.
                    </p>
                </div>

                <div class="space-y-4 w-full max-w-sm pt-4">
                    <div class="flex flex-col items-center gap-1.5">
                        <span class="loading loading-spinner loading-md text-indigo-400"></span>
                        <span class="text-xs text-slate-500">Redirigiéndote al panel de control en unos instantes...</span>
                    </div>
                </div>
            </div>
        {/if}

    </div>

    <!-- Elegant Footer -->
    <p class="text-center text-slate-600 text-xs mt-8 select-none">
        © 2026 OmniWISP. Todos los derechos reservados.
    </p>

</div>

<style>
    /* Premium visual animations definitions */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(4px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    @keyframes scaleUp {
        from { opacity: 0; transform: scale(0.96); }
        to { opacity: 1; transform: scale(1); }
    }

    @keyframes shake {
        0%, 100% { transform: translateX(0); }
        25% { transform: translateX(-4px); }
        75% { transform: translateX(4px); }
    }

    .animate-fade-in {
        animation: fadeIn 0.35s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }

    .animate-scale-up {
        animation: scaleUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }

    .animate-shake {
        animation: shake 0.25s ease-in-out;
    }
</style>

<script lang="ts">
    // Propiedades usando runas de Svelte 5
    let {
        title,
        serviceKey,
        status,
        testing = false,
        onTest,
        onAction,
    } = $props<{
        title: string;
        serviceKey: "postgres" | "redict";
        status: any;
        testing?: boolean;
        onTest: () => void;
        onAction: (action: any, advanced: any) => void;
    }>();

    // Estado del selector de acciones
    let selectedAction = $state<string>("skip");
    let showAdvanced = $state(false);

    // Configuración avanzada editable
    let customPort = $state<number>(serviceKey === "postgres" ? 5432 : 6379);
    let customNetwork = $state<string>("bridge");
    let envVarsInput = $state<string>("");

    // Sincronizar puerto predeterminado si viene en el status
    $effect(() => {
        if (status?.port) {
            customPort = status.port;
        }
        if (status?.conflict) {
            selectedAction = "reuse";
        }
    });

    const containerState = $derived(status?.omniwisp_container || "not_created");
    const containerPort = $derived(status?.port || (serviceKey === "postgres" ? 5432 : 6379));

    // Determinar badges de estado
    function getStateBadge(state: string) {
        switch (state) {
            case "running":
                return "badge-success";
            case "stopped":
                return "badge-warning";
            case "not_created":
                return "badge-ghost";
            default:
                return "badge-error";
        }
    }

    function getStateText(state: string) {
        switch (state) {
            case "running":
                return "Corriendo";
            case "stopped":
                return "Detenido";
            case "not_created":
                return "No Creado";
            default:
                return state;
        }
    }

    function triggerAction() {
        // Parsear variables de entorno (KEY=VAL)
        const env: Record<string, string> = {};
        if (envVarsInput.trim()) {
            envVarsInput.split("\n").forEach((line) => {
                const parts = line.split("=");
                if (parts.length >= 2) {
                    env[parts[0].trim()] = parts.slice(1).join("=").trim();
                }
            });
        }

        const advanced = {
            port: customPort,
            network: customNetwork,
            env,
        };

        onAction(selectedAction, advanced);
    }
</script>

<div class="mt-4 p-4 rounded-xl bg-base-200 border border-base-300 space-y-4">
    <!-- Encabezado de Estado de Docker -->
    <div class="flex items-center justify-between flex-wrap gap-2">
        <div class="flex items-center gap-2">
            <span class="text-xs font-bold uppercase opacity-60">Servicio Local (Docker)</span>
            <span class="badge {getStateBadge(containerState)} badge-xs font-semibold">
                {getStateText(containerState)}
            </span>
        </div>
        {#if containerState === "running"}
            <span class="text-xs font-mono opacity-50">Puerto: {containerPort}</span>
        {/if}
    </div>

    <!-- Alertas de Conflicto -->
    {#if status?.conflict}
        <div class="alert alert-warning text-xs py-2">
            ⚠️ Conflicto: Otro servicio está usando el puerto {containerPort} en el host.
        </div>
    {/if}

    <!-- Selector de Acciones -->
    <div class="flex flex-col gap-1.5">
        <label class="text-xs font-bold uppercase opacity-60" for="{serviceKey}-action-select">Acción a Ejecutar</label>
        <div class="flex gap-2">
            <select
                id="{serviceKey}-action-select"
                class="select select-sm select-bordered flex-1"
                bind:value={selectedAction}
            >
                <option value="skip">Saltar / No modificar</option>
                <option value="create">Crear / Levantar Contenedor</option>
                {#if status?.conflict || containerState !== "not_created"}
                    <option value="reuse">Reutilizar / Conectar Existente</option>
                {/if}
                {#if containerState !== "not_created"}
                    <option value="destroy">🔥 Destruir Contenedor</option>
                {/if}
            </select>
            <button
                class="btn btn-sm btn-primary"
                onclick={triggerAction}
                disabled={selectedAction === "skip"}
            >
                Aplicar
            </button>
        </div>
    </div>

    <!-- Ajustes Avanzados para "Crear" -->
    {#if selectedAction === "create"}
        <div class="border-t border-base-300 pt-3">
            <button
                class="btn btn-ghost btn-xs w-full justify-between"
                onclick={() => (showAdvanced = !showAdvanced)}
            >
                <span>⚙️ Ajustes Avanzados</span>
                <span>{showAdvanced ? "▲" : "▼"}</span>
            </button>

            {#if showAdvanced}
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3 p-3 bg-base-300/40 rounded-lg">
                    <div class="flex flex-col gap-1">
                        <label class="text-[10px] font-bold uppercase opacity-65" for="{serviceKey}-custom-port">Puerto en Host</label>
                        <input
                            id="{serviceKey}-custom-port"
                            type="number"
                            class="input input-bordered input-xs"
                            bind:value={customPort}
                        />
                    </div>
                    <div class="flex flex-col gap-1">
                        <label class="text-[10px] font-bold uppercase opacity-65" for="{serviceKey}-custom-net">Red Docker</label>
                        <input
                            id="{serviceKey}-custom-net"
                            type="text"
                            class="input input-bordered input-xs"
                            bind:value={customNetwork}
                        />
                    </div>
                    <div class="flex flex-col gap-1 sm:col-span-2">
                        <label class="text-[10px] font-bold uppercase opacity-65" for="{serviceKey}-env-vars">Variables de Entorno (KEY=VAL)</label>
                        <textarea
                            id="{serviceKey}-env-vars"
                            class="textarea textarea-bordered textarea-xs font-mono"
                            rows="2"
                            placeholder="MY_VAR=value"
                            bind:value={envVarsInput}
                        ></textarea>
                    </div>
                </div>
            {/if}
        </div>
    {/if}

    <!-- Botón de Test de Conexión si está corriendo -->
    {#if containerState === "running" || status?.online}
        <div class="border-t border-base-300 pt-3 flex justify-end">
            <button
                class="btn btn-outline btn-xs gap-1"
                onclick={onTest}
                disabled={testing}
            >
                {#if testing}
                    <span class="loading loading-spinner loading-xs"></span>
                {/if}
                ⚡ Probar Conexión
            </button>
        </div>
    {/if}
</div>

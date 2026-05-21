<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import { createPlan, updatePlan, getRouters } from "$lib/api";
    import type { Plan, PlanCreate, PlanUpdate } from "$lib/types/plan";
    import type { Router } from "$lib/types/router";

    export let show = false;
    export let plan: Plan | null = null; // null = Crear, objeto = Editar
    export let fixedRouterHost: string | null = null; // Bloquear a un router específico

    const dispatch = createEventDispatcher<{ saved: Plan; close: void }>();

    let routers: Router[] = [];
    let loading = false;
    let errorMsg = "";

    // --- Form state ---
    let form = getDefaultForm();

    function getDefaultForm(): PlanCreate {
        return {
            name: "",
            max_limit: "",
            price: 0,
            parent_queue: null,
            comment: null,
            router_host: fixedRouterHost ?? null,
            plan_type: "simple_queue",
            profile_name: null,
            suspension_method: "queue_limit",
            address_list_strategy: "blacklist",
            address_list_name: "morosos",
            v6_queue_type: "default-small",
            v7_queue_type: "cake-default",
        };
    }

    $: if (show) {
        errorMsg = "";
        if (plan) {
            form = {
                name: plan.name,
                max_limit: plan.max_limit,
                price: plan.price,
                parent_queue: plan.parent_queue,
                comment: plan.comment,
                router_host: plan.router_host,
                plan_type: plan.plan_type,
                profile_name: plan.profile_name,
                suspension_method: plan.suspension_method,
                address_list_strategy: plan.address_list_strategy,
                address_list_name: plan.address_list_name,
                v6_queue_type: plan.v6_queue_type,
                v7_queue_type: plan.v7_queue_type,
            };
        } else {
            form = getDefaultForm();
        }
        loadRouters();
    }

    async function loadRouters() {
        try {
            routers = await getRouters();
        } catch {
            routers = [];
        }
    }

    async function handleSubmit() {
        errorMsg = "";
        if (!form.name.trim() || !form.max_limit.trim()) {
            errorMsg = "Nombre y Max Limit son obligatorios.";
            return;
        }
        loading = true;
        try {
            let saved: Plan;
            if (plan?.id) {
                const upd: PlanUpdate = { ...form };
                saved = await updatePlan(plan.id, upd);
            } else {
                saved = await createPlan(form);
            }
            dispatch("saved", saved);
            close();
        } catch (e: any) {
            errorMsg = e?.response?.data?.detail ?? "Error al guardar el plan.";
        } finally {
            loading = false;
        }
    }

    function close() {
        dispatch("close");
    }

    const isEditing = !!plan;

    $: showAddressConfig = form.suspension_method === "address_list";
    $: showProfileName = form.plan_type === "pppoe";
</script>

{#if show}
    <!-- Modal backdrop -->
    <div class="modal modal-open z-50">
        <div class="modal-box w-11/12 max-w-2xl">
            <!-- Header -->
            <div class="flex items-center justify-between mb-4">
                <h3 class="font-bold text-lg">
                    {isEditing ? "✏️ Editar Plan" : "➕ Nuevo Plan"}
                </h3>
                <button class="btn btn-sm btn-circle btn-ghost" on:click={close}
                    >✕</button
                >
            </div>

            <!-- Error -->
            {#if errorMsg}
                <div class="alert alert-error mb-4">
                    <span>{errorMsg}</span>
                </div>
            {/if}

            <form on:submit|preventDefault={handleSubmit} class="space-y-4">
                <!-- Fila 1: Nombre + Max Limit -->
                <div class="grid grid-cols-2 gap-4">
                    <div class="form-control">
                        <label class="label" for="plan_name"
                            ><span class="label-text font-medium"
                                >Nombre del Plan *</span
                            ></label
                        >
                        <input
                            id="plan_name"
                            type="text"
                            class="input input-bordered input-sm"
                            placeholder="ej. 10 Megas"
                            bind:value={form.name}
                            required
                        />
                    </div>
                    <div class="form-control">
                        <label class="label" for="max_limit"
                            ><span class="label-text font-medium"
                                >Max Limit *</span
                            ></label
                        >
                        <input
                            id="max_limit"
                            type="text"
                            class="input input-bordered input-sm"
                            placeholder="ej. 10M/10M"
                            bind:value={form.max_limit}
                            required
                        />
                    </div>
                </div>

                <!-- Fila 2: Precio + Tipo de Plan -->
                <div class="grid grid-cols-2 gap-4">
                    <div class="form-control">
                        <label class="label" for="price"
                            ><span class="label-text font-medium"
                                >Precio ($)</span
                            ></label
                        >
                        <input
                            id="price"
                            type="number"
                            min="0"
                            step="0.01"
                            class="input input-bordered input-sm"
                            bind:value={form.price}
                        />
                    </div>
                    <div class="form-control">
                        <label class="label" for="plan_type"
                            ><span class="label-text font-medium"
                                >Tipo de Plan</span
                            ></label
                        >
                        <select
                            id="plan_type"
                            class="select select-bordered select-sm"
                            bind:value={form.plan_type}
                        >
                            <option value="simple_queue">Simple Queue</option>
                            <option value="pppoe">PPPoE</option>
                        </select>
                    </div>
                </div>

                <!-- Nombre de Perfil PPPoE (condicional) -->
                {#if showProfileName}
                    <div class="form-control">
                        <label class="label" for="profile_name"
                            ><span class="label-text font-medium"
                                >Nombre de Perfil PPPoE</span
                            ></label
                        >
                        <input
                            id="profile_name"
                            type="text"
                            class="input input-bordered input-sm"
                            placeholder="ej. 10M-profile"
                            bind:value={form.profile_name}
                        />
                    </div>
                {/if}

                <!-- Fila 3: Aplicar en (Router) -->
                <div class="form-control">
                    <label class="label" for={fixedRouterHost ? "fixed_router" : "router_host"}>
                        <span class="label-text font-medium">Aplicar en</span>
                        <span class="label-text-alt text-info"
                            >Global = aplica en todos los routers</span
                        >
                    </label>
                    {#if fixedRouterHost}
                        <!-- Router fijo (desde la vista del router) -->
                        <input
                            id="fixed_router"
                            type="text"
                            class="input input-bordered input-sm bg-base-200"
                            value={fixedRouterHost}
                            disabled
                        />
                    {:else}
                        <select
                            id="router_host"
                            class="select select-bordered select-sm"
                            bind:value={form.router_host}
                        >
                            <option value={null}>🌐 Global / Universal</option>
                            {#each routers as r}
                                <option value={r.host}
                                    >{r.hostname ?? r.host} ({r.host})</option
                                >
                            {/each}
                        </select>
                    {/if}
                </div>

                <!-- Método de Suspensión -->
                <div class="form-control">
                    <label class="label" for="suspension_method"
                        ><span class="label-text font-medium"
                            >Método de Suspensión</span
                        ></label
                    >
                    <select
                        id="suspension_method"
                        class="select select-bordered select-sm"
                        bind:value={form.suspension_method}
                    >
                        <option value="queue_limit"
                            >Throttle / Limit Queue</option
                        >
                        <option value="address_list"
                            >Lista de Direcciones</option
                        >
                        <option value="pppoe_secret_disable"
                            >Deshabilitar PPPoE Secret</option
                        >
                    </select>
                </div>

                <!-- Config Address List (condicional) -->
                {#if showAddressConfig}
                    <div
                        class="grid grid-cols-2 gap-4 p-3 bg-base-200 rounded-lg"
                    >
                        <div class="form-control">
                            <label class="label" for="address_list_strategy"
                                ><span class="label-text font-medium"
                                    >Estrategia</span
                                ></label
                            >
                            <select
                                id="address_list_strategy"
                                class="select select-bordered select-sm"
                                bind:value={form.address_list_strategy}
                            >
                                <option value="blacklist">Blacklist</option>
                                <option value="whitelist">Whitelist</option>
                            </select>
                        </div>
                        <div class="form-control">
                            <label class="label" for="address_list_name"
                                ><span class="label-text font-medium"
                                    >Nombre de Lista</span
                                ></label
                            >
                            <input
                                id="address_list_name"
                                type="text"
                                class="input input-bordered input-sm"
                                placeholder="ej. morosos"
                                bind:value={form.address_list_name}
                            />
                        </div>
                    </div>
                {/if}

                <!-- Parent Queue -->
                <div class="form-control">
                    <label class="label" for="parent_queue"
                        ><span class="label-text font-medium">Parent Queue</span
                        ></label
                    >
                    <input
                        id="parent_queue"
                        type="text"
                        class="input input-bordered input-sm"
                        placeholder="ej. ISP-Main (opcional)"
                        bind:value={form.parent_queue}
                    />
                </div>

                <!-- Comentario -->
                <div class="form-control">
                    <label class="label" for="comment"
                        ><span class="label-text font-medium">Comentario</span
                        ></label
                    >
                    <textarea
                        id="comment"
                        class="textarea textarea-bordered textarea-sm"
                        rows="2"
                        placeholder="Descripción del plan (opcional)"
                        bind:value={form.comment}
                    ></textarea>
                </div>

                <!-- Queue Types -->
                <div class="grid grid-cols-2 gap-4">
                    <div class="form-control">
                        <label class="label" for="v6_queue_type"
                            ><span class="label-text font-medium"
                                >Queue Type (RouterOS v6)</span
                            ></label
                        >
                        <input
                            id="v6_queue_type"
                            type="text"
                            class="input input-bordered input-sm"
                            placeholder="default-small"
                            bind:value={form.v6_queue_type}
                        />
                    </div>
                    <div class="form-control">
                        <label class="label" for="v7_queue_type"
                            ><span class="label-text font-medium"
                                >Queue Type (RouterOS v7)</span
                            ></label
                        >
                        <input
                            id="v7_queue_type"
                            type="text"
                            class="input input-bordered input-sm"
                            placeholder="cake-default"
                            bind:value={form.v7_queue_type}
                        />
                    </div>
                </div>

                <!-- Acciones -->
                <div class="modal-action pt-2">
                    <button
                        type="button"
                        class="btn btn-ghost"
                        on:click={close}
                        disabled={loading}>Cancelar</button
                    >
                    <button
                        type="submit"
                        class="btn btn-primary"
                        disabled={loading}
                    >
                        {#if loading}
                            <span class="loading loading-spinner loading-sm"
                            ></span>
                        {/if}
                        {isEditing ? "Guardar Cambios" : "Crear Plan"}
                    </button>
                </div>
            </form>
        </div>
        <button
            type="button"
            class="modal-backdrop"
            on:click={close}
            aria-label="Cerrar modal"
        ></button>
    </div>
{/if}

<script lang="ts">
    import { onMount } from "svelte";
    import { getPlans, deletePlan } from "$lib/api";
    import type { Plan } from "$lib/types/plan";
    import PlanFormModal from "$lib/components/planes/PlanFormModal.svelte";
    import AdminToolbar from "$lib/components/AdminToolbar.svelte";

    let plans: Plan[] = [];
    let loading = true;
    let errorMsg = "";

    // Modal state
    let showModal = false;
    let editingPlan: Plan | null = null;

    // Filtro
    let filter: "all" | "global" | "local" = "all";
    let searchQuery = "";

    onMount(() => {
        load();
    });

    async function load() {
        loading = true;
        errorMsg = "";
        try {
            plans = await getPlans();
        } catch {
            errorMsg = "No se pudieron cargar los planes.";
        } finally {
            loading = false;
        }
    }

    function openCreate() {
        editingPlan = null;
        showModal = true;
    }

    function openEdit(plan: Plan) {
        editingPlan = plan;
        showModal = true;
    }

    async function handleDelete(plan: Plan) {
        if (!confirm(`¿Eliminar el plan "${plan.name}"?`)) return;
        try {
            await deletePlan(plan.id);
            plans = plans.filter((p) => p.id !== plan.id);
        } catch {
            alert("Error al eliminar el plan.");
        }
    }

    function handleSaved(e: CustomEvent<Plan>) {
        const saved = e.detail;
        const idx = plans.findIndex((p) => p.id === saved.id);
        if (idx >= 0) {
            plans[idx] = saved;
            plans = [...plans];
        } else {
            plans = [...plans, saved];
        }
    }

    // Filtrado reactivo
    $: filtered = plans.filter((p) => {
        if (filter === "global" && p.router_host !== null) return false;
        if (filter === "local" && p.router_host === null) return false;
        if (searchQuery) {
            const q = searchQuery.toLowerCase();
            return (
                p.name.toLowerCase().includes(q) ||
                (p.router_name ?? "").toLowerCase().includes(q) ||
                p.max_limit.toLowerCase().includes(q)
            );
        }
        return true;
    });

    $: globalCount = plans.filter((p) => p.router_host === null).length;
    $: localCount = plans.filter((p) => p.router_host !== null).length;

    function suspensionLabel(method: string): string {
        const map: Record<string, string> = {
            queue_limit: "Throttle",
            address_list: "Lista IP",
            pppoe_secret_disable: "PPPoE Secret",
        };
        return map[method] ?? method;
    }
</script>

<div class="space-y-6">
    <!-- ── HEADER ─────────────────────────────────────────────────────────── -->
    <AdminToolbar
        title="Gestión de Planes"
        subtitle="{globalCount} globales · {localCount} locales"
    >
        {#snippet actions()}
            <button
                class="btn btn-primary btn-sm gap-2"
                on:click={openCreate}
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
                Nuevo Plan
            </button>
        {/snippet}
    </AdminToolbar>

    <!-- Filtros y búsqueda -->
    <div class="flex flex-col sm:flex-row gap-3">
        <div class="join">
            <button
                class="btn btn-sm join-item {filter === 'all'
                    ? 'btn-primary'
                    : 'btn-ghost'}"
                on:click={() => (filter = "all")}
            >
                Todos ({plans.length})
            </button>
            <button
                class="btn btn-sm join-item {filter === 'global'
                    ? 'btn-primary'
                    : 'btn-ghost'}"
                on:click={() => (filter = "global")}
            >
                🌐 Globales ({globalCount})
            </button>
            <button
                class="btn btn-sm join-item {filter === 'local'
                    ? 'btn-primary'
                    : 'btn-ghost'}"
                on:click={() => (filter = "local")}
            >
                📡 Locales ({localCount})
            </button>
        </div>
        <label
            class="input input-bordered input-sm flex items-center gap-2 flex-1"
        >
            <svg
                class="w-4 h-4 opacity-50"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
            >
                <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
            </svg>
            <input
                type="text"
                class="grow"
                placeholder="Buscar por nombre, router o velocidad..."
                bind:value={searchQuery}
            />
        </label>
    </div>

    <!-- Estados: Cargando / Error / Vacío -->
    {#if loading}
        <div class="flex items-center justify-center py-20">
            <span class="loading loading-spinner loading-lg text-primary"
            ></span>
        </div>
    {:else if errorMsg}
        <div class="alert alert-error">
            <span>{errorMsg}</span>
            <button class="btn btn-sm btn-ghost" on:click={load}
                >Reintentar</button
            >
        </div>
    {:else if filtered.length === 0}
        <div class="glass-card p-12 text-center">
            <div
                class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-secondary/10 text-secondary mb-4"
            >
                <svg
                    class="w-8 h-8"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M13 10V3L4 14h7v7l9-11h-7z"
                    />
                </svg>
            </div>
            <h3 class="text-lg font-semibold">No hay planes</h3>
            <p class="opacity-60 mt-2 text-sm">
                {plans.length === 0
                    ? "Crea tu primer plan para comenzar."
                    : "No hay planes que coincidan con el filtro."}
            </p>
            {#if plans.length === 0}
                <button
                    class="btn btn-primary btn-sm mt-4"
                    on:click={openCreate}>Crear Plan</button
                >
            {/if}
        </div>
    {:else}
        <!-- Tabla de planes -->
        <div class="overflow-x-auto rounded-lg border border-base-300">
            <table class="table table-zebra w-full">
                <thead>
                    <tr class="bg-base-200">
                        <th>Nombre</th>
                        <th>Velocidad</th>
                        <th>Tipo</th>
                        <th>Suspensión</th>
                        <th>Precio</th>
                        <th>Router</th>
                        <th class="text-right">Acciones</th>
                    </tr>
                </thead>
                <tbody>
                    {#each filtered as plan (plan.id)}
                        <tr class="hover">
                            <td class="font-medium">{plan.name}</td>
                            <td>
                                <span
                                    class="font-mono text-sm bg-base-200 px-2 py-0.5 rounded"
                                    >{plan.max_limit}</span
                                >
                            </td>
                            <td>
                                <span
                                    class="badge badge-sm {plan.plan_type ===
                                    'pppoe'
                                        ? 'badge-accent'
                                        : 'badge-neutral'}"
                                >
                                    {plan.plan_type === "pppoe"
                                        ? "PPPoE"
                                        : "Simple Q"}
                                </span>
                            </td>
                            <td>
                                <span class="text-sm opacity-80"
                                    >{suspensionLabel(
                                        plan.suspension_method,
                                    )}</span
                                >
                            </td>
                            <td>
                                <span class="font-semibold"
                                    >${plan.price?.toFixed(2) ?? "0.00"}</span
                                >
                            </td>
                            <td>
                                {#if plan.router_host === null}
                                    <span
                                        class="badge badge-primary badge-outline badge-sm gap-1"
                                    >
                                        🌐 Global
                                    </span>
                                {:else}
                                    <span
                                        class="badge badge-secondary badge-outline badge-sm"
                                        title={plan.router_host}
                                    >
                                        📡 {plan.router_name ??
                                            plan.router_host}
                                    </span>
                                {/if}
                            </td>
                            <td class="text-right">
                                <div class="flex gap-1 justify-end">
                                    <button
                                        class="btn btn-ghost btn-xs tooltip tooltip-left"
                                        data-tip="Editar"
                                        aria-label="Editar plan"
                                        on:click={() => openEdit(plan)}
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
                                                d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                                            />
                                        </svg>
                                    </button>
                                    <button
                                        class="btn btn-ghost btn-xs text-error tooltip tooltip-left"
                                        data-tip="Eliminar"
                                        aria-label="Eliminar plan"
                                        on:click={() => handleDelete(plan)}
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
                                                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                                            />
                                        </svg>
                                    </button>
                                </div>
                            </td>
                        </tr>
                    {/each}
                </tbody>
            </table>
        </div>
    {/if}
</div>

<!-- Modal de Crear / Editar -->
<PlanFormModal
    show={showModal}
    plan={editingPlan}
    on:saved={handleSaved}
    on:close={() => (showModal = false)}
/>

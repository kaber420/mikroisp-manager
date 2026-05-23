<script lang="ts">
    import { onMount } from "svelte";
    import { getPlansByRouter, deletePlan } from "$lib/api";
    import type { Plan } from "$lib/types/plan";
    import PlanFormModal from "$lib/components/planes/PlanFormModal.svelte";

    export let routerHost: string;

    let plans: Plan[] = [];
    let loading = true;
    let errorMsg = "";
    let showModal = false;
    let editingPlan: Plan | null = null;

    onMount(() => load());

    async function load() {
        loading = true;
        errorMsg = "";
        try {
            plans = await getPlansByRouter(routerHost);
        } catch {
            errorMsg = "No se pudieron cargar los planes locales.";
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

    function suspensionLabel(m: string | null | undefined) {
        if (!m) return "—";
        const map: Record<string, string> = {
            queue_limit: "Throttle",
            address_list: "Lista IP",
            pppoe_secret_disable: "PPPoE Secret",
        };
        return map[m] ?? m;
    }
</script>

<!-- Sección de Planes Locales del Router -->
<div class="glass-card-flat" style="padding:1.25rem;border-radius:1rem;">
    <div
        style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem;"
    >
        <div>
            <h3
                style="margin:0;font-size:0.85rem;font-weight:700;opacity:0.6;text-transform:uppercase;letter-spacing:0.06em;"
            >
                📡 Planes Locales
            </h3>
            <p style="margin:0.25rem 0 0;font-size:0.75rem;opacity:0.45;">
                Planes específicos de este router · {plans.length} configurado{plans.length !==
                1
                    ? "s"
                    : ""}
            </p>
        </div>
        <button class="btn btn-primary btn-xs gap-1" on:click={openCreate}>
            <svg
                class="w-3 h-3"
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
            Nuevo Plan Local
        </button>
    </div>

    {#if loading}
        <div style="text-align:center;padding:2rem;">
            <span class="loading loading-spinner loading-sm text-primary"
            ></span>
        </div>
    {:else if errorMsg}
        <div class="alert alert-error alert-sm py-2">
            <span style="font-size:0.85rem;">{errorMsg}</span>
            <button class="btn btn-xs btn-ghost" on:click={load}
                >Reintentar</button
            >
        </div>
    {:else if plans.length === 0}
        <div style="text-align:center;padding:2rem;opacity:0.5;">
            <p style="margin:0;font-size:0.85rem;">
                Sin planes locales. Los planes globales se aplican
                automáticamente.
            </p>
            <button
                class="btn btn-sm btn-outline btn-primary mt-3"
                on:click={openCreate}
            >
                Crear primer plan local
            </button>
        </div>
    {:else}
        <div class="overflow-x-auto">
            <table class="table table-zebra table-xs w-full">
                <thead>
                    <tr class="bg-base-200">
                        <th>Nombre</th>
                        <th>Velocidad</th>
                        <th>Tipo</th>
                        <th>Suspensión</th>
                        <th>Precio</th>
                        <th class="text-right">Acciones</th>
                    </tr>
                </thead>
                <tbody>
                    {#each plans as plan (plan.id)}
                        <tr class="hover">
                            <td class="font-medium">{plan.name}</td>
                            <td
                                ><span
                                    class="font-mono text-xs bg-base-200 px-1.5 py-0.5 rounded"
                                    >{plan.max_limit}</span
                                ></td
                            >
                            <td>
                                <span
                                    class="badge badge-xs {plan.plan_type ===
                                    'pppoe'
                                        ? 'badge-accent'
                                        : 'badge-neutral'}"
                                >
                                    {plan.plan_type === "pppoe"
                                        ? "PPPoE"
                                        : "Simple Q"}
                                </span>
                            </td>
                            <td
                                ><span class="text-xs opacity-70"
                                    >{suspensionLabel(
                                        plan.suspension_method,
                                    )}</span
                                ></td
                            >
                            <td
                                ><span class="font-semibold text-xs"
                                    >${plan.price?.toFixed(2) ?? "0.00"}</span
                                ></td
                            >
                            <td class="text-right">
                                <div class="flex gap-1 justify-end">
                                    <button
                                        class="btn btn-ghost btn-xs"
                                        title="Editar"
                                        on:click={() => openEdit(plan)}
                                        >✏️</button
                                    >
                                    <button
                                        class="btn btn-ghost btn-xs text-error"
                                        title="Eliminar"
                                        on:click={() => handleDelete(plan)}
                                        >🗑️</button
                                    >
                                </div>
                            </td>
                        </tr>
                    {/each}
                </tbody>
            </table>
        </div>
    {/if}
</div>

<!-- Modal con router fijo -->
<PlanFormModal
    show={showModal}
    plan={editingPlan}
    fixedRouterHost={routerHost}
    on:saved={handleSaved}
    on:close={() => (showModal = false)}
/>

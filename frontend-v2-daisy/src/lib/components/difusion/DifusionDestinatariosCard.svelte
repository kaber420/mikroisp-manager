<script lang="ts">
    import type { BroadcastTargetType } from "$lib/types/broadcast";

    interface Zone {
        id: number;
        name: string;
    }

    let {
        zones = [],
        targetType = $bindable<BroadcastTargetType>("clients"),
        allZones = $bindable(true),
        selectedZoneIds = $bindable<number[]>([]),
        staffRoles = $bindable({ admin: true, technician: true, billing: true }),
        ontogglezone,
    }: {
        zones: Zone[];
        targetType: BroadcastTargetType;
        allZones: boolean;
        selectedZoneIds: number[];
        staffRoles: { admin: boolean; technician: boolean; billing: boolean };
        ontogglezone?: (id: number) => void;
    } = $props();
</script>

<div class="card bg-base-100 shadow-sm">
    <div class="card-body gap-4">
        <h2 class="card-title text-base">
            <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-5 w-5 text-primary"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
            >
                <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"
                />
            </svg>
            Destinatarios
        </h2>

        <!-- Tabs de tipo -->
        <div class="grid grid-cols-2 gap-3">
            <!-- Clientes -->
            <button
                onclick={() => (targetType = "clients")}
                class="flex flex-col items-start gap-1 rounded-xl border-2 p-4 text-left transition-all
                       {targetType === 'clients'
                    ? 'border-primary bg-primary/10'
                    : 'border-base-300 hover:border-primary/40'}"
            >
                <span class="text-2xl">👥</span>
                <span class="font-semibold">Clientes</span>
                <span class="text-base-content/50 text-xs"
                    >Usuarios del servicio con Telegram</span
                >
            </button>

            <!-- Personal -->
            <button
                onclick={() => (targetType = "technicians")}
                class="flex flex-col items-start gap-1 rounded-xl border-2 p-4 text-left transition-all
                       {targetType === 'technicians'
                    ? 'border-primary bg-primary/10'
                    : 'border-base-300 hover:border-primary/40'}"
            >
                <span class="text-2xl">🏷️</span>
                <span class="font-semibold">Personal (Staff)</span>
                <span class="text-base-content/50 text-xs"
                    >Técnicos, Cobranza y Admins</span
                >
            </button>
        </div>

        <!-- Opciones de Clientes -->
        {#if targetType === "clients"}
            <div class="bg-base-200 rounded-xl p-4 transition-all">
                <label class="flex cursor-pointer items-center gap-3">
                    <input
                        type="checkbox"
                        class="checkbox checkbox-primary checkbox-sm"
                        bind:checked={allZones}
                    />
                    <span class="font-medium">Todas las Zonas</span>
                </label>

                {#if !allZones}
                    <div class="mt-4">
                        {#if zones.length === 0}
                            <div
                                class="text-base-content/50 flex flex-col items-center gap-2 py-6 text-sm"
                            >
                                <svg
                                    xmlns="http://www.w3.org/2000/svg"
                                    class="h-8 w-8 opacity-40"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke="currentColor"
                                >
                                    <path
                                        stroke-linecap="round"
                                        stroke-linejoin="round"
                                        stroke-width="2"
                                        d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064"
                                    />
                                </svg>
                                No hay zonas con clientes de Telegram
                            </div>
                        {:else}
                            <div
                                class="mt-2 grid max-h-48 grid-cols-1 gap-2 overflow-y-auto pr-1 sm:grid-cols-2"
                            >
                                {#each zones as zone (zone.id)}
                                    <label
                                        class="flex cursor-pointer items-center gap-3 rounded-lg p-3 transition-all
                                           {selectedZoneIds.includes(zone.id)
                                            ? 'bg-primary/10 border-primary border'
                                            : 'border-base-300 bg-base-100 hover:border-primary/40 border'}"
                                    >
                                        <input
                                            type="checkbox"
                                            class="checkbox checkbox-primary checkbox-sm"
                                            checked={selectedZoneIds.includes(zone.id)}
                                            onchange={() => ontogglezone?.(zone.id)}
                                        />
                                        <span class="text-sm font-medium">{zone.name}</span>
                                    </label>
                                {/each}
                            </div>
                        {/if}
                    </div>
                {/if}
            </div>
        {/if}

        <!-- Opciones de Personal -->
        {#if targetType === "technicians"}
            <div
                class="bg-primary/5 border-primary/20 rounded-xl border p-4 transition-all"
            >
                <p
                    class="text-primary mb-3 text-xs font-semibold uppercase tracking-wider"
                >
                    Filtrar por rol
                </p>
                <div class="flex flex-wrap gap-3">
                    <!-- Admin -->
                    <label
                        class="flex cursor-pointer items-center gap-2 rounded-lg border-2 px-4 py-2 transition-all
                           {staffRoles.admin
                            ? 'border-error bg-error/10 text-error'
                            : 'border-base-300 hover:border-error/50'}"
                    >
                        <input
                            type="checkbox"
                            class="checkbox checkbox-error checkbox-sm"
                            bind:checked={staffRoles.admin}
                        />
                        <span class="text-sm font-medium">Admin</span>
                    </label>

                    <!-- Técnico -->
                    <label
                        class="flex cursor-pointer items-center gap-2 rounded-lg border-2 px-4 py-2 transition-all
                           {staffRoles.technician
                            ? 'border-info bg-info/10 text-info'
                            : 'border-base-300 hover:border-info/50'}"
                    >
                        <input
                            type="checkbox"
                            class="checkbox checkbox-info checkbox-sm"
                            bind:checked={staffRoles.technician}
                        />
                        <span class="text-sm font-medium">Técnico</span>
                    </label>

                    <!-- Cobranza -->
                    <label
                        class="flex cursor-pointer items-center gap-2 rounded-lg border-2 px-4 py-2 transition-all
                           {staffRoles.billing
                            ? 'border-success bg-success/10 text-success'
                            : 'border-base-300 hover:border-success/50'}"
                    >
                        <input
                            type="checkbox"
                            class="checkbox checkbox-success checkbox-sm"
                            bind:checked={staffRoles.billing}
                        />
                        <span class="text-sm font-medium">Cobranza</span>
                    </label>
                </div>
            </div>
        {/if}
    </div>
</div>

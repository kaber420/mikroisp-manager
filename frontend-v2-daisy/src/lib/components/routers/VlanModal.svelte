<script lang="ts">
    import { createVlan, updateVlan } from "$lib/api";
    import type { InterfaceData } from "$lib/types/router";

    let {
        show = $bindable(false),
        routerHost,
        vlan = null,
        interfaces = [],
        onsuccess,
    } = $props<{
        show: boolean;
        routerHost: string;
        vlan?: InterfaceData | null;
        interfaces: InterfaceData[];
        onsuccess?: () => void;
    }>();

    let loading = $state(false);
    let errorMsg = $state<string | null>(null);

    // Form fields
    let name = $state("");
    let vlanId = $state("");
    let parentInterface = $state("");

    // Update state when modal opens/closes or vlan prop changes
    $effect(() => {
        if (show) {
            errorMsg = null;
            if (vlan) {
                name = vlan.name || "";
                vlanId = vlan["vlan-id"]?.toString() || "";
                parentInterface = vlan.interface || "";
            } else {
                name = "";
                vlanId = "";
                parentInterface = "";
            }
        }
    });

    const physicalInterfaces = $derived(
        interfaces.filter((i: InterfaceData) => ["ether", "wlan", "bonding"].includes(i.type)),
    );

    function close() {
        show = false;
    }

    async function handleSubmit() {
        if (!name || !vlanId || !parentInterface) {
            errorMsg = "Por favor, completa todos los campos requeridos.";
            return;
        }

        loading = true;
        errorMsg = null;

        const payload = {
            name,
            vlan_id: vlanId,
            interface: parentInterface,
            comment: "managed by umonitor",
        };

        try {
            if (vlan && (vlan[".id"] || vlan.id)) {
                const id = vlan[".id"] || vlan.id;
                await updateVlan(routerHost, id!, payload);
            } else {
                await createVlan(routerHost, payload);
            }
            if (onsuccess) onsuccess();
            close();
        } catch (e: any) {
            errorMsg =
                e.response?.data?.detail ||
                e.message ||
                "Error al guardar VLAN";
        } finally {
            loading = false;
        }
    }
</script>

{#if show}
    <div class="modal modal-open z-50">
        <div class="modal-box">
            <h3 class="font-bold text-lg mb-4">
                {vlan ? "Editar VLAN" : "Agregar VLAN"}
            </h3>

            {#if errorMsg}
                <div class="alert alert-error text-sm py-2 mb-4">
                    <span>{errorMsg}</span>
                </div>
            {/if}

            <form
                onsubmit={(e) => {
                    e.preventDefault();
                    handleSubmit();
                }}
                class="space-y-4"
            >
                <div class="form-control">
                    <label class="label" for="vlan-name"
                        ><span class="label-text">Nombre de VLAN</span></label
                    >
                    <input
                        id="vlan-name"
                        type="text"
                        class="input input-bordered w-full"
                        bind:value={name}
                        required
                        placeholder="Ej: vlan10-empleados"
                    />
                </div>

                <div class="form-control">
                    <label class="label" for="vlan-id"
                        ><span class="label-text">VLAN ID</span></label
                    >
                    <input
                        id="vlan-id"
                        type="number"
                        class="input input-bordered w-full"
                        bind:value={vlanId}
                        required
                        placeholder="10"
                    />
                </div>

                <div class="form-control">
                    <label class="label" for="parent-interface"
                        ><span class="label-text">Interfaz Padre</span></label
                    >
                    <select
                        id="parent-interface"
                        class="select select-bordered w-full"
                        bind:value={parentInterface}
                        required
                    >
                        <option value="" disabled
                            >Seleccionar interfaz...</option
                        >
                        {#each physicalInterfaces as intf}
                            <option value={intf.name}>{intf.name}</option>
                        {/each}
                    </select>
                </div>

                <div class="modal-action">
                    <button
                        type="button"
                        class="btn btn-ghost"
                        onclick={close}
                        disabled={loading}>Cancelar</button
                    >
                    <button
                        type="submit"
                        class="btn btn-primary"
                        disabled={loading}
                    >
                        {#if loading}<span
                                class="loading loading-spinner loading-sm"
                            ></span>{/if}
                        Guardar
                    </button>
                </div>
            </form>
        </div>
        <form method="dialog" class="modal-backdrop">
            <button onclick={close}>close</button>
        </form>
    </div>
{/if}

<script lang="ts">
    import { createBridge, updateBridge } from "$lib/api";
    import type { InterfaceData } from "$lib/types/router";

    let {
        show = $bindable(false),
        routerHost,
        bridge = null,
        interfaces = [],
        bridgePorts = [],
        onsuccess,
    } = $props<{
        show: boolean;
        routerHost: string;
        bridge?: InterfaceData | null;
        interfaces: InterfaceData[];
        bridgePorts: any[];
        onsuccess?: () => void;
    }>();

    let loading = $state(false);
    let errorMsg = $state<string | null>(null);

    // Form fields
    let name = $state("");
    let selectedPorts = $state<string[]>([]);

    $effect(() => {
        if (show) {
            errorMsg = null;
            if (bridge) {
                name = bridge.name || "";
                // Find ports currently assigned to this bridge
                selectedPorts = bridgePorts
                    .filter((p: any) => p.bridge === bridge!.name)
                    .map((p: any) => p.interface);
            } else {
                name = "";
                selectedPorts = [];
            }
        }
    });

    const portCapableTypes = ["ether", "wlan", "wifi", "vlan", "bonding"];
    const physicalInterfaces = $derived(
        interfaces.filter((i: InterfaceData) =>
            portCapableTypes.includes(i.type),
        ),
    );

    // Derive busy ports (assigned to OTHER bridges)
    const busyPortsMap = $derived(() => {
        const map: Record<string, string> = {};
        bridgePorts.forEach((p: any) => {
            if (!bridge || p.bridge !== bridge!.name) {
                map[p.interface] = p.bridge;
            }
        });
        return map;
    });

    function close() {
        show = false;
    }

    function togglePort(portName: string) {
        if (selectedPorts.includes(portName)) {
            selectedPorts = selectedPorts.filter((p) => p !== portName);
        } else {
            selectedPorts = [...selectedPorts, portName];
        }
    }

    async function handleSubmit() {
        if (!name) {
            errorMsg = "El nombre del bridge es requerido.";
            return;
        }

        loading = true;
        errorMsg = null;

        const payload = {
            name,
            ports: selectedPorts,
            comment: "managed by umonitor",
        };

        try {
            if (bridge && (bridge[".id"] || bridge.id)) {
                const id = bridge[".id"] || bridge.id;
                await updateBridge(routerHost, id!, payload);
            } else {
                await createBridge(routerHost, payload);
            }
            if (onsuccess) onsuccess();
            close();
        } catch (e: any) {
            errorMsg =
                e.response?.data?.detail ||
                e.message ||
                "Error al guardar Bridge";
        } finally {
            loading = false;
        }
    }
</script>

{#if show}
    <div class="modal modal-open z-50">
        <div class="modal-box">
            <h3 class="font-bold text-lg mb-4">
                {bridge ? "Editar Bridge" : "Agregar Bridge"}
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
                    <label class="label" for="bridge-name"
                        ><span class="label-text">Nombre del Bridge</span
                        ></label
                    >
                    <input
                        id="bridge-name"
                        type="text"
                        class="input input-bordered w-full"
                        bind:value={name}
                        required
                        placeholder="Ej: bridge-local"
                    />
                </div>

                <div class="form-control">
                    <label class="label"
                        ><span class="label-text">Puertos</span></label
                    >
                    <div
                        class="grid grid-cols-2 gap-2 max-h-60 overflow-y-auto bg-base-200 p-2 rounded-md border border-base-300"
                    >
                        {#each physicalInterfaces as intf}
                            {@const busyBridge = busyPortsMap()[intf.name]}
                            <label
                                class="flex items-center space-x-2 {busyBridge
                                    ? 'opacity-50 cursor-not-allowed'
                                    : 'cursor-pointer'}"
                            >
                                <input
                                    type="checkbox"
                                    class="checkbox checkbox-sm checkbox-primary"
                                    checked={selectedPorts.includes(intf.name)}
                                    disabled={!!busyBridge}
                                    onchange={() => togglePort(intf.name)}
                                />
                                <span class="text-sm">
                                    {intf.name}
                                    {#if busyBridge}
                                        <span
                                            class="text-xs text-base-content/50"
                                            >({busyBridge})</span
                                        >
                                    {/if}
                                </span>
                            </label>
                        {/each}
                    </div>
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

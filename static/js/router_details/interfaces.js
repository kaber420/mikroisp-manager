// static/js/router_details/interfaces.js
import { ApiClient, DomUtils } from './utils.js';
import { CONFIG, DOM_ELEMENTS, state, setAllInterfaces } from './config.js';
import { TableComponent } from '../components/TableComponent.js';

// --- ESTADO LOCAL DEL MÓDULO ---
let allModuleInterfaces = [];
let allModuleIps = [];
let allModuleBridgePorts = [];
let currentInterfaceFilter = 'general';
let interfacesTable = null; // Instancia del componente

// Definición de nuestros filtros
const FILTER_TYPES = {
    general: ['ether', 'bridge', 'vlan', 'wlan', 'bonding', 'loopback'],
    ppp: ['pppoe-out', 'pptp-out', 'l2tp-out', 'ovpn-out', 'sstp-out', 'ipip', 'gre', 'eoip', 'pppoe-in', 'pptp-in', 'l2tp-in']
};

// --- RENDERIZADORES ---

function initTableComponent() {
    if (interfacesTable) return;

    interfacesTable = new TableComponent({
        columns: ['Status', 'Name', 'Type', 'MAC Address', 'IP Address', 'RX Bytes', 'TX Bytes', 'Uptime', 'Acciones'],
        emptyMessage: 'No se encontraron interfaces para este filtro.',
        onAction: (action, payload) => {
            handleInterfaceAction(action, payload.id, payload.name, payload.type);
        },
        renderRow: (iface) => {
            const ip = allModuleIps.find(i => i.interface === iface.name);
            const interfaceId = iface['.id'] || iface.id;
            const isDisabled = iface.disabled === 'true' || iface.disabled === true;
            const isActuallyRunning = (iface.running === 'true' || iface.running === true);
            const isRunning = isActuallyRunning && !isDisabled;
            const statusClass = isRunning ? 'status-online' : 'status-offline';
            const rowClass = isDisabled ? 'opacity-50' : '';

            const canBeDeleted = ['vlan', 'bridge', 'bonding'].includes(iface.type);
            const canBeDisabled = !['pppoe-out', 'pptp-out', 'l2tp-out'].includes(iface.type);
            const isManaged = iface.comment && iface.comment.includes('managed by umonitor');

            let actionButtons = '';

            // Allow edit for all bridges, and for VLANs only if managed
            if (iface.type === 'bridge' || (isManaged && iface.type === 'vlan')) {
                actionButtons += `<button class="btn-action-icon" data-action="edit" data-id="${interfaceId}" data-name="${iface.name}" data-type="${iface.type}" title="Editar"><span class="material-symbols-outlined text-primary">edit</span></button>`;
            }

            if (canBeDisabled) {
                if (isDisabled) {
                    actionButtons += `<button class="btn-action-icon" data-action="enable" data-id="${interfaceId}" data-type="${iface.type}" title="Habilitar"><span class="material-symbols-outlined text-success">play_circle</span></button>`;
                } else {
                    actionButtons += `<button class="btn-action-icon" data-action="disable" data-id="${interfaceId}" data-type="${iface.type}" title="Deshabilitar"><span class="material-symbols-outlined text-warning">pause_circle</span></button>`;
                }
            }

            if (canBeDeleted) {
                actionButtons += `<button class="btn-action-icon" data-action="delete" data-id="${interfaceId}" data-type="${iface.type}" data-name="${iface.name}" title="Eliminar">${DOM_ELEMENTS.deleteIcon}</button>`;
            }

            const rxBytes = iface['rx-byte'] ? DomUtils.formatBytes(iface['rx-byte']) : '0 Bytes';
            const txBytes = iface['tx-byte'] ? DomUtils.formatBytes(iface['tx-byte']) : '0 Bytes';

            return `
                <tr class="${rowClass}">
                    <td class="text-center"><span class="status-indicator ${statusClass}" title="${isDisabled ? 'Disabled' : (isActuallyRunning ? 'Up' : 'Down')}"></span></td>
                    <td>${iface.name}</td>
                    <td><span class="badge bg-light text-dark">${iface.type}</span></td>
                    <td>${iface['mac-address'] || 'N/A'}</td>
                    <td>${ip ? ip.address : '(Dinámica)'}</td>
                    <td class="font-mono">${rxBytes}</td> <td class="font-mono">${txBytes}</td>
                    <td>${iface.uptime || 'N/A'}</td>
                    <td class="flex gap-1">${actionButtons}</td>
                </tr>
            `;
        }
    });
}

function renderInterfaces() {
    if (!DOM_ELEMENTS.interfacesTableContainer) return;

    const tableContainer = DOM_ELEMENTS.interfacesTableContainer;

    initTableComponent();

    let filteredInterfaces;
    switch (currentInterfaceFilter) {
        case 'general':
            filteredInterfaces = allModuleInterfaces.filter(iface => FILTER_TYPES.general.includes(iface.type));
            break;
        case 'ppp':
            filteredInterfaces = allModuleInterfaces.filter(iface => FILTER_TYPES.ppp.includes(iface.type) && iface.name !== 'none');
            break;
        default:
            filteredInterfaces = allModuleInterfaces;
    }

    DOM_ELEMENTS.resInterfaces.textContent = filteredInterfaces.length;

    // Actualizar mensaje vacío dinámicamente
    interfacesTable.emptyMessage = currentInterfaceFilter === 'ppp'
        ? 'No hay túneles o clientes PPPoE conectados.'
        : 'No se encontraron interfaces para este filtro.';

    filteredInterfaces.sort((a, b) => {
        if (a.type !== b.type) return a.type.localeCompare(b.type);
        return a.name.localeCompare(b.name);
    });

    // Explicitly call TableComponent.render to force UI update
    if (interfacesTable && tableContainer) {
        interfacesTable.render(filteredInterfaces, tableContainer);
    }
}

// --- SMART POLLING LOGIC ---

/**
 * Polls the backend until the predicate returns true or timeout.
 * @param {Function} predicate (data) => boolean
 * @param {number} maxAttempts Default 5
 * @param {number} intervalMs Default 1000
 */
async function smartRefresh(predicate, maxAttempts = 5, intervalMs = 1000) {
    for (let i = 0; i < maxAttempts; i++) {
        try {
            console.log(`🔄 Smart Polling attempt ${i + 1}/${maxAttempts}...`);
            const cacheBuster = `?_t=${Date.now()}`;
            const fullDetails = await ApiClient.request(`/api/routers/${CONFIG.currentHost}/full-details${cacheBuster}`);
            const tempInterfaces = fullDetails.interfaces || [];

            if (predicate(tempInterfaces)) {
                console.log('✅ Smart Polling success!');
                allModuleInterfaces = tempInterfaces;
                allModuleIps = fullDetails.ip_addresses || [];
                allModuleBridgePorts = fullDetails.bridge_ports || [];
                setAllInterfaces(allModuleInterfaces);

                renderInterfaces();
                populateInterfaceSelects(allModuleInterfaces);
                DomUtils.updateFeedback('Sincronización completada.', true);
                return;
            }
        } catch (e) {
            console.warn('Smart Polling transient error:', e);
        }
        await new Promise(r => setTimeout(r, intervalMs)); // Wait
    }
    console.warn('⚠️ Smart Polling timed out.');
    await refreshInterfaceData(); // Fallback
    DomUtils.updateFeedback('Sincronización finalizada.', true);
}

export function populateInterfaceSelects(interfaces) {
    const selects = document.querySelectorAll('.interface-select');
    if (!selects.length) return;

    const options = interfaces.length ? '<option value="">Seleccionar...</option>' + interfaces
        .filter(i => ['ether', 'bridge', 'vlan', 'wlan'].includes(i.type))
        .map(i => `<option value="${i.name}">${i.name}</option>`).join('') : '<option value="">Error</option>';

    selects.forEach(s => s.innerHTML = options);
}

// --- MODAL LOGIC ---

function openVlanModal(vlan = null) {
    DOM_ELEMENTS.vlanForm.reset();
    const physicalInterfaces = state.allInterfaces.filter(i => ['ether', 'wlan', 'bonding'].includes(i.type));
    DOM_ELEMENTS.vlanInterfaceSelect.innerHTML = physicalInterfaces.map(i => `<option value="${i.name}">${i.name}</option>`).join('');

    if (vlan) {
        DOM_ELEMENTS.vlanModalTitle.textContent = 'Edit VLAN';
        DOM_ELEMENTS.vlanForm.querySelector('#vlan-id').value = vlan['.id'];
        DOM_ELEMENTS.vlanNameInput.value = vlan.name;
        DOM_ELEMENTS.vlanIdInput.value = vlan['vlan-id'];
        DOM_ELEMENTS.vlanInterfaceSelect.value = vlan.interface;
    } else {
        DOM_ELEMENTS.vlanModalTitle.textContent = 'Add VLAN';
    }
    DOM_ELEMENTS.vlanModal.classList.remove('hidden');
    DOM_ELEMENTS.vlanModal.classList.add('flex');
}

function closeVlanModal() {
    DOM_ELEMENTS.vlanModal.classList.add('hidden');
    DOM_ELEMENTS.vlanModal.classList.remove('flex');
}

function openBridgeModal(bridge = null) {
    DOM_ELEMENTS.bridgeForm.reset();

    // Include all interface types that can be bridge ports
    // Types: ether, wlan, wifi, vlan, bonding (exclude bridge itself, loopback, ppp types)
    const portCapableTypes = ['ether', 'wlan', 'wifi', 'vlan', 'bonding'];
    const physicalInterfaces = state.allInterfaces.filter(i => portCapableTypes.includes(i.type));


    // Build a map of interface -> bridge name for ports already assigned
    const portToBridgeMap = {};
    allModuleBridgePorts.forEach(p => {
        portToBridgeMap[p.interface] = p.bridge;
    });

    // Ports assigned to the bridge being edited (if any)
    const currentBridgeName = bridge ? bridge.name : null;

    DOM_ELEMENTS.bridgePortsContainer.innerHTML = physicalInterfaces.map(i => {
        const assignedTo = portToBridgeMap[i.name];
        const isAssignedToThis = assignedTo === currentBridgeName;
        const isAssignedToOther = assignedTo && assignedTo !== currentBridgeName;

        let labelText = i.name;
        let disabledAttr = '';
        let checkedAttr = '';
        let labelClass = 'flex items-center space-x-2';

        if (isAssignedToThis) {
            checkedAttr = 'checked';
        } else if (isAssignedToOther) {
            labelText = `${i.name} <span class="text-xs text-muted">(${assignedTo})</span>`;
            disabledAttr = 'disabled';
            labelClass += ' opacity-50 cursor-not-allowed';
        }

        return `
            <label class="${labelClass}">
                <input type="checkbox" name="ports" value="${i.name}" ${checkedAttr} ${disabledAttr} class="rounded bg-background border-border-color text-primary focus:ring-primary">
                <span>${labelText}</span>
            </label>
        `;
    }).join('');

    if (bridge) {
        DOM_ELEMENTS.bridgeModalTitle.textContent = 'Editar Bridge';
        // Handle both .id and id formats from Mikrotik API
        const bridgeId = bridge['.id'] || bridge.id;
        DOM_ELEMENTS.bridgeForm.querySelector('#bridge-id').value = bridgeId;
        DOM_ELEMENTS.bridgeNameInput.value = bridge.name;
    } else {
        DOM_ELEMENTS.bridgeModalTitle.textContent = 'Agregar Bridge';
        DOM_ELEMENTS.bridgeForm.querySelector('#bridge-id').value = '';
    }
    DOM_ELEMENTS.bridgeModal.classList.remove('hidden');
    DOM_ELEMENTS.bridgeModal.classList.add('flex');
}

function closeBridgeModal() {
    DOM_ELEMENTS.bridgeModal.classList.add('hidden');
    DOM_ELEMENTS.bridgeModal.classList.remove('flex');
}

// --- CARGADOR DE DATOS ---

async function refreshInterfaceData() {
    try {
        // Direct API call with cache-busting to ensure fresh data
        const cacheBuster = `?_t=${Date.now()}`;
        const data = await ApiClient.request(`/api/routers/${CONFIG.currentHost}/full-details${cacheBuster}`);

        // Update module state directly
        allModuleInterfaces = data.interfaces || [];
        allModuleIps = data.ip_addresses || [];
        allModuleBridgePorts = data.bridge_ports || [];
        setAllInterfaces(allModuleInterfaces);

        // Re-render
        renderInterfaces();
        populateInterfaceSelects(allModuleInterfaces);

        console.log('✅ Interfaces reloaded:', allModuleInterfaces.length, 'interfaces');
        // Optional: Notify user sync is done implicitly by the list updating, 
        // but we can add a subtle indicator if needed.
        // For now, let's assume the previous message "Sincronizando..." implies it will finish.
        // Actually, maybe update feedback to "Listo"?
        // DomUtils.updateFeedback("Lista actualizada", true); 
    } catch (e) {
        console.error("Error recargando datos de interfaces:", e);
        DomUtils.updateFeedback(`Error al recargar interfaces: ${e.message}`, false);
    }
}

export async function loadInterfacesData(fullDetails) {
    allModuleInterfaces = fullDetails.interfaces || [];
    allModuleIps = fullDetails.ip_addresses || [];
    allModuleBridgePorts = fullDetails.bridge_ports || [];
    setAllInterfaces(allModuleInterfaces);

    renderInterfaces();
    populateInterfaceSelects(allModuleInterfaces);
}


// --- MANEJADORES DE ACCIONES ---

async function handleInterfaceAction(action, interfaceId, interfaceName = '', interfaceType) {
    if (action === 'edit') {
        // Search by .id, id, or name - Mikrotik API can return IDs in different formats
        const item = allModuleInterfaces.find(i =>
            i['.id'] === interfaceId ||
            i.id === interfaceId ||
            i.name === interfaceName
        );

        if (!item) {
            console.error('Interface not found:', interfaceId, interfaceName);
            DomUtils.updateFeedback('Error: No se encontró la interfaz para editar.', false);
            return;
        }

        if (interfaceType === 'vlan') {
            openVlanModal(item);
        } else if (interfaceType === 'bridge') {
            openBridgeModal(item);
        }
        return;
    }

    const host = CONFIG.currentHost;
    let requestOptions = {};
    let successMessage = '';
    let confirmMessage = '';

    try {
        switch (action) {
            case 'disable':
                confirmMessage = `¿Estás seguro de que quieres DESHABILITAR la interfaz ${interfaceName}?`;
                requestOptions = { method: 'PATCH', body: JSON.stringify({ disable: true }) };
                successMessage = 'Interfaz deshabilitada con éxito.';
                break;
            case 'enable':
                confirmMessage = `¿Estás seguro de que quieres HABILITAR la interfaz ${interfaceName}?`;
                requestOptions = { method: 'PATCH', body: JSON.stringify({ disable: false }) };
                successMessage = 'Interfaz habilitada con éxito.';
                break;
            case 'delete':
                confirmMessage = `¿Estás seguro de que quieres ELIMINAR PERMANENTEMENTE la interfaz "${interfaceName}" (${interfaceId})?`;
                requestOptions = { method: 'DELETE' };
                successMessage = 'Interfaz eliminada con éxito.';
                break;
            default:
                return;
        }

        DomUtils.confirmAndExecute(confirmMessage, async () => {

            const encodedId = encodeURIComponent(interfaceId);
            const encodedType = encodeURIComponent(interfaceType);
            const url = `/api/routers/${host}/interfaces/${encodedId}?type=${encodedType}`;

            await ApiClient.request(url, requestOptions);

            DomUtils.updateFeedback(successMessage, true);

            // Smart Polling
            DomUtils.updateFeedback('Sincronizando con router...', true);
            if (action === 'delete') {
                smartRefresh(list => !list.find(i => (i['.id'] || i.id) === interfaceId));
            } else {
                smartRefresh(() => true); // Generic wait for next update
            }
        });

    } catch (e) {
        console.error(`Error en handleInterfaceAction (${action}):`, e);
        DomUtils.updateFeedback(`Error: ${e.message}`, false);
    }
}

async function handleVlanFormSubmit(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    const id = formData.get('id');
    const data = {
        name: formData.get('name'),
        vlan_id: formData.get('vlan-id'),
        interface: formData.get('interface'),
        comment: 'managed by umonitor'
    };

    const url = id ? `/api/routers/${CONFIG.currentHost}/vlans/${id}` : `/api/routers/${CONFIG.currentHost}/vlans`;
    const method = id ? 'PUT' : 'POST';

    try {
        const result = await ApiClient.request(url, { method, body: JSON.stringify(data) });
        closeVlanModal();
        DomUtils.updateFeedback('Guardado correctamente. Sincronizando...', true);

        // Smart Polling: Wait until new VLAN appears
        smartRefresh(list => list.find(i => i.name === data.name));
    } catch (error) {
        DomUtils.updateFeedback(`Error saving VLAN: ${error.message}`, false);
    }
}

async function handleBridgeFormSubmit(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    const id = formData.get('id');
    const name = formData.get('name');
    const ports = formData.getAll('ports');

    const data = {
        name: name,
        ports: ports,
        comment: 'managed by umonitor'
    };

    const url = id ? `/api/routers/${CONFIG.currentHost}/bridges/${id}` : `/api/routers/${CONFIG.currentHost}/bridges`;
    const method = id ? 'PUT' : 'POST';

    try {
        const result = await ApiClient.request(url, { method, body: JSON.stringify(data) });
        closeBridgeModal();
        DomUtils.updateFeedback('Guardado correctamente. Sincronizando...', true);

        // Smart Polling: Wait until new Bridge appears
        smartRefresh(list => list.find(i => i.name === data.name));
    } catch (error) {
        DomUtils.updateFeedback(`Error saving bridge: ${error.message}`, false);
    }
}

// --- INICIALIZADOR ---

export function initInterfacesModule() {
    if (DOM_ELEMENTS.interfaceFilterButtons) {
        DOM_ELEMENTS.interfaceFilterButtons.addEventListener('click', (e) => {
            const button = e.target.closest('button');
            if (!button) return;
            const filter = button.dataset.filter;
            if (filter === currentInterfaceFilter) return;
            currentInterfaceFilter = filter;
            DOM_ELEMENTS.interfaceFilterButtons.querySelectorAll('button').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.filter === filter);
            });
            renderInterfaces();
        });
    }

    // Event delegation for table actions is now handled by TableComponent internally.


    // New event listeners
    DOM_ELEMENTS.addVlanBtn.addEventListener('click', () => openVlanModal());
    DOM_ELEMENTS.cancelVlanBtn.addEventListener('click', closeVlanModal);
    DOM_ELEMENTS.closeVlanModalBtn.addEventListener('click', closeVlanModal);
    DOM_ELEMENTS.vlanForm.addEventListener('submit', handleVlanFormSubmit);

    DOM_ELEMENTS.addBridgeBtn.addEventListener('click', () => openBridgeModal());
    DOM_ELEMENTS.cancelBridgeBtn.addEventListener('click', closeBridgeModal);
    DOM_ELEMENTS.closeBridgeModalBtn.addEventListener('click', closeBridgeModal);
    DOM_ELEMENTS.bridgeForm.addEventListener('submit', handleBridgeFormSubmit);
}

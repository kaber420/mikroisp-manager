// static/js/router_details/network.js
import { ApiClient, DomUtils } from './utils.js';
import { CONFIG, DOM_ELEMENTS, state } from './config.js';
import { TableComponent } from '../components/TableComponent.js';

// --- ESTADO LOCAL ---
let ipTable = null;
let natTable = null;
let activeAddIpModal = null;
let activeAddNatModal = null;

// --- MODAL FUNCTIONS ---

function openAddIpModal() {
    const template = DOM_ELEMENTS.addIpFormTemplate;
    if (!template) {
        console.error('Add IP form template not found');
        return;
    }

    const content = template.content.cloneNode(true);
    const wrapper = document.createElement('div');
    wrapper.appendChild(content);

    // Populate interface select
    const interfaceSelect = wrapper.querySelector('#add-ip-interface');
    if (interfaceSelect && state.allInterfaces?.length) {
        const validInterfaces = state.allInterfaces.filter(
            i => ['ether', 'bridge', 'vlan', 'wlan'].includes(i.type)
        );
        interfaceSelect.innerHTML = '<option value="">Seleccionar...</option>' +
            validInterfaces.map(i => `<option value="${i.name}">${i.name}</option>`).join('');
    }

    activeAddIpModal = window.ModalUtils.showCustomModal({
        title: 'Añadir Dirección IP',
        content: wrapper,
        modalId: 'add-ip-modal',
        size: 'md',
        actions: [
            {
                text: 'Cancelar',
                handler: () => { },
                closeOnClick: true
            },
            {
                text: 'Añadir IP',
                icon: 'add',
                primary: true,
                handler: () => handleAddIpSubmit(activeAddIpModal),
                closeOnClick: false
            }
        ]
    });
}

function openAddNatModal() {
    const template = DOM_ELEMENTS.addNatFormTemplate;
    if (!template) {
        console.error('Add NAT form template not found');
        return;
    }

    const content = template.content.cloneNode(true);
    const wrapper = document.createElement('div');
    wrapper.appendChild(content);

    // Populate interface select
    const interfaceSelect = wrapper.querySelector('#add-nat-interface');
    if (interfaceSelect && state.allInterfaces?.length) {
        const validInterfaces = state.allInterfaces.filter(
            i => ['ether', 'bridge', 'vlan', 'wlan', 'pppoe-out'].includes(i.type)
        );
        interfaceSelect.innerHTML = '<option value="">Seleccionar...</option>' +
            validInterfaces.map(i => `<option value="${i.name}">${i.name}</option>`).join('');
    }

    activeAddNatModal = window.ModalUtils.showCustomModal({
        title: 'Activar NAT (Masquerade)',
        content: wrapper,
        modalId: 'add-nat-modal',
        size: 'md',
        actions: [
            {
                text: 'Cancelar',
                handler: () => { },
                closeOnClick: true
            },
            {
                text: 'Activar NAT',
                icon: 'check',
                primary: true,
                handler: () => handleAddNatSubmit(activeAddNatModal),
                closeOnClick: false
            }
        ]
    });
}

// --- MANEJADORES (HANDLERS) ---

async function handleAddIpSubmit(modalRef) {
    const form = document.getElementById('add-ip-form');
    if (!form) return;

    const formData = new FormData(form);
    const interfaceValue = formData.get('interface');
    const address = formData.get('address');

    if (!interfaceValue || !address) {
        DomUtils.updateFeedback('Por favor completa todos los campos.', false);
        return;
    }

    try {
        const comment = "Managed by µMonitor";
        await ApiClient.request(`/api/routers/${CONFIG.currentHost}/write/add-ip`, {
            method: 'POST',
            body: JSON.stringify({ interface: interfaceValue, address: address, comment: comment })
        });
        if (modalRef) modalRef.close();
        DomUtils.updateFeedback('IP Añadida', true);
        await window.loadFullDetailsData();
    } catch (err) {
        DomUtils.updateFeedback(err.message, false);
    }
}

async function handleAddNatSubmit(modalRef) {
    const form = document.getElementById('add-nat-form');
    if (!form) return;

    const formData = new FormData(form);
    const outInterface = formData.get('out-interface');
    const comment = formData.get('comment');

    if (!outInterface) {
        DomUtils.updateFeedback('Por favor selecciona una interface.', false);
        return;
    }

    try {
        await ApiClient.request(`/api/routers/${CONFIG.currentHost}/write/add-nat`, {
            method: 'POST',
            body: JSON.stringify({ out_interface: outInterface, comment: comment })
        });
        if (modalRef) modalRef.close();
        DomUtils.updateFeedback('NAT Añadido', true);
        await window.loadFullDetailsData();
    } catch (err) {
        DomUtils.updateFeedback(err.message, false);
    }
}

const handleDeleteIp = (address) => {
    DomUtils.confirmAndExecute(`¿Borrar la IP "${address}"?`, async () => {
        try {
            await ApiClient.request(`/api/routers/${CONFIG.currentHost}/write/delete-ip?address=${encodeURIComponent(address)}`, { method: 'DELETE' });
            DomUtils.updateFeedback('IP Eliminada', true);
            await window.loadFullDetailsData();
        } catch (err) { DomUtils.updateFeedback(err.message, false); }
    });
};

const handleDeleteNat = (comment) => {
    DomUtils.confirmAndExecute(`¿Borrar la regla NAT "${comment}"?`, async () => {
        try {
            await ApiClient.request(`/api/routers/${CONFIG.currentHost}/write/delete-nat?comment=${encodeURIComponent(comment)}`, { method: 'DELETE' });
            DomUtils.updateFeedback('Regla NAT Eliminada', true);
            await window.loadFullDetailsData();
        } catch (err) { DomUtils.updateFeedback(err.message, false); }
    });
};

// --- RENDERIZADORES ---

function renderIpAddresses(ips = []) {
    if (!DOM_ELEMENTS.ipAddressList) return;

    if (!ipTable) {
        ipTable = new TableComponent({
            columns: ['Address', 'Interface', 'Action'],
            emptyMessage: 'No IP addresses found.',
            tableClass: 'data-table w-full',
            onAction: (action, payload) => {
                if (action === 'delete') handleDeleteIp(payload.address);
            },
            renderRow: (ip) => {
                return `
                    <tr>
                        <td>${ip.address}</td>
                        <td>${ip.interface}</td>
                        <td>
                            <button class="btn-action-icon text-danger hover:text-red-400" 
                                    data-action="delete" 
                                    data-address="${ip.address}"
                                    title="Eliminar IP">
                                ${DOM_ELEMENTS.deleteIcon}
                            </button>
                        </td>
                    </tr>
                `;
            }
        });
    }

    ipTable.render(ips, DOM_ELEMENTS.ipAddressList);
}

function renderNatRules(rules = []) {
    if (!DOM_ELEMENTS.natRulesList) return;

    if (!natTable) {
        natTable = new TableComponent({
            columns: ['Comment', 'Out-Interface', 'Action'],
            emptyMessage: 'No NAT rules found.',
            tableClass: 'data-table w-full',
            onAction: (action, payload) => {
                if (action === 'delete') handleDeleteNat(payload.comment);
            },
            renderRow: (rule) => {
                return `
                    <tr>
                        <td>${rule.comment || 'NAT Rule'}</td>
                        <td>${rule['out-interface']}</td>
                        <td>
                            <button class="btn-action-icon text-danger hover:text-red-400" 
                                    data-action="delete" 
                                    data-comment="${rule.comment}"
                                    title="Eliminar Regla">
                                ${DOM_ELEMENTS.deleteIcon}
                            </button>
                        </td>
                    </tr>
                `;
            }
        });
    }

    const filteredRules = rules.filter(r => r.action === 'masquerade');
    natTable.render(filteredRules, DOM_ELEMENTS.natRulesList);
}

function renderIpPools(pools) {
    if (!DOM_ELEMENTS.ipPoolList) return;
    DOM_ELEMENTS.ipPoolList.innerHTML = (!pools || pools.length === 0) ? '<p class="text-text-secondary">No hay pools.</p>' : '';
    pools?.forEach(pool => {
        DOM_ELEMENTS.ipPoolList.innerHTML += `<div class="flex justify-between items-center text-sm"><span>${pool.name}</span><span class="text-text-secondary font-mono">${pool.ranges}</span></div>`;
    });
}

// --- CARGADOR DE DATOS ---

export function loadNetworkData(fullDetails) {
    if (fullDetails) {
        renderIpAddresses(fullDetails.ip_addresses);
        renderNatRules(fullDetails.nat_rules);
        renderIpPools(fullDetails.ip_pools);
    }
}

// --- INICIALIZADOR ---

export function initNetworkModule() {
    // Modal buttons
    DOM_ELEMENTS.addIpBtn?.addEventListener('click', openAddIpModal);
    DOM_ELEMENTS.addNatBtn?.addEventListener('click', openAddNatModal);
}
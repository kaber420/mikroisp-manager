// static/js/router_details/network.js
import { ApiClient, DomUtils } from './utils.js';
import { CONFIG, DOM_ELEMENTS } from './config.js';
import { TableComponent } from '../components/TableComponent.js';

// --- ESTADO LOCAL ---
let ipTable = null;
let natTable = null;

// --- MANEJADORES (HANDLERS) ---

const handleAddIp = async (e) => {
    e.preventDefault();
    try {
        const data = new FormData(DOM_ELEMENTS.addIpForm);
        const comment = "Managed by µMonitor";
        await ApiClient.request(`/api/routers/${CONFIG.currentHost}/write/add-ip`, {
            method: 'POST',
            body: JSON.stringify({ interface: data.get('interface'), address: data.get('address'), comment: comment })
        });
        DomUtils.updateFeedback('IP Añadida', true);
        DOM_ELEMENTS.addIpForm.reset();
        await window.loadFullDetailsData(); // Recargar todo
    } catch (err) { DomUtils.updateFeedback(err.message, false); }
};

const handleAddNat = async (e) => {
    e.preventDefault();
    try {
        const data = new FormData(DOM_ELEMENTS.addNatForm);
        await ApiClient.request(`/api/routers/${CONFIG.currentHost}/write/add-nat`, {
            method: 'POST',
            body: JSON.stringify({ out_interface: data.get('out-interface'), comment: data.get('comment') })
        });
        DomUtils.updateFeedback('NAT Añadido', true);
        DOM_ELEMENTS.addNatForm.reset();
        await window.loadFullDetailsData(); // Recargar todo
    } catch (err) { DomUtils.updateFeedback(err.message, false); }
};

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

    // El contenedor original es un div con clases de lista, lo limpiamos y dejamos que la tabla tome control
    // OJO: Si el CSS espera items flex, la tabla podría verse rara si no quitamos las clases del contenedor padre.
    // Pero TableComponent reemplaza el innerHTML.
    ipTable.render(ips, DOM_ELEMENTS.ipAddressList);
}

function renderNatRules(rules = []) {
    if (!DOM_ELEMENTS.natRulesList) return;

    if (!natTable) {
        natTable = new TableComponent({
            columns: ['Comment', 'Out-Interface', 'Action'],
            emptyMessage: 'No NAT rules found.',
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

// --- CARGADOR DE DATOS ---

export function loadNetworkData(fullDetails) {
    if (fullDetails) {
        renderIpAddresses(fullDetails.ip_addresses);
        renderNatRules(fullDetails.nat_rules);
        populateInterfaceSelects(fullDetails.interfaces);
    }
}

function populateInterfaceSelects(interfaces) {
    const selects = document.querySelectorAll('.interface-select');
    if (!selects.length) return;
    const options = interfaces.length ? '<option value="">Seleccionar...</option>' + interfaces
        .filter(i => ['ether', 'bridge', 'vlan'].includes(i.type))
        .map(i => `<option value="${i.name}">${i.name}</option>`).join('') : '<option value="">Error</option>';
    selects.forEach(s => s.innerHTML = options);
}

// --- INICIALIZADOR ---

export function initNetworkModule() {
    DOM_ELEMENTS.addIpForm?.addEventListener('submit', handleAddIp);
    DOM_ELEMENTS.addNatForm?.addEventListener('submit', handleAddNat);
}
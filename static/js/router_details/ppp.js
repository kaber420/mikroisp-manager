// static/js/router_details/ppp.js
import { ApiClient, DomUtils } from './utils.js';
import { CONFIG, DOM_ELEMENTS } from './config.js';
import { TableComponent } from '../components/TableComponent.js';

// --- ESTADO LOCAL ---
let pppoeTable = null;

// --- MANEJADORES (HANDLERS) ---

const handleAddPppoe = async (e) => {
    e.preventDefault();
    try {
        const data = new FormData(DOM_ELEMENTS.addPppoeForm);
        const payload = {
            service_name: data.get('service_name'),
            interface: data.get('interface'),
            default_profile: 'default',
            one_session_per_host: data.get('one_session_per_host') === 'on',
            keepalive_timeout: parseInt(data.get('keepalive_timeout'), 10) || 10
        };
        await ApiClient.request(`/api/routers/${CONFIG.currentHost}/write/add-pppoe-server`, {
            method: 'POST',
            body: JSON.stringify(payload)
        });
        DomUtils.updateFeedback('Servidor PPPoE Añadido', true);
        DOM_ELEMENTS.addPppoeForm.reset();
        await window.loadFullDetailsData(); // Recargar todo
    } catch (err) { DomUtils.updateFeedback(err.message, false); }
};

const handleAddPlan = async (e) => {
    e.preventDefault();
    try {
        const formData = new FormData(DOM_ELEMENTS.addPlanForm);
        const data = Object.fromEntries(formData);
        data.comment = "Managed by µMonitor";
        if (data.parent_queue === "none") delete data.parent_queue;

        // Lógica para pool
        const poolInputValue = data.pool_input;
        delete data.pool_input;

        // Detectar si es CIDR (contiene /), rango (contiene - y .), o nombre de pool
        if (poolInputValue && poolInputValue.includes('.')) {
            if (poolInputValue.includes('/')) {
                // Es CIDR - convertir a rango para MikroTik
                data.pool_range = cidrToRange(poolInputValue);
            } else if (poolInputValue.includes('-')) {
                // Es un rango directo
                data.pool_range = poolInputValue;
            } else {
                // Es un nombre de pool existente
                data.remote_address = poolInputValue;
            }
        } else if (poolInputValue) {
            // No tiene punto, es un nombre de pool
            data.remote_address = poolInputValue;
        }

        await ApiClient.request(`/api/routers/${CONFIG.currentHost}/write/create-plan`, { method: 'POST', body: JSON.stringify(data) });
        DomUtils.updateFeedback('Plan Creado', true);
        DOM_ELEMENTS.addPlanForm.reset();
        await window.loadFullDetailsData(); // Recargar todo
    } catch (err) { DomUtils.updateFeedback(err.message, false); }
};

/**
 * Convierte notación CIDR a rango de IPs para MikroTik.
 * Ejemplo: "192.168.69.0/24" -> "192.168.69.1-192.168.69.254"
 */
function cidrToRange(cidr) {
    const [ip, prefixStr] = cidr.split('/');
    const prefix = parseInt(prefixStr, 10);
    const octets = ip.split('.').map(Number);

    // Convertir IP a número de 32 bits
    const ipNum = (octets[0] << 24) | (octets[1] << 16) | (octets[2] << 8) | octets[3];

    // Calcular máscara y rango
    const mask = ~((1 << (32 - prefix)) - 1) >>> 0;
    const networkAddr = ipNum & mask;
    const broadcastAddr = networkAddr | (~mask >>> 0);

    // Primer IP usable (network + 1) y última IP usable (broadcast - 1)
    const firstUsable = networkAddr + 1;
    const lastUsable = broadcastAddr - 1;

    // Convertir de vuelta a octetos
    const toOctets = (num) => [
        (num >>> 24) & 255,
        (num >>> 16) & 255,
        (num >>> 8) & 255,
        num & 255
    ].join('.');

    return `${toOctets(firstUsable)}-${toOctets(lastUsable)}`;
}



const handleDeletePppoe = (service) => {
    DomUtils.confirmAndExecute(`¿Borrar el servidor PPPoE "${service}"?`, async () => {
        try {
            await ApiClient.request(`/api/routers/${CONFIG.currentHost}/write/delete-pppoe-server?service_name=${encodeURIComponent(service)}`, { method: 'DELETE' });
            DomUtils.updateFeedback('Servidor PPPoE Eliminado', true);
            await window.loadFullDetailsData(); // Recargar todo
        } catch (err) { DomUtils.updateFeedback(err.message, false); }
    });
};

const handleDeletePlan = (e) => {
    const planName = e.currentTarget.dataset.plan; // El nombre base, ej. "Plan-5M"
    DomUtils.confirmAndExecute(`¿Borrar el Plan "${planName}"? Esto eliminará el perfil y el pool asociado.`, async () => {
        try {
            // El API endpoint espera el nombre base, no el "profile-..."
            await ApiClient.request(`/api/routers/${CONFIG.currentHost}/write/delete-plan?plan_name=${encodeURIComponent(planName)}`, { method: 'DELETE' });
            DomUtils.updateFeedback('Plan Eliminado', true);
            await window.loadFullDetailsData(); // Recargar todo
        } catch (err) { DomUtils.updateFeedback(err.message, false); }
    });
};

// --- RENDERIZADORES ---

function renderPppProfiles(profiles) {
    DOM_ELEMENTS.pppProfileList.innerHTML = (!profiles || profiles.length === 0) ? '<p class="text-text-secondary col-span-full">No hay planes PPPoE.</p>' : '';
    profiles?.forEach(profile => {
        const isManaged = profile.comment && profile.comment.includes('µMonitor');
        const rateLimit = profile['rate-limit'] ? profile['rate-limit'] : 'N/A';
        const profileCard = document.createElement('div');
        profileCard.className = `bg-surface-2 rounded-lg p-4 border-l-4 border-primary transition-all hover:shadow-md`;
        profileCard.innerHTML = `
            <div class="flex justify-between items-start mb-2">
                <h4 class="font-bold text-lg text-text-primary">${profile.name}</h4>
                ${isManaged ? `<button class="delete-plan-btn text-text-secondary hover:text-danger" title="Eliminar plan" data-plan="${profile.name}" data-id="${profile['.id'] || profile.id}">${DOM_ELEMENTS.deleteIcon}</button>` : ''}
            </div>
            <div class="flex justify-between text-sm">
                <span class="text-text-secondary">Velocidad:</span>
                <span class="font-mono font-semibold text-text-primary">${rateLimit}</span>
            </div>
        `;
        DOM_ELEMENTS.pppProfileList.appendChild(profileCard);
    });
    document.querySelectorAll('.delete-plan-btn').forEach(btn => btn.addEventListener('click', handleDeletePlan));
}

function renderIpPools(pools) {
    DOM_ELEMENTS.ipPoolList.innerHTML = (!pools || pools.length === 0) ? '<p class="text-text-secondary">No hay pools.</p>' : '';
    pools?.forEach(pool => {
        DOM_ELEMENTS.ipPoolList.innerHTML += `<div class="flex justify-between items-center text-sm"><span>${pool.name}</span><span class="text-text-secondary font-mono">${pool.ranges}</span></div>`;
    });
}

function renderPppoeServers(servers) {
    if (!DOM_ELEMENTS.pppoeServerList) return;

    if (!pppoeTable) {
        pppoeTable = new TableComponent({
            columns: ['Service Name', 'Interface', 'Action'],
            emptyMessage: 'No PPPoE Servers found.',
            onAction: (action, payload) => {
                if (action === 'delete') handleDeletePppoe(payload.service);
            },
            renderRow: (server) => {
                return `
                    <tr>
                        <td>${server['service-name']}</td>
                        <td>${server.interface}</td>
                        <td>
                            <button class="btn-action-icon text-danger hover:text-red-400" 
                                    data-action="delete" 
                                    data-service="${server['service-name']}"
                                    title="Eliminar Servidor">
                                ${DOM_ELEMENTS.deleteIcon}
                            </button>
                        </td>
                    </tr>
                `;
            }
        });
    }

    pppoeTable.render(servers, DOM_ELEMENTS.pppoeServerList);
}

function populateIpPoolSelects(pools) {
    const datalist = document.getElementById('ip-pool-datalist');
    if (datalist && pools) {
        datalist.innerHTML = pools
            .map(pool => `<option value="${pool.name}">${pool.name} (${pool.ranges})</option>`)
            .join('');
    }
}

// --- CARGADOR DE DATOS ---

export function loadPppData(fullDetails) {
    if (fullDetails) {
        renderPppProfiles(fullDetails.ppp_profiles);
        renderIpPools(fullDetails.ip_pools);
        renderPppoeServers(fullDetails.pppoe_servers);
        populateIpPoolSelects(fullDetails.ip_pools);
    }
}

// --- INICIALIZADOR ---

export function initPppModule() {
    DOM_ELEMENTS.addPppoeForm?.addEventListener('submit', handleAddPppoe);
    DOM_ELEMENTS.addPlanForm?.addEventListener('submit', handleAddPlan);
}
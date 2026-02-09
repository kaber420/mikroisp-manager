// static/js/router_details/plans.js
import { ApiClient, DomUtils } from './utils.js';
// ModalUtils is available globally as window.ModalUtils
import { CONFIG, DOM_ELEMENTS } from './config.js';
import { TableComponent } from '../components/TableComponent.js';

// --- LOCAL STATE ---
let localPlansTable = null;
let currentPlans = []; // Store current plans for direct manipulation

// --- DEDICATED RELOAD FUNCTION ---

/**
 * Reload only the plans data without a full page reload
 */
async function reloadPlansOnly() {
    const routerHost = CONFIG.currentHost;
    if (!routerHost) return;

    try {
        // Add cache-busting timestamp
        const cacheBuster = `?_t=${Date.now()}`;
        const localPlans = await ApiClient.request(`/api/plans/router/${routerHost}${cacheBuster}`);
        currentPlans = localPlans;
        renderLocalPlans(localPlans);
        console.log('✅ Plans reloaded:', localPlans.length, 'plans');
    } catch (e) {
        console.error("Error recargando planes:", e);
    }
}

// --- RENDERERS ---

/**
 * Populate PPPoE profiles select for plan creation
 */
function populatePppoeProfilesSelect(profiles) {
    const profileSelect = document.getElementById('lp-profile-name');
    if (!profileSelect || !profiles) return;

    const options = profiles.map(profile =>
        `<option value="${profile.name}">${profile.name} ${profile['rate-limit'] ? '(' + profile['rate-limit'] + ')' : ''}</option>`
    ).join('');

    profileSelect.innerHTML = '<option value="">-- Seleccionar Perfil --</option>' + options;
}

/**
 * Populate parent queue selects for plan creation
 */
function populateParentQueueSelects(queues) {
    const parentQueues = queues?.filter(q => q.comment && q.comment.includes('[PARENT]')) || [];

    const parentOptions = parentQueues.map(queue =>
        `<option value="${queue.name}">${queue.name} (${queue['max-limit'] || 'N/A'})</option>`
    ).join('');

    const parentSelects = document.querySelectorAll('#lp-parent');
    parentSelects.forEach(select => {
        if (select) {
            const defaultValue = select.querySelector('option[value=""], option[value="none"]')?.outerHTML || '<option value="">-- Ninguna (Root) --</option>';
            select.innerHTML = defaultValue + parentOptions;
        }
    });
}

/**
 * Render local plans table
 */
function renderLocalPlans(plans) {
    if (!DOM_ELEMENTS.localPlansTableContainer) return;

    const container = DOM_ELEMENTS.localPlansTableContainer;

    if (!localPlansTable) {
        localPlansTable = new TableComponent({
            columns: ['Nombre', 'Precio', 'Tipo', 'Suspensión', 'Velocidad/Perfil', 'Acción'],
            emptyMessage: 'No hay planes locales definidos.',
            onAction: (action, payload) => {
                if (action === 'delete') handleDeletePlan(payload.id);
            },
            renderRow: (plan) => {
                const isPPPoE = plan.plan_type === 'pppoe';
                const typeBadge = isPPPoE
                    ? `<span class="px-2 py-0.5 rounded text-xs bg-purple-900 text-purple-200">PPPoE</span>`
                    : `<span class="px-2 py-0.5 rounded text-xs bg-blue-900 text-blue-200">Queue</span>`;

                const methodLabels = {
                    'pppoe_secret_disable': 'Disable Secret',
                    'address_list': 'Address List',
                    'queue_limit': 'Limit 1k/1k'
                };
                const methodLabel = methodLabels[plan.suspension_method] || plan.suspension_method || 'N/A';

                const speedOrProfile = isPPPoE
                    ? (plan.profile_name || '-')
                    : (plan.max_limit || '-');

                return `
                    <tr>
                        <td>${plan.name}</td>
                        <td class="font-mono text-green-400">$${plan.price || '0.00'}</td>
                        <td>${typeBadge}</td>
                        <td class="text-xs">${methodLabel}</td>
                        <td class="font-mono text-xs">${speedOrProfile}</td>
                        <td>
                            <button class="btn-action-icon text-danger hover:text-red-400" 
                                    data-action="delete" 
                                    data-id="${plan.id}"
                                    title="Eliminar Plan">
                                ${DOM_ELEMENTS.deleteIcon}
                            </button>
                        </td>
                    </tr>
                `;
            }
        });
    }

    localPlansTable.render(plans || [], container);
}

// --- SMART POLLING ---

/**
 * Polls the plans API until predicate is met.
 * @param {Function} predicate (list) => boolean
 * @param {number} maxAttempts Default 5
 * @param {number} intervalMs Default 1000
 */
async function smartReloadPlans(predicate, maxAttempts = 5, intervalMs = 1000) {
    for (let i = 0; i < maxAttempts; i++) {
        try {
            console.log(`🔄 Smart Polling Plans attempt ${i + 1}/${maxAttempts}...`);
            const routerHost = CONFIG.currentHost;
            const cacheBuster = `?_t=${Date.now()}`;
            const localPlans = await ApiClient.request(`/api/plans/router/${routerHost}${cacheBuster}`);

            if (predicate(localPlans)) {
                console.log('✅ Smart Polling Plans success!');
                currentPlans = localPlans;
                renderLocalPlans(localPlans);
                DomUtils.updateFeedback('Sincronización completada.', true);
                return;
            }
        } catch (e) { console.warn(e); }
        await new Promise(r => setTimeout(r, intervalMs));
    }
    console.warn('⚠️ Smart Polling Plans timed out.');
    await reloadPlansOnly();
    DomUtils.updateFeedback('Sincronización finalizada.', true);
}

// --- MODALS ---

/**
 * Current cached data for modal population
 */
let cachedProfiles = [];
let cachedQueues = [];

/**
 * Open Add Local Plan Modal
 */
let currentModal = null; // Store modal reference for closing

function openAddLocalPlanModal() {
    const template = document.getElementById('add-local-plan-form-template');
    if (!template) {
        console.error('Template add-local-plan-form-template not found');
        return;
    }

    const content = template.content.cloneNode(true);
    const container = document.createElement('div');
    container.appendChild(content);

    // Populate profile select with cached data
    const profileSelect = container.querySelector('#modal-lp-profile-name');
    if (profileSelect && cachedProfiles.length > 0) {
        const options = cachedProfiles.map(profile =>
            `<option value="${profile.name}">${profile.name} ${profile['rate-limit'] ? '(' + profile['rate-limit'] + ')' : ''}</option>`
        ).join('');
        profileSelect.innerHTML = '<option value="">-- Seleccionar Perfil --</option>' + options;
    }

    // Populate parent queue select with cached data
    const parentSelect = container.querySelector('#modal-lp-parent');
    if (parentSelect && cachedQueues.length > 0) {
        const parentQueues = cachedQueues.filter(q => q.comment && q.comment.includes('[PARENT]'));
        const options = parentQueues.map(queue =>
            `<option value="${queue.name}">${queue.name} (${queue['max-limit'] || 'N/A'})</option>`
        ).join('');
        parentSelect.innerHTML = '<option value="">-- Ninguna (Root) --</option>' + options;
    }

    currentModal = window.ModalUtils.showCustomModal({
        title: 'Definir Nuevo Plan Local',
        content: container.innerHTML,
        size: 'lg',
        modalId: 'add-local-plan-modal',
        actions: [
            {
                text: 'Cancelar',
                closeOnClick: true
            },
            {
                text: 'Guardar Plan',
                icon: 'save',
                primary: true,
                closeOnClick: false,
                handler: handleAddLocalPlanSubmit
            }
        ]
    });

    // Initialize Alpine.js on the new content
    setTimeout(() => {
        const modalContent = document.getElementById('add-local-plan-modal-content');
        if (modalContent && window.Alpine) {
            window.Alpine.initTree(modalContent);
        }
    }, 50);
}

// --- HANDLERS ---

/**
 * Handle add local plan modal form submission
 */
const handleAddLocalPlanSubmit = async () => {
    const form = document.getElementById('add-local-plan-form');
    if (!form) return;

    DomUtils.updateFeedback("Procesando...", true);

    const routerHost = CONFIG.currentHost;
    if (!routerHost) {
        DomUtils.updateFeedback("Error: No se pudo determinar el router actual.", false);
        return;
    }

    const formData = new FormData(form);
    const planType = formData.get('plan_type') || 'simple_queue';

    let suspensionMethod;
    if (planType === 'pppoe') {
        suspensionMethod = document.getElementById('modal-lp-suspension-pppoe')?.value || 'pppoe_secret_disable';
    } else {
        suspensionMethod = document.getElementById('modal-lp-suspension-sq')?.value || 'queue_limit';
    }

    const payload = {
        router_host: routerHost,
        name: formData.get('name'),
        price: parseFloat(formData.get('price')) || 0.0,
        max_limit: formData.get('max_limit') || '0',
        parent_queue: formData.get('parent_queue') || null,
        plan_type: planType,
        profile_name: planType === 'pppoe' ? formData.get('profile_name') : null,
        suspension_method: suspensionMethod,
        address_list_strategy: formData.get('address_list_strategy') || 'blacklist',
        address_list_name: formData.get('address_list_name') || 'morosos',
        comment: "Creado desde µMonitor UI"
    };

    try {
        await ApiClient.request('/api/plans', {
            method: 'POST',
            body: JSON.stringify(payload)
        });

        DomUtils.updateFeedback("Plan guardado correctamente. Sincronizando...", true);
        if (currentModal) currentModal.close();

        // Smart Polling: Wait until plan appears
        smartReloadPlans(list => list.find(p => p.name === payload.name));
    } catch (err) {
        DomUtils.updateFeedback(`Error guardando plan: ${err.message}`, false);
    }
};

/**
 * Handle delete plan
 */
const handleDeletePlan = (planId) => {
    DomUtils.confirmAndExecute("¿Eliminar este plan local?", async () => {
        try {
            await ApiClient.request(`/api/plans/${planId}`, { method: 'DELETE' });
            DomUtils.updateFeedback("Plan eliminado. Sincronizando...", true);

            // Smart Polling: Wait until plan is GONE
            smartReloadPlans(list => !list.find(p => p.id === planId));
        } catch (err) {
            DomUtils.updateFeedback(err.message, false);
        }
    });
};

// --- DATA LOADER ---

export async function loadPlansData(fullDetails) {
    if (fullDetails) {
        // Cache PPPoE profiles for modal
        cachedProfiles = fullDetails.ppp_profiles || [];

        // Cache queues for modal
        cachedQueues = fullDetails.simple_queues || [];

        // Load local plans
        const routerHost = CONFIG.currentHost;
        if (routerHost) {
            try {
                // Add cache-busting timestamp to prevent stale data
                const cacheBuster = `?_t=${Date.now()}`;
                const localPlans = await ApiClient.request(`/api/plans/router/${routerHost}${cacheBuster}`);
                renderLocalPlans(localPlans);
            } catch (e) {
                console.error("Error cargando planes locales:", e);
            }
        }
    }
}

// --- INITIALIZER ---

export function initPlansModule() {
    // Modal button
    document.getElementById('add-local-plan-btn')?.addEventListener('click', openAddLocalPlanModal);
}

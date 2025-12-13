// static/js/router_details/plans.js
import { ApiClient, DomUtils } from './utils.js';
import { CONFIG, DOM_ELEMENTS } from './config.js';
import { TableComponent } from '../components/TableComponent.js';

// --- LOCAL STATE ---
let localPlansTable = null;

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
    if (!DOM_ELEMENTS.localPlansTableBody) return;

    const container = DOM_ELEMENTS.localPlansTableBody.closest('.overflow-x-auto');
    if (!container) return;

    if (!localPlansTable) {
        localPlansTable = new TableComponent({
            columns: ['Nombre', 'Tipo', 'Suspensión', 'Velocidad/Perfil', 'Acción'],
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

// --- HANDLERS ---

/**
 * Handle create local plan form submission
 */
const handleCreateLocalPlan = async (e) => {
    e.preventDefault();
    DomUtils.updateFeedback("Procesando...", true);

    const routerHost = CONFIG.currentHost;
    if (!routerHost) {
        DomUtils.updateFeedback("Error: No se pudo determinar el router actual.", false);
        return;
    }

    const formData = new FormData(DOM_ELEMENTS.createLocalPlanForm);
    const planType = formData.get('plan_type') || 'simple_queue';

    let suspensionMethod;
    if (planType === 'pppoe') {
        suspensionMethod = document.getElementById('lp-suspension-method-pppoe')?.value || 'pppoe_secret_disable';
    } else {
        suspensionMethod = document.getElementById('lp-suspension-method-sq')?.value || 'queue_limit';
    }

    const payload = {
        router_host: routerHost,
        name: formData.get('name'),
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

        DomUtils.updateFeedback("Plan guardado correctamente", true);
        DOM_ELEMENTS.createLocalPlanForm.reset();
        await window.loadFullDetailsData();
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
            await window.loadFullDetailsData();
            DomUtils.updateFeedback("Plan eliminado", true);
        } catch (err) {
            DomUtils.updateFeedback(err.message, false);
        }
    });
};

// --- DATA LOADER ---

export async function loadPlansData(fullDetails) {
    if (fullDetails) {
        // Populate PPPoE profiles selector
        populatePppoeProfilesSelect(fullDetails.ppp_profiles);

        // Populate parent queue selects
        populateParentQueueSelects(fullDetails.simple_queues);

        // Load local plans
        const routerHost = CONFIG.currentHost;
        if (routerHost) {
            try {
                const localPlans = await ApiClient.request(`/api/plans/router/${routerHost}`);
                renderLocalPlans(localPlans);
            } catch (e) {
                console.error("Error cargando planes locales:", e);
            }
        }
    }
}

// --- INITIALIZER ---

export function initPlansModule() {
    DOM_ELEMENTS.createLocalPlanForm?.addEventListener('submit', handleCreateLocalPlan);
}

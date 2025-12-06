// static/js/router_details/queues.js
import { ApiClient, DomUtils } from './utils.js';
import { CONFIG, DOM_ELEMENTS, state } from './config.js';
import { TableComponent } from '../components/TableComponent.js';

// --- ESTADO LOCAL ---
let parentQueuesTable = null;
let localPlansTable = null;

// --- RENDERIZADORES ---

function renderQueueTargetOptions(interfaces) {
    const datalist = document.getElementById('q-target-datalist');
    if (!datalist) return;
    datalist.innerHTML = '';
    interfaces?.forEach(iface => {
        datalist.innerHTML += `<option value="${iface.name}"></option>`;
    });
}

function renderParentQueues(queues) {
    // Clasificar colas
    const parentQueues = queues?.filter(q => q.comment && q.comment.includes('[PARENT]')) || [];

    // Renderizar la lista visual de colas padre usando TableComponent
    if (DOM_ELEMENTS.parentQueueListDisplay) {
        if (!parentQueuesTable) {
            parentQueuesTable = new TableComponent({
                columns: ['Name', 'Max Limit', 'Action'],
                emptyMessage: 'No hay colas de infraestructura.',
                onAction: (action, payload) => {
                    if (action === 'delete') handleDeleteParentQueue(payload.id);
                },
                renderRow: (queue) => {
                    const bw = queue['max-limit'] || '0/0';
                    const queueId = queue['.id'] || queue.id;
                    return `
                        <tr>
                            <td>${queue.name}</td>
                            <td class="font-mono text-warning text-xs">${bw}</td>
                            <td>
                                <button class="btn-action-icon text-danger hover:text-red-400" 
                                        data-action="delete" 
                                        data-id="${queueId}"
                                        title="Eliminar Cola">
                                    ${DOM_ELEMENTS.deleteIcon}
                                </button>
                            </td>
                        </tr>
                    `;
                }
            });
        }
        parentQueuesTable.render(parentQueues, DOM_ELEMENTS.parentQueueListDisplay);
    }

    // Poblar los <select> de "Cola Padre" solo con las colas de infraestructura
    const parentOptions = parentQueues.map(queue =>
        `<option value="${queue.name}">${queue.name} (${queue['max-limit'] || 'N/A'})</option>`
    ).join('');

    // Asumiendo que pueden existir múltiples selectores para colas padre
    const parentSelects = document.querySelectorAll('#add-plan-parent_queue, #lp-parent');
    parentSelects.forEach(select => {
        if (select) {
            const defaultValue = select.querySelector('option[value="none"], option[value=""]') ? select.querySelector('option[value="none"], option[value=""]').outerHTML : '';
            select.innerHTML = defaultValue + parentOptions;
        }
    });
}

// --- NUEVO: Renderizar planes locales ---
function renderLocalPlans(plans) {
    if (!DOM_ELEMENTS.localPlansTableBody) return;

    // Buscamos el contenedor .overflow-x-auto que envuelve la tabla original
    const container = DOM_ELEMENTS.localPlansTableBody.closest('.overflow-x-auto');
    if (!container) return;

    if (!localPlansTable) {
        localPlansTable = new TableComponent({
            columns: ['Nombre', 'Velocidad', 'Padre', 'Acción'],
            emptyMessage: 'No hay planes locales definidos.',
            onAction: (action, payload) => {
                if (action === 'delete') handleDeletePlan(payload.id);
            },
            renderRow: (plan) => {
                return `
                    <tr>
                        <td>${plan.name}</td>
                        <td class="font-mono text-xs">${plan.max_limit}</td>
                        <td class="text-xs text-text-secondary">${plan.parent_queue || '-'}</td>
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

// --- MANEJADORES (HANDLERS) ---

const handleAddParentQueue = async (e) => {
    e.preventDefault();
    try {
        const formData = new FormData(DOM_ELEMENTS.addParentQueueForm);
        const isParent = formData.get('is_parent') === 'on';

        const payload = {
            name: formData.get('name'),
            max_limit: formData.get('max_limit'),
            target: formData.get('target'),
            comment: `Managed by µMonitor: ${formData.get('name')}`,
            is_parent: isParent
        };

        const response = await ApiClient.request(`/api/routers/${CONFIG.currentHost}/write/add-simple-queue`, {
            method: 'POST',
            body: JSON.stringify(payload)
        });

        const feedbackMessage = response?.message || 'Cola Creada con éxito';
        DomUtils.updateFeedback(feedbackMessage, true);
        DOM_ELEMENTS.addParentQueueForm.reset();
        document.getElementById('is-parent-checkbox').checked = true;

        await window.loadFullDetailsData();
    } catch (err) {
        DomUtils.updateFeedback(err.message, false);
    }
};

const handleDeleteParentQueue = (queueId) => {
    DomUtils.confirmAndExecute('¿Borrar esta cola?', async () => {
        try {
            await ApiClient.request(`/api/routers/${CONFIG.currentHost}/write/delete-simple-queue/${encodeURIComponent(queueId)}`, { method: 'DELETE' });
            DomUtils.updateFeedback('Cola Eliminada', true);
            await window.loadFullDetailsData();
        } catch (err) { DomUtils.updateFeedback(err.message, false); }
    });
};

// --- NUEVO: Manejador para crear Plan Local ---
const handleCreateLocalPlan = async (e) => {
    e.preventDefault();
    DomUtils.updateFeedback("Procesando...", true);

    // The router host is always known from the page context
    const routerHost = CONFIG.currentHost;
    if (!routerHost) {
        DomUtils.updateFeedback("Error: No se pudo determinar el router actual.", false);
        return;
    }

    // 1. Preparar datos
    const formData = new FormData(DOM_ELEMENTS.createLocalPlanForm);
    const payload = {
        router_host: routerHost, // Use the host string
        name: formData.get('name'),
        max_limit: formData.get('max_limit'),
        parent_queue: formData.get('parent_queue') || null,
        comment: "Creado desde µMonitor UI"
    };

    // 2. Enviar a la API
    try {
        await ApiClient.request('/api/plans', {
            method: 'POST',
            body: JSON.stringify(payload)
        });

        DomUtils.updateFeedback("Plan guardado correctamente", true);
        DOM_ELEMENTS.createLocalPlanForm.reset();
        await window.loadFullDetailsData(); // Recargar listas
    } catch (err) {
        DomUtils.updateFeedback(`Error guardando plan: ${err.message}`, false);
    }
};

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

// --- CARGADOR DE DATOS ---

export async function loadQueuesData(fullDetails) {
    // NO hacer llamada API a full-details - usar los datos que ya vienen de main.js
    if (fullDetails) {
        renderParentQueues(fullDetails.simple_queues);
        renderQueueTargetOptions(fullDetails.interfaces);

        // Load local plans using the router's host string
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

// --- INICIALIZADOR ---

export function initQueuesModule() {
    DOM_ELEMENTS.addParentQueueForm?.addEventListener('submit', handleAddParentQueue);
    // NUEVO: Registrar el listener para el formulario de planes locales
    DOM_ELEMENTS.createLocalPlanForm?.addEventListener('submit', handleCreateLocalPlan);
}
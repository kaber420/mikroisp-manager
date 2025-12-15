// static/js/router_details/queues.js
import { ApiClient, DomUtils } from './utils.js';
import { CONFIG, DOM_ELEMENTS } from './config.js';
import { TableComponent } from '../components/TableComponent.js';

// --- LOCAL STATE ---
let parentQueuesTable = null;

// --- RENDERERS ---

function renderQueueTargetOptions(interfaces) {
    const datalist = document.getElementById('q-target-datalist');
    if (!datalist) return;
    datalist.innerHTML = '';
    interfaces?.forEach(iface => {
        datalist.innerHTML += `<option value="${iface.name}"></option>`;
    });
}

function renderParentQueues(queues) {
    // Filter parent queues
    const parentQueues = queues?.filter(q => q.comment && q.comment.includes('[PARENT]')) || [];

    // Render parent queues table
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

    // Populate parent queue selects (for PPP tab plan form)
    const parentOptions = parentQueues.map(queue =>
        `<option value="${queue.name}">${queue.name} (${queue['max-limit'] || 'N/A'})</option>`
    ).join('');

    const parentSelects = document.querySelectorAll('#add-plan-parent_queue');
    parentSelects.forEach(select => {
        if (select) {
            const defaultValue = select.querySelector('option[value="none"], option[value=""]') ? select.querySelector('option[value="none"], option[value=""]').outerHTML : '';
            select.innerHTML = defaultValue + parentOptions;
        }
    });
}

// --- HANDLERS ---

const handleAddParentQueue = async (e) => {
    e.preventDefault();
    try {
        const formData = new FormData(DOM_ELEMENTS.addParentQueueForm);
        const isParent = formData.get('is_parent') === 'on';

        const payload = {
            name: formData.get('name'),
            max_limit: formData.get('max_limit'),
            target: formData.get('target'),
            comment: `Managed by µMonitor: ${formData.get('name')}${isParent ? ' [PARENT]' : ''}`,
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

// --- DATA LOADER ---

export async function loadQueuesData(fullDetails) {
    if (fullDetails) {
        renderParentQueues(fullDetails.simple_queues);
        renderQueueTargetOptions(fullDetails.interfaces);
    }
}

// --- INITIALIZER ---

export function initQueuesModule() {
    DOM_ELEMENTS.addParentQueueForm?.addEventListener('submit', handleAddParentQueue);
}

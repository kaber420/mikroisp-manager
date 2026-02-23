// static/js/router_details/queues.js
import { ApiClient, DomUtils } from './utils.js';
import { CONFIG, DOM_ELEMENTS } from './config.js';
import { TableComponent } from '../components/TableComponent.js';

// --- LOCAL STATE ---
let parentQueuesTable = null;
let activeAddParentQueueModal = null;

// --- MODAL FUNCTIONS ---

function openAddParentQueueModal() {
    const template = DOM_ELEMENTS.addParentQueueFormTemplate;
    if (!template) {
        console.error('Add Parent Queue form template not found');
        return;
    }

    const content = template.content.cloneNode(true);
    const wrapper = document.createElement('div');
    wrapper.appendChild(content);

    activeAddParentQueueModal = window.ModalUtils.showCustomModal({
        title: 'Crear Cola',
        content: wrapper,
        modalId: 'add-parent-queue-modal',
        size: 'md',
        actions: [
            {
                text: 'Cancelar',
                handler: () => { },
                closeOnClick: true
            },
            {
                text: 'Crear Cola',
                icon: 'add',
                primary: true,
                handler: () => handleAddParentQueueSubmit(activeAddParentQueueModal),
                closeOnClick: false
            }
        ]
    });
}

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
    const parentQueuesList = queues || []; // Mostrar todas las colas de MikroTik

    if (DOM_ELEMENTS.parentQueueListDisplay) {
        if (!parentQueuesTable) {
            parentQueuesTable = new TableComponent({
                columns: ['Tipo', 'Name', 'Target', 'Max Limit', 'Action'],
                emptyMessage: 'No hay colas configuradas.',
                tableClass: 'data-table w-full',
                onAction: (action, payload) => {
                    if (action === 'delete') handleDeleteParentQueue(payload.id);
                },
                renderRow: (queue) => {
                    const bw = queue['max-limit'] || '0/0';
                    const target = queue.target || 'N/A';
                    const queueId = queue['.id'] || queue.id;
                    const comment = queue.comment || '';

                    let badgeClass = 'badge badge-ghost badge-sm';
                    let badgeText = 'Ordinaria';

                    if (comment.includes('[PARENT]')) {
                        badgeClass = 'badge badge-primary badge-sm';
                        badgeText = 'Infraestructura';
                    } else if (comment.includes('Managed by µMonitor')) {
                        badgeClass = 'badge badge-success badge-sm';
                        badgeText = 'Cliente µMonitor';
                    }

                    return `
                        <tr>
                            <td><span class="${badgeClass}">${badgeText}</span></td>
                            <td>${queue.name}</td>
                            <td class="font-mono text-xs">${target}</td>
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
        parentQueuesTable.render(parentQueuesList, DOM_ELEMENTS.parentQueueListDisplay);
    }

    // Populate parent queue selects (for PPP tab plan form modal)
    // Only select queues marked as [PARENT] for the modal drop down
    const parentQueuesOptions = queues?.filter(q => q.comment && q.comment.includes('[PARENT]')) || [];
    const parentOptionsHtml = parentQueuesOptions.map(queue =>
        `<option value="${queue.name}">${queue.name} (${queue['max-limit'] || 'N/A'})</option>`
    ).join('');

    const parentSelects = document.querySelectorAll('#plan-parent-queue');
    parentSelects.forEach(select => {
        if (select) {
            select.innerHTML = '<option value="none">-- Sin Cola Padre --</option>' + parentOptionsHtml;
        }
    });
}

// --- HANDLERS ---

async function handleAddParentQueueSubmit(modalRef) {
    const form = document.getElementById('add-parent-queue-form');
    if (!form) return;

    const formData = new FormData(form);
    const name = formData.get('name');
    const maxLimit = formData.get('max_limit');
    const isParent = formData.get('is_parent') === 'on';

    if (!name || !maxLimit) {
        DomUtils.updateFeedback('Nombre y Max Limit son requeridos.', false);
        return;
    }

    try {
        const payload = {
            name: name,
            max_limit: maxLimit,
            target: formData.get('target') || '',
            comment: `Managed by µMonitor: ${name}${isParent ? ' [PARENT]' : ''}`,
            is_parent: isParent
        };

        const response = await ApiClient.request(`/api/routers/${CONFIG.currentHost}/write/add-simple-queue`, {
            method: 'POST',
            body: JSON.stringify(payload)
        });

        if (modalRef) modalRef.close();
        const feedbackMessage = response?.message || 'Cola Creada con éxito';
        DomUtils.updateFeedback(feedbackMessage, true);
        await window.loadFullDetailsData();
    } catch (err) {
        DomUtils.updateFeedback(err.message, false);
    }
}

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
    // Modal button
    DOM_ELEMENTS.addParentQueueBtn?.addEventListener('click', openAddParentQueueModal);
}

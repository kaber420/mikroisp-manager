import { ApiClient, DomUtils } from './utils.js';
import { CONFIG, DOM_ELEMENTS } from './config.js';

let activeEditRouterModal = null;

export function initEditRouter() {
    const editBtn = document.getElementById('edit-router-btn');

    if (!editBtn) {
        console.warn('Edit Router button not found.');
        return;
    }

    editBtn.addEventListener('click', async () => {
        openEditRouterModal();
    });
}

async function openEditRouterModal() {
    const template = DOM_ELEMENTS.editRouterFormTemplate;
    if (!template) {
        console.error('Edit Router form template not found');
        return;
    }

    const content = template.content.cloneNode(true);
    const wrapper = document.createElement('div');
    wrapper.appendChild(content);

    // Pre-populate form fields
    try {
        const data = await ApiClient.request(`/api/routers/${CONFIG.currentHost}`);
        wrapper.querySelector('#edit-r-host').value = data.host;
        wrapper.querySelector('#edit-r-username').value = data.username;
        wrapper.querySelector('#edit-r-api-port').value = data.api_port;
    } catch (e) {
        DomUtils.showToast(`Warning: Could not load latest router config (${e.message}). You can still repair SSL.`, 'warning');
        wrapper.querySelector('#edit-r-host').value = CONFIG.currentHost;
    }

    activeEditRouterModal = window.ModalUtils.showCustomModal({
        title: 'Editar Router',
        content: wrapper,
        modalId: 'edit-router-modal',
        size: 'lg',
        actions: [
            {
                text: 'Cancelar',
                handler: () => { },
                closeOnClick: true
            },
            {
                text: 'Guardar Cambios',
                icon: 'save',
                primary: true,
                handler: handleEditRouterFormSubmit,
                closeOnClick: false
            }
        ]
    });

    // Bind repair SSL button after modal is rendered
    setTimeout(() => {
        const repairBtn = document.getElementById('edit-repair-router-btn');
        if (repairBtn) {
            repairBtn.addEventListener('click', handleRepairSSL);
        }
    }, 50);
}

async function handleEditRouterFormSubmit() {
    const form = document.getElementById('edit-router-form');
    if (!form) return;

    const formData = new FormData(form);
    const payload = {
        username: formData.get('username'),
        api_port: parseInt(formData.get('api_port')),
    };
    const pass = formData.get('password');
    if (pass) payload.password = pass;

    try {
        await ApiClient.request(`/api/routers/${CONFIG.currentHost}`, 'PUT', payload);
        DomUtils.showToast('Router updated successfully', 'success');
        if (activeEditRouterModal) {
            activeEditRouterModal.close();
            activeEditRouterModal = null;
        }
        // Reload page to reflect changes
        setTimeout(() => window.location.reload(), 500);
    } catch (err) {
        DomUtils.showToast(`Error updating router: ${err.message}`, 'error');
    }
}

async function handleRepairSSL() {
    const host = document.getElementById('edit-r-host').value;
    const hostname = document.getElementById('main-hostname')?.textContent?.trim() || '';

    if (window.SSLActions) {
        await window.SSLActions.showRepairModal('router', host, hostname, () => {
            if (activeEditRouterModal) {
                activeEditRouterModal.close();
                activeEditRouterModal = null;
            }
            window.location.reload();
        });
    } else {
        console.error('SSLActions not loaded');
    }
}


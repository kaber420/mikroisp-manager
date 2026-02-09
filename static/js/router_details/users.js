// static/js/router_details/users.js
import { ApiClient, DomUtils } from './utils.js';
import { CONFIG, DOM_ELEMENTS } from './config.js';
import { TableComponent } from '../components/TableComponent.js';

// --- ESTADO LOCAL ---
let usersTable = null;
let activeAddUserModal = null;
let cachedAppUsers = []; // Cached for modal population

// --- MODAL FUNCTIONS ---

function openAddRouterUserModal() {
    const template = DOM_ELEMENTS.addRouterUserFormTemplate;
    if (!template) {
        console.error('Add Router User form template not found');
        return;
    }

    const content = template.content.cloneNode(true);
    const wrapper = document.createElement('div');
    wrapper.appendChild(content);

    // Populate app users select
    const appUserSelect = wrapper.querySelector('#modal-app-user-select');
    if (appUserSelect && cachedAppUsers?.length) {
        appUserSelect.innerHTML = '<option value="">Copiar de App...</option>' +
            cachedAppUsers.map(u => `<option value="${u.username}">${u.username}</option>`).join('');
    }

    // Setup app user select change handler
    const userNameInput = wrapper.querySelector('#modal-router-user-name');
    if (appUserSelect && userNameInput) {
        appUserSelect.addEventListener('change', () => {
            if (appUserSelect.value) {
                userNameInput.value = appUserSelect.value;
            }
        });
    }

    activeAddUserModal = window.ModalUtils.showCustomModal({
        title: 'Añadir Usuario Router',
        content: wrapper,
        modalId: 'add-router-user-modal',
        size: 'md',
        actions: [
            {
                text: 'Cancelar',
                handler: () => { },
                closeOnClick: true
            },
            {
                text: 'Añadir Usuario',
                icon: 'person_add',
                primary: true,
                handler: () => handleAddRouterUserSubmit(activeAddUserModal),
                closeOnClick: false
            }
        ]
    });
}

// --- RENDERIZADORES ---

function renderRouterUsers(users) {
    if (!DOM_ELEMENTS.routerUsersList) return;

    if (!usersTable) {
        usersTable = new TableComponent({
            columns: ['Name', 'Group', 'Action'],
            emptyMessage: 'No hay usuarios.',
            tableClass: 'data-table w-full',
            onAction: (action, payload) => {
                if (action === 'delete') handleDeleteRouterUser(payload.id);
            },
            renderRow: (user) => {
                // Asumiendo que no se puede borrar 'admin' o el usuario 'api-user'
                const isSystem = user.name === 'admin' || user.name === 'api-user';
                const userId = user['.id'] || user.id;

                let actionBtn = '';
                if (!isSystem) {
                    actionBtn = `
                        <button class="btn-action-icon text-danger hover:text-red-400" 
                                data-action="delete" 
                                data-id="${userId}"
                                title="Eliminar Usuario">
                            ${DOM_ELEMENTS.deleteIcon}
                        </button>
                    `;
                }

                return `
                    <tr>
                        <td class="font-semibold">${user.name}</td>
                        <td><span class="badge bg-light text-dark">${user.group}</span></td>
                        <td>${actionBtn}</td>
                    </tr>
                `;
            }
        });
    }

    usersTable.render(users || [], DOM_ELEMENTS.routerUsersList);
}

// --- MANEJADORES (HANDLERS) ---

async function handleAddRouterUserSubmit(modalRef) {
    const form = document.getElementById('add-router-user-form');
    if (!form) return;

    const u = document.getElementById('modal-router-user-name').value;
    const p = document.getElementById('modal-router-user-password').value;
    const g = document.getElementById('modal-router-user-group').value;

    if (!u || !p || !g) {
        DomUtils.updateFeedback('Todos los campos son requeridos.', false);
        return;
    }

    try {
        await ApiClient.request(`/api/routers/${CONFIG.currentHost}/system/users`, {
            method: 'POST',
            body: JSON.stringify({ username: u, password: p, group: g })
        });
        if (modalRef) modalRef.close();
        DomUtils.updateFeedback('Usuario creado', true);
        window.loadFullDetailsData();
    } catch (err) {
        DomUtils.updateFeedback(err.message, false);
    }
}

const handleDeleteRouterUser = (userId) => {
    DomUtils.confirmAndExecute('¿Borrar Usuario del Router?', async () => {
        try {
            await ApiClient.request(`/api/routers/${CONFIG.currentHost}/system/users/${encodeURIComponent(userId)}`, { method: 'DELETE' });
            DomUtils.updateFeedback('Usuario Eliminado', true);
            window.loadFullDetailsData();
        } catch (err) { DomUtils.updateFeedback(err.message, false); }
    });
};

// --- CARGADOR DE DATOS ---

export function loadUsersData(fullDetails) {
    // La data de usuarios del router ahora viene del loader principal
    if (fullDetails && fullDetails.users) {
        renderRouterUsers(fullDetails.users);
    }

    // La carga de usuarios de la app (para el dropdown) es separada
    ApiClient.request('/api/users')
        .then(users => {
            cachedAppUsers = users || [];
        })
        .catch(err => console.error("Error fetching app users:", err));
}

// --- INICIALIZADOR ---

export function initUsersModule() {
    // Modal button
    DOM_ELEMENTS.addRouterUserBtn?.addEventListener('click', openAddRouterUserModal);
}
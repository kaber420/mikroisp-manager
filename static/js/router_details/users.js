// static/js/router_details/users.js
import { ApiClient, DomUtils } from './utils.js';
import { CONFIG, DOM_ELEMENTS } from './config.js';
import { TableComponent } from '../components/TableComponent.js';

// --- ESTADO LOCAL ---
let usersTable = null;

// --- RENDERIZADORES ---

function renderRouterUsers(users) {
    if (!DOM_ELEMENTS.routerUsersList) return;

    if (!usersTable) {
        usersTable = new TableComponent({
            columns: ['Name', 'Group', 'Action'],
            emptyMessage: 'No hay usuarios.',
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

function populateAppUsers(users) {
    if (!DOM_ELEMENTS.appUserSelect) return;
    DOM_ELEMENTS.appUserSelect.innerHTML = '<option value="">Copiar de App...</option>' + users.map(u => `<option value="${u.username}">${u.username}</option>`).join('');
}


// --- MANEJADORES (HANDLERS) ---

const handleAddRouterUser = async (e) => {
    e.preventDefault();
    try {
        const u = document.getElementById('router-user-name').value;
        const p = document.getElementById('router-user-password').value;
        const g = document.getElementById('router-user-group').value;
        if (!u || !p || !g) {
            DomUtils.updateFeedback('Todos los campos son requeridos.', false);
            return;
        }
        await ApiClient.request(`/api/routers/${CONFIG.currentHost}/system/users`, {
            method: 'POST',
            body: JSON.stringify({ username: u, password: p, group: g })
        });
        DomUtils.updateFeedback('Usuario creado', true);
        DOM_ELEMENTS.addRouterUserForm.reset();
        window.loadFullDetailsData(); // Recargar todo
    } catch (err) { DomUtils.updateFeedback(err.message, false); }
};

const handleDeleteRouterUser = (userId) => {
    DomUtils.confirmAndExecute('¿Borrar Usuario del Router?', async () => {
        try {
            await ApiClient.request(`/api/routers/${CONFIG.currentHost}/system/users/${encodeURIComponent(userId)}`, { method: 'DELETE' });
            DomUtils.updateFeedback('Usuario Eliminado', true);
            window.loadFullDetailsData(); // Recargar todo
        } catch (err) { DomUtils.updateFeedback(err.message, false); }
    });
};

const handleAppUserSelectChange = () => {
    const userNameInput = document.getElementById('router-user-name');
    if (DOM_ELEMENTS.appUserSelect.value && userNameInput) {
        userNameInput.value = DOM_ELEMENTS.appUserSelect.value;
    }
};

// --- CARGADOR DE DATOS ---

export function loadUsersData(fullDetails) {
    // La data de usuarios del router ahora viene del loader principal
    if (fullDetails && fullDetails.users) {
        renderRouterUsers(fullDetails.users);
    }

    // La carga de usuarios de la app (para el dropdown) es separada y está bien así
    ApiClient.request('/api/users')
        .then(populateAppUsers)
        .catch(err => console.error("Error fetching app users:", err));
}

// --- INICIALIZADOR ---

export function initUsersModule() {
    DOM_ELEMENTS.addRouterUserForm?.addEventListener('submit', handleAddRouterUser);
    DOM_ELEMENTS.appUserSelect?.addEventListener('change', handleAppUserSelectChange);
}
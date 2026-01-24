import { ApiClient, DomUtils } from './utils.js';
import { CONFIG } from './config.js';

export function initEditRouter() {
    const editBtn = document.getElementById('edit-router-btn');
    const modal = document.getElementById('edit-router-modal');
    const form = document.getElementById('edit-router-form');
    const cancelBtn = document.getElementById('cancel-edit-router-btn');
    const repairBtn = document.getElementById('edit-repair-router-btn');

    if (!editBtn || !modal || !form) {
        console.warn('Edit Router elements not found.');
        return;
    }

    editBtn.addEventListener('click', async () => {
        // Populate form
        try {
            const data = await ApiClient.request(`/api/routers/${CONFIG.currentHost}`);
            document.getElementById('edit-r-host').value = data.host;
            document.getElementById('edit-r-username').value = data.username;
            document.getElementById('edit-r-api-port').value = data.api_port;
            // Password is empty by default
        } catch (e) {
            DomUtils.showToast(`Warning: Could not load latest router config (${e.message}). You can still repair SSL.`, 'warning');
            // Fallback: Populate Host from CONFIG even if API fails
            document.getElementById('edit-r-host').value = CONFIG.currentHost;
        }

        // Always open modal (unless critical error prevents even this)
        modal.classList.remove('hidden');
        modal.classList.add('flex');
    });

    const closeModal = () => {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
        form.reset();
    };

    cancelBtn.addEventListener('click', closeModal);

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
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
            closeModal();
            // Reload page to reflect changes
            setTimeout(() => window.location.reload(), 500);
        } catch (err) {
            DomUtils.showToast(`Error updating router: ${err.message}`, 'error');
        }
    });

    if (repairBtn) {
        repairBtn.addEventListener('click', async () => {
            const host = document.getElementById('edit-r-host').value;
            const hostname = document.getElementById('main-hostname').textContent.trim();

            if (window.SSLActions) {
                await window.SSLActions.showRepairModal('router', host, hostname, () => {
                    closeModal();
                    window.location.reload();
                });
            } else {
                console.error('SSLActions not loaded');
            }
        });
    }
}

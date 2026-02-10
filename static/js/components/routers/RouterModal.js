/**
 * Router Modal Component - Alpine.js Component
 *
 * Handles the Add/Edit Router modal form.
 * Uses $store.routers for state and ModalUtils for shell.
 *
 * Usage: Called via openRouterModalViaUtils(router) from RouterList.
 */

// --- Global modal handle ---
let activeRouterModal = null;

function openRouterModalViaUtils(router = null) {
    if (activeRouterModal) {
        activeRouterModal.close();
        activeRouterModal = null;
    }

    // Prepare store state first
    Alpine.store('routers').openModal(router);

    const template = document.getElementById('router-modal-template');
    if (!template) {
        console.error('Router modal template not found');
        return;
    }

    const content = template.content.cloneNode(true);
    const wrapper = content.firstElementChild;

    const isEditing = Alpine.store('routers').isEditing;
    const title = isEditing ? 'Edit Router' : 'Add New Router';

    activeRouterModal = window.ModalUtils.showCustomModal({
        title: title,
        content: wrapper,
        modalId: 'router-modal',
        size: 'lg',
        actions: [
            {
                text: 'Cancel',
                handler: () => {
                    Alpine.store('routers').closeModal();
                }
            },
            {
                text: isEditing ? 'Save Changes' : 'Save Router',
                primary: true,
                icon: 'save',
                closeOnClick: false,
                handler: () => {
                    const modalEl = document.getElementById('router-modal');
                    if (modalEl) {
                        const form = modalEl.querySelector('form');
                        if (form) form.requestSubmit();
                    }
                }
            }
        ]
    });

    const modalEl = document.getElementById('router-modal');
    if (!modalEl) return;

    const alpineRoot = modalEl.querySelector('[x-data="routerModal()"]');
    if (alpineRoot) {
        Alpine.initTree(alpineRoot);
    }
}

window.openRouterModalViaUtils = openRouterModalViaUtils;

// --- Alpine Component ---
document.addEventListener('alpine:init', () => {
    Alpine.data('routerModal', () => ({
        get isEditing() {
            return Alpine.store('routers').isEditing;
        },

        get currentRouter() {
            return Alpine.store('routers').currentRouter;
        },

        set currentRouter(val) {
            Alpine.store('routers').currentRouter = val;
        },

        get error() {
            return Alpine.store('routers').error;
        },

        get allZones() {
            return Alpine.store('routers').allZones;
        },

        close() {
            Alpine.store('routers').closeModal();
            if (activeRouterModal) {
                activeRouterModal.close();
                activeRouterModal = null;
            }
        },

        async save() {
            await Alpine.store('routers').save();
            if (!Alpine.store('routers').error) {
                if (activeRouterModal) {
                    activeRouterModal.close();
                    activeRouterModal = null;
                }
            }
        },

        async renewSSL() {
            if (!this.currentRouter?.host) return;

            const hostname = this.currentRouter.hostname || this.currentRouter.host;
            const confirmed = await window.ModalUtils.showConfirmModal({
                title: 'Renovar Certificado SSL',
                message: `¿Renovar certificado SSL para "<strong>${hostname}</strong>"?<br><br>Esto reinstalará el certificado sin cambiar usuario/contraseña.`,
                confirmText: 'Renovar SSL',
                confirmIcon: 'sync_lock',
                type: 'primary',
            });

            if (confirmed) {
                const result = await window.SSLActions.renew('router', this.currentRouter.host);
                if (result.success) {
                    this.close();
                    Alpine.store('routers').loadData();
                }
            }
        },

        async unlinkRouter() {
            if (!this.currentRouter?.host) return;

            const hostname = this.currentRouter.hostname || this.currentRouter.host;
            const confirmed = await window.ModalUtils.showConfirmModal({
                title: 'Desvincular Router',
                message: `¿Desvincular el router "<strong>${hostname}</strong>"?<br><br>Esto lo marcará como no aprovisionado para re-configurar.`,
                confirmText: 'Desvincular',
                confirmIcon: 'link_off',
                type: 'warning',
            });

            if (confirmed) {
                const result = await window.SSLActions.unprovision('router', this.currentRouter.host);
                if (result.success) {
                    this.close();
                    Alpine.store('routers').loadData();
                }
            }
        }
    }));

    console.log('[Component] RouterModal initialized');
});

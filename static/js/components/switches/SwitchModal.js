/**
 * Switch Modal Component - Alpine.js Component
 *
 * Handles the Add/Edit Switch modal form.
 * Uses $store.switches for state and ModalUtils for shell.
 *
 * Usage: Called via openSwitchModalViaUtils(sw) from SwitchList.
 */

// --- Global modal handle ---
let activeSwitchModal = null;

function openSwitchModalViaUtils(sw = null) {
    // Close any existing instance
    if (activeSwitchModal) {
        activeSwitchModal.close();
        activeSwitchModal = null;
    }

    // Prepare store state first
    Alpine.store('switches').openModal(sw);

    const template = document.getElementById('switch-modal-template');
    if (!template) {
        console.error('Switch modal template not found');
        return;
    }

    const content = template.content.cloneNode(true);
    const wrapper = content.firstElementChild;

    const isEditing = Alpine.store('switches').isEditing;
    const title = isEditing ? 'Edit Switch' : 'Add New Switch';

    activeSwitchModal = window.ModalUtils.showCustomModal({
        title: title,
        content: wrapper,
        modalId: 'switch-modal',
        size: 'lg',
        actions: [
            {
                text: 'Cancel',
                handler: () => {
                    Alpine.store('switches').closeModal();
                }
            },
            {
                text: isEditing ? 'Save Changes' : 'Save Switch',
                primary: true,
                icon: 'save',
                closeOnClick: false,
                handler: () => {
                    const modalEl = document.getElementById('switch-modal');
                    if (modalEl) {
                        const form = modalEl.querySelector('form');
                        if (form) form.requestSubmit();
                    }
                }
            }
        ]
    });

    // Find and init Alpine on the injected content
    const modalEl = document.getElementById('switch-modal');
    if (!modalEl) return;

    const alpineRoot = modalEl.querySelector('[x-data="switchModal()"]');
    if (alpineRoot) {
        Alpine.initTree(alpineRoot);
    }
}

// Expose globally
window.openSwitchModalViaUtils = openSwitchModalViaUtils;

// --- Alpine Component ---
document.addEventListener('alpine:init', () => {
    Alpine.data('switchModal', () => ({
        // --- Computed Helpers ---
        get isEditing() {
            return Alpine.store('switches').isEditing;
        },

        get currentSwitch() {
            return Alpine.store('switches').currentSwitch;
        },

        set currentSwitch(val) {
            Alpine.store('switches').currentSwitch = val;
        },

        get error() {
            return Alpine.store('switches').error;
        },

        get allZones() {
            return Alpine.store('switches').allZones;
        },

        // --- Actions ---
        close() {
            Alpine.store('switches').closeModal();
            if (activeSwitchModal) {
                activeSwitchModal.close();
                activeSwitchModal = null;
            }
        },

        async save() {
            await Alpine.store('switches').save();
            // If save was successful (no error), close the modal
            if (!Alpine.store('switches').error) {
                if (activeSwitchModal) {
                    activeSwitchModal.close();
                    activeSwitchModal = null;
                }
            }
        },

        async renewSSL() {
            if (!this.currentSwitch?.host) return;

            const hostname = this.currentSwitch.hostname || this.currentSwitch.host;
            const confirmed = await window.ModalUtils.showConfirmModal({
                title: 'Renovar Certificado SSL',
                message: `¿Renovar certificado SSL para "<strong>${hostname}</strong>"?<br><br>Esto reinstalará el certificado sin cambiar usuario/contraseña.`,
                confirmText: 'Renovar SSL',
                confirmIcon: 'sync_lock',
                type: 'primary',
            });

            if (confirmed) {
                const result = await window.SSLActions.renew('switch', this.currentSwitch.host);
                if (result.success) {
                    this.close();
                    Alpine.store('switches').loadData();
                }
            }
        },

        async unlinkSwitch() {
            if (!this.currentSwitch?.host) return;

            const hostname = this.currentSwitch.hostname || this.currentSwitch.host;
            const confirmed = await window.ModalUtils.showConfirmModal({
                title: 'Desvincular Switch',
                message: `¿Desvincular el switch "<strong>${hostname}</strong>"?<br><br>Esto lo marcará como no aprovisionado para re-configurar.`,
                confirmText: 'Desvincular',
                confirmIcon: 'link_off',
                type: 'warning',
            });

            if (confirmed) {
                const result = await window.SSLActions.unprovision('switch', this.currentSwitch.host);
                if (result.success) {
                    this.close();
                    Alpine.store('switches').loadData();
                }
            }
        }
    }));

    console.log('[Component] SwitchModal initialized');
});

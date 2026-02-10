/**
 * Plan Modal Component - Alpine.js Component
 *
 * Handles the Plans Management modal.
 * Uses $store.plans for state and ModalUtils for shell.
 *
 * Usage: Called via openPlanModalViaUtils() from RouterList.
 */

// --- Global modal handle ---
let activePlanModal = null;

function openPlanModalViaUtils() {
    if (activePlanModal) {
        activePlanModal.close();
        activePlanModal = null;
    }

    // Prepare store state
    Alpine.store('plans').openModal();

    const template = document.getElementById('plan-modal-template');
    if (!template) {
        console.error('Plan modal template not found');
        return;
    }

    const content = template.content.cloneNode(true);
    const wrapper = content.firstElementChild;

    activePlanModal = window.ModalUtils.showCustomModal({
        title: 'Manage Plans',
        content: wrapper,
        modalId: 'plan-modal',
        size: 'xl',
        actions: [
            {
                text: 'Close',
                handler: () => {
                    Alpine.store('plans').closeModal();
                }
            }
        ]
    });

    const modalEl = document.getElementById('plan-modal');
    if (!modalEl) return;

    const alpineRoot = modalEl.querySelector('[x-data="planModal()"]');
    if (alpineRoot) {
        Alpine.initTree(alpineRoot);
    }
}

window.openPlanModalViaUtils = openPlanModalViaUtils;

// --- Alpine Component ---
document.addEventListener('alpine:init', () => {
    Alpine.data('planModal', () => ({
        get showForm() {
            return Alpine.store('plans').showForm;
        },

        get isEditing() {
            return Alpine.store('plans').isEditing;
        },

        get currentPlan() {
            return Alpine.store('plans').currentPlan;
        },

        set currentPlan(val) {
            Alpine.store('plans').currentPlan = val;
        },

        get error() {
            return Alpine.store('plans').error;
        },

        get plans() {
            return Alpine.store('plans').list;
        },

        get routers() {
            return Alpine.store('routers').list;
        },

        close() {
            Alpine.store('plans').closeModal();
            if (activePlanModal) {
                activePlanModal.close();
                activePlanModal = null;
            }
        },

        openForm(plan = null) {
            Alpine.store('plans').openForm(plan);
        },

        closeForm() {
            Alpine.store('plans').closeForm();
        },

        async save() {
            await Alpine.store('plans').save();
        },

        editPlan(plan) {
            Alpine.store('plans').openForm(plan);
        },

        deletePlan(plan) {
            Alpine.store('plans').delete(plan);
        }
    }));

    console.log('[Component] PlanModal initialized');
});

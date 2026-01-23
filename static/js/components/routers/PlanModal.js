/**
 * Plan Modal Component - Alpine.js Component
 *
 * Handles the Plans Management modal.
 * Uses $store.plans for state.
 *
 * Usage:
 *   <div x-data="planModal()">...</div>
 */
document.addEventListener('alpine:init', () => {
    Alpine.data('planModal', () => ({
        // --- Computed Helpers ---
        get isOpen() {
            return Alpine.store('plans').isModalOpen;
        },

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

        // --- Actions ---
        close() {
            Alpine.store('plans').closeModal();
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

/**
 * Plan Store - Alpine.js Global Store
 *
 * Shared state for plan-related components. Registered with Alpine.store().
 *
 * Usage in Alpine components:
 *   Alpine.store('plans').list
 *   Alpine.store('plans').loadPlans()
 */
document.addEventListener('alpine:init', () => {
    Alpine.store('plans', {
        // --- State ---
        list: [],

        // Modal state
        isModalOpen: false,
        showForm: false,
        isEditing: false,
        currentPlan: {},
        error: '',

        // --- Actions ---
        async loadPlans() {
            try {
                const response = await fetch('/api/plans');
                if (!response.ok) throw new Error('Failed to load plans');
                this.list = await response.json();
            } catch (error) {
                console.error('Error loading plans:', error);
                showToast(`Error: ${error.message}`, 'danger');
            }
        },

        getDefaultPlan() {
            return {
                name: '',
                max_limit: '',
                router_host: '',
                price: 0,
                plan_type: 'simple_queue',
                parent_queue: 'none',
                v6_queue_type: 'default-small',
                v7_queue_type: 'cake-default',
                profile_name: '',
            };
        },

        // --- Modal Actions ---
        async openModal() {
            this.isModalOpen = true;
            await this.loadPlans();
        },

        closeModal() {
            this.isModalOpen = false;
            this.showForm = false;
            this.currentPlan = {};
            this.error = '';
        },

        openForm(plan = null) {
            this.error = '';
            if (plan) {
                this.isEditing = true;
                this.currentPlan = { ...plan };
            } else {
                this.isEditing = false;
                this.currentPlan = this.getDefaultPlan();
            }
            this.showForm = true;
        },

        closeForm() {
            this.showForm = false;
            this.currentPlan = {};
            this.error = '';
            this.isEditing = false;
        },

        async save() {
            this.error = '';
            if (!this.currentPlan.name || !this.currentPlan.max_limit) {
                this.error = 'Please fill in all required fields.';
                return;
            }

            // Convert empty router_host to null for Universal Plans
            const planData = { ...this.currentPlan };
            if (planData.router_host === '') {
                planData.router_host = null;
            }

            try {
                let response;
                if (this.isEditing) {
                    // For now, delete and recreate (simple approach)
                    // TODO: Add PUT endpoint in API
                    await fetch(`/api/plans/${this.currentPlan.id}`, { method: 'DELETE' });
                    response = await fetch('/api/plans', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(planData)
                    });
                } else {
                    response = await fetch('/api/plans', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(planData)
                    });
                }

                if (!response.ok) {
                    const err = await response.json();
                    throw new Error(err.detail || 'Failed to save plan');
                }

                showToast(this.isEditing ? 'Plan updated successfully!' : 'Plan created successfully!', 'success');
                await this.loadPlans();
                this.closeForm();
            } catch (error) {
                this.error = error.message;
            }
        },

        async delete(plan) {
            window.ModalUtils.showConfirmModal({
                title: 'Delete Plan',
                message: `Are you sure you want to delete the plan "<strong>${plan.name}</strong>"?`,
                confirmText: 'Delete',
                confirmIcon: 'delete',
                type: 'danger',
            }).then(async (confirmed) => {
                if (confirmed) {
                    try {
                        const response = await fetch(`/api/plans/${plan.id}`, { method: 'DELETE' });
                        if (!response.ok) {
                            const err = await response.json();
                            throw new Error(err.detail || 'Failed to delete plan');
                        }
                        showToast('Plan deleted successfully!', 'success');
                        this.list = this.list.filter(p => p.id !== plan.id);
                    } catch (error) {
                        showToast(`Error: ${error.message}`, 'danger');
                    }
                }
            });
        }
    });

    console.log('[Store] PlanStore initialized');
});

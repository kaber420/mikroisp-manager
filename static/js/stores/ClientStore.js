/**
 * Client Store - Alpine.js Global Store
 * 
 * Shared state for client-related components. Registered with Alpine.store().
 * 
 * Usage in Alpine components:
 *   Alpine.store('client').clientId
 *   Alpine.store('client').setClient(data)
 */
document.addEventListener('alpine:init', () => {
    Alpine.store('client', {
        // --- State ---
        clientId: window.location.pathname.split('/').pop(),
        clientData: null,
        allServices: [],
        allPlans: [],
        paidMonthsSet: new Set(),
        currentYear: new Date().getFullYear(),

        // --- Computed/Getters ---
        get billingDay() {
            return (this.allServices && this.allServices.length > 0)
                ? (this.allServices[0].billing_day || 1)
                : 1;
        },

        // --- Actions ---
        setClient(data) {
            this.clientData = data;
        },

        setServices(services) {
            this.allServices = services;
        },

        setPlans(plans) {
            this.allPlans = plans;
        },

        addPaidMonth(month) {
            this.paidMonthsSet.add(month);
        },

        clearPaidMonths() {
            this.paidMonthsSet.clear();
        },

        isMonthPaid(yearMonth) {
            return this.paidMonthsSet.has(yearMonth);
        },

        prevYear() {
            this.currentYear--;
        },

        nextYear() {
            this.currentYear++;
        }
    });

    console.log('[Store] ClientStore initialized');
});

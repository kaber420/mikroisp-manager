// static/js/router_details/components.js

document.addEventListener('alpine:init', () => {

    // Component for managing the main tabs in Router Details
    Alpine.data('routerTabs', () => ({
        activeTab: 'overview',

        init() {
            // Optional: Check URL hash to set initial tab
            const hash = window.location.hash.replace('#', '');
            if (hash && ['overview', 'interfaces', 'network', 'ppp', 'queues', 'plans', 'users', 'backup'].includes(hash)) {
                this.activeTab = hash;
            }

            // Update URL hash when tab changes
            this.$watch('activeTab', (value) => {
                window.location.hash = value;
            });
        }
    }));

    // Component for the "Create Local Plan" form
    Alpine.data('localPlanForm', () => ({
        planType: 'simple_queue',

        init() {
            // Future logic for form validation or resetting can go here
        }
    }));
});

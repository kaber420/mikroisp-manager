document.addEventListener('alpine:init', () => {
    Alpine.data('switchVlanList', () => ({
        get vlans() {
            return Alpine.store('switchDetails').vlans;
        },
        get isLoading() {
            return Alpine.store('switchDetails').isLoading;
        }
    }));

    console.log('[Component] SwitchVlanList initialized');
});

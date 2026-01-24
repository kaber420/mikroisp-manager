document.addEventListener('alpine:init', () => {
    Alpine.data('switchInterfaceList', () => ({
        get interfaces() {
            return Alpine.store('switchDetails').interfaces;
        },
        get isLoading() {
            return Alpine.store('switchDetails').isLoading;
        },
        formatBytes(bytes) {
            return Alpine.store('switchDetails').formatBytes(bytes);
        }
    }));

    console.log('[Component] SwitchInterfaceList initialized');
});

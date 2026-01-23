/**
 * CPE List Component - Alpine.js Component
 *
 * Displays connected CPE clients reactively.
 * Uses $store.apDetails for state.
 *
 * Usage:
 *   <div x-data="cpeList()">...</div>
 */
document.addEventListener('alpine:init', () => {
    Alpine.data('cpeList', () => ({
        // --- Computed Helpers ---
        get cpes() {
            return Alpine.store('apDetails').cpes;
        },

        get liveCpes() {
            return Alpine.store('apDetails').liveCpes;
        },

        get isDiagnosticActive() {
            return Alpine.store('apDetails').isDiagnosticActive;
        },

        get currentVendor() {
            return Alpine.store('apDetails').currentVendor;
        },

        // --- CPE Processing ---
        get liveMacsSet() {
            return new Set(this.liveCpes.map(cpe => cpe.cpe_mac));
        },

        isOnline(cpe) {
            return this.liveMacsSet.has(cpe.cpe_mac);
        },

        getDisplayCPE(cpe) {
            if (this.isOnline(cpe)) {
                return this.liveCpes.find(lc => lc.cpe_mac === cpe.cpe_mac) || cpe;
            }
            return cpe;
        },

        getCPEHealthStatus(cpe) {
            const displayCPE = this.getDisplayCPE(cpe);
            const isOnline = this.isOnline(cpe);

            if (!isOnline) {
                return { colorClass: 'border-text-secondary', label: 'Offline', icon: 'signal_cellular_off' };
            }

            return Alpine.store('apDetails').getCPEHealthStatus(displayCPE);
        },

        getCardClasses(cpe) {
            const health = this.getCPEHealthStatus(cpe);
            const isOnline = this.isOnline(cpe);
            let classes = 'bg-surface-1 rounded-lg border-l-4 p-4 flex flex-col gap-3 transition-all hover:shadow-lg';
            if (!isOnline) {
                classes += ' opacity-50';
            }
            return `${classes} ${health.colorClass}`;
        },

        // --- Formatters ---
        formatBytes(bytes) {
            return Alpine.store('apDetails').formatBytes(bytes);
        },

        formatThroughput(kbps) {
            if (kbps == null) return 'N/A';
            return `${kbps.toFixed(1)}`;
        },

        formatSignalChains(cpe) {
            const displayCPE = this.getDisplayCPE(cpe);
            if (displayCPE.signal_chain0 != null && displayCPE.signal_chain1 != null) {
                return `(${displayCPE.signal_chain0}/${displayCPE.signal_chain1})`;
            }
            return '';
        },

        formatCableStatus(cpe) {
            const displayCPE = this.getDisplayCPE(cpe);
            if (displayCPE.eth_speed != null) {
                return `${displayCPE.eth_speed} Mbps`;
            }
            return 'N/A';
        },

        formatCapacity(cpe) {
            const displayCPE = this.getDisplayCPE(cpe);
            const dl = displayCPE.dl_capacity ? (displayCPE.dl_capacity / 1000).toFixed(0) : 'N/A';
            const ul = displayCPE.ul_capacity ? (displayCPE.ul_capacity / 1000).toFixed(0) : 'N/A';
            return `${dl} / ${ul} Mbps`;
        },

        formatLastSeen(cpe) {
            const date = new Date(cpe.timestamp);
            return new Intl.DateTimeFormat(navigator.language, {
                day: 'numeric',
                month: 'short',
                hour: '2-digit',
                minute: '2-digit'
            }).format(date);
        }
    }));

    console.log('[Component] CpeList initialized');
});

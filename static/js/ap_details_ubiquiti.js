/**
 * AP Details - Ubiquiti Vendor Module
 * 
 * Implements window.APVendor interface for Ubiquiti-specific functionality:
 * - Airtime usage (Total, TX, RX)
 * - GPS satellites
 * - AirMAX capacity metrics for CPEs
 */
(function () {
    'use strict';

    // ============================================================================
    // APVendor INTERFACE IMPLEMENTATION
    // ============================================================================
    window.APVendor = {
        /**
         * Initialize Ubiquiti-specific features
         */
        init: function (apData) {
            // Update Ubiquiti-specific fields if present
            updateUbiquitiFields(apData);
        },

        /**
         * Called when live data is received
         */
        onDataUpdate: function (apData) {
            // Update airtime field with full breakdown
            const airtimeTotal = apData.airtime_total_usage != null ? `${(apData.airtime_total_usage / 10.0).toFixed(1)}%` : 'N/A';
            const airtimeTx = apData.airtime_tx_usage != null ? `${(apData.airtime_tx_usage / 10.0).toFixed(1)}%` : 'N/A';
            const airtimeRx = apData.airtime_rx_usage != null ? `${(apData.airtime_rx_usage / 10.0).toFixed(1)}%` : 'N/A';

            const airtimeEl = document.getElementById('detail-airtime');
            if (airtimeEl) {
                airtimeEl.textContent = `${airtimeTotal} (Tx: ${airtimeTx} / Rx: ${airtimeRx})`;
            }

            // Update Ubiquiti-specific fields in partial
            updateUbiquitiFields(apData);
        },

        /**
         * Render CPE-specific columns for Ubiquiti (AirMAX Capacity)
         */
        renderCPEExtra: function (cpe) {
            const c_dl = cpe.dl_capacity ? (cpe.dl_capacity / 1000).toFixed(0) : 'N/A';
            const c_ul = cpe.ul_capacity ? (cpe.ul_capacity / 1000).toFixed(0) : 'N/A';
            return `
                <span>Capacity (DL/UL):</span><span class="font-semibold text-text-primary text-right">${c_dl} / ${c_ul} Mbps</span>
            `;
        },

        /**
         * Ubiquiti doesn't have Spectral Scan via API
         */
        isSpectralActive: function () {
            return false;
        },

        /**
         * Cleanup on page navigation
         */
        destroy: function () {
            // No cleanup needed for Ubiquiti
        }
    };

    // ============================================================================
    // UBIQUITI-SPECIFIC FIELD UPDATES
    // ============================================================================
    function updateUbiquitiFields(apData) {
        const airtimeTxEl = document.getElementById('detail-airtime-tx');
        const airtimeRxEl = document.getElementById('detail-airtime-rx');
        const gpsSatsEl = document.getElementById('detail-gps-sats');
        const devModelEl = document.getElementById('detail-devmodel');

        if (airtimeTxEl && apData.airtime_tx_usage != null) {
            airtimeTxEl.textContent = `${(apData.airtime_tx_usage / 10.0).toFixed(1)}%`;
        }
        if (airtimeRxEl && apData.airtime_rx_usage != null) {
            airtimeRxEl.textContent = `${(apData.airtime_rx_usage / 10.0).toFixed(1)}%`;
        }
        if (gpsSatsEl && apData.gps_sats != null) {
            gpsSatsEl.textContent = apData.gps_sats;
        }
        if (devModelEl && apData.model) {
            devModelEl.textContent = apData.model;
        }
    }

})();

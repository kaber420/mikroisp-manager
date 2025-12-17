/**
 * AP Details Core Module
 * 
 * Shared functionality for AP details page:
 * - Chart creation and updates
 * - Diagnostic (Live) mode polling
 * - Edit/Delete modals
 * - CPE list rendering
 * 
 * Vendor-specific modules should implement window.APVendor interface:
 * {
 *   init: function(),
 *   onDataUpdate: function(apData),
 *   renderCPEExtra: function(cpe) -> string,
 *   destroy: function()
 * }
 */
document.addEventListener('DOMContentLoaded', async () => {
    const API_BASE_URL = window.location.origin;
    const currentHost = window.location.pathname.split('/').pop();
    let charts = {};
    let isStopping = false;
    let currentPeriod = '24h';
    let currentVendor = 'ubiquiti';

    const deviceInfoCard = document.getElementById('device-info-card');
    const chartsCard = document.getElementById('charts-card');
    const clientListSection = document.getElementById('client-list-section');

    // Expose to vendor modules
    window.APDetailsCore = {
        API_BASE_URL,
        currentHost,
        charts,
        getCurrentVendor: () => currentVendor,
        isSpectralActive: () => window.APVendor?.isSpectralActive?.() || false
    };

    // ============================================================================
    // DIAGNOSTIC MODE MANAGER
    // ============================================================================
    let diagnosticManager = {
        intervalId: null, timeoutId: null, countdownId: null,
        stop: function (shouldUpdateUI = true) {
            if (this.intervalId) clearInterval(this.intervalId);
            if (this.timeoutId) clearTimeout(this.timeoutId);
            if (this.countdownId) clearInterval(this.countdownId);
            this.intervalId = null; this.timeoutId = null; this.countdownId = null;
            if (shouldUpdateUI) {
                const toggle = document.getElementById('auto-refresh-toggle');
                const timerSpan = document.getElementById('refresh-timer');
                if (toggle) toggle.checked = false;
                if (timerSpan) timerSpan.textContent = '';
                document.getElementById('main-hostname').classList.remove('text-orange');
            }
            console.log('Diagnostic mode stopped.');
        }
    };

    // ============================================================================
    // REACTIVE LISTENER (WebSocket Data Refresh)
    // ============================================================================
    window.addEventListener('data-refresh-needed', () => {
        // Don't reload during active operations
        if (!diagnosticManager.intervalId && !window.APDetailsCore.isSpectralActive()) {
            console.log("⚡ AP Details: Reloading data via Monitor signal...");
            loadApDetails();
            loadChartData(currentPeriod);
        } else {
            console.log("⏳ AP Details: Update paused (active operation in progress).");
        }
    });

    // ============================================================================
    // FORMATTERS
    // ============================================================================
    function formatBytes(bytes) {
        if (bytes == null || bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    function formatThroughput(kbps) {
        if (kbps == null) return 'N/A';
        if (kbps < 1000) return `${kbps.toFixed(1)} kbps`;
        return `${(kbps / 1000).toFixed(1)} Mbps`;
    }

    // Expose formatters globally for vendor modules
    window.APDetailsCore.formatBytes = formatBytes;
    window.APDetailsCore.formatThroughput = formatThroughput;

    // ============================================================================
    // CPE HEALTH STATUS
    // ============================================================================
    function getCPEHealthStatus(cpe) {
        if (cpe.eth_plugged === false) return { colorClass: 'border-danger', label: 'Cable Unplugged', icon: 'power_off' };
        if (cpe.eth_speed != null && cpe.eth_speed < 100) return { colorClass: 'border-orange', label: `${cpe.eth_speed} Mbps Link`, icon: 'warning' };
        if (cpe.signal == null) return { colorClass: 'border-text-secondary', label: 'No Signal Data', icon: 'signal_cellular_off' };
        if (cpe.signal < -75) return { colorClass: 'border-warning', label: 'Weak Signal', icon: 'signal_cellular_1_bar' };
        return { colorClass: 'border-success', label: 'Good Signal', icon: 'signal_cellular_4_bar' };
    }

    // ============================================================================
    // CHART FUNCTIONS
    // ============================================================================
    function createChart(canvasId, type, labels, datasets, unit) {
        if (charts[canvasId]) { charts[canvasId].destroy(); }
        const ctx = document.getElementById(canvasId).getContext('2d');
        charts[canvasId] = new Chart(ctx, {
            type,
            data: { labels, datasets },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    x: {
                        type: 'time',
                        time: { tooltipFormat: 'MMM d, HH:mm', unit },
                        grid: { color: 'rgba(51, 65, 85, 0.5)' },
                        ticks: { color: '#94A3B8', maxRotation: 20, autoSkip: true, maxTicksLimit: 6 }
                    },
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(51, 65, 85, 0.5)' },
                        ticks: { color: '#94A3B8' }
                    }
                },
                plugins: {
                    legend: { labels: { color: '#F1F5F9' } },
                    tooltip: { titleColor: '#F1F5F9', bodyColor: '#cbd5e1' }
                },
                interaction: { intersect: false, mode: 'index' }
            }
        });
    }

    function updateChartsWithLiveData(apData) {
        const timestamp = Date.now();
        ['clientsChart', 'airtimeChart', 'throughputChart'].forEach(chartId => {
            const chart = charts[chartId];
            if (!chart) return;
            chart.data.labels.push(timestamp);
            if (chart.data.labels.length > 30) { chart.data.labels.shift(); }

            if (chartId === 'clientsChart') {
                chart.data.datasets[0].data.push(apData.client_count);
                if (chart.data.datasets[0].data.length > 30) { chart.data.datasets[0].data.shift(); }
            } else if (chartId === 'airtimeChart') {
                const airtime = apData.airtime_total_usage != null ? (apData.airtime_total_usage / 10.0) : null;
                chart.data.datasets[0].data.push(airtime);
                if (chart.data.datasets[0].data.length > 30) { chart.data.datasets[0].data.shift(); }
            } else if (chartId === 'throughputChart') {
                chart.data.datasets[0].data.push(apData.total_throughput_tx);
                chart.data.datasets[1].data.push(apData.total_throughput_rx);
                if (chart.data.datasets[0].data.length > 30) { chart.data.datasets[0].data.shift(); }
                if (chart.data.datasets[1].data.length > 30) { chart.data.datasets[1].data.shift(); }
            }
            chart.update('quiet');
        });
    }

    // ============================================================================
    // PAGE UPDATE FUNCTIONS
    // ============================================================================
    function updatePageWithLiveData(ap) {
        currentVendor = ap.vendor || 'ubiquiti';

        // Update status indicator
        document.getElementById('detail-status').innerHTML = `<div class="flex items-center gap-2 font-semibold text-orange animate-pulse"><div class="size-2 rounded-full bg-orange"></div><span>Live</span></div>`;

        // Update common device info fields
        if (ap.model) document.getElementById('detail-model').textContent = ap.model;
        if (ap.mac) document.getElementById('detail-mac').textContent = ap.mac;
        if (ap.firmware) document.getElementById('detail-firmware').textContent = ap.firmware;
        if (ap.essid) document.getElementById('detail-essid').textContent = ap.essid;
        if (ap.hostname) document.getElementById('main-hostname').textContent = ap.hostname;

        if (ap.frequency != null || ap.chanbw != null) {
            const freq = ap.frequency != null ? `${ap.frequency} MHz` : 'N/A';
            const width = ap.chanbw != null ? ` / ${ap.chanbw}` : '';
            document.getElementById('detail-frequency').textContent = `${freq}${width}`;
        }

        document.getElementById('detail-clients').textContent = ap.client_count != null ? ap.client_count : 'N/A';
        document.getElementById('detail-noise').textContent = ap.noise_floor != null ? `${ap.noise_floor} dBm` : 'N/A';

        // Vendor-specific field update via Adapter
        if (window.APVendor?.onDataUpdate) {
            window.APVendor.onDataUpdate(ap);
        } else {
            // Fallback for Airtime (Ubiquiti default) - check element exists
            const airtimeEl = document.getElementById('detail-airtime');
            if (airtimeEl) {
                const airtimeTotal = ap.airtime_total_usage != null ? `${(ap.airtime_total_usage / 10.0).toFixed(1)}%` : 'N/A';
                const airtimeTx = ap.airtime_tx_usage != null ? `${(ap.airtime_tx_usage / 10.0).toFixed(1)}%` : 'N/A';
                const airtimeRx = ap.airtime_rx_usage != null ? `${(ap.airtime_rx_usage / 10.0).toFixed(1)}%` : 'N/A';
                airtimeEl.textContent = `${airtimeTotal} (Tx: ${airtimeTx} / Rx: ${airtimeRx})`;
            }
        }

        document.getElementById('detail-throughput').textContent = `${formatThroughput(ap.total_throughput_tx)} / ${formatThroughput(ap.total_throughput_rx)}`;
        document.getElementById('detail-total-data').textContent = `${formatBytes(ap.total_tx_bytes)} / ${formatBytes(ap.total_rx_bytes)}`;
        renderCPEList(ap.clients, ap.clients, currentVendor);
        updateChartsWithLiveData(ap);
    }

    async function refreshLiveData() {
        try {
            const response = await fetch(`${API_BASE_URL}/api/aps/${encodeURIComponent(currentHost)}/live`);
            if (!response.ok) {
                document.getElementById('detail-status').innerHTML = `<div class="flex items-center gap-2 font-semibold text-danger"><div class="size-2 rounded-full bg-danger"></div><span>Unreachable</span></div>`;
                return;
            }
            const apData = await response.json();
            updatePageWithLiveData(apData);
        } catch (error) {
            console.error("Error during live data refresh:", error);
            await stopDiagnosticMode();
        }
    }

    // ============================================================================
    // CPE LIST RENDERING
    // ============================================================================
    function renderCPEList(historicalCPEs, liveCPEs = null, vendor = 'ubiquiti') {
        const cpeListDiv = document.getElementById('client-list');
        if (!historicalCPEs || historicalCPEs.length === 0) {
            cpeListDiv.innerHTML = '<p class="text-text-secondary col-span-full text-center py-8">No CPE data available for this AP.</p>';
            return;
        }

        cpeListDiv.innerHTML = '';
        const liveMacs = new Set(liveCPEs ? liveCPEs.map(cpe => cpe.cpe_mac) : []);
        const timeFormatter = new Intl.DateTimeFormat(navigator.language, {
            day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'
        });

        historicalCPEs.forEach(cpe => {
            const card = document.createElement('div');
            const isOnline = liveMacs.has(cpe.cpe_mac);
            const displayCPE = isOnline ? liveCPEs.find(lc => lc.cpe_mac === cpe.cpe_mac) : cpe;

            let health = getCPEHealthStatus(displayCPE);
            let cardClasses = 'bg-surface-1 rounded-lg border-l-4 p-4 flex flex-col gap-3 transition-all hover:shadow-lg';

            if (!isOnline) {
                health = { colorClass: 'border-text-secondary', label: 'Offline', icon: 'signal_cellular_off' };
                cardClasses += ' opacity-50';
            }

            card.className = `${cardClasses} ${health.colorClass}`;

            const t_tx = displayCPE.throughput_tx_kbps != null ? `${displayCPE.throughput_tx_kbps.toFixed(1)}` : 'N/A';
            const t_rx = displayCPE.throughput_rx_kbps != null ? `${displayCPE.throughput_rx_kbps.toFixed(1)}` : 'N/A';
            const chains = displayCPE.signal_chain0 != null && displayCPE.signal_chain1 != null ? `(${displayCPE.signal_chain0}/${displayCPE.signal_chain1})` : '';
            const cableStatus = displayCPE.eth_speed != null ? `${displayCPE.eth_speed} Mbps` : 'N/A';

            // Vendor-specific metrics via Adapter
            let vendorSpecificRow = '';
            if (window.APVendor?.renderCPEExtra) {
                vendorSpecificRow = window.APVendor.renderCPEExtra(displayCPE);
            } else {
                // Fallback: Ubiquiti Capacity
                const c_dl = displayCPE.dl_capacity ? (displayCPE.dl_capacity / 1000).toFixed(0) : 'N/A';
                const c_ul = displayCPE.ul_capacity ? (displayCPE.ul_capacity / 1000).toFixed(0) : 'N/A';
                vendorSpecificRow = `
                    <span>Capacity (DL/UL):</span><span class="font-semibold text-text-primary text-right">${c_dl} / ${c_ul} Mbps</span>
                `;
            }

            const lastSeenDate = new Date(cpe.timestamp);
            const lastSeenHtml = !isOnline
                ? `<span>Last seen:</span><span class="font-semibold text-text-secondary text-right">${timeFormatter.format(lastSeenDate)}</span>`
                : `<span>Cable Status:</span><span class="font-semibold text-text-primary text-right">${cableStatus}</span>`;

            card.innerHTML = `
                <div class="flex justify-between items-start">
                    <div>
                        <p class="font-bold text-text-primary">${displayCPE.cpe_hostname || 'Unnamed Device'}</p>
                        <p class="text-xs text-text-secondary font-mono">${displayCPE.ip_address || 'No IP'}</p>
                    </div>
                    <div class="flex items-center gap-1 text-xs font-semibold px-2 py-1 rounded-full bg-black bg-opacity-20">
                        <span class="material-symbols-outlined text-xs">${health.icon}</span>
                        <span>${health.label}</span>
                    </div>
                </div>
                <div class="grid grid-cols-2 gap-x-4 gap-y-2 text-sm text-text-secondary">
                    <span>Signal / Chains:</span><span class="font-semibold text-text-primary text-right">${displayCPE.signal || 'N/A'} dBm ${chains}</span>
                    <span>Noise Floor:</span><span class="font-semibold text-text-primary text-right">${displayCPE.noisefloor || 'N/A'} dBm</span>
                    ${vendorSpecificRow}
                    <span>Throughput (DL/UL):</span><span class="font-semibold text-text-primary text-right">${t_tx} / ${t_rx} kbps</span>
                    <span>Total Data (DL/UL):</span><span class="font-semibold text-text-primary text-right">${formatBytes(displayCPE.total_tx_bytes)} / ${formatBytes(displayCPE.total_rx_bytes)}</span>
                    ${lastSeenHtml}
                </div>
            `;
            cpeListDiv.appendChild(card);
        });
    }

    async function loadCPEDataFromHistory() {
        try {
            const [historyResponse, liveResponse] = await Promise.all([
                fetch(`${API_BASE_URL}/api/aps/${encodeURIComponent(currentHost)}/cpes`),
                fetch(`${API_BASE_URL}/api/aps/${encodeURIComponent(currentHost)}/live`)
            ]);

            if (!historyResponse.ok) throw new Error('Failed to fetch CPE history');
            const historicalCPEs = await historyResponse.json();

            let liveCPEs = null;
            let vendor = currentVendor;
            if (liveResponse.ok) {
                const liveData = await liveResponse.json();
                liveCPEs = liveData.clients;
                vendor = liveData.vendor || 'ubiquiti';
                currentVendor = vendor;
            } else {
                console.warn("Could not fetch live CPE data. Offline status may not be accurate.");
            }

            renderCPEList(historicalCPEs, liveCPEs, vendor);

        } catch (error) {
            console.error("Error loading CPE data:", error);
            document.getElementById('client-list').innerHTML = '<p class="text-danger col-span-3">Failed to load CPE data.</p>';
        }
    }

    // ============================================================================
    // DIAGNOSTIC MODE
    // ============================================================================
    async function stopDiagnosticMode() {
        isStopping = true;
        diagnosticManager.stop(true);
        console.log('Exiting Live Mode, restoring history view...');
        try {
            await loadApDetails();
            await loadChartData(currentPeriod);
            console.log('History view restored.');
        } catch (error) {
            console.error('Error restoring history view:', error);
        }
        setTimeout(() => { isStopping = false; }, 500);
    }

    async function startDiagnosticMode() {
        diagnosticManager.stop(false);
        const DURATION_MINUTES = 5;
        let remaining = DURATION_MINUTES * 60;
        const timerSpan = document.getElementById('refresh-timer');
        const toggle = document.getElementById('auto-refresh-toggle');
        try {
            const apSettingsResponse = await fetch(`${API_BASE_URL}/api/aps/${encodeURIComponent(currentHost)}`);
            if (!apSettingsResponse.ok) throw new Error("Could not fetch AP settings");
            const apSettings = await apSettingsResponse.json();
            const refreshIntervalSeconds = apSettings.monitor_interval;
            if (refreshIntervalSeconds && refreshIntervalSeconds > 0) {
                document.getElementById('main-hostname').classList.add('text-orange');
                Object.values(charts).forEach(chart => {
                    chart.data.labels = [];
                    chart.data.datasets.forEach(dataset => dataset.data = []);
                    chart.update('quiet');
                });
                await refreshLiveData();
                diagnosticManager.intervalId = setInterval(refreshLiveData, refreshIntervalSeconds * 1000);
                const countdown = () => {
                    remaining--;
                    const minutes = Math.floor(remaining / 60);
                    const seconds = remaining % 60;
                    timerSpan.textContent = `(${minutes}:${seconds.toString().padStart(2, '0')})`;
                    if (remaining <= 0) { stopDiagnosticMode(); }
                };
                countdown();
                diagnosticManager.countdownId = setInterval(countdown, 1000);
                diagnosticManager.timeoutId = setTimeout(stopDiagnosticMode, DURATION_MINUTES * 60 * 1000);
            } else {
                showToast('No specific monitor interval found for this AP. Please set a default in the edit menu.', 'warning');
                if (toggle) toggle.checked = false;
            }
        } catch (error) {
            showToast('Could not load AP settings to start diagnostic mode.', 'danger');
            if (toggle) toggle.checked = false;
        }
    }

    // ============================================================================
    // CHART DATA LOADING
    // ============================================================================
    function loadChartData(period = '24h') {
        currentPeriod = period;
        if (chartsCard) {
            chartsCard.style.filter = 'blur(4px)';
            chartsCard.style.opacity = '0.6';
        }
        setTimeout(async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/api/aps/${encodeURIComponent(currentHost)}/history?period=${period}`);
                if (!response.ok) throw new Error('Failed to fetch history');
                const data = await response.json();
                const labels = data.history.map(p => new Date(p.timestamp.endsWith('Z') ? p.timestamp : p.timestamp + 'Z'));
                const timeUnit = period === '24h' ? 'hour' : 'day';
                createChart('clientsChart', 'line', labels, [{ label: 'Clients', data: data.history.map(p => p.client_count), borderColor: '#3B82F6', tension: 0.2, fill: false, pointRadius: 0 }], timeUnit);
                createChart('airtimeChart', 'line', labels, [{ label: 'Airtime (%)', data: data.history.map(p => p.airtime_total_usage != null ? (p.airtime_total_usage / 10.0) : null), borderColor: '#EAB308', tension: 0.2, fill: false, pointRadius: 0 }], timeUnit);
                createChart('throughputChart', 'line', labels, [{ label: 'Download (kbps)', data: data.history.map(p => p.total_throughput_tx), borderColor: '#22C55E', tension: 0.2, fill: false, pointRadius: 0 }, { label: 'Upload (kbps)', data: data.history.map(p => p.total_throughput_rx), borderColor: '#F97316', tension: 0.2, fill: false, pointRadius: 0 }], timeUnit);
            } catch (error) {
                console.error("Error loading chart data:", error);
            } finally {
                if (chartsCard) {
                    setTimeout(() => {
                        chartsCard.style.filter = 'blur(0px)';
                        chartsCard.style.opacity = '1';
                    }, 50);
                }
            }
        }, 300);
    }

    // ============================================================================
    // LOAD AP DETAILS
    // ============================================================================
    function loadApDetails() {
        if (deviceInfoCard) { deviceInfoCard.style.filter = 'blur(4px)'; deviceInfoCard.style.opacity = '0.6'; }
        if (clientListSection) { clientListSection.style.filter = 'blur(4px)'; clientListSection.style.opacity = '0.6'; }

        setTimeout(async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/api/aps/${encodeURIComponent(currentHost)}`);
                if (!response.ok) throw new Error('AP not found');
                const ap = await response.json();
                document.title = `${ap.hostname || ap.host} - AP Details`;
                document.getElementById('main-hostname').textContent = ap.hostname || ap.host;
                document.getElementById('detail-host').textContent = ap.host || 'N/A';
                if (!diagnosticManager.intervalId) {
                    document.getElementById('detail-status').innerHTML = `<div class="flex items-center gap-2 font-semibold"><div class="size-2 rounded-full ${ap.last_status === 'online' ? 'bg-success' : 'bg-danger'}"></div><span>${ap.last_status ? ap.last_status.charAt(0).toUpperCase() + ap.last_status.slice(1) : 'Unknown'}</span></div>`;
                }
                document.getElementById('detail-model').textContent = ap.model || 'N/A';
                document.getElementById('detail-mac').textContent = ap.mac || 'N/A';
                document.getElementById('detail-firmware').textContent = ap.firmware || 'N/A';
                document.getElementById('detail-essid').textContent = ap.essid || 'N/A';
                try {
                    const zonesRes = await fetch(`${API_BASE_URL}/api/zonas`);
                    const zones = await zonesRes.json();
                    const zone = Array.isArray(zones) ? zones.find(z => z.id === ap.zona_id) : null;
                    document.getElementById('detail-zona').textContent = zone ? zone.nombre : (ap.zona_nombre || 'N/A');
                } catch (e) {
                    console.warn("Could not load zones, displaying fallback name.", e);
                    document.getElementById('detail-zona').textContent = ap.zona_nombre || 'N/A';
                }
                document.getElementById('detail-clients').textContent = ap.client_count != null ? ap.client_count : 'N/A';
                document.getElementById('detail-noise').textContent = ap.noise_floor != null ? `${ap.noise_floor} dBm` : 'N/A';
                document.getElementById('detail-frequency').textContent = ap.frequency != null ? `${ap.frequency} MHz / ${ap.chanbw} MHz` : 'N/A';

                // Ubiquiti-specific fields (may not exist for MikroTik)
                const satsEl = document.getElementById('detail-sats');
                if (satsEl) satsEl.textContent = ap.gps_sats != null ? ap.gps_sats : 'N/A';

                const gpsEl = document.getElementById('detail-gps');
                if (gpsEl) gpsEl.textContent = ap.gps_lat && ap.gps_lon ? `${ap.gps_lat.toFixed(6)}, ${ap.gps_lon.toFixed(6)}` : 'N/A';

                const airtimeEl = document.getElementById('detail-airtime');
                if (airtimeEl) {
                    const airtimeTotal = ap.airtime_total_usage != null ? `${(ap.airtime_total_usage / 10.0).toFixed(1)}%` : 'N/A';
                    const airtimeTx = ap.airtime_tx_usage != null ? `${(ap.airtime_tx_usage / 10.0).toFixed(1)}%` : 'N/A';
                    const airtimeRx = ap.airtime_rx_usage != null ? `${(ap.airtime_rx_usage / 10.0).toFixed(1)}%` : 'N/A';
                    airtimeEl.textContent = `${airtimeTotal} (Tx: ${airtimeTx} / Rx: ${airtimeRx})`;
                }

                document.getElementById('detail-throughput').textContent = `${formatThroughput(ap.total_throughput_tx)} / ${formatThroughput(ap.total_throughput_rx)}`;
                document.getElementById('detail-total-data').textContent = `${formatBytes(ap.total_tx_bytes)} / ${formatBytes(ap.total_rx_bytes)}`;

                document.getElementById('edit-ap-button').addEventListener('click', () => openEditModal(ap));
                document.getElementById('delete-ap-button').addEventListener('click', handleDelete);

                // Update vendor and call vendor init
                currentVendor = ap.vendor || 'ubiquiti';
                if (window.APVendor?.init) {
                    window.APVendor.init(ap);
                }

                if (!diagnosticManager.intervalId) {
                    await loadCPEDataFromHistory();
                }
            } catch (error) {
                console.error("Error in loadApDetails:", error);
                document.getElementById('main-hostname').textContent = 'Error';
            } finally {
                setTimeout(() => {
                    if (deviceInfoCard) { deviceInfoCard.style.filter = 'blur(0px)'; deviceInfoCard.style.opacity = '1'; }
                    if (clientListSection) { clientListSection.style.filter = 'blur(0px)'; clientListSection.style.opacity = '1'; }
                }, 50);
            }
        }, 300);
    }

    // ============================================================================
    // EDIT/DELETE MODAL HANDLERS
    // ============================================================================
    async function handleEditFormSubmit(event) {
        event.preventDefault();
        const editApForm = document.getElementById('edit-ap-form');
        const formData = new FormData(editApForm);
        const data = {
            username: formData.get('username'),
            zona_id: parseInt(formData.get('zona_id'), 10),
            monitor_interval: parseInt(formData.get('monitor_interval'), 10) || null
        };
        const password = formData.get('password');
        if (password) { data.password = password; }

        try {
            const response = await fetch(`${API_BASE_URL}/api/aps/${encodeURIComponent(currentHost)}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
            if (!response.ok) throw new Error('Failed to update AP');
            closeEditModal();
            loadApDetails();
        } catch (error) {
            document.getElementById('edit-form-error').textContent = error.message;
            document.getElementById('edit-form-error').classList.remove('hidden');
        }
    }

    async function handleDelete() {
        const apHostname = document.getElementById('main-hostname').textContent;
        if (confirm(`Are you sure you want to delete the AP "${apHostname}" (${currentHost})?\nThis action cannot be undone.`)) {
            try {
                const response = await fetch(`${API_BASE_URL}/api/aps/${encodeURIComponent(currentHost)}`, { method: 'DELETE' });
                if (!response.ok) throw new Error('Failed to delete AP');
                showToast('AP deleted successfully.', 'success');
                window.location.href = '/';
            } catch (error) {
                showToast(`Error: ${error.message}`, 'danger');
            }
        }
    }

    function openEditModal(apData) {
        document.getElementById('edit-host').value = apData.host;
        document.getElementById('edit-username').value = apData.username;
        document.getElementById('edit-monitor_interval').value = apData.monitor_interval;
        populateZoneSelect(document.getElementById('edit-zona_id'), apData.zona_id);
        document.getElementById('edit-ap-modal').classList.remove('hidden');
        document.getElementById('edit-ap-modal').classList.add('flex');
    }

    function closeEditModal() {
        document.getElementById('edit-ap-form').reset();
        document.getElementById('edit-form-error').classList.add('hidden');
        document.getElementById('edit-ap-modal').classList.add('hidden');
        document.getElementById('edit-ap-modal').classList.remove('flex');
    }

    async function populateZoneSelect(selectElement, selectedId) {
        try {
            const response = await fetch(`${API_BASE_URL}/api/zonas`);
            const zones = await response.json();
            selectElement.innerHTML = '<option value="">Select a zone...</option>';
            zones.forEach(zone => {
                const option = document.createElement('option');
                option.value = zone.id;
                option.textContent = zone.nombre;
                if (zone.id === selectedId) { option.selected = true; }
                selectElement.appendChild(option);
            });
        } catch (error) {
            console.error('Failed to load zones for modal:', error);
        }
    }

    // ============================================================================
    // INITIAL SETUP
    // ============================================================================
    document.querySelectorAll('.chart-button').forEach(button => {
        button.addEventListener('click', () => {
            document.querySelectorAll('.chart-button').forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            const period = button.dataset.period;
            loadChartData(period);
        });
    });

    const autoRefreshToggle = document.getElementById('auto-refresh-toggle');
    if (autoRefreshToggle) {
        autoRefreshToggle.checked = false;
        autoRefreshToggle.addEventListener('change', async () => {
            if (isStopping) return;
            if (autoRefreshToggle.checked) {
                await startDiagnosticMode();
            } else {
                await stopDiagnosticMode();
            }
        });
    }

    // Initialize page
    loadApDetails();
    loadChartData('24h');

    const editCancelButton = document.getElementById('edit-cancel-button');
    const editApForm = document.getElementById('edit-ap-form');

    if (editCancelButton && editApForm) {
        editCancelButton.addEventListener('click', closeEditModal);
        editApForm.addEventListener('submit', handleEditFormSubmit);
    } else {
        console.error("Edit form elements not found. Edit functionality may fail.");
    }
});

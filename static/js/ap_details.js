document.addEventListener('DOMContentLoaded', async () => {
    const API_BASE_URL = window.location.origin;
    const currentHost = window.location.pathname.split('/').pop();
    let charts = {};
    let isStopping = false;

    // Estado para saber qué gráfica mostrar al actualizar
    let currentPeriod = '24h';

    // Spectral Scan state (declared early for use in data-refresh-needed listener)
    let spectralWs = null;
    let spectralChart = null;
    let spectralData = { labels: [], signal: [], peak: [] };
    let spectralCountdownInterval = null;
    let spectralRemainingSeconds = 0;

    const deviceInfoCard = document.getElementById('device-info-card');
    const chartsCard = document.getElementById('charts-card');
    const clientListSection = document.getElementById('client-list-section');

    // --- SECCIÓN ELIMINADA: loadAndSetRefreshInterval, startBackgroundRefresh, etc. ---
    // Ya no necesitamos polling de fondo.

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

    // --- INICIO: Escucha Reactiva (WebSocket) ---
    window.addEventListener('data-refresh-needed', () => {
        // LÓGICA IMPORTANTE:
        // NO recargamos si hay operaciones activas que se interrumpirían:
        // 1. Modo Diagnóstico/Live activo
        // 2. Spectral Scan en progreso (conexión WebSocket activa)
        if (!diagnosticManager.intervalId && !spectralWs) {
            console.log("⚡ AP Details: Recargando datos por señal del Monitor...");

            // Recargar datos del AP (Estado, Clientes, etc)
            loadApDetails();

            // Recargar gráficas manteniendo el periodo seleccionado
            loadChartData(currentPeriod);
        } else {
            console.log("⏳ AP Details: Actualización pausada (operación activa en curso).");
        }
    });
    // --- FIN: Escucha Reactiva ---

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

    function getCPEHealthStatus(cpe) {
        if (cpe.eth_plugged === false) return { colorClass: 'border-danger', label: 'Cable Unplugged', icon: 'power_off' };
        if (cpe.eth_speed != null && cpe.eth_speed < 100) return { colorClass: 'border-orange', label: `${cpe.eth_speed} Mbps Link`, icon: 'warning' };
        if (cpe.signal == null) return { colorClass: 'border-text-secondary', label: 'No Signal Data', icon: 'signal_cellular_off' };
        if (cpe.signal < -75) return { colorClass: 'border-warning', label: 'Weak Signal', icon: 'signal_cellular_1_bar' };
        return { colorClass: 'border-success', label: 'Good Signal', icon: 'signal_cellular_4_bar' };
    }

    function createChart(canvasId, type, labels, datasets, unit) {
        if (charts[canvasId]) { charts[canvasId].destroy(); }
        const ctx = document.getElementById(canvasId).getContext('2d');
        charts[canvasId] = new Chart(ctx, { type, data: { labels, datasets }, options: { responsive: true, maintainAspectRatio: true, scales: { x: { type: 'time', time: { tooltipFormat: 'MMM d, HH:mm', unit }, grid: { color: 'rgba(51, 65, 85, 0.5)' }, ticks: { color: '#94A3B8', maxRotation: 20, autoSkip: true, maxTicksLimit: 6 } }, y: { beginAtZero: true, grid: { color: 'rgba(51, 65, 85, 0.5)' }, ticks: { color: '#94A3B8' } } }, plugins: { legend: { labels: { color: '#F1F5F9' } }, tooltip: { titleColor: '#F1F5F9', bodyColor: '#cbd5e1' } }, interaction: { intersect: false, mode: 'index' } } });
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

    // Track current vendor for conditional rendering
    let currentVendor = 'ubiquiti';

    function updatePageWithLiveData(ap) {
        // Store vendor for use in renderCPEList
        currentVendor = ap.vendor || 'ubiquiti';

        // Update status indicator
        document.getElementById('detail-status').innerHTML = `<div class="flex items-center gap-2 font-semibold text-orange animate-pulse"><div class="size-2 rounded-full bg-orange"></div><span>Live</span></div>`;

        // Update device info fields that come from live data
        if (ap.model) document.getElementById('detail-model').textContent = ap.model;
        if (ap.mac) document.getElementById('detail-mac').textContent = ap.mac;
        if (ap.firmware) document.getElementById('detail-firmware').textContent = ap.firmware;
        if (ap.essid) document.getElementById('detail-essid').textContent = ap.essid;
        if (ap.hostname) document.getElementById('main-hostname').textContent = ap.hostname;

        // Frequency and channel width
        if (ap.frequency != null || ap.chanbw != null) {
            const freq = ap.frequency != null ? `${ap.frequency} MHz` : 'N/A';
            const width = ap.chanbw != null ? ` / ${ap.chanbw}` : '';
            document.getElementById('detail-frequency').textContent = `${freq}${width}`;
        }

        document.getElementById('detail-clients').textContent = ap.client_count != null ? ap.client_count : 'N/A';
        document.getElementById('detail-noise').textContent = ap.noise_floor != null ? `${ap.noise_floor} dBm` : 'N/A';

        // Airtime is Ubiquiti-specific; for MikroTik show CPU Load if available
        if (currentVendor === 'mikrotik') {
            const cpuLoad = ap.extra?.cpu_load;
            document.getElementById('detail-airtime').textContent = cpuLoad != null ? `CPU: ${cpuLoad}%` : 'N/A (MikroTik)';
        } else {
            const airtimeTotal = ap.airtime_total_usage != null ? `${(ap.airtime_total_usage / 10.0).toFixed(1)}%` : 'N/A';
            const airtimeTx = ap.airtime_tx_usage != null ? `${(ap.airtime_tx_usage / 10.0).toFixed(1)}%` : 'N/A';
            const airtimeRx = ap.airtime_rx_usage != null ? `${(ap.airtime_rx_usage / 10.0).toFixed(1)}%` : 'N/A';
            document.getElementById('detail-airtime').textContent = `${airtimeTotal} (Tx: ${airtimeTx} / Rx: ${airtimeRx})`;
        }

        document.getElementById('detail-throughput').textContent = `${formatThroughput(ap.total_throughput_tx)} / ${formatThroughput(ap.total_throughput_rx)}`;
        document.getElementById('detail-total-data').textContent = `${formatBytes(ap.total_tx_bytes)} / ${formatBytes(ap.total_rx_bytes)}`;
        renderCPEList(ap.clients, ap.clients, currentVendor);
        updateChartsWithLiveData(ap);
    }

    async function refreshLiveData() {
        try {
            const response = await fetch(`${API_BASE_URL}/api/aps/${encodeURIComponent(currentHost)}/live`);
            if (!response.ok) { document.getElementById('detail-status').innerHTML = `<div class="flex items-center gap-2 font-semibold text-danger"><div class="size-2 rounded-full bg-danger"></div><span>Unreachable</span></div>`; return; }
            const apData = await response.json();
            updatePageWithLiveData(apData);
        } catch (error) {
            console.error("Error during live data refresh:", error);
            await stopDiagnosticMode();
        }
    }

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

        const isMikroTik = vendor === 'mikrotik';

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

            // Vendor-specific metrics
            let vendorSpecificRow;
            if (isMikroTik) {
                // MikroTik: Show CCQ and TX/RX Rate
                const ccq = displayCPE.ccq != null ? `${displayCPE.ccq}%` : 'N/A';
                // tx_rate and rx_rate come in bps, convert to Mbps
                const txRate = displayCPE.tx_rate != null ? `${(displayCPE.tx_rate / 1000000).toFixed(1)} Mbps` : 'N/A';
                const rxRate = displayCPE.rx_rate != null ? `${(displayCPE.rx_rate / 1000000).toFixed(1)} Mbps` : 'N/A';
                vendorSpecificRow = `
                    <span>CCQ:</span><span class="font-semibold text-text-primary text-right">${ccq}</span>
                    <span>TX/RX Rate:</span><span class="font-semibold text-text-primary text-right">${txRate} / ${rxRate}</span>
                `;
            } else {
                // Ubiquiti: Show Capacity
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
            let vendor = currentVendor; // Use cached vendor
            if (liveResponse.ok) {
                const liveData = await liveResponse.json();
                liveCPEs = liveData.clients;
                vendor = liveData.vendor || 'ubiquiti';
                currentVendor = vendor; // Update cached vendor
            } else {
                console.warn("Could not fetch live CPE data. Offline status may not be accurate.");
            }

            renderCPEList(historicalCPEs, liveCPEs, vendor);

        } catch (error) {
            console.error("Error loading CPE data:", error);
            document.getElementById('client-list').innerHTML = '<p class="text-danger col-span-3">Failed to load CPE data.</p>';
        }
    }

    async function stopDiagnosticMode() {
        isStopping = true;
        diagnosticManager.stop(true);
        console.log('Saliendo del Modo Live, restaurando vista de historial...');
        try {
            await loadApDetails();
            // Restauramos la gráfica con el periodo seleccionado actualmente
            await loadChartData(currentPeriod);
            console.log('Vista de historial restaurada.');
            // startBackgroundRefresh(); // ELIMINADO
        } catch (error) {
            console.error('Ocurrió un error al restaurar la vista de historial:', error);
        }
        setTimeout(() => { isStopping = false; }, 500);
    }

    async function startDiagnosticMode() {
        // stopBackgroundRefresh(); // ELIMINADO (Ya no existe)
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
                Object.values(charts).forEach(chart => { chart.data.labels = []; chart.data.datasets.forEach(dataset => dataset.data = []); chart.update('quiet'); });
                await refreshLiveData();
                diagnosticManager.intervalId = setInterval(refreshLiveData, refreshIntervalSeconds * 1000);
                const countdown = () => { remaining--; const minutes = Math.floor(remaining / 60); const seconds = remaining % 60; timerSpan.textContent = `(${minutes}:${seconds.toString().padStart(2, '0')})`; if (remaining <= 0) { stopDiagnosticMode(); } };
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

    function loadChartData(period = '24h') {
        currentPeriod = period; // Guardamos el estado actual
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
                document.getElementById('detail-sats').textContent = ap.gps_sats != null ? ap.gps_sats : 'N/A';
                const airtimeTotal = ap.airtime_total_usage != null ? `${(ap.airtime_total_usage / 10.0).toFixed(1)}%` : 'N/A';
                const airtimeTx = ap.airtime_tx_usage != null ? `${(ap.airtime_tx_usage / 10.0).toFixed(1)}%` : 'N/A';
                const airtimeRx = ap.airtime_rx_usage != null ? `${(ap.airtime_rx_usage / 10.0).toFixed(1)}%` : 'N/A';
                document.getElementById('detail-airtime').textContent = `${airtimeTotal} (Tx: ${airtimeTx} / Rx: ${airtimeRx})`;
                document.getElementById('detail-throughput').textContent = `${formatThroughput(ap.total_throughput_tx)} / ${formatThroughput(ap.total_throughput_rx)}`;
                document.getElementById('detail-total-data').textContent = `${formatBytes(ap.total_tx_bytes)} / ${formatBytes(ap.total_rx_bytes)}`;
                document.getElementById('detail-gps').textContent = ap.gps_lat && ap.gps_lon ? `${ap.gps_lat.toFixed(6)}, ${ap.gps_lon.toFixed(6)}` : 'N/A';
                document.getElementById('edit-ap-button').addEventListener('click', () => openEditModal(ap));
                document.getElementById('delete-ap-button').addEventListener('click', handleDelete);

                // Render vendor-specific section (Spectral Scan for MikroTik, info for Ubiquiti)
                const vendor = ap.vendor || 'ubiquiti';
                currentVendor = vendor;
                renderVendorSection(vendor);

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
    // VENDOR-SPECIFIC SECTION RENDERING
    // ============================================================================

    function renderVendorSection(vendor) {
        const container = document.getElementById('vendor-specific-section');
        if (!container) return;

        if (vendor === 'mikrotik') {
            container.innerHTML = getMikrotikSectionHTML();
            initSpectralScan();
        } else if (vendor === 'ubiquiti') {
            container.innerHTML = getUbiquitiSectionHTML();
        } else {
            container.innerHTML = `<div class="bg-surface-2/50 rounded-lg border border-border-color p-4 mb-8">
                <p class="text-text-secondary">Vendor-specific details not available for "${vendor}".</p>
            </div>`;
        }
    }

    function getMikrotikSectionHTML() {
        return `
            <div id="spectral-scan-section" class="bg-surface-1 rounded-lg border border-border-color p-6 mb-8">
                <div class="flex flex-wrap justify-between items-center gap-4 mb-4">
                    <div>
                        <h2 class="text-xl font-bold">Spectrum Analyzer</h2>
                        <p class="text-sm text-text-secondary">Real-time RF spectrum analysis (MikroTik only)</p>
                    </div>
                    <div class="flex items-center gap-3">
                        <span id="spectral-status" class="text-sm text-text-secondary"></span>
                        <span id="spectral-countdown" class="text-sm font-mono text-orange hidden"></span>
                    </div>
                </div>
                
                <!-- Configuration Panel -->
                <div id="spectral-config" class="mb-4">
                    <div class="flex flex-wrap items-end gap-4 mb-4">
                        <div class="flex flex-col gap-1">
                            <label class="text-sm text-text-secondary">Interface</label>
                            <select id="spectral-interface" class="h-10 px-3 rounded-lg bg-surface-2 border border-border-color text-text-primary focus:outline-none focus:ring-2 focus:ring-primary">
                                <option value="">Loading...</option>
                            </select>
                        </div>
                        <div class="flex flex-col gap-1">
                            <label class="text-sm text-text-secondary">Duration</label>
                            <select id="spectral-duration" class="h-10 px-3 rounded-lg bg-surface-2 border border-border-color text-text-primary focus:outline-none focus:ring-2 focus:ring-primary">
                                <option value="30">30 seconds</option>
                                <option value="60">1 minute</option>
                                <option value="120" selected>2 minutes</option>
                                <option value="180">3 minutes</option>
                                <option value="300">5 minutes (max)</option>
                            </select>
                        </div>
                        <button id="spectral-scan-btn" 
                                class="flex items-center justify-center h-10 px-4 text-sm font-bold text-white rounded-lg bg-primary hover:bg-primary-hover transition-colors">
                            <span class="material-symbols-outlined mr-2">radio</span>
                            <span>Start Scan</span>
                        </button>
                    </div>
                    
                    <!-- Warning Message -->
                    <div class="flex items-start gap-3 p-3 rounded-lg bg-warning/10 border border-warning/30">
                        <span class="material-symbols-outlined text-warning">warning</span>
                        <p class="text-sm text-warning">
                            <strong>Warning:</strong> Clients connected to the selected interface will be temporarily disconnected during the scan.
                        </p>
                    </div>
                </div>
                
                <!-- Chart Container -->
                <div id="spectral-chart-container" class="hidden">
                    <div class="h-64 lg:h-80">
                        <canvas id="spectralChart"></canvas>
                    </div>
                    <div class="flex justify-center gap-6 mt-4 text-sm">
                        <div class="flex items-center gap-2">
                            <div class="w-4 h-1 bg-blue-500 rounded"></div>
                            <span class="text-text-secondary">Signal (Current)</span>
                        </div>
                        <div class="flex items-center gap-2">
                            <div class="w-4 h-1 bg-red-500 rounded" style="border-top: 2px dashed;"></div>
                            <span class="text-text-secondary">Peak (Max)</span>
                        </div>
                    </div>
                </div>
                
                <!-- Unsupported Message -->
                <div id="spectral-unsupported" class="hidden text-center py-8">
                    <span class="material-symbols-outlined text-4xl text-warning mb-2">warning</span>
                    <p id="spectral-unsupported-msg" class="text-text-secondary"></p>
                </div>
            </div>
        `;
    }

    function getUbiquitiSectionHTML() {
        return `
            <div class="bg-surface-2/50 rounded-lg border border-border-color p-4 mb-8">
                <div class="flex items-start gap-3">
                    <span class="material-symbols-outlined text-warning">info</span>
                    <div>
                        <h3 class="font-semibold text-text-primary mb-1">Spectrum Analyzer Not Available</h3>
                        <p class="text-sm text-text-secondary">
                            Ubiquiti's spectrum analyzer (airView) is only accessible through the device's web interface and requires a Java applet. 
                            It cannot be accessed remotely via API.
                        </p>
                    </div>
                </div>
            </div>
        `;
    }

    // ============================================================================
    // SPECTRAL SCAN MODULE (MikroTik Only)
    // ============================================================================
    // Note: State variables (spectralWs, spectralChart, etc.) are declared at the top
    // of the file for proper scoping with the data-refresh-needed listener.

    async function initSpectralScan() {
        const btn = document.getElementById('spectral-scan-btn');
        if (!btn) return;

        // Load available interfaces
        await loadSpectralInterfaces();

        btn.addEventListener('click', () => {
            if (spectralWs && spectralWs.readyState === WebSocket.OPEN) {
                stopSpectralScan();
            } else {
                startSpectralScan();
            }
        });
    }

    async function loadSpectralInterfaces() {
        const interfaceSelect = document.getElementById('spectral-interface');
        if (!interfaceSelect) return;

        try {
            const response = await fetch(`${API_BASE_URL}/api/aps/${encodeURIComponent(currentHost)}/wireless-interfaces`);
            if (!response.ok) throw new Error('Failed to fetch interfaces');

            const data = await response.json();
            const interfaces = data.interfaces || [];

            interfaceSelect.innerHTML = '';

            if (interfaces.length === 0) {
                interfaceSelect.innerHTML = '<option value="">No interfaces found</option>';
                return;
            }

            interfaces.forEach((iface, index) => {
                const option = document.createElement('option');
                option.value = iface.name;
                option.textContent = `${iface.name} (${iface.type})`;
                if (index === 0) option.selected = true;
                interfaceSelect.appendChild(option);
            });
        } catch (error) {
            console.error('Error loading spectral interfaces:', error);
            interfaceSelect.innerHTML = '<option value="">Error loading</option>';
        }
    }

    function startSpectralScan() {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${window.location.host}/api/ws/aps/${encodeURIComponent(currentHost)}/spectral-scan`;

        spectralWs = new WebSocket(wsUrl);

        const btn = document.getElementById('spectral-scan-btn');
        const statusSpan = document.getElementById('spectral-status');
        const chartContainer = document.getElementById('spectral-chart-container');
        const unsupportedDiv = document.getElementById('spectral-unsupported');
        const configPanel = document.getElementById('spectral-config');
        const countdownSpan = document.getElementById('spectral-countdown');

        // Get selected interface and duration
        const selectedInterface = document.getElementById('spectral-interface')?.value || null;
        const selectedDuration = parseInt(document.getElementById('spectral-duration')?.value || '120', 10);

        spectralWs.onopen = () => {
            statusSpan.textContent = 'Connecting...';
            btn.innerHTML = '<span class="material-symbols-outlined mr-2 animate-spin">sync</span><span>Connecting...</span>';
        };

        spectralWs.onmessage = (event) => {
            const msg = JSON.parse(event.data);

            switch (msg.status) {
                case 'connecting':
                    statusSpan.textContent = 'Connecting to device...';
                    break;
                case 'waiting_config':
                    // Send configuration to backend
                    spectralWs.send(JSON.stringify({
                        interface: selectedInterface,
                        duration: selectedDuration
                    }));
                    statusSpan.textContent = 'Sending configuration...';
                    break;
                case 'starting':
                    statusSpan.textContent = msg.message || 'Starting scan...';
                    btn.innerHTML = '<span class="material-symbols-outlined mr-2 animate-spin">sync</span><span>Starting...</span>';
                    break;
                case 'preparing':
                    statusSpan.textContent = msg.message || 'Preparing scanner...';
                    btn.innerHTML = '<span class="material-symbols-outlined mr-2 animate-pulse">radio</span><span>Calibrating...</span>';
                    // Hide config panel early
                    configPanel.classList.add('hidden');
                    break;
                case 'scanning':
                    statusSpan.textContent = msg.interface ? `Scanning ${msg.interface}...` : 'Scanning...';
                    btn.innerHTML = '<span class="material-symbols-outlined mr-2">stop</span><span>Stop Scan</span>';
                    btn.classList.remove('bg-primary', 'hover:bg-primary-hover');
                    btn.classList.add('bg-danger', 'hover:bg-red-700');
                    chartContainer.classList.remove('hidden');
                    unsupportedDiv.classList.add('hidden');
                    configPanel.classList.add('hidden');

                    // Start countdown timer
                    const duration = msg.duration || selectedDuration;
                    startSpectralCountdown(duration, countdownSpan);

                    initSpectralChart();
                    break;
                case 'data':
                    updateSpectralChart(msg.data);
                    break;
                case 'completed':
                    showToast(msg.message || 'Scan completed', 'success');
                    stopSpectralScan();
                    break;
                case 'stopped':
                    showToast(msg.message || 'Scan stopped', 'info');
                    stopSpectralScan();
                    break;
                case 'unsupported':
                    stopSpectralScan();
                    chartContainer.classList.add('hidden');
                    unsupportedDiv.classList.remove('hidden');
                    document.getElementById('spectral-unsupported-msg').textContent = msg.message;
                    break;
                case 'error':
                    showToast(msg.message || 'Spectral scan error', 'danger');
                    stopSpectralScan();
                    break;
            }
        };

        spectralWs.onerror = (error) => {
            console.error('Spectral WebSocket error:', error);
            showToast('Connection error during spectral scan', 'danger');
            stopSpectralScan();
        };

        spectralWs.onclose = () => {
            resetSpectralUI();
        };
    }

    function startSpectralCountdown(durationSeconds, countdownSpan) {
        spectralRemainingSeconds = durationSeconds;

        if (countdownSpan) {
            countdownSpan.classList.remove('hidden');
            updateCountdownDisplay(countdownSpan);
        }

        if (spectralCountdownInterval) {
            clearInterval(spectralCountdownInterval);
        }

        spectralCountdownInterval = setInterval(() => {
            spectralRemainingSeconds--;

            if (countdownSpan) {
                updateCountdownDisplay(countdownSpan);
            }

            if (spectralRemainingSeconds <= 0) {
                clearInterval(spectralCountdownInterval);
                spectralCountdownInterval = null;
            }
        }, 1000);
    }

    function updateCountdownDisplay(countdownSpan) {
        const minutes = Math.floor(spectralRemainingSeconds / 60);
        const seconds = spectralRemainingSeconds % 60;
        countdownSpan.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
    }

    function stopSpectralCountdown() {
        if (spectralCountdownInterval) {
            clearInterval(spectralCountdownInterval);
            spectralCountdownInterval = null;
        }
        spectralRemainingSeconds = 0;

        const countdownSpan = document.getElementById('spectral-countdown');
        if (countdownSpan) {
            countdownSpan.classList.add('hidden');
            countdownSpan.textContent = '';
        }
    }

    function stopSpectralScan() {
        if (spectralWs) {
            spectralWs.send('stop');
            spectralWs.close();
            spectralWs = null;
        }
        resetSpectralUI();
    }

    function resetSpectralUI() {
        const btn = document.getElementById('spectral-scan-btn');
        const statusSpan = document.getElementById('spectral-status');
        const configPanel = document.getElementById('spectral-config');

        // Stop the countdown timer
        stopSpectralCountdown();

        if (btn) {
            btn.innerHTML = '<span class="material-symbols-outlined mr-2">radio</span><span>Start Scan</span>';
            btn.classList.remove('bg-danger', 'hover:bg-red-700');
            btn.classList.add('bg-primary', 'hover:bg-primary-hover');
        }
        if (statusSpan) {
            statusSpan.textContent = '';
        }

        // Show config panel again
        if (configPanel) {
            configPanel.classList.remove('hidden');
        }
    }

    function initSpectralChart() {
        const ctx = document.getElementById('spectralChart');
        if (!ctx) return;

        // Reset data
        spectralData = { labels: [], signal: [], peak: [] };

        if (spectralChart) {
            spectralChart.destroy();
        }

        spectralChart = new Chart(ctx.getContext('2d'), {
            type: 'line',
            data: {
                labels: spectralData.labels,
                datasets: [
                    {
                        label: 'Signal (dBm)',
                        data: spectralData.signal,
                        borderColor: '#3B82F6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        fill: true,
                        tension: 0.2,
                        pointRadius: 0
                    },
                    {
                        label: 'Peak (dBm)',
                        data: spectralData.peak,
                        borderColor: '#EF4444',
                        borderDash: [5, 5],
                        fill: false,
                        tension: 0.2,
                        pointRadius: 0
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 0 },
                scales: {
                    x: {
                        type: 'linear',
                        title: { display: true, text: 'Frequency (MHz)', color: '#94A3B8' },
                        grid: { color: 'rgba(51, 65, 85, 0.5)' },
                        ticks: { color: '#94A3B8' }
                    },
                    y: {
                        title: { display: true, text: 'dBm', color: '#94A3B8' },
                        min: -120,
                        max: -40,
                        grid: { color: 'rgba(51, 65, 85, 0.5)' },
                        ticks: { color: '#94A3B8' }
                    }
                },
                plugins: {
                    legend: { labels: { color: '#F1F5F9' } },
                    tooltip: { titleColor: '#F1F5F9', bodyColor: '#cbd5e1' }
                }
            }
        });
    }

    function updateSpectralChart(data) {
        if (!spectralChart || !data) return;

        const freq = data.freq;
        const signal = data.signal;
        const peak = data.peak;

        // Find if this frequency already exists
        const index = spectralData.labels.indexOf(freq);

        if (index !== -1) {
            // Update existing
            spectralData.signal[index] = signal;
            spectralData.peak[index] = peak;
        } else {
            // Add new and keep sorted
            spectralData.labels.push(freq);
            spectralData.signal.push(signal);
            spectralData.peak.push(peak);

            // Sort by frequency
            const combined = spectralData.labels.map((label, i) => ({
                freq: label,
                signal: spectralData.signal[i],
                peak: spectralData.peak[i]
            }));
            combined.sort((a, b) => a.freq - b.freq);

            spectralData.labels = combined.map(c => c.freq);
            spectralData.signal = combined.map(c => c.signal);
            spectralData.peak = combined.map(c => c.peak);
        }

        // Update chart
        spectralChart.data.labels = spectralData.labels;
        spectralChart.data.datasets[0].data = spectralData.signal;
        spectralChart.data.datasets[1].data = spectralData.peak;
        spectralChart.update('none');
    }

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
            zones.forEach(zone => { const option = document.createElement('option'); option.value = zone.id; option.textContent = zone.nombre; if (zone.id === selectedId) { option.selected = true; } selectElement.appendChild(option); });
        } catch (error) {
            console.error('Failed to load zones for modal:', error);
        }
    }

    // --- Initial Setup ---
    document.querySelectorAll('.chart-button').forEach(button => {
        button.addEventListener('click', () => {
            document.querySelectorAll('.chart-button').forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            // Guardar el periodo seleccionado
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

    // Inicialización (Sin startBackgroundRefresh)
    loadApDetails();
    loadChartData('24h');

    const editCancelButton = document.getElementById('edit-cancel-button');
    const editApForm = document.getElementById('edit-ap-form');

    if (editCancelButton && editApForm) {
        editCancelButton.addEventListener('click', closeEditModal);
        editApForm.addEventListener('submit', handleEditFormSubmit);
    } else {
        console.error("Los elementos del formulario de edición no se encontraron. La funcionalidad de edición puede fallar.");
    }
});
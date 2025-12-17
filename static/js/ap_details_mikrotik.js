/**
 * AP Details - MikroTik Vendor Module
 * 
 * Implements window.APVendor interface for MikroTik-specific functionality:
 * - Spectral Scan (WebSocket-based spectrum analyzer)
 * - CPU Load, Memory Usage display
 * - CCQ and TX/RX Rate for CPE cards
 */
(function () {
    'use strict';

    // NOTE: Access window.APDetailsCore properties LAZILY inside functions,
    // not at module load time, because Core initializes on DOMContentLoaded.

    // Spectral Scan state
    let spectralWs = null;
    let spectralChart = null;
    let spectralData = { labels: [], signal: [], peak: [] };
    let spectralCountdownInterval = null;
    let spectralRemainingSeconds = 0;

    // ============================================================================
    // APVendor INTERFACE IMPLEMENTATION
    // ============================================================================
    window.APVendor = {
        /**
         * Initialize MikroTik-specific features
         */
        init: function (apData) {
            initSpectralScan();
            // Update MikroTik-specific fields if present in initial data
            if (apData.extra) {
                updateMikrotikFields(apData.extra);
            }
        },

        /**
         * Called when live data is received
         */
        onDataUpdate: function (apData) {
            const cpuLoad = apData.extra?.cpu_load;
            const memoryUsage = apData.extra?.memory_usage;

            // Update airtime field with CPU load for MikroTik
            const airtimeEl = document.getElementById('detail-airtime');
            if (airtimeEl) {
                airtimeEl.textContent = cpuLoad != null ? `CPU: ${cpuLoad}%` : 'N/A (MikroTik)';
            }

            // Update MikroTik-specific fields in partial
            if (apData.extra) {
                updateMikrotikFields(apData.extra);
            }
        },

        /**
         * Render CPE-specific columns for MikroTik
         */
        renderCPEExtra: function (cpe) {
            const ccq = cpe.ccq != null ? `${cpe.ccq}%` : 'N/A';
            const txRate = cpe.tx_rate != null ? `${(cpe.tx_rate / 1000000).toFixed(1)} Mbps` : 'N/A';
            const rxRate = cpe.rx_rate != null ? `${(cpe.rx_rate / 1000000).toFixed(1)} Mbps` : 'N/A';
            return `
                <span>CCQ:</span><span class="font-semibold text-text-primary text-right">${ccq}</span>
                <span>TX/RX Rate:</span><span class="font-semibold text-text-primary text-right">${txRate} / ${rxRate}</span>
            `;
        },

        /**
         * Check if spectral scan is active (blocks Core polling)
         */
        isSpectralActive: function () {
            return spectralWs && spectralWs.readyState === WebSocket.OPEN;
        },

        /**
         * Cleanup on page navigation
         */
        destroy: function () {
            stopSpectralScan();
        }
    };

    // ============================================================================
    // MIKROTIK-SPECIFIC FIELD UPDATES
    // ============================================================================
    function updateMikrotikFields(extra) {
        const cpuLoadEl = document.getElementById('detail-cpu-load');
        const memoryEl = document.getElementById('detail-memory');
        const platformEl = document.getElementById('detail-platform');
        const wirelessTypeEl = document.getElementById('detail-wireless-type');
        const uptimeEl = document.getElementById('detail-uptime');
        const liveNotice = document.getElementById('mikrotik-live-notice');
        const liveBadge = document.getElementById('mikrotik-live-badge');

        // Hide notice and show badge when we have live data
        if (extra && (extra.cpu_load != null || extra.memory_usage != null)) {
            if (liveNotice) liveNotice.classList.add('hidden');
            if (liveBadge) liveBadge.classList.remove('hidden');
        }

        if (cpuLoadEl && extra.cpu_load != null) {
            cpuLoadEl.textContent = `${extra.cpu_load}%`;
        }
        if (memoryEl && extra.memory_usage != null) {
            memoryEl.textContent = `${extra.memory_usage}%`;
        }
        if (platformEl && extra.platform) {
            platformEl.textContent = extra.platform;
        }
        if (wirelessTypeEl && extra.wireless_type) {
            wirelessTypeEl.textContent = extra.wireless_type;
        }
        if (uptimeEl && extra.uptime) {
            uptimeEl.textContent = extra.uptime;
        }
    }

    // ============================================================================
    // SPECTRAL SCAN MODULE
    // ============================================================================
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

        const API_BASE_URL = window.APDetailsCore?.API_BASE_URL || window.location.origin;
        const currentHost = window.APDetailsCore?.currentHost || window.location.pathname.split('/').pop();

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
        const currentHost = window.APDetailsCore?.currentHost || window.location.pathname.split('/').pop();
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
                    if (configPanel) configPanel.classList.add('hidden');
                    break;
                case 'scanning':
                    statusSpan.textContent = msg.interface ? `Scanning ${msg.interface}...` : 'Scanning...';
                    btn.innerHTML = '<span class="material-symbols-outlined mr-2">stop</span><span>Stop Scan</span>';
                    btn.classList.remove('bg-primary', 'hover:bg-primary-hover');
                    btn.classList.add('bg-danger', 'hover:bg-red-700');
                    if (chartContainer) chartContainer.classList.remove('hidden');
                    if (unsupportedDiv) unsupportedDiv.classList.add('hidden');
                    if (configPanel) configPanel.classList.add('hidden');

                    // Start countdown timer
                    const duration = msg.duration || selectedDuration;
                    startSpectralCountdown(duration, countdownSpan);

                    initSpectralChart();
                    break;
                case 'data':
                    updateSpectralChart(msg.data);
                    break;
                case 'completed':
                    if (typeof showToast === 'function') showToast(msg.message || 'Scan completed', 'success');
                    stopSpectralScan();
                    break;
                case 'stopped':
                    if (typeof showToast === 'function') showToast(msg.message || 'Scan stopped', 'info');
                    stopSpectralScan();
                    break;
                case 'unsupported':
                    stopSpectralScan();
                    if (chartContainer) chartContainer.classList.add('hidden');
                    if (unsupportedDiv) unsupportedDiv.classList.remove('hidden');
                    const unsupportedMsg = document.getElementById('spectral-unsupported-msg');
                    if (unsupportedMsg) unsupportedMsg.textContent = msg.message;
                    break;
                case 'error':
                    if (typeof showToast === 'function') showToast(msg.message || 'Spectral scan error', 'danger');
                    stopSpectralScan();
                    break;
            }
        };

        spectralWs.onerror = (error) => {
            console.error('Spectral WebSocket error:', error);
            if (typeof showToast === 'function') showToast('Connection error during spectral scan', 'danger');
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

})();

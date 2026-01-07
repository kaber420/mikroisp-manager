// static/js/router_details/history.js
import { CONFIG } from './config.js';
import { ApiClient } from './utils.js';

let cpuChart = null;
let memoryChart = null;

const CHART_OPTIONS = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
        mode: 'index',
        intersect: false,
    },
    plugins: {
        legend: {
            labels: { color: '#94A3B8' }
        },
        tooltip: {
            backgroundColor: '#1E293B',
            borderColor: '#334155',
            borderWidth: 1,
            titleColor: '#F1F5F9',
            bodyColor: '#F1F5F9',
        }
    },
    scales: {
        x: {
            type: 'time',
            time: {
                tooltipFormat: 'MMM d, HH:mm',
                displayFormats: {
                    hour: 'HH:mm',
                    day: 'MMM d'
                }
            },
            grid: { color: 'rgba(148, 163, 184, 0.1)' },
            ticks: { color: '#94A3B8' }
        },
        y: {
            beginAtZero: true,
            grid: { color: 'rgba(148, 163, 184, 0.1)' },
            ticks: { color: '#94A3B8' }
        }
    }
};

/**
 * Load and render router history charts.
 * @param {number} rangeHours - Number of hours of history to display.
 */
export async function loadHistory(rangeHours = 24) {
    const cpuCanvas = document.getElementById('history-cpu-chart');
    const memoryCanvas = document.getElementById('history-memory-chart');
    const container = document.getElementById('history-charts-container');
    const loadingEl = document.getElementById('history-loading');
    const noDataEl = document.getElementById('history-no-data');

    if (!cpuCanvas || !memoryCanvas) {
        console.warn('History chart canvases not found.');
        return;
    }

    if (loadingEl) loadingEl.classList.remove('hidden');
    if (noDataEl) noDataEl.classList.add('hidden');

    try {
        const response = await ApiClient.request(`/api/routers/${CONFIG.currentHost}/history?range_hours=${rangeHours}`);

        if (loadingEl) loadingEl.classList.add('hidden');

        if (!response || !response.data || response.data.length === 0) {
            if (noDataEl) noDataEl.classList.remove('hidden');
            return;
        }

        const data = response.data;

        // Prepare data for charts
        const timestamps = data.map(d => new Date(d.timestamp + 'Z')); // Assume UTC
        const cpuLoads = data.map(d => d.cpu_load);
        const memoryUsage = data.map(d => {
            if (d.total_memory && d.free_memory) {
                return ((d.total_memory - d.free_memory) / d.total_memory * 100).toFixed(1);
            }
            return null;
        });

        // Destroy existing charts if any
        if (cpuChart) cpuChart.destroy();
        if (memoryChart) memoryChart.destroy();

        // CPU Chart
        cpuChart = new Chart(cpuCanvas, {
            type: 'line',
            data: {
                labels: timestamps,
                datasets: [{
                    label: 'CPU Load (%)',
                    data: cpuLoads,
                    borderColor: '#3B82F6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: 0,
                    pointHoverRadius: 4,
                }]
            },
            options: {
                ...CHART_OPTIONS,
                scales: {
                    ...CHART_OPTIONS.scales,
                    y: {
                        ...CHART_OPTIONS.scales.y,
                        max: 100,
                        ticks: {
                            ...CHART_OPTIONS.scales.y.ticks,
                            callback: (val) => `${val}%`
                        }
                    }
                }
            }
        });

        // Memory Chart
        memoryChart = new Chart(memoryCanvas, {
            type: 'line',
            data: {
                labels: timestamps,
                datasets: [{
                    label: 'Memory Usage (%)',
                    data: memoryUsage,
                    borderColor: '#22C55E',
                    backgroundColor: 'rgba(34, 197, 94, 0.1)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: 0,
                    pointHoverRadius: 4,
                }]
            },
            options: {
                ...CHART_OPTIONS,
                scales: {
                    ...CHART_OPTIONS.scales,
                    y: {
                        ...CHART_OPTIONS.scales.y,
                        max: 100,
                        ticks: {
                            ...CHART_OPTIONS.scales.y.ticks,
                            callback: (val) => `${val}%`
                        }
                    }
                }
            }
        });

    } catch (error) {
        console.error('Error loading history:', error);
        if (loadingEl) loadingEl.classList.add('hidden');
        if (noDataEl) {
            noDataEl.textContent = 'Error loading history data.';
            noDataEl.classList.remove('hidden');
        }
    }
}

/**
 * Initialize the history charts on page load.
 * Charts are now in the Overview tab, so load them immediately.
 */
export function initHistoryTab() {
    // Load history immediately since charts are now on the Overview tab
    loadHistory(24);

    // Range selector (if present)
    const rangeSelect = document.getElementById('history-range-select');
    if (rangeSelect) {
        rangeSelect.addEventListener('change', (e) => {
            loadHistory(parseInt(e.target.value, 10));
        });
    }
}


// Variables Globales para el estado de paginación
let currentLogPage = 1;
let currentLogPageSize = 10;
let currentLogTotalPages = 1;
let currentHostFilter = 'all';

// Funciones expuestas al HTML (window scope)
window.changeLogPageSize = (size) => {
    currentLogPageSize = parseInt(size);
    currentLogPage = 1; // Reset a la primera página
    loadEventLogs(currentHostFilter);
};

window.changeLogPage = (direction) => {
    const newPage = currentLogPage + direction;
    if (newPage > 0 && newPage <= currentLogTotalPages) {
        currentLogPage = newPage;
        loadEventLogs(currentHostFilter);
    }
};

// Modificamos la función existente
async function loadEventLogs(hostFilter = 'all') {
    const tbody = document.getElementById('events-log-body');
    const infoSpan = document.getElementById('logs-pagination-info');
    const btnPrev = document.getElementById('btn-prev-page');
    const btnNext = document.getElementById('btn-next-page');

    if (!tbody) return;

    // Si cambiamos de filtro, reseteamos a página 1
    if (hostFilter !== currentHostFilter) {
        currentLogPage = 1;
        currentHostFilter = hostFilter;
    }

    tbody.style.opacity = '0.5';

    try {
        // Nueva URL con parámetros de paginación
        const url = `${API_BASE_URL}/api/stats/events?host=${encodeURIComponent(hostFilter)}&page=${currentLogPage}&page_size=${currentLogPageSize}`;

        const res = await fetch(url);
        if (res.ok) {
            const data = await res.json();

            // Extraemos items y metadatos
            const events = data.items;
            currentLogTotalPages = data.total_pages;
            const totalRecords = data.total;

            // Renderizar Tabla
            tbody.innerHTML = '';
            if (events.length === 0) {
                tbody.innerHTML = `<tr><td colspan="4" class="px-4 py-4 text-center text-text-secondary">No hay eventos registrados.</td></tr>`;
            } else {
                events.forEach(evt => {
                    const dateObj = new Date(evt.timestamp + "Z");
                    const timeStr = dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                    const dateStr = dateObj.toLocaleDateString();
                    let icon = 'info';
                    let colorClass = 'text-blue-400 bg-blue-400/10';

                    if (evt.event_type === 'danger') { icon = 'error'; colorClass = 'text-danger bg-danger/10'; }
                    else if (evt.event_type === 'success') { icon = 'check_circle'; colorClass = 'text-success bg-success/10'; }

                    tbody.innerHTML += `
                        <tr class="border-b border-white/5 hover:bg-white/5 transition-colors">
                            <td class="px-4 py-3 whitespace-nowrap">
                                <span class="block text-text-primary font-medium">${timeStr}</span>
                                <span class="text-xs">${dateStr}</span>
                            </td>
                            <td class="px-4 py-3 text-text-primary font-medium">${evt.device_host}</td>
                            <td class="px-4 py-3">${evt.message}</td>
                            <td class="px-4 py-3">
                                <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold border border-white/5 ${colorClass}">
                                    <span class="material-symbols-outlined text-[14px]">${icon}</span>
                                    ${evt.event_type.toUpperCase()}
                                </span>
                            </td>
                        </tr>
                    `;
                });
            }

            // Actualizar Controles UI
            if (infoSpan) {
                const start = (currentLogPage - 1) * currentLogPageSize + 1;
                const end = Math.min(start + currentLogPageSize - 1, totalRecords);
                infoSpan.textContent = totalRecords > 0 ? `Mostrando ${start}-${end} de ${totalRecords}` : 'Sin resultados';
            }

            if (btnPrev) btnPrev.disabled = currentLogPage <= 1;
            if (btnNext) btnNext.disabled = currentLogPage >= currentLogTotalPages;

        }
    } catch (error) {
        console.error("Error logs:", error);
        tbody.innerHTML = `<tr><td colspan="4" class="text-center text-danger py-4">Error cargando logs</td></tr>`;
    } finally {
        tbody.style.opacity = '1';
    }
}

// El resto del archivo dashboard.js se mantiene igual (loadInitialData, etc.)

// Define API_BASE_URL en el scope global para que esté disponible en todas las funciones
const API_BASE_URL = window.location.origin;

async function loadLogFilterOptions() {
    const select = document.getElementById('log-filter');
    if (!select) return;

    // Agregar un listener para el evento 'change'
    select.addEventListener('change', (event) => {
        currentHostFilter = event.target.value; // Actualiza el filtro global
        currentLogPage = 1; // Reset a la primera página
        loadEventLogs(); // Llama a la función sin el parámetro hostFilter
    });

    try {
        // Cargar lista de Routers para el select
        const res = await fetch(`${API_BASE_URL}/api/routers`);
        if (res.ok) {
            const routers = await res.json();
            // Agregar la opción "Todos" al principio
            const allOption = document.createElement('option');
            allOption.value = 'all';
            allOption.textContent = 'Todos los Dispositivos';
            select.appendChild(allOption);

            routers.forEach(r => {
                const opt = document.createElement('option');
                opt.value = r.host;
                opt.textContent = r.hostname || r.host;
                select.appendChild(opt);
            });
        }
    } catch (e) { console.error("Error cargando filtro:", e); }
}

document.addEventListener('DOMContentLoaded', () => {
    // --- FUNCIÓN 1: Cargar Tops ---
    async function loadTopStats() {
        const topAirtimeList = document.getElementById('top-airtime-list');
        const topSignalList = document.getElementById('top-signal-list');

        if (!topAirtimeList || !topSignalList) return;

        topAirtimeList.style.opacity = '0.5';
        topSignalList.style.opacity = '0.5';

        try {
            const [airtimeRes, signalRes] = await Promise.all([
                fetch(`${API_BASE_URL}/api/stats/top-aps-by-airtime`),
                fetch(`${API_BASE_URL}/api/stats/top-cpes-by-signal`)
            ]);

            // --- RENDER AIRTIME ---
            if (airtimeRes.ok) {
                const topAirtime = await airtimeRes.json();
                topAirtimeList.innerHTML = '';

                if (topAirtime.length > 0) {
                    topAirtime.forEach(ap => {
                        const usageVal = (ap.airtime_total_usage / 10.0).toFixed(1);
                        // Usamos tus colores definidos en tailwind.config
                        const barColor = usageVal > 80 ? 'bg-danger' : 'bg-primary';

                        topAirtimeList.innerHTML += `
                            <div class="group">
                                <div class="flex justify-between text-sm mb-2">
                                    <span class="text-text-secondary font-medium group-hover:text-text-primary transition-colors truncate pr-4 flex items-center gap-2">
                                        <span class="material-symbols-outlined text-[16px]">router</span>
                                        ${ap.hostname || ap.host}
                                    </span>
                                    <span class="text-primary font-bold">${usageVal}%</span>
                                </div>
                                <div class="w-full bg-surface-2 rounded-full h-1.5 overflow-hidden">
                                    <div class="${barColor} h-full rounded-full transition-all duration-500" style="width: ${usageVal}%"></div>
                                </div>
                            </div>
                        `;
                    });
                } else {
                    topAirtimeList.innerHTML = `<div class="text-text-secondary text-sm italic text-center py-4">Sin datos de tráfico.</div>`;
                }
            }

            // --- RENDER SEÑAL ---
            if (signalRes.ok) {
                const topSignal = await signalRes.json();
                topSignalList.innerHTML = '';

                if (topSignal.length > 0) {
                    topSignal.forEach(cpe => {
                        const signal = cpe.signal;

                        // Lógica de colores basada en tu theme.css/config
                        let badgeClass = "text-warning bg-warning/10 border-warning/20";
                        if (signal < -75) {
                            badgeClass = "text-danger bg-danger/10 border-danger/20";
                        }

                        topSignalList.innerHTML += `
                            <div class="flex items-center justify-between p-3 mb-2 rounded-lg hover:bg-surface-2/50 transition-colors group border border-transparent hover:border-white/5">
                                <div class="flex items-center gap-3 overflow-hidden">
                                    <div class="size-8 rounded-full bg-surface-2 flex items-center justify-center text-text-secondary group-hover:text-text-primary group-hover:bg-surface-1 transition-all">
                                         <span class="material-symbols-outlined text-[18px]">person</span>
                                    </div>
                                    <p class="text-sm font-medium text-text-secondary group-hover:text-text-primary truncate transition-colors">
                                        ${cpe.cpe_hostname || cpe.cpe_mac}
                                    </p>
                                </div>
                                <span class="px-2 py-1 rounded text-xs font-bold border ${badgeClass}">
                                    ${signal} dBm
                                </span>
                            </div>
                        `;
                    });
                } else {
                    topSignalList.innerHTML = `<div class="text-text-secondary text-sm italic text-center py-4">Señal óptima en todos los clientes.</div>`;
                }
            }

        } catch (error) {
            console.error("Error loading top stats:", error);
        } finally {
            topAirtimeList.style.opacity = '1';
            topSignalList.style.opacity = '1';
        }
    }

    // --- FUNCIÓN 2: KPIs (Sin cambios lógicos, solo aseguramos IDs) ---
    async function loadInitialData() {
        try {
            const [apsRes, cpeCountRes, routersRes] = await Promise.all([
                fetch(`${API_BASE_URL}/api/aps`),
                fetch(`${API_BASE_URL}/api/stats/cpe-count`),
                fetch(`${API_BASE_URL}/api/routers`)
            ]);

            if (!apsRes.ok || !cpeCountRes.ok || !routersRes.ok) throw new Error('Failed to load dashboard data');

            const allAps = await apsRes.json();
            const cpeCountData = await cpeCountRes.json();
            const allRouters = await routersRes.json();

            let cpesOnline = 0;
            let apsOnline = 0;

            allAps.forEach(ap => {
                if (ap.last_status === 'online') {
                    apsOnline++;
                    if (ap.client_count != null) cpesOnline += ap.client_count;
                }
            });

            // Router stats
            let routersOnline = 0;
            allRouters.forEach(router => {
                if (router.last_status === 'online') {
                    routersOnline++;
                }
            });

            updateStatWithTransition('total-aps', allAps.length);
            updateStatWithTransition('aps-online', apsOnline);
            updateStatWithTransition('aps-offline', allAps.length - apsOnline);
            updateStatWithTransition('total-cpes', cpeCountData.total_cpes);
            updateStatWithTransition('cpes-online', cpesOnline);
            updateStatWithTransition('cpes-offline', cpeCountData.total_cpes - cpesOnline);

            // Router KPIs
            updateStatWithTransition('total-routers', allRouters.length);
            updateStatWithTransition('routers-online', routersOnline);
            updateStatWithTransition('routers-offline', allRouters.length - routersOnline);

            loadTopStats();

        } catch (error) {
            console.error("Dashboard Load Error:", error);
        }
    }

    function updateStatWithTransition(elementId, newValue) {
        const element = document.getElementById(elementId);
        if (!element) return;

        const newValueStr = String(newValue);
        if (element.textContent === newValueStr) return;

        element.style.transition = 'opacity 0.2s ease';
        element.style.opacity = '0.5';
        setTimeout(() => {
            element.textContent = newValueStr;
            element.style.opacity = '1';
        }, 200);
    }

    // --- INIT ---
    loadInitialData();
    window.addEventListener('data-refresh-needed', () => loadInitialData());
    loadLogFilterOptions();
    loadEventLogs(); // Carga inicial
});
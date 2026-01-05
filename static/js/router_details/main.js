//static/js/router_details/main.js
import { ApiClient, DomUtils } from './utils.js';
import { CONFIG, DOM_ELEMENTS } from './config.js';

// --- IMPORTAR LA NUEVA FUNCIÓN initResourceStream y WAN functions ---
import { loadOverviewData, loadOverviewStats, initResourceStream, loadWanInterfaceConfig, initWanSelector } from './overview.js';

// Imports de módulos
import { initInterfacesModule, loadInterfacesData } from './interfaces.js';
import { initNetworkModule, loadNetworkData } from './network.js';
import { initPppModule, loadPppData } from './ppp.js';
import { initQueuesModule, loadQueuesData } from './queues.js';
import { initPlansModule, loadPlansData } from './plans.js';
import { initUsersModule, loadUsersData } from './users.js';
import { initBackupModule, loadBackupData } from './backup.js';
import { initSslModule, loadSslStatus } from './ssl.js';
import { initHistoryTab } from './history.js';

async function loadFullDetailsData() {
    try {
        // Add cache-busting timestamp to prevent stale data
        const cacheBuster = `?_t=${Date.now()}`;
        const data = await ApiClient.request(`/api/routers/${CONFIG.currentHost}/full-details${cacheBuster}`);

        // Consolidar TODAS las cargas de datos
        loadOverviewData(data);
        loadInterfacesData(data);
        loadNetworkData(data);
        loadPppData(data);
        loadQueuesData(data);
        loadPlansData(data);
        loadUsersData(data);
        loadBackupData(data);
        loadOverviewStats(data);

    } catch (e) {
        console.error("Error fatal cargando datos del router:", e);
        DomUtils.updateFeedback(`Error al cargar datos del router: ${e.message}`, false);
    }
}
// Exponer para que los módulos puedan refrescar
window.loadFullDetailsData = loadFullDetailsData;


document.addEventListener('DOMContentLoaded', async () => {

    // 1. Inicializar módulos de UI (event listeners, etc.)
    initInterfacesModule();
    initNetworkModule();
    initPppModule();
    initQueuesModule();
    initPlansModule();
    initUsersModule();
    initBackupModule();
    initSslModule();
    initHistoryTab();

    // 2. Carga ÚNICA de todos los datos pesados y estáticos
    await loadWanInterfaceConfig(); // Load saved WAN interface first
    await loadFullDetailsData();

    // 2.5. Inicializar selector de WAN
    initWanSelector();

    // 3. Iniciar el stream de datos en vivo (CPU, RAM)
    initResourceStream();
});

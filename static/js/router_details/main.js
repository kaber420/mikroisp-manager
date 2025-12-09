//static/js/router_details/main.js
import { ApiClient, DomUtils } from './utils.js';
import { CONFIG, DOM_ELEMENTS } from './config.js';

// --- IMPORTAR LA NUEVA FUNCIÓN initResourceStream ---
import { loadOverviewData, loadOverviewStats, initResourceStream } from './overview.js';

// Imports de módulos
import { initInterfacesModule, loadInterfacesData } from './interfaces.js';
import { initNetworkModule, loadNetworkData } from './network.js';
import { initPppModule, loadPppData } from './ppp.js';
import { initQueuesModule, loadQueuesData } from './queues.js';
import { initUsersModule, loadUsersData } from './users.js';
import { initBackupModule, loadBackupData } from './backup.js';

async function loadFullDetailsData() {
    try {
        const data = await ApiClient.request(`/api/routers/${CONFIG.currentHost}/full-details`);

        // Consolidar TODAS las cargas de datos
        loadOverviewData(data);
        loadInterfacesData(data);
        loadNetworkData(data);
        loadPppData(data);
        loadQueuesData(data);
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
    initUsersModule();
    initBackupModule();

    // 2. Carga ÚNICA de todos los datos pesados y estáticos
    await loadFullDetailsData();

    // 3. Iniciar el stream de datos en vivo (CPU, RAM)
    initResourceStream();
});
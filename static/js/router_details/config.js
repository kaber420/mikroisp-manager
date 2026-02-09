// static/js/router_details/config.js

/**
 * Configuración estática de la aplicación.
 */
export const CONFIG = {
    API_BASE_URL: window.location.origin,
    currentHost: window.location.pathname.split('/').pop(),
    COLORS: {
        BACKUP: '#3B82F6',
        RSC: '#F97316',
        SUCCESS: '#22C55E',
        DANGER: '#EF4444',
        WARNING: '#EAB308',
        PRIMARY: '#3B82F6'
    }
};

/**
 * Referencias a elementos del DOM cacheados.
 */
export const DOM_ELEMENTS = {
    // Headers
    mainHostname: document.getElementById('main-hostname'),
    // Feedback
    formFeedback: document.getElementById('form-feedback'),
    // Listas de Datos
    interfacesTableContainer: document.getElementById('interfaces-table-container'),
    interfaceFilterButtons: document.getElementById('interface-filter-buttons'),
    ipAddressList: document.getElementById('ip-address-list'),
    natRulesList: document.getElementById('nat-rules-list'),
    pppProfileList: document.getElementById('ppp-profile-list'),
    ipPoolList: document.getElementById('ip-pool-list'),
    pppoeServerList: document.getElementById('pppoe-server-list'),
    parentQueueListDisplay: document.getElementById('parent-queue-list-display'),
    pppoeSecretsList: document.getElementById('pppoe-secrets-list'),
    pppoeActiveList: document.getElementById('pppoe-active-list'),
    backupFilesList: document.getElementById('backup-files-list'),
    localBackupFilesList: document.getElementById('local-backup-files-list'),
    refreshLocalBackupsBtn: document.getElementById('refresh-local-backups-btn'),
    routerUsersList: document.getElementById('router-users-list'),

    // --- NUEVO: Tabla para planes locales ---
    localPlansTableContainer: document.getElementById('local-plans-table-container'),

    // Formularios (dinámicos mediante modales - las referencias que aún usan getById son para formularios que siguen inline)
    // --- NUEVO: Formulario de Planes Locales (Pestaña Queues) ---
    createLocalPlanForm: document.getElementById('create-local-plan-form'),
    // Overview Stats
    resUptime: document.getElementById('res-uptime'),
    resCpuLoad: document.getElementById('res-cpu-load'),
    resCpuBar: document.getElementById('res-cpu-bar'),
    resCpuText: document.getElementById('res-cpu-text'),
    resMemoryPerc: document.getElementById('res-memory-perc'),
    resMemoryText: document.getElementById('res-memory-text'),
    resMemoryBar: document.getElementById('res-memory-bar'),
    resDiskText: document.getElementById('res-disk-text'),
    resDiskBar: document.getElementById('res-disk-bar'),
    resHost: document.getElementById('res-host'),
    resFirmware: document.getElementById('res-firmware'),
    resStatusIndicator: document.getElementById('res-status-indicator'),
    resStatusText: document.getElementById('res-status-text'),
    resInterfaces: document.getElementById('res-interfaces'),
    // WAN Stats
    resWanRx: document.getElementById('res-wan-rx'),
    resWanTx: document.getElementById('res-wan-tx'),
    resWanInterface: document.getElementById('res-wan-interface'),
    wanInterfaceCard: document.getElementById('wan-interface-card'),
    // Overview Info
    infoModel: document.getElementById('info-model'),
    infoFirmware: document.getElementById('info-firmware'),
    infoPlatform: document.getElementById('info-platform'),
    infoCpu: document.getElementById('info-cpu'),
    infoSerial: document.getElementById('info-serial'),
    infoLicense: document.getElementById('info-license'),
    infoCpuDetails: document.getElementById('info-cpu-details'),
    // Health
    healthInfo: document.getElementById('health-info'),
    resVoltage: document.getElementById('res-voltage'),
    resTemperature: document.getElementById('res-temperature'),
    // Modals - Now use templates, elements fetched dynamically
    // Templates
    vlanFormTemplate: document.getElementById('vlan-form-template'),
    bridgeFormTemplate: document.getElementById('bridge-form-template'),
    editRouterFormTemplate: document.getElementById('edit-router-form-template'),
    wanFormTemplate: document.getElementById('wan-form-template'),
    addIpFormTemplate: document.getElementById('add-ip-form-template'),
    addNatFormTemplate: document.getElementById('add-nat-form-template'),
    addPppoeFormTemplate: document.getElementById('add-pppoe-form-template'),
    addPlanFormTemplate: document.getElementById('add-plan-form-template'),
    addRouterUserFormTemplate: document.getElementById('add-router-user-form-template'),
    createBackupFormTemplate: document.getElementById('create-backup-form-template'),
    addParentQueueFormTemplate: document.getElementById('add-parent-queue-form-template'),

    // Buttons (these still exist in the DOM)
    addVlanBtn: document.getElementById('add-vlan-btn'),
    addBridgeBtn: document.getElementById('add-bridge-btn'),
    wanInterfaceCard: document.getElementById('wan-interface-card'),
    addIpBtn: document.getElementById('add-ip-btn'),
    addNatBtn: document.getElementById('add-nat-btn'),
    addPppoeBtn: document.getElementById('add-pppoe-btn'),
    addPlanBtn: document.getElementById('add-plan-btn'),
    addRouterUserBtn: document.getElementById('add-router-user-btn'),
    createBackupBtn: document.getElementById('create-backup-btn'),
    addParentQueueBtn: document.getElementById('add-parent-queue-btn'),

    // Iconos
    deleteIcon: `<span class="material-symbols-outlined text-base">delete</span>`
};

/**
 * Estado global de la aplicación.
 */
export let state = {
    allInterfaces: [],
    currentRouterName: 'router',
    routerId: null, // Para guardar el ID de la BD
    wanInterface: null // Interfaz WAN seleccionada
};

/**
 * Actualiza el estado global de las interfaces.
 * @param {Array} newInterfaces - El nuevo array de interfaces.
 */
export function setAllInterfaces(newInterfaces) {
    state.allInterfaces = newInterfaces;
}

/**
 * Actualiza el estado global del nombre del router.
 * @param {string} newName - El nuevo nombre del router.
 */
export function setCurrentRouterName(newName) {
    state.currentRouterName = newName;
}

/**
 * Actualiza el estado global de la interfaz WAN.
 * @param {string} wanInterfaceName - El nombre de la interfaz WAN.
 */
export function setWanInterface(wanInterfaceName) {
    state.wanInterface = wanInterfaceName;
}
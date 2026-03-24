import axios from 'axios';
import { setUser, type User } from '../stores/auth';

const BASE_URL = '/api';

export * from './portal';
export * from './settings';
export * from './infra';

// Instancia global de Axios
const api = axios.create({
    baseURL: BASE_URL,
    withCredentials: true,
    headers: {
        'Content-Type': 'application/json'
    }
});

// Interceptor para manejar errores globales (logout si 401)
api.interceptors.response.use(
    (response) => response.data,
    (error) => {
        if (error.response?.status === 401) {
            // Limpiar sesión si el token expiró o es inválido
            localStorage.removeItem('user');
            setUser(null);
            if (window.location.pathname !== '/login') {
                window.location.href = '/login';
            }
        }
        return Promise.reject(error);
    }
);

/**
 * Función genérica para peticiones (para compatibilidad con código existente)
 */
export async function request<T = any>(path: string, options: any = {}): Promise<T> {
    const method = options.method?.toLowerCase() || 'get';
    
    // Configuración base de Axios
    const config: any = {
        method,
        url: path,
        ...options
    };

    // Manejo inteligente del cuerpo de la petición
    if (options.body) {
        if (options.body instanceof FormData || options.body instanceof URLSearchParams) {
            config.data = options.body;
            // No sobreescribir Content-Type para FormData (dejar que el navegador ponga el boundary)
            if (options.body instanceof FormData) {
                delete config.headers?.['Content-Type'];
            }
        } else if (typeof options.body === 'string') {
            try {
                config.data = JSON.parse(options.body);
            } catch (e) {
                // Si no es JSON válido, enviar como string (ej: raw text)
                config.data = options.body;
            }
        } else {
            // Ya es un objeto
            config.data = options.body;
        }
    }

    return api.request<any, T>(config);
}


export const securityApi = {
    // Endpoints originales basados en el código anterior
    getMe: () => request<User>('/users/me'),
    loginStatus: () => request('/auth/status'), 
    getCaCertificateUrl: () => `${BASE_URL}/security/ca-certificate`,
    login: (credentials: any) => {
        const formData = new URLSearchParams();
        formData.append("username", credentials.username);
        formData.append("password", credentials.password);
        
        return request('/auth/cookie/login', {
            method: 'POST',
            body: formData,
            headers: {
                "Content-Type": "application/x-www-form-urlencoded",
            }
        });
    }
};

// --- Routers ---
export async function getRouters() {
    return request('/routers');
}

export async function getRouter(host: string) {
    return request(`/routers/${host}`);
}

export async function createRouter(payload: any) {
    return request('/routers', {
        method: 'POST',
        body: JSON.stringify(payload)
    });
}

export async function updateRouter(host: string, payload: any) {
    return request(`/routers/${host}`, {
        method: 'PATCH',
        body: JSON.stringify(payload)
    });
}

export async function deleteRouter(host: string) {
    return request(`/routers/${host}`, {
        method: 'DELETE'
    });
}

export async function getRouterHistory(host: string, hours = 24) {
    return request(`/routers/${host}/history?hours=${hours}`);
}

export async function provisionRouter(host: string, user: string, pass?: string, method = 'ssh') {
    return request(`/routers/${host}/provision`, {
        method: 'POST',
        body: JSON.stringify({ user, pass, method })
    });
}

export async function repairRouter(host: string, action: string) {
    return request(`/routers/${host}/repair`, {
        method: 'POST',
        body: JSON.stringify({ action })
    });
}

// Router Advanced System
export async function getRouterUsers(host: string) {
    return request(`/routers/${host}/users`);
}

export async function createRouterUser(host: string, payload: any) {
    return request(`/routers/${host}/users`, {
        method: 'POST',
        body: JSON.stringify(payload)
    });
}

export async function deleteRouterUser(host: string, userId: string) {
    return request(`/routers/${host}/users/${encodeURIComponent(userId)}`, {
        method: 'DELETE'
    });
}

export async function createBridge(host: string, payload: any) {
    return request(`/routers/${host}/bridges`, {
        method: 'POST',
        body: JSON.stringify(payload)
    });
}

export async function updateBridge(host: string, bridgeId: string, payload: any) {
    return request(`/routers/${host}/bridges/${bridgeId}`, {
        method: 'PUT',
        body: JSON.stringify(payload)
    });
}

// --- Access Points (APs) ---
export async function getAPs() {
    return request('/aps');
}

export async function getAP(host: string) {
    return request(`/aps/${host}`);
}

export async function createAP(payload: any) {
    return request('/aps', {
        method: 'POST',
        body: JSON.stringify(payload)
    });
}

export async function updateAP(host: string, payload: any) {
    return request(`/aps/${host}`, {
        method: 'PUT',
        body: JSON.stringify(payload)
    });
}

export async function deleteAP(host: string) {
    return request(`/aps/${host}`, {
        method: 'DELETE'
    });
}

export async function validateAP(payload: any) {
    return request('/aps/validate', {
        method: 'POST',
        body: JSON.stringify(payload)
    });
}

export async function syncAPCPEs(host: string) {
    return request(`/aps/${host}/sync-names`, {
        method: 'POST'
    });
}

export async function getAPHistory(host: string, period = '24h') {
    return request(`/aps/${host}/history?period=${period}`);
}

export async function provisionAP(host: string, payload: any) {
    return request(`/aps/${host}/provision`, {
        method: 'POST',
        body: JSON.stringify(payload)
    });
}

export async function repairAP(host: string, action: string) {
    return request(`/aps/${host}/repair`, {
        method: 'POST',
        body: JSON.stringify({ action })
    });
}

// --- Zones ---
export async function getZonas() {
    return request('/zonas');
}

export async function createZona(payload: any) {
    return request('/zonas', {
        method: 'POST',
        body: JSON.stringify(payload)
    });
}

export async function deleteZona(id: number | string) {
    return request(`/zonas/${id}`, {
        method: 'DELETE'
    });
}

export async function getZonaDetails(id: number | string) {
    return request(`/zonas/${id}`);
}

export async function updateZona(id: number | string, payload: any) {
    return request(`/zonas/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(payload)
    });
}

export async function updateZonaInfra(id: number | string, payload: any) {
    return request(`/zonas/${id}/infra`, {
        method: 'PUT',
        body: JSON.stringify(payload)
    });
}

export async function createZonaNote(id: number | string, payload: any) {
    return request(`/zonas/${id}/notes`, {
        method: 'POST',
        body: JSON.stringify(payload)
    });
}

export async function updateZonaNote(noteId: string, payload: any) {
    return request(`/notes/${noteId}`, {
        method: 'PATCH',
        body: JSON.stringify(payload)
    });
}

export async function deleteZonaNote(noteId: string) {
    return request(`/notes/${noteId}`, {
        method: 'DELETE'
    });
}

export async function deleteZonaDocumento(docId: string) {
    return request(`/documents/${docId}`, {
        method: 'DELETE'
    });
}

export async function uploadZonaDocumento(zonaId: number | string, file: File) {
    const formData = new FormData();
    formData.append('file', file);
    return request(`/zonas/${zonaId}/documents`, {
        method: 'POST',
        body: formData,
        headers: {} // Let browser set boundary
    });
}

// --- Users ---
export async function getUsers() {
    return request('/users');
}

export async function createUser(payload: any) {
    return request('/users', {
        method: 'POST',
        body: JSON.stringify(payload)
    });
}

export async function updateUser(id: string, payload: any) {
    return request(`/users/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(payload)
    });
}

export async function deleteUser(id: string) {
    return request(`/users/${id}`, {
        method: 'DELETE'
    });
}

// --- Clients ---
export async function getClients(params: any = {}) {
    const searchParams = new URLSearchParams(params);
    return request(`/clients?${searchParams.toString()}`);
}

export async function getClient(id: string | number) {
    return request(`/clients/${id}`);
}

export async function createClient(payload: any) {
    return request('/clients', {
        method: 'POST',
        body: JSON.stringify(payload)
    });
}

export async function updateClient(id: string | number, payload: any) {
    return request(`/clients/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(payload)
    });
}

export async function deleteClient(id: string | number) {
    return request(`/clients/${id}`, {
        method: 'DELETE'
    });
}

export async function getClientDetails(id: string | number) {
    return request(`/clients/${id}`);
}

export async function getClientServices(id: string | number) {
    return request(`/clients/${id}/services`);
}

export async function getPaymentHistory(id: string | number) {
    return request(`/clients/${id}/payments`);
}

export async function registerPayment(clientId: string | number, payload: any) {
    return request(`/clients/${clientId}/payments`, {
        method: 'POST',
        body: JSON.stringify(payload)
    });
}

export async function changeServicePlan(serviceId: number | string, planId: number) {
    return request(`/services/${serviceId}/plan?new_plan_id=${planId}`, {
        method: 'PUT'
    });
}

export async function syncServiceToRouter(serviceId: number | string) {
    return request(`/services/${serviceId}/sync`, {
        method: 'POST'
    });
}

export async function deleteClientService(serviceId: number | string) {
    return request(`/services/${serviceId}`, {
        method: 'DELETE'
    });
}

export async function getPlansForService(host: string) {
    return request(`/plans/router/${host}`);
}

export async function getPPPoESecrets(host: string, username?: string) {
    const url = username 
        ? `/routers/${host}/pppoe/secrets?name=${encodeURIComponent(username)}`
        : `/routers/${host}/pppoe/secrets`;
    return request(url);
}

export async function getPPPoEActive(host: string, username?: string) {
    const url = username 
        ? `/routers/${host}/pppoe/active?name=${encodeURIComponent(username)}`
        : `/routers/${host}/pppoe/active`;
    return request(url);
}

export async function getPPPoEProfiles(host: string) {
    return request(`/routers/${host}/pppoe/profiles`);
}

export async function getPPPoEServers(host: string) {
    return request(`/routers/${host}/pppoe/servers`);
}

export async function createPPPoESecret(host: string, payload: any) {
    return request(`/routers/${host}/pppoe/secrets`, {
        method: 'POST',
        body: JSON.stringify(payload)
    });
}

export async function updatePPPoESecret(host: string, secretId: string, payload: any) {
    return request(`/routers/${host}/pppoe/secrets/${secretId}`, {
        method: 'PATCH',
        body: JSON.stringify(payload)
    });
}

export async function disablePPPoESecret(host: string, secretId: string, disabled: boolean) {
    return request(`/routers/${host}/pppoe/secrets/${secretId}/disable?disabled=${disabled}`, {
        method: 'POST'
    });
}

export async function deletePPPoESecret(host: string, secretId: string) {
    return request(`/routers/${host}/pppoe/secrets/${secretId}`, {
        method: 'DELETE'
    });
}

export async function killPPPoEConnection(host: string, username: string) {
    return request(`/routers/${host}/pppoe/active/kill?name=${encodeURIComponent(username)}`, {
        method: 'POST'
    });
}

export async function addPPPoEServer(host: string, payload: any) {
    return request(`/routers/${host}/pppoe/servers`, {
        method: 'POST',
        body: JSON.stringify(payload)
    });
}

export async function deletePPPoEServer(host: string, serviceName: string) {
    return request(`/routers/${host}/pppoe/servers/${encodeURIComponent(serviceName)}`, {
        method: 'DELETE'
    });
}

export async function createPPPProfile(host: string, payload: any) {
    return request(`/routers/${host}/pppoe/profiles`, {
        method: 'POST',
        body: JSON.stringify(payload)
    });
}

export async function deletePPPProfile(host: string, profileName: string) {
    return request(`/routers/${host}/pppoe/profiles/${encodeURIComponent(profileName)}`, {
        method: 'DELETE'
    });
}

export async function getQueueStats(host: string, ip: string) {
    return request(`/routers/${host}/queue/stats?target=${encodeURIComponent(ip)}`);
}

export async function generateClientAccess(clientId: string | number, payload: any) {
    return request(`/clients/${clientId}/generate-access`, {
        method: 'POST',
        body: JSON.stringify(payload)
    });
}

// --- Tickets ---
export async function getTickets(params: any = {}) {
    const searchParams = new URLSearchParams(params);
    return request(`/tickets/?${searchParams.toString()}`);
}

export async function createTicket(payload: any) {
    return request('/tickets/', {
        method: 'POST',
        body: JSON.stringify(payload)
    });
}

export async function searchClientsForTicket(query: string) {
    return request(`/clients/search?query=${encodeURIComponent(query)}`);
}

export async function getTicket(id: string) {
    return request(`/tickets/${id}`);
}

export async function replyTicket(id: string, payload: any) {
    return request(`/tickets/${id}/replies`, {
        method: 'POST',
        body: JSON.stringify(payload)
    });
}

export async function updateTicketStatus(id: string, payload: any) {
    return request(`/tickets/${id}/status`, {
        method: 'PATCH',
        body: JSON.stringify(payload)
    });
}

export async function getPaymentReceipt(paymentId: string | number) {
    return request(`/clients/payments/${paymentId}/receipt`);
}

export async function logout() {
    return request('/security/logout', { method: 'POST' });
}

// --- System Services ---
export async function getSystemServicesStatus() {
    return request('/settings/system/status');
}

export async function getSystemServices() {
    return request('/settings/system/services');
}

export async function updateSystemServices(payload: any) {
    return request('/settings/system/services', {
        method: 'POST',
        body: JSON.stringify(payload)
    });
}

export async function testServiceConnection(payload: any) {
    return request('/settings/system/test-connection', {
        method: 'POST',
        body: JSON.stringify(payload)
    });
}

export async function restartBots() {
    return request('/settings/restart-bots', {
        method: 'POST'
    });
}

// --- Communication (Broadcast) ---
export async function uploadBroadcastImage(file: File) {
    const formData = new FormData();
    formData.append('file', file);
    return request('/broadcast/upload', {
        method: 'POST',
        body: formData,
        headers: {} // Let browser set boundary correctly for Multipart
    });
}

export async function sendBroadcast(payload: any) {
    return request('/broadcast/send', {
        method: 'POST',
        body: JSON.stringify(payload)
    });
}

export async function getBroadcastZones() {
    return request('/broadcast/zones');
}

// --- Router Backups ---
export interface BackupCreatePayload {
    backup_name: string;
    backup_type: 'backup' | 'export';
    overwrite?: boolean;
}

export async function getRouterFiles(host: string) {
    return request(`/routers/${host}/backups/router-files`);
}

export async function createRouterBackup(host: string, payload: BackupCreatePayload) {
    return request(`/routers/${host}/backups/create`, {
        method: 'POST',
        body: JSON.stringify(payload)
    });
}

export async function deleteRouterFile(host: string, fileId: string) {
    return request(`/routers/${host}/backups/router-files/${encodeURIComponent(fileId)}`, {
        method: 'DELETE'
    });
}

export async function saveBackupToServer(host: string, filename: string) {
    return request(`/routers/${host}/backups/save-to-server?filename=${encodeURIComponent(filename)}`, {
        method: 'POST'
    });
}

export async function getLocalBackups(host: string) {
    return request(`/routers/${host}/backups/local-files`);
}

export async function deleteLocalBackup(host: string, filename: string) {
    return request(`/routers/${host}/backups/local-files/${encodeURIComponent(filename)}`, {
        method: 'DELETE'
    });
}

export function getLocalBackupDownloadUrl(host: string, filename: string) {
    const baseUrl = import.meta.env.VITE_API_URL || '';
    return `${baseUrl}/routers/${host}/backups/download/${encodeURIComponent(filename)}`;
}

// --- Router Users ---
// Removed duplicates


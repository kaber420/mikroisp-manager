import { request } from './index';

export async function getPortalMe() {
    return request('/portal/me');
}

export async function getPortalTickets(limit: number = 10, offset: number = 0) {
    return request(`/portal/tickets?limit=${limit}&offset=${offset}`);
}

export async function getPortalPlanes() {
    return request('/portal/planes');
}

export async function getPortalAnnouncements() {
    return request('/portal/announcements');
}

export async function createPortalTicket(data: any) {
    return request('/portal/tickets', {
        method: 'POST',
        body: JSON.stringify(data)
    });
}

export async function sendTicketMessage(ticketId: string, message: string) {
    return request(`/portal/tickets/${ticketId}/messages`, {
        method: 'POST',
        body: JSON.stringify({ content: message })
    });
}

// --- Admin Portal CMS (Announcements) ---

export async function getAdminPortalAnnouncements() {
    return request('/broadcast/announcements/');
}

export async function createAdminPortalAnnouncement(data: any) {
    return request('/broadcast/announcements/', {
        method: 'POST',
        body: JSON.stringify(data)
    });
}

export async function updateAdminPortalAnnouncement(id: string, data: any) {
    return request(`/broadcast/announcements/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data)
    });
}

export async function deleteAdminPortalAnnouncement(id: string) {
    return request(`/broadcast/announcements/${id}`, {
        method: 'DELETE'
    });
}

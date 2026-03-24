import { request } from './index';

export async function getPublicSettings() {
    return request('/settings/public');
}

export async function getSettings() {
    return request('/settings');
}

export async function updateSettings(payload: any) {
    return request('/settings', {
        method: 'PUT',
        body: JSON.stringify(payload)
    });
}

export async function forceBilling() {
    return request('/settings/force-billing', {
        method: 'POST'
    });
}

export async function backupNow() {
    return request('/settings/backup-now', {
        method: 'POST'
    });
}

export async function getAuditLogs(page = 1, pageSize = 20, action?: string, username?: string) {
    let url = `/settings/audit-logs?page=${page}&page_size=${pageSize}`;
    if (action) url += `&action=${action}`;
    if (username) url += `&username=${username}`;
    return request(url);
}

export async function getAuditLogFilters() {
    return request('/settings/audit-logs/filters');
}


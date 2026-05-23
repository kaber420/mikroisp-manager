import { request } from './index';

// CPEs & APs
export async function getAPs() {
    return request('/aps');
}

// Router Management
export async function getRouterFullDetails(host: string) {
    return request(`/routers/${host}/full-details`);
}

export async function addIpAddress(host: string, payload: any) {
    return request(`/routers/${host}/write/add-ip`, {
        method: 'POST',
        body: JSON.stringify(payload)
    });
}

export async function deleteIpAddress(host: string, address: string) {
    return request(`/routers/${host}/write/delete-ip?address=${encodeURIComponent(address)}`, {
        method: 'DELETE'
    });
}

export async function createVlan(host: string, payload: any) {
    return request(`/routers/${host}/vlans`, {
        method: 'POST',
        body: JSON.stringify(payload)
    });
}

export async function updateVlan(host: string, vlanId: string, payload: any) {
    return request(`/routers/${host}/vlans/${vlanId}`, {
        method: 'PUT',
        body: JSON.stringify(payload)
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

export async function updateInterfaceState(host: string, id: string, disabled: boolean) {
    return request(`/routers/${host}/interfaces/${id}/state?disabled=${disabled}`, {
        method: 'POST'
    });
}

export async function deleteInterface(host: string, id: string, type: string) {
    return request(`/routers/${host}/interfaces/${id}?type=${type}`, {
        method: 'DELETE'
    });
}

export async function addNatRule(host: string, payload: any) {
    return request(`/routers/${host}/write/add-nat`, {
        method: 'POST',
        body: JSON.stringify(payload)
    });
}

export async function deleteNatRule(host: string, comment: string) {
    return request(`/routers/${host}/write/delete-nat?comment=${encodeURIComponent(comment)}`, {
        method: 'DELETE'
    });
}

export async function addSimpleQueue(host: string, payload: any) {
    return request(`/routers/${host}/write/add-simple-queue`, {
        method: 'POST',
        body: JSON.stringify(payload)
    });
}

export async function deleteSimpleQueue(host: string, queueId: string) {
    return request(`/routers/${host}/write/delete-simple-queue?queue_id=${encodeURIComponent(queueId)}`, {
        method: 'DELETE'
    });
}

// Plans
export async function getPlans() {
    return request('/plans');
}

export async function getPlansByRouter(host: string) {
    return request(`/plans/router/${host}`);
}

export async function createPlan(payload: any) {
    return request('/plans', {
        method: 'POST',
        body: JSON.stringify(payload)
    });
}

export async function updatePlan(id: number | string, payload: any) {
    return request(`/plans/${id}`, {
        method: 'PUT',
        body: JSON.stringify(payload)
    });
}

export async function deletePlan(id: number | string) {
    return request(`/plans/${id}`, {
        method: 'DELETE'
    });
}

// CPEs
export async function getCPEs(params: any = {}) {
    const searchParams = new URLSearchParams(params);
    return request(`/cpes/all?${searchParams.toString()}`);
}

export async function updateCPE(mac: string, payload: any) {
    return request(`/cpes/${mac}`, {
        method: 'PUT',
        body: JSON.stringify(payload)
    });
}

export async function disableCPE(mac: string) {
    return request(`/cpes/${mac}/disable`, {
        method: 'POST'
    });
}

export async function deleteCPE(mac: string) {
    return request(`/cpes/${mac}`, {
        method: 'DELETE'
    });
}

// Docker Infrastructure (Stack Management)
export async function getInfraStatus() {
    return request('/settings/infra/status');
}

export async function deployInfraStack(payload: any) {
    return request('/settings/infra/deploy', {
        method: 'POST',
        body: JSON.stringify(payload)
    });
}

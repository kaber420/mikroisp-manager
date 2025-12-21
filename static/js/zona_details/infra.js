/**
 * Infrastructure visualization module for Zone Details
 * Handles router diagrams, port SVG rendering, and VLAN visualization
 * Uses shared InfraViz module for SVG rendering
 */

/**
 * Load infrastructure data for a zone
 */
async function loadInfrastructure(zonaId) {
    const routerDiagramsContainer = document.getElementById('router-diagrams');
    const infraStatusEl = document.getElementById('infra-status');
    const API_BASE_URL = window.location.origin;

    if (!routerDiagramsContainer) return;

    infraStatusEl.textContent = 'Loading...';
    routerDiagramsContainer.innerHTML = '<p class="text-text-secondary">Fetching device data...</p>';

    try {
        // Fetch routers and switches in parallel
        const [routersResponse, switchesResponse] = await Promise.all([
            fetch(`${API_BASE_URL}/api/zonas/${zonaId}/infra/routers`),
            fetch(`${API_BASE_URL}/api/zonas/${zonaId}/infra/switches`)
        ]);

        if (!routersResponse.ok) throw new Error('Failed to fetch routers');

        const routers = await routersResponse.json();
        const switches = switchesResponse.ok ? await switchesResponse.json() : [];

        // Mark each device type
        routers.forEach(r => r.device_type = 'router');
        switches.forEach(s => s.device_type = 'switch');

        // Combine all devices
        const allDevices = [...routers, ...switches];

        if (allDevices.length === 0) {
            routerDiagramsContainer.innerHTML = `
                <div class="text-center py-12">
                    <span class="material-symbols-outlined text-6xl text-text-secondary mb-4 block">router</span>
                    <p class="text-text-secondary">No routers or switches linked to this zone.</p>
                    <p class="text-sm text-text-secondary mt-2">Assign devices to this zone from the Routers or Switches page.</p>
                </div>
            `;
            infraStatusEl.textContent = 'No devices';
            return;
        }

        // Clear container and render each device
        routerDiagramsContainer.innerHTML = '';

        const routerCount = routers.length;
        const switchCount = switches.length;
        const statusParts = [];
        if (routerCount > 0) statusParts.push(`${routerCount} router(s)`);
        if (switchCount > 0) statusParts.push(`${switchCount} switch(es)`);
        infraStatusEl.textContent = statusParts.join(', ');

        for (const device of allDevices) {
            const deviceCard = document.createElement('div');
            deviceCard.className = 'bg-surface-2 rounded-lg border border-border-color overflow-hidden';

            const deviceIcon = device.device_type === 'switch' ? 'switch' : 'router';
            const deviceLabel = device.device_type === 'switch' ? 'Switch' : 'Router';

            deviceCard.innerHTML = `
                <div class="p-4 border-b border-border-color flex justify-between items-center">
                    <div class="flex items-center gap-3">
                        <span class="material-symbols-outlined text-2xl text-text-secondary">${deviceIcon}</span>
                        <div>
                            <h4 class="font-semibold text-lg">${device.hostname || device.host}</h4>
                            <p class="text-sm text-text-secondary">${device.host} • ${device.model || 'Unknown model'} • <span class="text-xs opacity-70">${deviceLabel}</span></p>
                        </div>
                    </div>
                    <span class="px-2 py-1 rounded text-xs font-medium ${device.last_status === 'online' ? 'bg-success/20 text-success' : 'bg-danger/20 text-danger'}">
                        ${device.last_status || 'unknown'}
                    </span>
                </div>
                <div class="p-4" id="device-svg-${device.host.replace(/\./g, '-')}">
                    <p class="text-text-secondary text-sm">Loading ports...</p>
                </div>
            `;
            routerDiagramsContainer.appendChild(deviceCard);

            // Fetch detailed port info for this device
            if (device.is_enabled && device.last_status === 'online') {
                loadDevicePorts(device.host, device.device_type);
            } else {
                const svgContainer = document.getElementById(`device-svg-${device.host.replace(/\./g, '-')}`);
                svgContainer.innerHTML = `<p class="text-text-secondary text-sm italic">Device offline or disabled</p>`;
            }
        }

    } catch (error) {
        routerDiagramsContainer.innerHTML = `<p class="text-danger">Error: ${error.message}</p>`;
        infraStatusEl.textContent = 'Error';
    }
}

/**
 * Load port data for a single device (router or switch) and render SVG
 */
async function loadDevicePorts(host, deviceType = 'router') {
    const API_BASE_URL = window.location.origin;
    const containerId = `device-svg-${host.replace(/\./g, '-')}`;
    const container = document.getElementById(containerId);
    if (!container) return;

    try {
        // Use appropriate endpoint based on device type
        // Both endpoints live under /api/zonas/infra/ for consistency
        const endpoint = deviceType === 'switch'
            ? `${API_BASE_URL}/api/zonas/infra/switch/${host}/ports`
            : `${API_BASE_URL}/api/zonas/infra/router/${host}/ports`;

        const response = await fetch(endpoint);
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to load');
        }
        const data = await response.json();
        renderDeviceSVG(container, data, deviceType);
    } catch (error) {
        container.innerHTML = `<p class="text-danger text-sm">Error: ${error.message}</p>`;
    }
}

/**
 * Render an SVG device diagram using shared InfraViz module
 */
function renderDeviceSVG(container, data, deviceType = 'router') {
    InfraViz.renderDeviceSVG(container, data, deviceType);
}

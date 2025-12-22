/**
 * Infrastructure visualization module for Zone Details
 * Handles router diagrams, port SVG rendering, VLAN visualization, and layout editing
 * Uses shared InfraViz module for SVG rendering
 */

// State
let currentZonaId = null;
let currentRackLayout = {};
let editingRackLayout = {};
let currentDevices = [];
let isEditingLayout = false;

/**
 * Initialize the infrastructure module
 */
function initInfrastructure(zonaId) {
    currentZonaId = zonaId;

    // Set up event listeners
    const editBtn = document.getElementById('edit-layout-btn');
    const saveBtn = document.getElementById('save-layout-btn');
    const refreshBtn = document.getElementById('refresh-infra-btn');

    if (editBtn) {
        editBtn.addEventListener('click', toggleLayoutEditor);
    }
    if (saveBtn) {
        saveBtn.addEventListener('click', saveRackLayout);
    }
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => loadInfrastructure(zonaId));
    }

    // Load infrastructure
    loadInfrastructure(zonaId);
}

/**
 * Toggle layout editor visibility
 */
function toggleLayoutEditor() {
    isEditingLayout = !isEditingLayout;

    const editorPanel = document.getElementById('layout-editor-panel');
    const editBtn = document.getElementById('edit-layout-btn');
    const saveBtn = document.getElementById('save-layout-btn');

    if (isEditingLayout) {
        editorPanel.style.display = 'block';
        editBtn.classList.add('bg-primary', 'text-white');
        editBtn.classList.remove('bg-surface-2', 'text-text-secondary');
        editBtn.querySelector('span:last-child').textContent = 'Editing Layout';
        saveBtn.style.display = 'flex';

        // Populate editor inputs
        populateLayoutInputs();
    } else {
        editorPanel.style.display = 'none';
        editBtn.classList.remove('bg-primary', 'text-white');
        editBtn.classList.add('bg-surface-2', 'text-text-secondary');
        editBtn.querySelector('span:last-child').textContent = 'Edit Layout';
        saveBtn.style.display = 'none';
    }
}

/**
 * Populate the layout editor inputs with current devices
 */
function populateLayoutInputs() {
    const container = document.getElementById('layout-inputs-container');
    if (!container) return;

    container.innerHTML = currentDevices.map(device => `
        <div class="flex items-center gap-2 p-2 rounded bg-surface-1/50">
            <span class="material-symbols-outlined text-lg text-text-secondary">${device.device_type === 'switch' ? 'switch' : 'router'}</span>
            <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-white truncate">${device.hostname || device.host}</p>
                <p class="text-xs text-text-secondary truncate">${device.host}</p>
            </div>
            <input type="text" 
                id="layout-input-${device.host.replace(/\./g, '-')}"
                value="${editingRackLayout[device.host] || ''}"
                placeholder="e.g. 1-f"
                class="w-20 px-2 py-1 text-sm bg-surface-1 border border-border-color rounded focus:ring-primary focus:border-primary text-white placeholder-text-secondary/50">
        </div>
    `).join('');
}

/**
 * Save rack layout to API
 */
async function saveRackLayout() {
    if (!currentZonaId) return;

    const saveBtn = document.getElementById('save-layout-btn');
    const originalBtnHtml = saveBtn.innerHTML;
    saveBtn.innerHTML = '<span class="material-symbols-outlined text-base animate-spin">sync</span> Saving...';
    saveBtn.disabled = true;

    try {
        // Collect values from inputs
        const cleanLayout = {};
        currentDevices.forEach(device => {
            const input = document.getElementById(`layout-input-${device.host.replace(/\./g, '-')}`);
            if (input && input.value.trim()) {
                cleanLayout[device.host] = input.value.trim().toLowerCase();
            }
        });

        const response = await fetch(`${window.location.origin}/api/zonas/${currentZonaId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ rack_layout: cleanLayout })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to save layout');
        }

        currentRackLayout = { ...cleanLayout };
        editingRackLayout = { ...cleanLayout };

        // Close editor and re-render
        toggleLayoutEditor();
        renderRackView();

        showToast('Layout saved successfully', 'success');

    } catch (error) {
        console.error('Error saving rack layout:', error);
        showToast(`Error saving layout: ${error.message}`, 'danger');
    } finally {
        saveBtn.innerHTML = originalBtnHtml;
        saveBtn.disabled = false;
    }
}

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
        // Fetch zone details to get rack_layout, and routers/switches in parallel
        const [zoneResponse, routersResponse, switchesResponse] = await Promise.all([
            fetch(`${API_BASE_URL}/api/zonas/${zonaId}/details`),
            fetch(`${API_BASE_URL}/api/zonas/${zonaId}/infra/routers`),
            fetch(`${API_BASE_URL}/api/zonas/${zonaId}/infra/switches`)
        ]);

        if (!routersResponse.ok) throw new Error('Failed to fetch routers');

        const zoneData = zoneResponse.ok ? await zoneResponse.json() : {};
        const routers = await routersResponse.json();
        const switches = switchesResponse.ok ? await switchesResponse.json() : [];

        // Get rack_layout from zone data
        currentRackLayout = zoneData.rack_layout || {};
        editingRackLayout = { ...currentRackLayout };

        // Mark each device type
        routers.forEach(r => r.device_type = 'router');
        switches.forEach(s => s.device_type = 'switch');

        // Combine all devices
        currentDevices = [...routers, ...switches];

        if (currentDevices.length === 0) {
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

        // Update status
        const routerCount = routers.length;
        const switchCount = switches.length;
        const statusParts = [];
        if (routerCount > 0) statusParts.push(`${routerCount} router(s)`);
        if (switchCount > 0) statusParts.push(`${switchCount} switch(es)`);
        infraStatusEl.textContent = statusParts.join(', ');

        // Render rack view
        renderRackView();

    } catch (error) {
        routerDiagramsContainer.innerHTML = `<p class="text-danger">Error: ${error.message}</p>`;
        infraStatusEl.textContent = 'Error';
    }
}

/**
 * Render the virtual rack view
 */
function renderRackView() {
    const routerDiagramsContainer = document.getElementById('router-diagrams');
    if (!routerDiagramsContainer) return;

    InfraViz.renderRack(
        routerDiagramsContainer,
        currentDevices,
        currentRackLayout,
        (deviceContainer, device) => {
            if (device.is_enabled && device.last_status === 'online') {
                loadDevicePortsIntoContainer(deviceContainer, device.host, device.device_type);
            } else {
                deviceContainer.innerHTML = '<p class="text-text-secondary text-sm italic">Device offline or disabled</p>';
            }
        }
    );
}

/**
 * Load device ports into a specific container
 */
async function loadDevicePortsIntoContainer(container, host, deviceType = 'router') {
    const API_BASE_URL = window.location.origin;

    try {
        const endpoint = deviceType === 'switch'
            ? `${API_BASE_URL}/api/zonas/infra/switch/${host}/ports`
            : `${API_BASE_URL}/api/zonas/infra/router/${host}/ports`;

        const response = await fetch(endpoint);
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to load');
        }
        const data = await response.json();
        InfraViz.renderDeviceSVG(container, data, deviceType);
    } catch (error) {
        container.innerHTML = `<p class="text-danger text-sm">Error: ${error.message}</p>`;
    }
}

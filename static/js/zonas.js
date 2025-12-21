document.addEventListener('alpine:init', () => {

    Alpine.data('zoneManager', () => ({

        // --- ESTADO (STATE) ---
        zones: [],
        searchQuery: '', // Faltaba esto para la barra de búsqueda
        isLoading: true,
        isModalOpen: false,
        modalMode: 'add', // 'add' o 'edit'
        currentZone: { id: null, nombre: '', descripcion: '' }, // Añadido campo descripción
        error: '',
        API_BASE_URL: window.location.origin,

        // --- Read-Only Details Modal State ---
        isDetailsModalOpen: false,
        isLoadingDetails: false,
        selectedZoneDetails: { id: null, nombre: '', notes: [] },
        noteSearchQuery: '',
        selectedNote: null,
        activeDetailsTab: 'notes', // 'notes' or 'infra'

        // --- Infrastructure (Virtual Rack) State ---
        isLoadingInfra: false,
        infraDevices: [],
        infraStatusText: '',
        infraDataLoaded: false, // Track if data has been loaded for current zone

        // --- COMPUTADOS (GETTERS) ---
        // Esto es lo que faltaba: Filtra las zonas según lo que escribas en el buscador
        get filteredZones() {
            if (this.searchQuery === '') {
                return this.zones;
            }
            const lowerSearch = this.searchQuery.toLowerCase();
            return this.zones.filter(zone => {
                const nombre = zone.nombre ? zone.nombre.toLowerCase() : '';
                const desc = zone.descripcion ? zone.descripcion.toLowerCase() : '';
                return nombre.includes(lowerSearch) || desc.includes(lowerSearch);
            });
        },

        // --- MÉTODOS (METHODS) ---

        init() {
            this.loadZones();
        },

        async loadZones() {
            this.isLoading = true;
            try {
                const response = await fetch(`${this.API_BASE_URL}/api/zonas`);
                if (!response.ok) throw new Error('Failed to load zones');
                this.zones = await response.json();
            } catch (err) {
                console.error('Error loading zones:', err);
                this.error = 'Could not load zones. Please refresh the page.';
            } finally {
                this.isLoading = false;
            }
        },

        openModal(zone = null) {
            this.error = '';
            if (zone) {
                // Modo Editar
                this.modalMode = 'edit';
                // Copiamos el objeto para no modificar la tabla directamente mientras editamos
                this.currentZone = {
                    id: zone.id,
                    nombre: zone.nombre,
                    descripcion: zone.descripcion || ''
                };
            } else {
                // Modo Añadir
                this.modalMode = 'add';
                this.currentZone = { id: null, nombre: '', descripcion: '' };
            }
            this.isModalOpen = true;
        },

        closeModal() {
            this.isModalOpen = false;
            this.error = '';
            // Limpiamos la zona actual al cerrar
            setTimeout(() => {
                this.currentZone = { id: null, nombre: '', descripcion: '' };
            }, 300);
        },

        async saveZone() {
            this.error = '';

            // Validación simple
            if (!this.currentZone.nombre || this.currentZone.nombre.trim() === '') {
                this.error = 'Zone name cannot be empty.';
                return;
            }

            const isEditing = this.modalMode === 'edit';
            const url = isEditing
                ? `${this.API_BASE_URL}/api/zonas/${this.currentZone.id}`
                : `${this.API_BASE_URL}/api/zonas`;

            const method = isEditing ? 'PUT' : 'POST';

            // Enviamos tanto nombre como descripción
            const data = {
                nombre: this.currentZone.nombre,
                descripcion: this.currentZone.descripcion
            };

            try {
                const response = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data),
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || 'Failed to save zone');
                }

                await this.loadZones(); // Recargamos la lista
                this.closeModal();

            } catch (err) {
                this.error = `Error: ${err.message}`;
            }
        },

        async deleteZone(zone) {
            if (confirm(`Are you sure you want to delete "${zone.nombre}"?`)) {
                try {
                    const response = await fetch(`${this.API_BASE_URL}/api/zonas/${zone.id}`, { method: 'DELETE' });

                    if (!response.ok) {
                        const errorData = await response.json();
                        throw new Error(errorData.detail || 'Failed to delete zone');
                    }

                    // Actualizamos la lista localmente para que sea más rápido
                    this.zones = this.zones.filter(z => z.id !== zone.id);

                } catch (err) {
                    showToast(`Error: ${err.message}`, 'danger');
                }
            }
        },

        // --- Read-Only Details Modal Methods ---

        get filteredNotes() {
            const notes = this.selectedZoneDetails.notes || [];
            if (!this.noteSearchQuery) {
                return notes;
            }
            const lowerSearch = this.noteSearchQuery.toLowerCase();
            return notes.filter(note =>
                (note.title && note.title.toLowerCase().includes(lowerSearch)) ||
                (note.content && note.content.toLowerCase().includes(lowerSearch))
            );
        },

        get renderedNoteContent() {
            if (this.selectedNote && this.selectedNote.content && typeof marked !== 'undefined') {
                return marked.parse(this.selectedNote.content);
            }
            return '<p class="text-text-secondary">No content available.</p>';
        },

        async openDetailsModal(zone) {
            this.isDetailsModalOpen = true;
            this.isLoadingDetails = true;
            this.selectedZoneDetails = { id: zone.id, nombre: zone.nombre, notes: [] };
            this.noteSearchQuery = '';
            this.selectedNote = null;
            this.activeDetailsTab = 'notes';

            // Reset infrastructure state
            this.infraDevices = [];
            this.infraStatusText = '';
            this.infraDataLoaded = false;

            try {
                const response = await fetch(`${this.API_BASE_URL}/api/zonas/${zone.id}/details`);
                if (!response.ok) throw new Error('Failed to load zone details');
                const data = await response.json();

                this.selectedZoneDetails = {
                    id: zone.id,
                    nombre: data.nombre || zone.nombre,
                    notes: data.notes || []
                };

                // Auto-select first note if available
                if (this.selectedZoneDetails.notes.length > 0) {
                    this.selectedNote = this.selectedZoneDetails.notes[0];
                }
            } catch (err) {
                console.error('Error loading zone details:', err);
                showToast(`Error loading details: ${err.message}`, 'danger');
            } finally {
                this.isLoadingDetails = false;
            }
        },

        closeDetailsModal() {
            this.isDetailsModalOpen = false;
            setTimeout(() => {
                this.selectedZoneDetails = { id: null, nombre: '', notes: [] };
                this.selectedNote = null;
                this.noteSearchQuery = '';
                this.activeDetailsTab = 'notes';
                this.infraDevices = [];
                this.infraDataLoaded = false;
            }, 300);
        },

        selectNote(note) {
            this.selectedNote = note;
        },

        // --- Infrastructure (Virtual Rack) Methods ---

        async loadInfrastructureData() {
            // Don't reload if already loaded for this zone
            if (this.infraDataLoaded) return;

            const zonaId = this.selectedZoneDetails.id;
            if (!zonaId) return;

            this.isLoadingInfra = true;
            this.infraDevices = [];
            this.infraStatusText = '';

            try {
                // Fetch routers and switches in parallel
                const [routersResponse, switchesResponse] = await Promise.all([
                    fetch(`${this.API_BASE_URL}/api/zonas/${zonaId}/infra/routers`),
                    fetch(`${this.API_BASE_URL}/api/zonas/${zonaId}/infra/switches`)
                ]);

                if (!routersResponse.ok) throw new Error('Failed to fetch routers');

                const routers = await routersResponse.json();
                const switches = switchesResponse.ok ? await switchesResponse.json() : [];

                // Mark each device type
                routers.forEach(r => r.device_type = 'router');
                switches.forEach(s => s.device_type = 'switch');

                // Combine all devices
                this.infraDevices = [...routers, ...switches];

                // Update status text
                const routerCount = routers.length;
                const switchCount = switches.length;
                const statusParts = [];
                if (routerCount > 0) statusParts.push(`${routerCount} router(s)`);
                if (switchCount > 0) statusParts.push(`${switchCount} switch(es)`);
                this.infraStatusText = statusParts.join(', ') || 'No devices';

                this.infraDataLoaded = true;

                // After a short delay to allow DOM to render, load port SVGs
                // Using setTimeout since Alpine.js doesn't have $nextTick like Vue
                setTimeout(() => {
                    for (const device of this.infraDevices) {
                        if (device.is_enabled && device.last_status === 'online') {
                            this.loadDevicePorts(device.host, device.device_type);
                        }
                    }
                }, 100);

            } catch (error) {
                console.error('Error loading infrastructure:', error);
                showToast(`Error loading infrastructure: ${error.message}`, 'danger');
                this.infraStatusText = 'Error loading';
            } finally {
                this.isLoadingInfra = false;
            }
        },

        async loadDevicePorts(host, deviceType = 'router') {
            const containerId = `zone-device-svg-${host.replace(/\./g, '-')}`;
            const container = document.getElementById(containerId);
            if (!container) return;

            try {
                // Use appropriate endpoint based on device type
                const endpoint = deviceType === 'switch'
                    ? `${this.API_BASE_URL}/api/zonas/infra/switch/${host}/ports`
                    : `${this.API_BASE_URL}/api/zonas/infra/router/${host}/ports`;

                const response = await fetch(endpoint);
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Failed to load');
                }
                const data = await response.json();
                this.renderDeviceSVG(container, data, deviceType);
            } catch (error) {
                container.innerHTML = `<p class="text-danger text-sm">Error: ${error.message}</p>`;
            }
        },

        /**
         * Generate a consistent color based on VLAN ID
         */
        vlanIdToColor(vlanId) {
            if (!vlanId) return '#6B7280'; // grey for untagged
            const hue = (parseInt(vlanId) * 137.508) % 360; // Golden angle
            return `hsl(${hue}, 70%, 50%)`;
        },

        /**
         * Render an SVG device diagram with RJ45-style ports
         */
        renderDeviceSVG(container, data, deviceType = 'router') {
            const ports = data.ports || [];
            if (ports.length === 0) {
                container.innerHTML = '<p class="text-text-secondary text-sm italic">No physical ports found</p>';
                return;
            }

            // Calculate dimensions
            const portWidth = 48;
            const portHeight = 52;
            const portGap = 8;
            const padding = 16;
            const portsPerRow = Math.min(ports.length, 12);
            const rows = Math.ceil(ports.length / portsPerRow);

            const svgWidth = (portWidth + portGap) * portsPerRow + padding * 2 - portGap;
            const svgHeight = (portHeight + portGap) * rows + padding * 2 + 36;

            // Generate unique ID for this SVG
            const svgId = `svg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
            const self = this;

            let svgContent = `
                <svg id="${svgId}" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${svgWidth} ${svgHeight}" 
                     class="w-full max-w-4xl" style="background: var(--background); border-radius: 8px;">
                    
                    <!-- Device chassis -->
                    <rect x="0" y="0" width="${svgWidth}" height="${svgHeight - 28}" rx="8" 
                          fill="var(--surface-1)" stroke="var(--border-color)" stroke-width="1"/>
            `;

            // Render ports
            ports.forEach((port, index) => {
                const row = Math.floor(index / portsPerRow);
                const col = index % portsPerRow;
                const x = padding + col * (portWidth + portGap);
                const y = padding + row * (portHeight + portGap);

                const isActive = port.running && !port.disabled;
                const portFill = port.disabled ? '#1F2937' : '#374151';
                const portStroke = port.disabled ? '#374151' : (isActive ? '#6B7280' : '#4B5563');

                // VLAN pins (8 pins, color-coded by VLAN if assigned)
                const portVlans = port.vlans || [];
                const pinColors = [];
                for (let i = 0; i < 8; i++) {
                    if (i < portVlans.length) {
                        pinColors.push(self.vlanIdToColor(portVlans[i].id));
                    } else {
                        pinColors.push(isActive ? '#D4AF37' : '#6B7280');
                    }
                }

                // LED colors
                const linkLedColor = isActive ? '#10B981' : '#6B7280';
                const isPoeActive = port.poe && ['powered-on', 'auto-on', 'forced-on'].includes(port.poe);
                const isPoeConfigured = port.poe && port.poe !== 'off' && port.poe !== null;
                const poeLedColor = isPoeActive ? '#F59E0B' : (isPoeConfigured ? '#F97316' : '#374151');

                svgContent += `
                    <g class="port-group" data-port="${port.name}" data-port-index="${index}" style="cursor: pointer;">
                        <g transform="translate(${x}, ${y})">
                            <rect x="0" y="0" width="${portWidth}" height="38" rx="4" 
                                  fill="${portFill}" stroke="${portStroke}" stroke-width="1.5"/>
                            <rect x="4" y="4" width="${portWidth - 8}" height="22" rx="2" 
                                  fill="#1a1a1a" stroke="#2a2a2a" stroke-width="0.5"/>
                            ${pinColors.map((color, i) => `
                                <rect x="${6 + i * 4.5}" y="6" width="3" height="16" rx="0.5" 
                                      fill="${color}" opacity="${isActive ? 1 : 0.5}"/>
                            `).join('')}
                            <path d="M${portWidth / 2 - 8},26 L${portWidth / 2 - 4},30 L${portWidth / 2 + 4},30 L${portWidth / 2 + 8},26" 
                                  fill="none" stroke="${portStroke}" stroke-width="1"/>
                            <circle cx="8" cy="33" r="3" fill="${linkLedColor}"/>
                            <circle cx="${portWidth - 8}" cy="33" r="3" fill="${poeLedColor}"/>
                        </g>
                        <text x="${x + portWidth / 2}" y="${y + 48}" 
                              text-anchor="middle" font-size="8" fill="var(--text-secondary)" font-weight="500">
                            ${port.name.replace('ether', 'e').replace('sfp-sfpplus', 'sfp+')}
                        </text>
                    </g>
                `;
            });

            // Legend
            const legendY = svgHeight - 20;
            svgContent += `
                <g class="legend" font-size="7" fill="var(--text-secondary)">
                    <circle cx="${padding + 5}" cy="${legendY}" r="3" fill="#10B981"/>
                    <text x="${padding + 12}" y="${legendY + 3}">Link</text>
                    <circle cx="${padding + 42}" cy="${legendY}" r="3" fill="#F59E0B"/>
                    <text x="${padding + 49}" y="${legendY + 3}">PoE Active</text>
                    <circle cx="${padding + 100}" cy="${legendY}" r="3" fill="#F97316"/>
                    <text x="${padding + 107}" y="${legendY + 3}">PoE Waiting</text>
                    <circle cx="${padding + 170}" cy="${legendY}" r="3" fill="#6B7280"/>
                    <text x="${padding + 177}" y="${legendY + 3}">Down/Off</text>
                    <text x="${padding + 225}" y="${legendY + 3}">Pins = VLANs (hover for details)</text>
                </g>
            `;

            svgContent += '</svg>';

            // Bridge summary
            let bridgeSummary = '';
            if (data.bridges && data.bridges.length > 0) {
                bridgeSummary = `
                    <div class="mt-4 pt-4 border-t border-border-color">
                        <h5 class="text-sm font-semibold mb-2">Bridges</h5>
                        <div class="flex flex-wrap gap-2">
                            ${data.bridges.map(b => `
                                <span class="inline-flex items-center gap-1 px-2 py-1 rounded bg-blue-500/20 text-blue-400 text-xs">
                                    <span class="material-symbols-outlined text-sm">lan</span>
                                    ${b.name}: ${b.members.join(', ')}
                                </span>
                            `).join('')}
                        </div>
                    </div>
                `;
            }

            // Store port data for tooltip
            container._portData = ports;

            // Tooltip popup element
            const tooltipId = `port-tooltip-${svgId}`;
            const tooltipHtml = `
                <div id="${tooltipId}" class="fixed z-50 hidden bg-surface-1 border border-border-color rounded-lg shadow-xl p-3 min-w-52 max-w-72 text-sm pointer-events-none">
                    <div class="font-semibold text-base mb-2" id="${tooltipId}-name">ether1</div>
                    <div class="space-y-1 text-text-secondary" id="${tooltipId}-content"></div>
                </div>
            `;

            container.innerHTML = svgContent + bridgeSummary + tooltipHtml;

            // Add hover event listeners
            const svg = container.querySelector('svg');
            const tooltip = container.querySelector(`#${tooltipId}`);
            const tooltipName = container.querySelector(`#${tooltipId}-name`);
            const tooltipContent = container.querySelector(`#${tooltipId}-content`);

            svg.querySelectorAll('.port-group').forEach(group => {
                group.addEventListener('mouseenter', (e) => {
                    const portIndex = parseInt(group.dataset.portIndex);
                    const port = container._portData[portIndex];
                    if (!port) return;

                    const isActive = port.running && !port.disabled;

                    // Build tooltip content
                    let html = `
                        <div class="flex items-center gap-2 mb-1">
                            <span class="inline-block w-2 h-2 rounded-full" style="background: ${isActive ? '#10B981' : '#6B7280'}"></span>
                            <span class="font-medium">${isActive ? 'Link Up' : (port.disabled ? 'Disabled' : 'Link Down')}</span>
                        </div>
                    `;

                    if (port.rate || port.speed) {
                        html += `<div>Speed: <span class="font-medium text-green-400">${port.rate || port.speed}</span></div>`;
                    } else if (isActive) {
                        html += `<div>Speed: <span class="text-text-secondary italic">Unknown</span></div>`;
                    }

                    if (port.poe) {
                        const isPoeActive = ['powered-on', 'auto-on', 'forced-on'].includes(port.poe);
                        const poeStatusText = port.poe === 'powered-on' ? 'Supplying Power' :
                            port.poe === 'auto-on' ? 'Auto (Supplying)' :
                                port.poe === 'forced-on' ? 'Forced On' :
                                    port.poe === 'waiting-for-load' ? 'Waiting for Load' :
                                        port.poe;
                        html += `<div class="flex items-center gap-2">PoE: <span class="${isPoeActive ? 'text-yellow-400 font-medium' : 'text-text-secondary'}">${poeStatusText}</span></div>`;

                        if (isPoeActive && (port.poe_voltage || port.poe_power)) {
                            html += `<div class="text-xs pl-4 text-text-secondary">`;
                            if (port.poe_voltage) html += `${port.poe_voltage}V`;
                            if (port.poe_current) html += ` / ${port.poe_current}mA`;
                            if (port.poe_power) html += ` / ${port.poe_power}W`;
                            html += `</div>`;
                        }
                    } else {
                        html += `<div>PoE: <span class="text-text-secondary">Not available</span></div>`;
                    }

                    if (port.mac_address) {
                        html += `<div class="text-xs opacity-70">MAC: ${port.mac_address}</div>`;
                    }

                    if (port.bridge) {
                        html += `<div>Bridge: <span class="text-blue-400">${port.bridge}</span></div>`;
                    }

                    const portVlans = port.vlans || [];
                    if (portVlans.length > 0) {
                        html += `
                            <div class="mt-2 pt-2 border-t border-border-color">
                                <div class="font-medium mb-2">VLANs (${portVlans.length}):</div>
                                <div class="grid grid-cols-2 gap-1">
                                    ${portVlans.map((v, i) => `
                                        <div class="flex items-center gap-1.5 text-xs">
                                            <span class="inline-block w-2 h-2 rounded-sm flex-shrink-0" style="background: ${self.vlanIdToColor(v.id)}"></span>
                                            <span class="opacity-60">Pin ${i + 1}:</span>
                                            <span>${v.id}${v.name ? ' (' + v.name + ')' : ''}</span>
                                        </div>
                                    `).join('')}
                                </div>
                            </div>
                        `;
                    } else {
                        html += `<div class="text-xs opacity-50 mt-1">No VLANs assigned (untagged)</div>`;
                    }

                    tooltipName.textContent = port.name;
                    tooltipContent.innerHTML = html;

                    // Position tooltip
                    const rect = group.getBoundingClientRect();
                    const tooltipWidth = 288;

                    if (window.innerWidth - rect.right > tooltipWidth + 20) {
                        tooltip.style.left = `${rect.right + 10}px`;
                    } else {
                        tooltip.style.left = `${rect.left - tooltipWidth - 10}px`;
                    }
                    tooltip.style.top = `${rect.top}px`;
                    tooltip.classList.remove('hidden');
                });

                group.addEventListener('mouseleave', () => {
                    tooltip.classList.add('hidden');
                });
            });
        }
    }));
});
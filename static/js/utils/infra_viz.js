/**
 * Infrastructure Visualization Utility
 * Shared module for rendering SVG device diagrams with RJ45-style ports
 * Used by both Zone Manager modal and Zone Details page
 */

const InfraViz = (function () {

    /**
     * Generate a consistent color based on VLAN ID
     */
    function vlanIdToColor(vlanId) {
        if (!vlanId) return '#6B7280'; // grey for untagged
        const hue = (parseInt(vlanId) * 137.508) % 360; // Golden angle
        return `hsl(${hue}, 70%, 50%)`;
    }

    /**
     * Render an SVG device diagram with RJ45-style ports
     * Design: 8 pins inside RJ45 represent VLANs (color-coded)
     * 2 LEDs at bottom: Left = Link status, Right = PoE status
     * 
     * @param {HTMLElement} container - DOM element to render SVG into
     * @param {Object} data - Port data with { ports: [], bridges: [] }
     * @param {string} deviceType - 'router' or 'switch'
     */
    function renderDeviceSVG(container, data, deviceType = 'router') {
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
        const svgHeight = (portHeight + portGap) * rows + padding * 2;

        // Generate unique ID for this SVG
        const svgId = `svg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

        let svgContent = `
            <svg id="${svgId}" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${svgWidth} ${svgHeight}" 
                 class="w-full" style="background: var(--background); border-radius: 8px;">
                
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

            // Disabled/down styling
            const isActive = port.running && !port.disabled;
            const portFill = port.disabled ? '#1F2937' : '#374151';
            const portStroke = port.disabled ? '#374151' : (isActive ? '#6B7280' : '#4B5563');

            // VLAN pins (8 pins, color-coded by VLAN if assigned)
            const portVlans = port.vlans || [];
            const pinColors = [];
            for (let i = 0; i < 8; i++) {
                if (i < portVlans.length) {
                    pinColors.push(vlanIdToColor(portVlans[i].id));
                } else {
                    // Default pin color (metallic/copper look)
                    pinColors.push(isActive ? '#D4AF37' : '#6B7280');
                }
            }

            // LED colors
            const linkLedColor = isActive ? '#10B981' : '#6B7280';
            // PoE states: 'powered-on', 'auto-on', 'forced-on' are active; 'off', 'waiting-for-load' are not
            const isPoeActive = port.poe && ['powered-on', 'auto-on', 'forced-on'].includes(port.poe);
            const isPoeConfigured = port.poe && port.poe !== 'off' && port.poe !== null;
            // Yellow = active, Orange = configured but not powering, Gray = off/none
            const poeLedColor = isPoeActive ? '#F59E0B' : (isPoeConfigured ? '#F97316' : '#374151');

            svgContent += `
                <g class="port-group" data-port="${port.name}" data-port-index="${index}" style="cursor: pointer;">
                    <!-- RJ45 Port Housing -->
                    <g transform="translate(${x}, ${y})">
                        <!-- Outer frame (rounded rectangle like reference) -->
                        <rect x="0" y="0" width="${portWidth}" height="38" rx="4" 
                              fill="${portFill}" stroke="${portStroke}" stroke-width="1.5"/>
                        
                        <!-- Inner slot (where pins are) -->
                        <rect x="4" y="4" width="${portWidth - 8}" height="22" rx="2" 
                              fill="#1a1a1a" stroke="#2a2a2a" stroke-width="0.5"/>
                        
                        <!-- 8 Connector Pins (VLAN colored) -->
                        ${pinColors.map((color, i) => `
                            <rect x="${6 + i * 4.5}" y="6" width="3" height="16" rx="0.5" 
                                  fill="${color}" opacity="${isActive ? 1 : 0.5}"/>
                        `).join('')}
                        
                        <!-- Clip/latch at bottom of socket -->
                        <path d="M${portWidth / 2 - 8},26 L${portWidth / 2 - 4},30 L${portWidth / 2 + 4},30 L${portWidth / 2 + 8},26" 
                              fill="none" stroke="${portStroke}" stroke-width="1"/>
                        
                        <!-- Two LEDs at bottom corners -->
                        <circle cx="8" cy="33" r="3" fill="${linkLedColor}"/>
                        <circle cx="${portWidth - 8}" cy="33" r="3" fill="${poeLedColor}"/>
                    </g>
                    
                    <!-- Port name below -->
                    <text x="${x + portWidth / 2}" y="${y + 48}" 
                          text-anchor="middle" font-size="8" fill="var(--text-secondary)" font-weight="500">
                        ${port.name.replace('ether', 'e').replace('sfp-sfpplus', 'sfp+')}
                    </text>
                </g>
            `;
        });

        svgContent += '</svg>';

        // Store port data for tooltip
        container._portData = ports;

        // Tooltip popup element - unique per container
        const tooltipId = `port-tooltip-${svgId}`;
        const tooltipHtml = `
            <div id="${tooltipId}" class="fixed z-50 hidden bg-surface-1 border border-border-color rounded-lg shadow-xl p-3 min-w-52 max-w-72 text-sm pointer-events-none">
                <div class="font-semibold text-base mb-2" id="${tooltipId}-name">ether1</div>
                <div class="space-y-1 text-text-secondary" id="${tooltipId}-content"></div>
            </div>
        `;

        container.innerHTML = svgContent + tooltipHtml;

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

                    // Show power details if available
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
                                        <span class="inline-block w-2 h-2 rounded-sm flex-shrink-0" style="background: ${vlanIdToColor(v.id)}"></span>
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
                const tooltipWidth = 288; // max-w-72 = 18rem = 288px

                // Try right side first, if not enough space use left
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

    /**
     * Parse layout code like "1-f", "2-h1", "3-q2"
     * Returns { row, width, slot } or null if invalid
     */
    function parseLayoutCode(code) {
        if (!code || typeof code !== 'string') return null;
        const match = code.match(/^(\d+)-([fhq])(\d)?$/i);
        if (!match) return null;

        const row = parseInt(match[1], 10);
        const sizeCode = match[2].toLowerCase();
        const slot = match[3] ? parseInt(match[3], 10) : 1;

        let width;
        switch (sizeCode) {
            case 'f': width = 100; break;
            case 'h': width = 50; break;
            case 'q': width = 25; break;
            default: return null;
        }

        return { row, width, slot, sizeCode };
    }

    /**
     * Render a Virtual Rack layout with devices positioned according to layoutMap
     * @param {HTMLElement} container - DOM element to render rack into
     * @param {Array} devices - Array of device objects with { host, hostname, device_type, ... }
     * @param {Object} layoutMap - Map of host -> layout code (e.g., { "192.168.1.1": "1-f" })
     * @param {Function} onRenderDevice - Callback(containerDiv, device) to render device SVG
     */
    function renderRack(container, devices, layoutMap, onRenderDevice) {
        if (!devices || devices.length === 0) {
            container.innerHTML = '<p class="text-text-secondary text-sm italic">No devices to display</p>';
            return;
        }

        layoutMap = layoutMap || {};

        // Group devices by row
        const rowsMap = new Map();
        const unassigned = [];

        devices.forEach(device => {
            const code = layoutMap[device.host];
            const parsed = parseLayoutCode(code);
            if (parsed) {
                if (!rowsMap.has(parsed.row)) {
                    rowsMap.set(parsed.row, []);
                }
                rowsMap.get(parsed.row).push({ device, ...parsed });
            } else {
                unassigned.push(device);
            }
        });

        // Sort rows by row number
        const sortedRows = Array.from(rowsMap.keys()).sort((a, b) => a - b);

        // If all devices are unassigned, auto-assign them to sequential full-width rows
        if (sortedRows.length === 0 && unassigned.length > 0) {
            unassigned.forEach((device, index) => {
                rowsMap.set(index + 1, [{ device, row: index + 1, width: 100, slot: 1, sizeCode: 'f' }]);
                sortedRows.push(index + 1);
            });
            unassigned.length = 0; // Clear unassigned
        }

        // Build rack HTML - using CSS Grid with 4 columns for proper slot positioning
        let html = '<div class="virtual-rack">';

        sortedRows.forEach(rowNum => {
            const rowDevices = rowsMap.get(rowNum);
            // Sort by slot within row
            rowDevices.sort((a, b) => a.slot - b.slot);

            // Use grid with 4 columns to support quarter-width positioning
            html += `<div class="rack-row grid grid-cols-4 gap-4 mb-4" data-row="${rowNum}">`;
            rowDevices.forEach(item => {
                // Calculate grid column span and start position
                let colSpan, colStart;
                switch (item.sizeCode) {
                    case 'f': // Full width = span all 4 columns
                        colSpan = 4;
                        colStart = 1;
                        break;
                    case 'h': // Half width = span 2 columns
                        colSpan = 2;
                        colStart = item.slot === 1 ? 1 : 3;
                        break;
                    case 'q': // Quarter width = span 1 column
                        colSpan = 1;
                        colStart = item.slot;
                        break;
                    default:
                        colSpan = 4;
                        colStart = 1;
                }

                const gridStyle = `grid-column: ${colStart} / span ${colSpan};`;
                html += `
                    <div class="rack-slot bg-surface-2 rounded-lg border border-border-color overflow-hidden" 
                         style="${gridStyle}" data-host="${item.device.host}">
                        <div class="p-3 border-b border-border-color flex justify-between items-center bg-surface-1/50">
                            <div class="flex items-center gap-2">
                                <span class="material-symbols-outlined text-xl text-text-secondary">${item.device.device_type === 'switch' ? 'switch' : 'router'}</span>
                                <div>
                                    <h5 class="font-semibold text-sm text-white">${item.device.hostname || item.device.host}</h5>
                                    <p class="text-xs text-text-secondary">${item.device.host}</p>
                                </div>
                            </div>
                            <span class="text-xs text-text-secondary/50">${item.row}-${item.sizeCode}${item.width !== 100 ? item.slot : ''}</span>
                        </div>
                        <div class="rack-device-content p-3" id="rack-device-${item.device.host.replace(/\./g, '-')}">
                            <p class="text-text-secondary text-sm">Loading...</p>
                        </div>
                    </div>
                `;
            });
            html += '</div>';
        });

        // Render unassigned devices in a separate section
        if (unassigned.length > 0) {
            html += `
                <div class="unassigned-devices mt-6 pt-4 border-t border-border-color/50">
                    <p class="text-text-secondary text-xs mb-3 uppercase tracking-wide">Unassigned Devices</p>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            `;
            unassigned.forEach(device => {
                html += `
                    <div class="rack-slot bg-surface-2/50 rounded-lg border border-border-color/50 overflow-hidden" data-host="${device.host}">
                        <div class="p-3 border-b border-border-color/50 flex items-center gap-2">
                            <span class="material-symbols-outlined text-xl text-text-secondary">${device.device_type === 'switch' ? 'switch' : 'router'}</span>
                            <div>
                                <h5 class="font-semibold text-sm text-white">${device.hostname || device.host}</h5>
                                <p class="text-xs text-text-secondary">${device.host}</p>
                            </div>
                        </div>
                        <div class="rack-device-content p-3" id="rack-device-${device.host.replace(/\./g, '-')}">
                            <p class="text-text-secondary text-sm">Loading...</p>
                        </div>
                    </div>
                `;
            });
            html += '</div></div>';
        }

        html += '</div>';
        container.innerHTML = html;

        // Trigger onRenderDevice callback for each device
        if (typeof onRenderDevice === 'function') {
            devices.forEach(device => {
                const deviceContainer = document.getElementById(`rack-device-${device.host.replace(/\./g, '-')}`);
                if (deviceContainer) {
                    onRenderDevice(deviceContainer, device);
                }
            });
        }
    }

    // Public API
    return {
        vlanIdToColor: vlanIdToColor,
        renderDeviceSVG: renderDeviceSVG,
        renderRack: renderRack,
        parseLayoutCode: parseLayoutCode
    };

})();

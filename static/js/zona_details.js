document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = window.location.origin;
    const zonaId = window.location.pathname.split('/').pop();
    let zonaData = null;

    // --- Element Cache ---
    const mainZoneName = document.getElementById('main-zonaname');
    const noteModal = document.getElementById('note-modal');
    const noteModalTitle = document.getElementById('note-modal-title');
    const noteForm = document.getElementById('note-form');
    const noteIdInput = document.getElementById('note-id');
    const noteTitleInput = document.getElementById('note-title');
    const noteEditor = document.getElementById('note-editor');
    const notePreview = document.getElementById('note-preview');
    const noteIsEncryptedInput = document.getElementById('note-is-encrypted');
    const notesListContainer = document.getElementById('notes-list');

    // Infrastructure elements
    const routerDiagramsContainer = document.getElementById('router-diagrams');
    const infraStatusEl = document.getElementById('infra-status');
    const refreshInfraBtn = document.getElementById('refresh-infra-btn');

    // --- Tab Switching Logic ---
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabPanels = document.querySelectorAll('.tab-panel');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            tabButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            const tabName = button.getAttribute('data-tab');
            tabPanels.forEach(panel => {
                if (panel.id === `tab-${tabName}`) {
                    panel.classList.add('active');
                } else {
                    panel.classList.remove('active');
                }
            });
            // Load infrastructure when tab is clicked
            if (tabName === 'infra') {
                loadInfrastructure();
            }
        });
    });

    // --- Data Loading & Rendering ---
    async function loadAllDetails() {
        try {
            const response = await fetch(`${API_BASE_URL}/api/zonas/${zonaId}/details`);
            if (!response.ok) throw new Error('Zone not found');
            zonaData = await response.json();

            renderGeneralInfo();
            renderDocuments();
            renderNotes();
        } catch (error) {
            mainZoneName.textContent = 'Error';
            showToast(`Failed to load zone details: ${error.message}`, 'danger');
        }
    }

    function renderGeneralInfo() {
        if (!zonaData) return;
        mainZoneName.textContent = zonaData.nombre;
        document.getElementById('zona-nombre').value = zonaData.nombre;
        document.getElementById('zona-coordenadas').value = zonaData.coordenadas_gps || '';
        document.getElementById('zona-direccion').value = zonaData.direccion || '';
    }

    // =========================================================================
    // --- INFRASTRUCTURE VISUALIZATION ---
    // =========================================================================

    /**
     * Generate a consistent color based on VLAN ID
     */
    function vlanIdToColor(vlanId) {
        if (!vlanId) return '#6B7280'; // grey for untagged
        const hue = (parseInt(vlanId) * 137.508) % 360; // Golden angle
        return `hsl(${hue}, 70%, 50%)`;
    }

    /**
     * Load infrastructure data for this zone
     */
    async function loadInfrastructure() {
        if (!routerDiagramsContainer) return;

        infraStatusEl.textContent = 'Loading...';
        routerDiagramsContainer.innerHTML = '<p class="text-text-secondary">Fetching router data...</p>';

        try {
            // First, get the list of routers in this zone
            const routersResponse = await fetch(`${API_BASE_URL}/api/zonas/${zonaId}/infra/routers`);
            if (!routersResponse.ok) throw new Error('Failed to fetch routers');
            const routers = await routersResponse.json();

            if (routers.length === 0) {
                routerDiagramsContainer.innerHTML = `
                    <div class="text-center py-12">
                        <span class="material-symbols-outlined text-6xl text-text-secondary mb-4 block">router</span>
                        <p class="text-text-secondary">No routers linked to this zone.</p>
                        <p class="text-sm text-text-secondary mt-2">Assign routers to this zone from the Routers page.</p>
                    </div>
                `;
                infraStatusEl.textContent = 'No routers';
                return;
            }

            // Clear container and render each router
            routerDiagramsContainer.innerHTML = '';
            infraStatusEl.textContent = `${routers.length} router(s)`;

            for (const router of routers) {
                const routerCard = document.createElement('div');
                routerCard.className = 'bg-surface-2 rounded-lg border border-border-color overflow-hidden';
                routerCard.innerHTML = `
                    <div class="p-4 border-b border-border-color flex justify-between items-center">
                        <div>
                            <h4 class="font-semibold text-lg">${router.hostname || router.host}</h4>
                            <p class="text-sm text-text-secondary">${router.host} • ${router.model || 'Unknown model'}</p>
                        </div>
                        <span class="px-2 py-1 rounded text-xs font-medium ${router.last_status === 'online' ? 'bg-success/20 text-success' : 'bg-danger/20 text-danger'}">
                            ${router.last_status || 'unknown'}
                        </span>
                    </div>
                    <div class="p-4" id="router-svg-${router.host.replace(/\./g, '-')}">
                        <p class="text-text-secondary text-sm">Loading ports...</p>
                    </div>
                `;
                routerDiagramsContainer.appendChild(routerCard);

                // Fetch detailed port info for this router
                if (router.is_enabled && router.last_status === 'online') {
                    loadRouterPorts(router.host);
                } else {
                    const svgContainer = document.getElementById(`router-svg-${router.host.replace(/\./g, '-')}`);
                    svgContainer.innerHTML = `<p class="text-text-secondary text-sm italic">Router offline or disabled</p>`;
                }
            }

        } catch (error) {
            routerDiagramsContainer.innerHTML = `<p class="text-danger">Error: ${error.message}</p>`;
            infraStatusEl.textContent = 'Error';
        }
    }

    /**
     * Load port data for a single router and render SVG
     */
    async function loadRouterPorts(host) {
        const containerId = `router-svg-${host.replace(/\./g, '-')}`;
        const container = document.getElementById(containerId);
        if (!container) return;

        try {
            const response = await fetch(`${API_BASE_URL}/api/zonas/infra/router/${host}/ports`);
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to load');
            }
            const data = await response.json();
            renderRouterSVG(container, data);
        } catch (error) {
            container.innerHTML = `<p class="text-danger text-sm">Error: ${error.message}</p>`;
        }
    }

    /**
     * Render an SVG router diagram with RJ45-style ports
     * Design: 8 pins inside RJ45 represent VLANs (color-coded)
     * 2 LEDs at bottom: Left = Link status, Right = PoE status
     */
    function renderRouterSVG(container, data) {
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

        let svgContent = `
            <svg id="${svgId}" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${svgWidth} ${svgHeight}" 
                 class="w-full max-w-4xl" style="background: var(--background); border-radius: 8px;">
                
                <!-- Router chassis -->
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

        // Legend
        const legendY = svgHeight - 20;
        svgContent += `
            <g class="legend" font-size="7" fill="var(--text-secondary)">
                <!-- Link LED -->
                <circle cx="${padding + 5}" cy="${legendY}" r="3" fill="#10B981"/>
                <text x="${padding + 12}" y="${legendY + 3}">Link</text>
                
                <!-- PoE Active LED -->
                <circle cx="${padding + 42}" cy="${legendY}" r="3" fill="#F59E0B"/>
                <text x="${padding + 49}" y="${legendY + 3}">PoE Active</text>
                
                <!-- PoE Configured LED -->
                <circle cx="${padding + 100}" cy="${legendY}" r="3" fill="#F97316"/>
                <text x="${padding + 107}" y="${legendY + 3}">PoE Waiting</text>
                
                <!-- Down indicator -->
                <circle cx="${padding + 170}" cy="${legendY}" r="3" fill="#6B7280"/>
                <text x="${padding + 177}" y="${legendY + 3}">Down/Off</text>
                
                <!-- VLAN info -->
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
        const tooltipHtml = `
            <div id="port-tooltip" class="fixed z-50 hidden bg-surface-1 border border-border-color rounded-lg shadow-xl p-3 min-w-52 max-w-72 text-sm pointer-events-none">
                <div class="font-semibold text-base mb-2" id="tooltip-port-name">ether1</div>
                <div class="space-y-1 text-text-secondary" id="tooltip-content"></div>
            </div>
        `;

        container.innerHTML = svgContent + bridgeSummary + tooltipHtml;

        // Add hover event listeners
        const svg = container.querySelector('svg');
        const tooltip = container.querySelector('#port-tooltip');
        const tooltipName = container.querySelector('#tooltip-port-name');
        const tooltipContent = container.querySelector('#tooltip-content');

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

    // Refresh button handler
    if (refreshInfraBtn) {
        refreshInfraBtn.addEventListener('click', loadInfrastructure);
    }

    function renderDocuments() {
        const gallery = document.getElementById('document-gallery');
        gallery.innerHTML = '';
        if (!zonaData || zonaData.documentos.length === 0) {
            gallery.innerHTML = '<p class="text-text-secondary">No documents uploaded for this zone.</p>';
            return;
        }

        const grid = document.createElement('div');
        grid.className = 'grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4';

        zonaData.documentos.forEach(doc => {
            const isImage = doc.tipo === 'image';
            const fileUrl = `/uploads/zonas/${doc.zona_id}/${doc.nombre_guardado}`;

            const card = document.createElement('div');
            card.className = 'bg-surface-2 rounded-lg p-3 text-center space-y-2';
            card.innerHTML = `
                <div class="flex items-center justify-center h-24 bg-background rounded-md">
                    ${isImage ?
                    `<img src="${fileUrl}" alt="${doc.descripcion || 'Image'}" class="max-h-full max-w-full object-contain">` :
                    `<span class="material-symbols-outlined text-5xl text-text-secondary">description</span>`
                }
                </div>
                <p class="text-sm font-medium truncate" title="${doc.nombre_original}">${doc.nombre_original}</p>
                <div class="flex justify-center gap-2">
                    <a href="${fileUrl}" target="_blank" class="text-primary hover:underline text-xs">View</a>
                    <a href="${fileUrl}" download="${doc.nombre_original}" class="text-primary hover:underline text-xs">Download</a>
                    <button data-doc-id="${doc.id}" class="delete-doc-btn text-danger hover:underline text-xs">Delete</button>
                </div>
            `;
            grid.appendChild(card);
        });
        gallery.appendChild(grid);
    }

    function renderNotes() {
        if (!zonaData || !zonaData.notes) return;
        notesListContainer.innerHTML = '';

        if (zonaData.notes.length === 0) {
            notesListContainer.innerHTML = '<p class="text-text-secondary">No notes for this zone yet.</p>';
            return;
        }

        zonaData.notes.forEach(note => {
            const card = document.createElement('div');
            card.className = 'bg-surface-1 rounded-lg border border-border-color p-4 flex justify-between items-start';

            const contentPreview = note.is_encrypted
                ? '<p class="text-text-secondary italic">This note is encrypted.</p>'
                : marked.parse(note.content.substring(0, 200) + (note.content.length > 200 ? '...' : ''));

            card.innerHTML = `
                <div class="prose prose-invert max-w-none">
                    <h4 class="font-bold text-lg mb-2 flex items-center gap-2">
                        ${note.is_encrypted ? '<span class="material-symbols-outlined text-base">lock</span>' : ''}
                        ${note.title}
                    </h4>
                    <div class="text-sm text-text-secondary">${contentPreview}</div>
                </div>
                <div class="flex-shrink-0 ml-4">
                    <button data-note-id="${note.id}" class="edit-note-btn text-primary hover:underline text-sm">Edit</button>
                    <button data-note-id="${note.id}" class="delete-note-btn text-danger hover:underline text-sm ml-2">Delete</button>
                </div>
            `;
            notesListContainer.appendChild(card);
        });
    }

    // --- Modal Logic ---
    function openNoteModal(note = null) {
        noteForm.reset();
        if (note) {
            noteModalTitle.textContent = 'Edit Note';
            noteIdInput.value = note.id;
            noteTitleInput.value = note.title;
            noteEditor.value = note.content;
            noteIsEncryptedInput.checked = note.is_encrypted;
        } else {
            noteModalTitle.textContent = 'New Note';
            noteIdInput.value = '';
        }
        notePreview.innerHTML = marked.parse(noteEditor.value);
        noteModal.classList.remove('hidden');
        noteModal.classList.add('flex');
    }

    function closeNoteModal() {
        noteModal.classList.add('hidden');
        noteModal.classList.remove('flex');
    }

    // --- Event Listeners ---
    document.getElementById('new-note-btn').addEventListener('click', () => openNoteModal());
    document.getElementById('cancel-note-btn').addEventListener('click', closeNoteModal);
    document.getElementById('close-note-modal-btn').addEventListener('click', closeNoteModal);

    noteEditor.addEventListener('input', () => {
        notePreview.innerHTML = marked.parse(noteEditor.value);
    });

    notesListContainer.addEventListener('click', (e) => {
        if (e.target.classList.contains('edit-note-btn')) {
            const noteId = parseInt(e.target.getAttribute('data-note-id'));
            const noteToEdit = zonaData.notes.find(n => n.id === noteId);
            openNoteModal(noteToEdit);
        }
        if (e.target.classList.contains('delete-note-btn')) {
            const noteId = parseInt(e.target.getAttribute('data-note-id'));
            if (confirm('Are you sure you want to delete this note?')) {
                deleteNote(noteId);
            }
        }
    });

    // --- Form Submissions & API Calls ---
    noteForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const noteId = noteIdInput.value;
        const data = {
            title: noteTitleInput.value,
            content: noteEditor.value,
            is_encrypted: noteIsEncryptedInput.checked,
        };

        const url = noteId
            ? `${API_BASE_URL}/api/zonas/notes/${noteId}`
            : `${API_BASE_URL}/api/zonas/${zonaId}/notes`;
        const method = noteId ? 'PUT' : 'POST';

        try {
            const response = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            });
            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Failed to save note');
            }

            closeNoteModal();
            await loadAllDetails(); // Reload all data to get the updated notes list
            showToast('Note saved successfully!', 'success');

        } catch (error) {
            showToast(`Error saving note: ${error.message}`, 'danger');
        }
    });

    async function deleteNote(noteId) {
        try {
            const response = await fetch(`${API_BASE_URL}/api/zonas/notes/${noteId}`, {
                method: 'DELETE',
            });
            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Failed to delete note');
            }
            await loadAllDetails();
            showToast('Note deleted successfully!', 'success');
        } catch (error) {
            showToast(`Error deleting note: ${error.message}`, 'danger');
        }
    }

    document.getElementById('form-general').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const data = Object.fromEntries(formData.entries());

        try {
            await fetch(`${API_BASE_URL}/api/zonas/${zonaId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            showToast('General info saved!', 'success');
            loadAllDetails();
        } catch (error) {
            showToast(`Error saving: ${error.message}`, 'danger');
        }
    });

    document.getElementById('form-docs').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);

        try {
            const response = await fetch(`${API_BASE_URL}/api/zonas/${zonaId}/documentos`, {
                method: 'POST',
                body: formData
            });
            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Failed to upload');
            }
            e.target.reset();
            showToast('File uploaded successfully!', 'success');
            loadAllDetails();
        } catch (error) {
            showToast(`Error uploading file: ${error.message}`, 'danger');
        }
    });

    // --- Event Delegation for Delete Buttons ---
    document.getElementById('document-gallery').addEventListener('click', async (e) => {
        if (e.target.classList.contains('delete-doc-btn')) {
            const docId = e.target.getAttribute('data-doc-id');
            if (confirm('Are you sure you want to delete this document?')) {
                try {
                    await fetch(`${API_BASE_URL}/api/documentos/${docId}`, { method: 'DELETE' });
                    showToast('Document deleted.', 'success');
                    loadAllDetails();
                } catch (error) {
                    showToast(`Error deleting document: ${error.message}`, 'danger');
                }
            }
        }
    });

    // Initial Load
    loadAllDetails();
});
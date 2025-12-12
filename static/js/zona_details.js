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
     */
    function renderRouterSVG(container, data) {
        const ports = data.ports || [];
        if (ports.length === 0) {
            container.innerHTML = '<p class="text-text-secondary text-sm italic">No physical ports found</p>';
            return;
        }

        // Calculate dimensions
        const portWidth = 44;
        const portHeight = 56; // Taller to fit VLAN LEDs
        const portGap = 10;
        const padding = 20;
        const portsPerRow = Math.min(ports.length, 12);
        const rows = Math.ceil(ports.length / portsPerRow);

        const svgWidth = (portWidth + portGap) * portsPerRow + padding * 2 - portGap;
        const svgHeight = (portHeight + portGap) * rows + padding * 2 + 50;

        // Generate unique ID for this SVG (for tooltip)
        const svgId = `svg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

        let svgContent = `
            <svg id="${svgId}" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${svgWidth} ${svgHeight}" 
                 class="w-full max-w-4xl" style="background: var(--background); border-radius: 8px;">
                
                <!-- Defs for RJ45 shape -->
                <defs>
                    <clipPath id="rj45-clip">
                        <path d="M4,0 L36,0 L40,4 L40,28 L0,28 L0,4 Z"/>
                    </clipPath>
                </defs>
                
                <!-- Router chassis -->
                <rect x="0" y="0" width="${svgWidth}" height="${svgHeight - 40}" rx="8" 
                      fill="var(--surface-1)" stroke="var(--border-color)" stroke-width="1"/>
        `;

        // Speed to color mapping
        function getSpeedColor(rate) {
            if (!rate) return { fill: '#374151', stroke: '#6B7280', label: '?' }; // Unknown - grey
            const speed = rate.toLowerCase();
            if (speed.includes('10g') || speed.includes('10000')) {
                return { fill: '#3B82F6', stroke: '#60A5FA', label: '10G' }; // Blue - 10Gbps+
            } else if (speed.includes('1g') || speed.includes('1000')) {
                return { fill: '#10B981', stroke: '#34D399', label: '1G' }; // Green - 1Gbps
            } else if (speed.includes('100m') || speed.includes('100')) {
                return { fill: '#F59E0B', stroke: '#FBBF24', label: '100M' }; // Yellow - 100Mbps
            } else if (speed.includes('10m') || speed.includes('10')) {
                return { fill: '#EF4444', stroke: '#F87171', label: '10M' }; // Red - 10Mbps
            }
            return { fill: '#374151', stroke: '#6B7280', label: '?' }; // Unknown
        }

        // Render ports
        ports.forEach((port, index) => {
            const row = Math.floor(index / portsPerRow);
            const col = index % portsPerRow;
            const x = padding + col * (portWidth + portGap);
            const y = padding + row * (portHeight + portGap);

            // Get speed color
            const speedInfo = getSpeedColor(port.rate || port.speed);

            // Override colors for disabled/down ports
            let fillColor = speedInfo.fill;
            let strokeColor = speedInfo.stroke;

            if (port.disabled) {
                fillColor = '#1F2937';
                strokeColor = '#374151';
            } else if (!port.running) {
                fillColor = '#292524';
                strokeColor = '#44403C';
            }

            // RJ45 silhouette shape
            const rj45Height = 28;
            const rj45Y = y + 8;

            // VLAN LEDs - max 4 top, 4 bottom
            const portVlans = port.vlans || [];
            const topLeds = portVlans.slice(0, 4);
            const bottomLeds = portVlans.slice(4, 8);
            const extraVlans = portVlans.length > 8 ? portVlans.length - 8 : 0;

            // Status indicator (link up/down)
            const statusColor = port.running && !port.disabled ? '#10B981' : '#6B7280';

            svgContent += `
                <g class="port-group" data-port="${port.name}" data-port-index="${index}" style="cursor: pointer;">
                    <!-- Top VLAN LEDs -->
                    <g class="vlan-leds-top">
                        ${topLeds.map((v, i) => `
                            <circle cx="${x + 6 + i * 10}" cy="${y + 3}" r="3" fill="${vlanIdToColor(v.id)}"/>
                        `).join('')}
                        ${extraVlans > 0 ? `<text x="${x + portWidth - 4}" y="${y + 6}" font-size="6" fill="var(--text-secondary)" text-anchor="end">+${extraVlans}</text>` : ''}
                    </g>
                    
                    <!-- RJ45 Port Shape -->
                    <g transform="translate(${x + 2}, ${rj45Y})">
                        <!-- Outer housing -->
                        <path d="M0,4 L0,26 L40,26 L40,4 L36,0 L4,0 Z" 
                              fill="${fillColor}" stroke="${strokeColor}" stroke-width="1.5"/>
                        <!-- Inner connector area -->
                        <rect x="4" y="4" width="32" height="14" rx="1" fill="rgba(0,0,0,0.3)"/>
                        <!-- Connector pins -->
                        <g fill="rgba(255,255,255,0.4)">
                            <rect x="7" y="6" width="2" height="8"/>
                            <rect x="11" y="6" width="2" height="8"/>
                            <rect x="15" y="6" width="2" height="8"/>
                            <rect x="19" y="6" width="2" height="8"/>
                            <rect x="23" y="6" width="2" height="8"/>
                            <rect x="27" y="6" width="2" height="8"/>
                            <rect x="31" y="6" width="2" height="8"/>
                            <rect x="35" y="6" width="2" height="3"/>
                        </g>
                        <!-- Link status LED -->
                        <circle cx="36" cy="22" r="2.5" fill="${statusColor}"/>
                    </g>
                    
                    <!-- Bottom VLAN LEDs -->
                    <g class="vlan-leds-bottom">
                        ${bottomLeds.map((v, i) => `
                            <circle cx="${x + 6 + i * 10}" cy="${y + rj45Height + 14}" r="3" fill="${vlanIdToColor(v.id)}"/>
                        `).join('')}
                    </g>
                    
                    <!-- Port name -->
                    <text x="${x + portWidth / 2 + 1}" y="${y + portHeight - 2}" 
                          text-anchor="middle" font-size="8" fill="var(--text-secondary)" font-weight="500">
                        ${port.name.replace('ether', 'e').replace('sfp-sfpplus', 'sfp+')}
                    </text>
                </g>
            `;
        });

        // Legend
        const legendY = svgHeight - 32;
        svgContent += `
            <g class="legend" font-size="8" fill="var(--text-secondary)">
                <!-- Speed Legend -->
                <text x="${padding}" y="${legendY}" font-weight="600">Speed:</text>
                <rect x="${padding + 35}" y="${legendY - 9}" width="10" height="10" rx="2" fill="#EF4444"/>
                <text x="${padding + 48}" y="${legendY}">10M</text>
                <rect x="${padding + 70}" y="${legendY - 9}" width="10" height="10" rx="2" fill="#F59E0B"/>
                <text x="${padding + 83}" y="${legendY}">100M</text>
                <rect x="${padding + 112}" y="${legendY - 9}" width="10" height="10" rx="2" fill="#10B981"/>
                <text x="${padding + 125}" y="${legendY}">1G</text>
                <rect x="${padding + 142}" y="${legendY - 9}" width="10" height="10" rx="2" fill="#3B82F6"/>
                <text x="${padding + 155}" y="${legendY}">10G+</text>
                
                <!-- Status Legend -->
                <text x="${padding + 200}" y="${legendY}" font-weight="600">Status:</text>
                <circle cx="${padding + 240}" cy="${legendY - 4}" r="4" fill="#10B981"/>
                <text x="${padding + 248}" y="${legendY}">Link Up</text>
                <circle cx="${padding + 290}" cy="${legendY - 4}" r="4" fill="#6B7280"/>
                <text x="${padding + 298}" y="${legendY}">Down</text>
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
            <div id="port-tooltip" class="fixed z-50 hidden bg-surface-1 border border-border-color rounded-lg shadow-xl p-3 min-w-48 max-w-64 text-sm pointer-events-none">
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

                // Build tooltip content
                const speedInfo = getSpeedColor(port.rate || port.speed);
                let html = `
                    <div class="flex items-center gap-2">
                        <span class="inline-block w-2 h-2 rounded-full" style="background: ${port.running && !port.disabled ? '#10B981' : '#6B7280'}"></span>
                        <span>${port.running && !port.disabled ? 'Link Up' : (port.disabled ? 'Disabled' : 'Link Down')}</span>
                    </div>
                `;

                if (port.rate || port.speed) {
                    html += `<div>Speed: ${port.rate || port.speed}</div>`;
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
                            <div class="font-medium mb-1">VLANs (${portVlans.length}):</div>
                            <div class="flex flex-wrap gap-1">
                                ${portVlans.map(v => `
                                    <span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs" style="background: ${vlanIdToColor(v.id)}20; color: ${vlanIdToColor(v.id)}">
                                        <span class="w-2 h-2 rounded-full" style="background: ${vlanIdToColor(v.id)}"></span>
                                        ${v.id}${v.name ? ' - ' + v.name : ''}
                                    </span>
                                `).join('')}
                            </div>
                        </div>
                    `;
                }

                tooltipName.textContent = port.name;
                tooltipContent.innerHTML = html;

                // Position tooltip
                const rect = group.getBoundingClientRect();
                tooltip.style.left = `${rect.right + 10}px`;
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
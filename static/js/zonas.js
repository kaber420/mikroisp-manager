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

        // --- Rack Layout State ---
        isEditingLayout: false,
        isSavingLayout: false,
        rackLayout: {},           // Current saved layout from API
        editingRackLayout: {},    // Temp layout being edited

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
            this.isEditingLayout = false;
            this.rackLayout = {};
            this.editingRackLayout = {};

            try {
                const response = await fetch(`${this.API_BASE_URL}/api/zonas/${zone.id}/details`);
                if (!response.ok) throw new Error('Failed to load zone details');
                const data = await response.json();

                this.selectedZoneDetails = {
                    id: zone.id,
                    nombre: data.nombre || zone.nombre,
                    notes: data.notes || []
                };

                // Load rack layout from API
                this.rackLayout = data.rack_layout || {};
                this.editingRackLayout = { ...this.rackLayout };

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
                this.isEditingLayout = false;
                this.rackLayout = {};
                this.editingRackLayout = {};
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

                // After a short delay to allow DOM to render, render the rack
                setTimeout(() => {
                    this.renderRackView();
                }, 100);

            } catch (error) {
                console.error('Error loading infrastructure:', error);
                showToast(`Error loading infrastructure: ${error.message}`, 'danger');
                this.infraStatusText = 'Error loading';
            } finally {
                this.isLoadingInfra = false;
            }
        },

        /**
         * Render the virtual rack using InfraViz
         */
        renderRackView() {
            const container = document.getElementById('virtual-rack-container');
            if (!container) return;

            // Use renderRack with callback to load device ports
            InfraViz.renderRack(
                container,
                this.infraDevices,
                this.rackLayout,
                (deviceContainer, device) => {
                    if (device.is_enabled && device.last_status === 'online') {
                        this.loadDevicePortsIntoContainer(deviceContainer, device.host, device.device_type);
                    } else {
                        deviceContainer.innerHTML = '<p class="text-text-secondary text-sm">Device offline or disabled</p>';
                    }
                }
            );
        },

        /**
         * Load device ports into a specific container
         */
        async loadDevicePortsIntoContainer(container, host, deviceType = 'router') {
            try {
                const endpoint = deviceType === 'switch'
                    ? `${this.API_BASE_URL}/api/zonas/infra/switch/${host}/ports`
                    : `${this.API_BASE_URL}/api/zonas/infra/router/${host}/ports`;

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
        },

        /**
         * Save rack layout to API
         */
        async saveRackLayout() {
            const zonaId = this.selectedZoneDetails.id;
            if (!zonaId) return;

            this.isSavingLayout = true;
            try {
                // Clean up empty values
                const cleanLayout = {};
                Object.entries(this.editingRackLayout).forEach(([host, code]) => {
                    if (code && code.trim()) {
                        cleanLayout[host] = code.trim().toLowerCase();
                    }
                });

                const response = await fetch(`${this.API_BASE_URL}/api/zonas/${zonaId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ rack_layout: cleanLayout })
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Failed to save layout');
                }

                this.rackLayout = { ...cleanLayout };
                this.isEditingLayout = false;
                showToast('Layout saved successfully', 'success');

                // Re-render rack with new layout
                this.renderRackView();

            } catch (error) {
                console.error('Error saving rack layout:', error);
                showToast(`Error saving layout: ${error.message}`, 'danger');
            } finally {
                this.isSavingLayout = false;
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
         * Render an SVG device diagram using shared utility
         */
        renderDeviceSVG(container, data, deviceType = 'router') {
            InfraViz.renderDeviceSVG(container, data, deviceType);
        }
    }));
});
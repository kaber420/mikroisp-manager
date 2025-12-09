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
                    alert(`Error: ${err.message}`);
                }
            }
        }
    }));
});
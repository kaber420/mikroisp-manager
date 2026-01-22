// static/js/aps.js

document.addEventListener('alpine:init', () => {
    Alpine.data('apManager', () => ({
        // Spread the shared provisioning mixin
        ...window.provisionMixin,

        // State
        aps: [],
        allZones: [],
        isLoading: true,
        isModalOpen: false,

        // Test Connection State
        isTesting: false,
        testMessage: '',
        testStatus: '',

        // Edit State
        isEditing: false,
        originalHost: null, // Para guardar la IP original en caso de edición (ID)

        currentAp: {
            host: '',
            zona_id: '',
            username: 'ubnt',
            password: '',
            monitor_interval: '',
            vendor: 'ubiquiti',
            api_port: ''
        },
        error: '',
        searchQuery: '',
        selectedZone: '',


        // Computed properties
        get filteredAps() {
            return this.aps.filter(ap => {
                const searchMatch = !this.searchQuery ||
                    (ap.hostname && ap.hostname.toLowerCase().includes(this.searchQuery.toLowerCase())) ||
                    (ap.host && ap.host.toLowerCase().includes(this.searchQuery.toLowerCase())) ||
                    (ap.mac && ap.mac.toLowerCase().includes(this.searchQuery.toLowerCase()));

                const zoneMatch = !this.selectedZone || ap.zona_id === parseInt(this.selectedZone);
                return searchMatch && zoneMatch;
            });
        },

        // Methods
        async init() {
            this.isLoading = true;
            await this.loadInitialData();
            this.isLoading = false;

            // ELIMINADO: this.startAutoRefresh(); 

            // NUEVO: Escucha Reactiva Global
            window.addEventListener('data-refresh-needed', () => {
                // Solo recargamos si el usuario NO está interactuando con un modal
                if (!this.isModalOpen && !this.isTesting) {
                    console.log("⚡ APs: Recargando lista por actualización en vivo.");
                    this.loadInitialData();
                } else {
                    console.log("⏳ APs: Actualización pausada (Usuario editando).");
                }
            });
        },

        async loadInitialData() {
            try {
                const [apsResponse, zonesResponse] = await Promise.all([
                    fetch('/api/aps'),
                    fetch('/api/zonas')
                ]);

                if (!apsResponse.ok) throw new Error('Failed to load APs.');
                if (!zonesResponse.ok) throw new Error('Failed to load zones.');

                this.aps = await apsResponse.json();
                this.allZones = await zonesResponse.json();

            } catch (error) {
                console.error('Error loading initial data:', error);
                this.error = error.message;
            }
        },

        async loadZonesForModal() {
            if (this.allZones.length === 0) {
                try {
                    const response = await fetch('/api/zonas');
                    if (!response.ok) throw new Error('Failed to load zones for modal.');
                    this.allZones = await response.json();
                } catch (error) {
                    console.error(error);
                    this.error = 'Could not load zones for the modal.';
                }
            }
        },

        resetModalState() {
            this.error = '';
            this.testMessage = '';
            this.testStatus = '';
            this.isTesting = false;
        },

        openModal(ap = null) {
            this.resetModalState();
            this.loadZonesForModal();

            if (ap) {
                // Lógica de EDICIÓN
                this.isEditing = true;
                this.originalHost = ap.host;
                // Copiamos los datos y limpiamos el password para no enviarlo si no se cambia
                this.currentAp = {
                    ...ap,
                    password: '' // Dejar en blanco para mantener la actual
                };
            } else {
                // Lógica de CREACIÓN
                this.isEditing = false;
                this.originalHost = null;
                this.currentAp = {
                    host: '',
                    zona_id: '',
                    username: 'ubnt',
                    password: '',
                    monitor_interval: '',
                    vendor: 'ubiquiti',
                    api_port: ''
                };
            }
            this.isModalOpen = true;
        },

        // Multi-vendor helper methods
        getDefaultPort() {
            return this.currentAp.vendor === 'mikrotik' ? '8729' : '443';
        },

        getPortHint() {
            if (this.currentAp.vendor === 'mikrotik') {
                return 'Default: 8729 (API-SSL). Requires API-SSL enabled on MikroTik.';
            }
            return 'Default: 443 (HTTPS). Standard AirOS port.';
        },

        onVendorChange() {
            // Clear api_port to use the new default when vendor changes
            // Only if creating a new AP or port wasn't manually set
            if (!this.isEditing) {
                this.currentAp.api_port = '';
                // Update default username for common vendors
                if (this.currentAp.vendor === 'mikrotik' && this.currentAp.username === 'ubnt') {
                    this.currentAp.username = 'admin';
                } else if (this.currentAp.vendor === 'ubiquiti' && this.currentAp.username === 'admin') {
                    this.currentAp.username = 'ubnt';
                }
            }
        },

        renderVendorBadge(vendor) {
            if (vendor === 'mikrotik') {
                return `<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-500/20 text-blue-400 border border-blue-500/30">MikroTik</span>`;
            }
            return `<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-500/20 text-green-400 border border-green-500/30">Ubiquiti</span>`;
        },

        async testConnection() {
            this.testMessage = '';
            this.testStatus = '';
            this.error = '';

            if (!this.currentAp.host || !this.currentAp.username || !this.currentAp.password) {
                this.testMessage = 'Host, Username, and Password are required for testing.';
                this.testStatus = 'error';
                return;
            }

            this.isTesting = true;

            try {
                const payload = {
                    host: this.currentAp.host,
                    username: this.currentAp.username,
                    password: this.currentAp.password,
                    zona_id: this.currentAp.zona_id || 0,
                    is_enabled: true,
                    vendor: this.currentAp.vendor || 'ubiquiti',
                    api_port: parseInt(this.currentAp.api_port) || (this.currentAp.vendor === 'mikrotik' ? 8729 : 443)
                };

                const response = await fetch('/api/aps/validate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                const data = await response.json();

                if (!response.ok) throw new Error(data.detail || 'Connection failed');

                this.testMessage = data.message;
                this.testStatus = 'success';

            } catch (error) {
                this.testMessage = error.message;
                this.testStatus = 'error';
            } finally {
                this.isTesting = false;
            }
        },

        closeModal() {
            this.isModalOpen = false;
            // Limpieza ligera, el reset completo se hace en openModal
            this.error = '';
        },

        async saveAp() {
            this.error = '';

            // Validación básica
            if (!this.currentAp.host || !this.currentAp.zona_id || !this.currentAp.username) {
                this.error = 'Please fill out all required fields (Host, Zone, Username).';
                return;
            }

            // En creación, el password es obligatorio
            if (!this.isEditing && !this.currentAp.password) {
                this.error = 'Password is required for new APs.';
                return;
            }

            // Determinar URL y Método
            const url = this.isEditing
                ? `/api/aps/${encodeURIComponent(this.originalHost)}`
                : '/api/aps';

            const method = this.isEditing ? 'PUT' : 'POST';

            // Preparar payload
            const defaultPort = this.currentAp.vendor === 'mikrotik' ? 8729 : 443;
            const payload = {
                ...this.currentAp,
                zona_id: parseInt(this.currentAp.zona_id),
                monitor_interval: this.currentAp.monitor_interval ? parseInt(this.currentAp.monitor_interval) : null,
                api_port: this.currentAp.api_port ? parseInt(this.currentAp.api_port) : defaultPort,
                vendor: this.currentAp.vendor || 'ubiquiti'
            };

            // Limpieza para actualización
            if (this.isEditing) {
                // No enviamos el host en el cuerpo si es una actualización (es la clave primaria en la URL)
                // Opcional: si permites cambiar la IP, el backend debe soportarlo, pero usualmente es mejor recrear.
                // Aquí asumimos que el host es inmutable en el body.
                delete payload.host;

                if (!payload.password) delete payload.password; // No enviar password vacío
            }

            try {
                const response = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || 'Failed to save AP.');
                }

                await this.loadInitialData(); // Refrescar tabla
                this.closeModal();

            } catch (error) {
                console.error('Save AP error:', error);
                this.error = error.message;
            }
        },

        async deleteAp(ap) {
            window.ModalUtils.showConfirmModal({
                title: 'Delete AP',
                message: `Are you sure you want to delete AP "<strong>${ap.hostname || ap.host}</strong>"?`,
                confirmText: 'Delete',
                confirmIcon: 'delete',
                type: 'danger',
            }).then(async (confirmed) => {
                if (confirmed) {
                    try {
                        const response = await fetch(`/api/aps/${encodeURIComponent(ap.host)}`, {
                            method: 'DELETE'
                        });

                        if (!response.ok) {
                            const errorData = await response.json();
                            throw new Error(errorData.detail || 'Failed to delete AP.');
                        }

                        // Optimista: eliminar de la lista local para respuesta instantánea
                        this.aps = this.aps.filter(a => a.host !== ap.host);

                    } catch (error) {
                        console.error('Delete AP error:', error);
                        showToast(error.message, 'danger');
                    }
                }
            });
        },

        renderStatusBadge(status) {
            if (status === 'online') return `<div class="flex items-center gap-2"><div class="size-2 rounded-full bg-success"></div><span>Online</span></div>`;
            if (status === 'offline') return `<div class="flex items-center gap-2 text-danger"><div class="size-2 rounded-full bg-danger"></div><span>Offline</span></div>`;
            return `<div class="flex items-center gap-2 text-text-secondary"><div class="size-2 rounded-full bg-text-secondary"></div><span>Unknown</span></div>`;
        },

        getZoneName(zoneId) {
            const zone = this.allZones.find(z => z.id === zoneId);
            return zone ? zone.nombre : 'Unassigned';
        },

        // Override openProvisionModal to set AP-specific values
        openProvisionModal(ap) {
            // Call base mixin method with AP-specific config
            window.provisionMixin.openProvisionModal.call(this, ap, 'AP', '/api/aps');
        },

        // Repair AP - allows re-provisioning
        async repairAp(ap) {
            const hostname = ap.hostname || ap.host;

            window.ModalUtils.showConfirmModal({
                title: 'Reparar AP',
                message: `¿Desea permitir re-aprovisionar el AP "<strong>${hostname}</strong>"?<br><br>Esto mostrará el botón "Provision" para configurar SSL nuevamente.`,
                confirmText: 'Permitir',
                confirmIcon: 'build',
                type: 'warning',
            }).then(async (confirmed) => {
                if (confirmed) {
                    try {
                        const url = `/api/aps/${encodeURIComponent(ap.host)}/repair?reset_provision=true`;
                        const response = await fetch(url, { method: 'POST' });
                        const data = await response.json();

                        if (!response.ok) {
                            throw new Error(data.detail || 'Error al reparar AP');
                        }

                        showToast('AP listo para re-aprovisionar', 'success');
                        await this.loadInitialData();

                    } catch (error) {
                        console.error('Repair error:', error);
                        showToast(`Error: ${error.message}`, 'danger');
                    }
                }
            });
        },

        isApProvisioned(ap) {
            return ap.is_provisioned === true;
        }
    }));
});

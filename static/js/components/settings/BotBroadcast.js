/**
 * BotBroadcast.js
 * Alpine.js component for sending Telegram broadcasts
 */

document.addEventListener('alpine:init', () => {
    Alpine.data('botBroadcast', () => ({
        message: '',
        target_type: 'clients', // clients, technicians
        all_zones: true,
        selected_zones: [],
        available_zones: [],

        // Technician/Staff roles
        staff_roles: {
            'admin': true,
            'technician': true,
            'billing': true
        },

        image_url: '',
        previewMode: false,
        sending: false,
        lastResult: null,

        async init() {
            await this.loadZones();
        },

        async loadZones() {
            try {
                const response = await fetch('/api/broadcast/zones');
                if (response.ok) {
                    this.available_zones = await response.json();
                }
            } catch (e) {
                console.error("Error loading zones:", e);
                window.showToast("Error cargando zonas", "danger");
            }
        },

        get targetLabel() {
            if (this.target_type === 'technicians') {
                const roles = Object.keys(this.staff_roles).filter(k => this.staff_roles[k]);
                if (roles.length === 3) return 'Todo el Personal (Admin, Tech, Billing)';
                if (roles.length === 0) return 'Ningún rol seleccionado';
                // Translate role names
                const roleNames = { 'billing': 'Cobranza', 'technician': 'Técnicos', 'admin': 'Admin' };
                const names = roles.map(r => roleNames[r] || r);
                return `Personal: ${names.join(', ')}`;
            }
            if (this.all_zones) {
                return 'Todos los Clientes (Multizona)';
            }
            return `${this.selected_zones.length} Zonas Seleccionadas`;
        },

        async send() {
            if (!this.message) return window.showToast('Escribe un mensaje primero.', 'danger');

            // Validation for clients
            if (this.target_type === 'clients' && !this.all_zones && this.selected_zones.length === 0) {
                return window.showToast('Selecciona al menos una zona o marca "Todas".', 'warning');
            }

            // Validation for staff
            if (this.target_type === 'technicians') {
                const hasRole = Object.values(this.staff_roles).some(v => v);
                if (!hasRole) return window.showToast('Selecciona al menos un rol de personal.', 'warning');
            }

            const confirmed = await window.ModalUtils.showConfirmModal({
                title: 'Confirmar Broadcast',
                message: `Estás a punto de enviar este mensaje a:<br><strong class="text-lg text-primary block mt-2">${this.targetLabel}</strong><br>¿Estás seguro?`,
                confirmText: 'Sí, enviar ahora',
                confirmIcon: 'send',
                type: 'warning'
            });

            if (!confirmed) return;

            this.sending = true;
            this.lastResult = null;

            try {
                const payload = {
                    message: this.message,
                    target_type: this.target_type,
                    image_url: this.image_url || null
                };

                if (this.target_type === 'clients' && !this.all_zones) {
                    // Alpine proxies need to be converted to array
                    payload.zone_ids = Array.from(this.selected_zones).map(Number);
                }

                if (this.target_type === 'technicians') {
                    // Send selected roles
                    payload.staff_roles = Object.keys(this.staff_roles).filter(k => this.staff_roles[k]);
                }

                const response = await fetch(`${window.location.origin}/api/broadcast/send`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (!response.ok) {
                    const err = await response.json();
                    throw new Error(err.detail || 'Error sending broadcast');
                }

                const data = await response.json();
                this.lastResult = data;
                window.showToast(`Broadcast en cola para ${data.recipient_count} destinatarios.`, 'success');

                // Reset form slightly but keep context
                this.message = '';
                this.image_url = '';

            } catch (e) {
                console.error(e);
                window.showToast(e.message, 'danger');
            } finally {
                this.sending = false;
            }
        }
    }));
});

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
                return 'Técnicos y Administradores';
            }
            if (this.all_zones) {
                return 'Todos los Clientes (Multizona)';
            }
            return `${this.selected_zones.length} Zonas Seleccionadas`;
        },

        async send() {
            if (!this.message) return window.showToast('Escribe un mensaje primero.', 'danger');

            // Validation for zones
            if (this.target_type === 'clients' && !this.all_zones && this.selected_zones.length === 0) {
                return window.showToast('Selecciona al menos una zona o marca "Todas".', 'warning');
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

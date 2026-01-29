/**
 * BotBroadcast.js
 * Alpine.js component for sending Telegram broadcasts
 */

document.addEventListener('alpine:init', () => {
    Alpine.data('botBroadcast', () => ({
        message: '',
        target_group: 'all_clients', // all_clients, prospects, all
        image_url: '',

        previewMode: false,
        sending: false,
        lastResult: null,

        // Computed
        get targetLabel() {
            const labels = {
                'all_clients': 'Todos los Clientes (Vinculados)',
                'prospects': 'Prospectos (No Vinculados)',
                'all': 'Todos (Clientes + Prospectos)'
            };
            return labels[this.target_group] || this.target_group;
        },

        async send() {
            if (!this.message) return window.showToast('Escribe un mensaje first.', 'danger');

            const confirmed = await window.ModalUtils.showConfirmModal({
                title: 'Confirmar Broadcast',
                message: `Estás a punto de enviar este mensaje a <strong>${this.targetLabel}</strong>.<br>¿Estás seguro?`,
                confirmText: 'Sí, enviar ahora',
                confirmIcon: 'send',
                type: 'warning'
            });

            if (!confirmed) return;

            this.sending = true;
            this.lastResult = null;

            try {
                const response = await fetch(`${window.location.origin}/api/broadcast/send`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        message: this.message,
                        target_group: this.target_group,
                        image_url: this.image_url || null
                    })
                });

                if (!response.ok) {
                    const err = await response.json();
                    throw new Error(err.detail || 'Error sending broadcast');
                }

                const data = await response.json();
                this.lastResult = data;
                window.showToast(`Broadcast en cola para ${data.recipient_count} destinatarios.`, 'success');

                // Reset form
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

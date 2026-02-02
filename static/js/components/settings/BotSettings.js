/**
 * BotSettings.js
 * Alpine.js component for the Telegram Bot settings tab
 */

document.addEventListener('alpine:init', () => {
    Alpine.data('botSettings', () => ({
        // Bot Token fields
        telegram_bot_token: '',
        client_bot_token: '',
        telegram_chat_id: '',

        // Execution Mode
        bot_execution_mode: 'auto',
        bot_external_url: '',
        isRestarting: false,

        // Form fields with default values
        bot_welcome_msg_client: '',
        bot_welcome_msg_guest: '',
        bot_val_btn_report: '',
        bot_val_btn_status: '',
        bot_val_btn_agent: '',
        bot_val_btn_wifi: '',
        bot_auto_reply_msg: '',

        // Initialize component
        async init() {
            try {
                // Fetch all settings from store (cached or fresh)
                const settings = await this.$store.settings.fetchSettings();

                // Populate token fields
                this.telegram_bot_token = settings.telegram_bot_token || '';
                this.client_bot_token = settings.client_bot_token || '';
                this.telegram_chat_id = settings.telegram_chat_id || '';

                this.bot_execution_mode = settings.bot_execution_mode || 'auto';
                this.bot_external_url = settings.bot_external_url || '';

                // Populate message fields
                this.bot_welcome_msg_client = settings.bot_welcome_msg_client || "¡Hola de nuevo, {name}! 👋\n\n¿En qué podemos ayudarte?";
                this.bot_welcome_msg_guest = settings.bot_welcome_msg_guest || "Hola, bienvenido. 👋\n\nParece que tu cuenta de Telegram no está vinculada.\nPor favor, comparte este ID con soporte:\n`{user_id}`";
                this.bot_val_btn_report = settings.bot_val_btn_report || "📞 Reportar Falla / Solicitar Ayuda";
                this.bot_val_btn_status = settings.bot_val_btn_status || "📋 Ver Mis Tickets";
                this.bot_val_btn_agent = settings.bot_val_btn_agent || "🙋 Solicitar Agente Humano";
                this.bot_val_btn_wifi = settings.bot_val_btn_wifi || "🔑 Solicitar Cambio Clave WiFi";
                this.bot_auto_reply_msg = settings.bot_auto_reply_msg || "🤖 Soy un asistente virtual. Solo puedo procesar reportes y solicitudes a través del menú.\nSi deseas hablar con un humano, por favor presiona el botón '🙋 Solicitar Agente Humano'.";

            } catch (error) {
                console.error('Failed to initialize bot settings:', error);
            }
        },

        // Save settings
        async save() {
            const settingsData = {
                // Token settings
                telegram_bot_token: this.telegram_bot_token,
                client_bot_token: this.client_bot_token,
                telegram_chat_id: this.telegram_chat_id,
                bot_execution_mode: this.bot_execution_mode,
                bot_external_url: this.bot_external_url,
                // Message settings
                bot_welcome_msg_client: this.bot_welcome_msg_client,
                bot_welcome_msg_guest: this.bot_welcome_msg_guest,
                bot_val_btn_report: this.bot_val_btn_report,
                bot_val_btn_status: this.bot_val_btn_status,
                bot_val_btn_agent: this.bot_val_btn_agent,
                bot_val_btn_wifi: this.bot_val_btn_wifi,
                bot_auto_reply_msg: this.bot_auto_reply_msg,
            };

            await this.$store.settings.updateSettings(settingsData);
        },

        // Helper to insert variables in textarea
        insertVariable(field, variable) {
            const el = document.querySelector(`[name="${field}"]`);
            if (el) {
                const start = el.selectionStart;
                const end = el.selectionEnd;
                const text = this[field];
                const before = text.substring(0, start);
                const after = text.substring(end, text.length);
                this[field] = before + variable + after;

                // Restore focus next tick
                setTimeout(() => {
                    el.focus();
                    el.setSelectionRange(start + variable.length, start + variable.length);
                }, 10);
            } else {
                this[field] += variable;
            }
        },

        // Restart bots with current settings
        async restartBots() {
            this.isRestarting = true;
            try {
                // Save settings first
                await this.save();
                // Then restart bots
                const response = await fetch('/api/settings/restart-bots', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                if (response.ok) {
                    window.toast?.success?.('Bots reiniciados correctamente') || console.log('Bots restarted');
                } else {
                    const data = await response.json();
                    window.toast?.error?.(data.detail || 'Error al reiniciar bots') || console.error('Restart failed');
                }
            } catch (error) {
                console.error('Restart bots failed:', error);
                window.toast?.error?.('Error de conexión') || console.error(error);
            } finally {
                this.isRestarting = false;
            }
        }
    }));
});

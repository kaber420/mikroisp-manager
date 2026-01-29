/**
 * BotSettings.js
 * Alpine.js component for the Telegram Bot settings tab
 */

document.addEventListener('alpine:init', () => {
    Alpine.data('botSettings', () => ({
        // Form fields with default values
        bot_welcome_msg_client: '',
        bot_welcome_msg_guest: '',
        bot_val_btn_report: '',
        bot_val_btn_status: '',
        bot_val_btn_agent: '',
        bot_val_btn_wifi: '',

        // Initialize component
        async init() {
            try {
                // Fetch all settings from store (cached or fresh)
                const settings = await this.$store.settings.fetchSettings();

                // Populate fields
                this.bot_welcome_msg_client = settings.bot_welcome_msg_client || "¡Hola de nuevo, {name}! 👋\n\n¿En qué podemos ayudarte?";
                this.bot_welcome_msg_guest = settings.bot_welcome_msg_guest || "Hola, bienvenido. 👋\n\nParece que tu cuenta de Telegram no está vinculada.\nPor favor, comparte este ID con soporte:\n`{user_id}`";
                this.bot_val_btn_report = settings.bot_val_btn_report || "📞 Reportar Falla / Solicitar Ayuda";
                this.bot_val_btn_status = settings.bot_val_btn_status || "📋 Ver Mis Tickets";
                this.bot_val_btn_agent = settings.bot_val_btn_agent || "🙋 Solicitar Agente Humano";
                this.bot_val_btn_wifi = settings.bot_val_btn_wifi || "🔑 Solicitar Cambio Clave WiFi";

            } catch (error) {
                console.error('Failed to initialize bot settings:', error);
            }
        },

        // Save settings
        async save() {
            const settingsData = {
                bot_welcome_msg_client: this.bot_welcome_msg_client,
                bot_welcome_msg_guest: this.bot_welcome_msg_guest,
                bot_val_btn_report: this.bot_val_btn_report,
                bot_val_btn_status: this.bot_val_btn_status,
                bot_val_btn_agent: this.bot_val_btn_agent,
                bot_val_btn_wifi: this.bot_val_btn_wifi,
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
        }
    }));
});

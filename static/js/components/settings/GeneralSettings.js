/**
 * GeneralSettings.js
 * Alpine.js component for the settings form
 */

document.addEventListener('alpine:init', () => {
    Alpine.data('generalSettings', () => ({
        // Form fields
        company_name: '',
        notification_email: '',
        currency_symbol: '',
        company_logo_url: '',
        billing_address: '',
        ticket_footer_message: '',

        default_monitor_interval: '',
        monitor_max_workers: '',
        dashboard_refresh_interval: '',
        backup_frequency: 'daily',
        backup_day_of_week: 'mon',
        backup_run_hour: '',
        db_backup_run_hour: '',
        days_before_due: '',
        billing_alert_days: '',
        suspension_run_hour: '',

        // Computed property for showing backup day field
        get showBackupDay() {
            return this.backup_frequency === 'weekly';
        },

        // Initialize component
        async init() {
            try {
                const settings = await this.$store.settings.fetchSettings();

                // Populate form fields with fetched settings
                Object.keys(settings).forEach(key => {
                    // Use direct assignment if key exists in component data
                    // Alpine proxies might not handle hasOwnProperty as expected
                    if (typeof this[key] !== 'undefined') {
                        this[key] = settings[key];
                    }
                });
            } catch (error) {
                console.error('Failed to initialize settings:', error);
            }
        },

        // Save settings
        async save() {
            const settingsData = {
                company_name: this.company_name,
                notification_email: this.notification_email,
                currency_symbol: this.currency_symbol,
                company_logo_url: this.company_logo_url,
                billing_address: this.billing_address,
                ticket_footer_message: this.ticket_footer_message,

                default_monitor_interval: this.default_monitor_interval,
                monitor_max_workers: this.monitor_max_workers,
                dashboard_refresh_interval: this.dashboard_refresh_interval,
                backup_frequency: this.backup_frequency,
                backup_day_of_week: this.backup_day_of_week,
                backup_run_hour: this.backup_run_hour,
                db_backup_run_hour: this.db_backup_run_hour,
                days_before_due: this.days_before_due,
                billing_alert_days: this.billing_alert_days,
                suspension_run_hour: this.suspension_run_hour,
            };

            await this.$store.settings.updateSettings(settingsData);
        },

        // Trigger force billing
        async forceBilling() {
            await this.$store.settings.triggerForceBilling();
        },

        // Trigger manual backup
        async backupNow() {
            await this.$store.settings.triggerManualBackup();
        }
    }));
});

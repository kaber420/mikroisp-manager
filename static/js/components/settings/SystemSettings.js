document.addEventListener('alpine:init', () => {
    Alpine.data('systemSettings', () => ({
        config: {
            db_provider: 'sqlite',
            postgres_host: 'localhost',
            postgres_port: '5432',
            postgres_db: 'umanager',
            postgres_user: 'postgres',
            postgres_password: '',
            cache_provider: 'memory',
            redict_url: ''
        },
        isSaving: false,

        async init() {
            await this.loadSettings();
        },

        async loadSettings() {
            const settings = await Alpine.store('settings').fetchSystemSettings();

            // Map env vars to config object
            if (settings.DATABASE_URL_SYNC && settings.DATABASE_URL_SYNC.startsWith('postgres')) {
                this.config.db_provider = 'postgres';
                try {
                    // Parse: postgresql+psycopg://user:pass@host:port/db
                    const url = new URL(settings.DATABASE_URL_SYNC.replace('postgresql+psycopg://', 'http://'));
                    this.config.postgres_user = url.username;
                    this.config.postgres_password = url.password;
                    this.config.postgres_host = url.hostname;
                    this.config.postgres_port = url.port;
                    this.config.postgres_db = url.pathname.substring(1);
                } catch (e) {
                    console.error('Error parsing DB URL', e);
                }
            } else {
                this.config.db_provider = 'sqlite';
            }

            if (settings.CACHE_BACKEND === 'redict') {
                this.config.cache_provider = 'redict';
                this.config.redict_url = settings.REDICT_URL || '';
            } else {
                this.config.cache_provider = 'memory';
            }
        },

        async save() {
            this.isSaving = true;
            try {
                const result = await Alpine.store('settings').updateSystemSettings(this.config);

                await window.ModalUtils.showConfirmModal({
                    title: 'System Restart Required',
                    message: `<p class="mb-4 text-warning">Configuration saved successfully.</p>
                             <p>You must <strong>restart the application service</strong> manually for these changes to take effect.</p>`,
                    confirmText: 'OK, I understand',
                    confirmIcon: 'check_circle',
                    type: 'success',
                });

            } catch (error) {
                window.showToast?.(error.message, 'danger');
            } finally {
                this.isSaving = false;
            }
        }
    }));
});

document.addEventListener('alpine:init', () => {
    Alpine.data('dashboardManager', () => ({
        get store() { return this.$store.dashboard; },
        get kpis() { return this.store.kpis; },

        init() {
            this.store.loadAll();

            // Debounce refresh to prevent repeated API calls
            let refreshTimeout;
            const debouncedRefresh = () => {
                clearTimeout(refreshTimeout);
                refreshTimeout = setTimeout(() => {
                    this.store.loadAll();
                }, 1000);
            };

            window.addEventListener('data-refresh-needed', debouncedRefresh);
            window.refreshDashboard = debouncedRefresh;
        }
    }));

    Alpine.data('dashboardKpis', () => ({
        get store() { return this.$store.dashboard; },
        get kpis() { return this.store.kpis; },

        statClass(stat) {
            return stat.online === stat.total && stat.total > 0 ? 'text-success' : 'text-primary';
        },

        statIcon(type) {
            const icons = {
                aps: 'cell_tower',
                cpes: 'settings_input_antenna',
                routers: 'dns',
                switches: 'lan'
            };
            return icons[type] || 'analytics';
        }
    }));

    Alpine.data('dashboardTopStats', () => ({
        get store() { return this.$store.dashboard; },
        get topAirtime() { return this.store.topAirtime; },
        get topSignal() { return this.store.topSignal; },

        getAirtimeBarColor(usageVal) {
            return usageVal > 80 ? 'bg-danger' : 'bg-primary';
        },

        getSignalBadgeClass(signal) {
            let badgeClass = "text-warning bg-warning/10 border-warning/20";
            if (signal < -75) {
                badgeClass = "text-danger bg-danger/10 border-danger/20";
            }
            return badgeClass;
        }
    }));

    Alpine.data('dashboardEventLogs', () => ({
        get store() { return this.$store.dashboard; },
        get events() { return this.store.events; },
        get routerOptions() { return this.store.routerOptions; },

        init() {
            this.store.loadRouterOptions();
            this.store.loadEvents();
        },

        changePage(direction) {
            this.store.changeEventPage(direction);
        },

        changePageSize(size) {
            this.store.changeEventPageSize(size);
        },

        changeFilter(hostFilter) {
            this.store.changeEventFilter(hostFilter);
        },

        getEventTime(timestamp) {
            const { timeStr, dateStr } = this.store.formatEventDate(timestamp);
            return { timeStr, dateStr };
        },

        getEventIconAndClass(eventType) {
            return this.store.getEventIconClass(eventType);
        },

        get paginationInfo() {
            return this.store.getPaginationInfo();
        }
    }));

    Alpine.data('sslCertificate', () => ({
        get store() { return this.$store.dashboard; },

        get status() {
            const data = this.store.caStatus.data;
            if (this.store.caStatus.loading && !data) return 'Verificando estado...';
            if (this.store.caStatus.error) return 'Error verificando estado SSL';

            if (data) {
                if (data.https_active) {
                    return '✅ HTTPS activo - Descarga el certificado para evitar advertencias en otros dispositivos.';
                } else if (data.ca_available) {
                    return '⚠️ Certificado disponible - HTTPS no está configurado en modo producción.';
                } else {
                    return 'HTTPS no configurado. Ejecuta <code class="bg-surface-2 px-1 rounded">sudo bash scripts/install_proxy.sh</code>';
                }
            }
            return 'Verificando estado...';
        },

        get downloadDisabled() {
            const data = this.store.caStatus.data;
            if (!data) return true;
            return !data.https_active && !data.ca_available;
        },

        init() {
            this.store.loadCaStatus();
        },

        downloadCertificate() {
            window.location.href = '/api/security/ca-certificate';
        }
    }));

    Alpine.data('sslInstructionsModal', () => ({
        open: false,
        activeTab: 'windows',

        tabs: [
            { id: 'windows', label: 'Windows', icon: 'desktop_windows' },
            { id: 'android', label: 'Android', icon: 'android' },
            { id: 'ios', label: 'iOS/macOS', icon: 'phone_iphone' }
        ],

        openModal() {
            this.open = true;
            document.body.style.overflow = 'hidden';
        },

        closeModal() {
            this.open = false;
            document.body.style.overflow = '';
        },

        switchTab(tab) {
            this.activeTab = tab;
        },

        isActiveTab(tab) {
            return this.activeTab === tab;
        }
    }));
});

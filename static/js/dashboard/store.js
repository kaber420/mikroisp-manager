document.addEventListener('alpine:init', () => {
    Alpine.store('dashboard', {
        loading: false,
        apiBase: window.location.origin,

        kpis: {
            aps: { total: 0, online: 0, offline: 0 },
            cpes: { total: 0, online: 0, offline: 0 },
            routers: { total: 0, online: 0, offline: 0 },
            switches: { total: 0, online: 0, offline: 0 }
        },

        topAirtime: [],
        topSignal: [],

        routers: null,
        routersPromise: null,
        topStatsPromise: null,

        caStatus: {
            loading: false,
            data: null,
            error: null,
            promise: null
        },

        events: {
            items: [],
            page: 1,
            pageSize: 10,
            totalPages: 1,
            total: 0,
            hostFilter: 'all',
            loading: false
        },

        routerOptions: [{ value: 'all', label: 'Todos los Dispositivos' }],

        async loadAll() {
            // Provide a small debounce/throttle here too if needed, but components.js handles the main one.
            // However, we want to allow forced reloading if the user clicks "Refresh".
            // The components.js debounce is for the initial load race.

            // If already loading, we might want to let it finish.
            if (this.loading) return;

            this.loading = true;
            try {
                const routersPromise = this.fetchRouters(true);

                const [apsRes, cpeCountRes, switchCountRes] = await Promise.all([
                    fetch(`${this.apiBase}/api/aps`),
                    fetch(`${this.apiBase}/api/stats/cpe-count`),
                    fetch(`${this.apiBase}/api/stats/switch-count`)
                ]);

                if (!apsRes.ok || !cpeCountRes.ok) throw new Error('Failed to load dashboard data');

                const allAps = await apsRes.json();
                const cpeCountData = await cpeCountRes.json();
                const allRouters = await routersPromise;
                const switchCountData = switchCountRes.ok ? await switchCountRes.json() : { total_switches: 0, online: 0, offline: 0 };

                let cpesOnline = 0;
                let apsOnline = 0;

                allAps.forEach(ap => {
                    if (ap.last_status === 'online') {
                        apsOnline++;
                        if (ap.client_count != null) cpesOnline += ap.client_count;
                    }
                });

                let routersOnline = 0;
                allRouters.forEach(router => {
                    if (router.last_status === 'online') {
                        routersOnline++;
                    }
                });

                this.kpis = {
                    aps: { total: allAps.length, online: apsOnline, offline: allAps.length - apsOnline },
                    cpes: { total: cpeCountData.total_cpes, online: cpesOnline, offline: cpeCountData.total_cpes - cpesOnline },
                    routers: { total: allRouters.length, online: routersOnline, offline: allRouters.length - routersOnline },
                    switches: {
                        total: switchCountData.total_switches,
                        online: switchCountData.online,
                        offline: switchCountData.offline
                    }
                };

                // Use the shared method which handles promises
                await this.loadTopStats();
            } catch (error) {
                console.error("Dashboard Load Error:", error);
            } finally {
                this.loading = false;
            }
        },

        async loadTopStats() {
            if (this.topStatsPromise) return this.topStatsPromise;

            this.topStatsPromise = (async () => {
                try {
                    const [airtimeRes, signalRes] = await Promise.all([
                        fetch(`${this.apiBase}/api/stats/top-aps-by-airtime`),
                        fetch(`${this.apiBase}/api/stats/top-cpes-by-signal`)
                    ]);

                    if (airtimeRes.ok) {
                        this.topAirtime = await airtimeRes.json();
                    }

                    if (signalRes.ok) {
                        this.topSignal = await signalRes.json();
                    }
                } catch (error) {
                    console.error("Error loading top stats:", error);
                } finally {
                    this.topStatsPromise = null;
                }
            })();

            return this.topStatsPromise;
        },

        generateRouterOptions() {
            if (this.routers) {
                this.routerOptions = [{ value: 'all', label: 'Todos los Dispositivos' }];
                this.routers.forEach(r => {
                    this.routerOptions.push({ value: r.host, label: r.hostname || r.host });
                });
            }
        },

        async fetchRouters(force = false) {
            if (!force && this.routers) return this.routers;
            if (this.routersPromise) return this.routersPromise;

            this.routersPromise = fetch(`${this.apiBase}/api/routers`)
                .then(res => {
                    if (!res.ok) throw new Error('Failed to fetch routers');
                    return res.json();
                })
                .then(data => {
                    this.routers = data;
                    this.generateRouterOptions();
                    return data;
                })
                .catch(err => {
                    throw err;
                })
                .finally(() => {
                    this.routersPromise = null;
                });

            return this.routersPromise;
        },

        async loadCaStatus() {
            if (this.caStatus.data) return;
            if (this.caStatus.promise) return this.caStatus.promise;

            this.caStatus.loading = true;
            this.caStatus.promise = (async () => {
                try {
                    const res = await fetch(`${this.apiBase}/api/security/ca-status`);
                    if (res.ok) {
                        this.caStatus.data = await res.json();
                    }
                } catch (e) {
                    console.error("Error loading CA status", e);
                    this.caStatus.error = e;
                } finally {
                    this.caStatus.loading = false;
                    this.caStatus.promise = null;
                }
            })();

            return this.caStatus.promise;
        },

        async loadRouterOptions() {
            try {
                await this.fetchRouters(false);
            } catch (e) {
                console.error("Error cargando filtro:", e);
            }
        },

        async loadEvents() {
            this.events.loading = true;
            try {
                const url = `${this.apiBase}/api/stats/events?host=${encodeURIComponent(this.events.hostFilter)}&page=${this.events.page}&page_size=${this.events.pageSize}`;
                const res = await fetch(url);
                if (res.ok) {
                    const data = await res.json();
                    this.events.items = data.items;
                    this.events.totalPages = data.total_pages;
                    this.events.total = data.total;
                }
            } catch (error) {
                console.error("Error loading events:", error);
            } finally {
                this.events.loading = false;
            }
        },

        changeEventPage(direction) {
            const newPage = this.events.page + direction;
            if (newPage > 0 && newPage <= this.events.totalPages) {
                this.events.page = newPage;
                this.loadEvents();
            }
        },

        changeEventPageSize(size) {
            this.events.pageSize = parseInt(size);
            this.events.page = 1;
            this.loadEvents();
        },

        changeEventFilter(hostFilter) {
            this.events.hostFilter = hostFilter;
            this.events.page = 1;
            this.loadEvents();
        },

        formatEventDate(timestamp) {
            const dateObj = new Date(timestamp + "Z");
            const timeStr = dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            const dateStr = dateObj.toLocaleDateString();
            return { timeStr, dateStr };
        },

        getEventIconClass(eventType) {
            let icon = 'info';
            let colorClass = 'text-blue-400 bg-blue-400/10';

            if (eventType === 'danger') { icon = 'error'; colorClass = 'text-danger bg-danger/10'; }
            else if (eventType === 'success') { icon = 'check_circle'; colorClass = 'text-success bg-success/10'; }

            return { icon, colorClass };
        },

        getPaginationInfo() {
            const start = (this.events.page - 1) * this.events.pageSize + 1;
            const end = Math.min(start + this.events.pageSize - 1, this.events.total);
            return this.events.total > 0 ? `Mostrando ${start}-${end} de ${this.events.total}` : 'Sin resultados';
        }
    });
});

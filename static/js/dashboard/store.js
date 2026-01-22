document.addEventListener('alpine:init', () => {
    Alpine.store('dashboard', {
        loading: true,
        apiBase: window.location.origin,

        kpis: {
            aps: { total: 0, online: 0, offline: 0 },
            cpes: { total: 0, online: 0, offline: 0 },
            routers: { total: 0, online: 0, offline: 0 },
            switches: { total: 0, online: 0, offline: 0 }
        },

        topAirtime: [],
        topSignal: [],

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
            this.loading = true;
            try {
                const [apsRes, cpeCountRes, routersRes, switchCountRes] = await Promise.all([
                    fetch(`${this.apiBase}/api/aps`),
                    fetch(`${this.apiBase}/api/stats/cpe-count`),
                    fetch(`${this.apiBase}/api/routers`),
                    fetch(`${this.apiBase}/api/stats/switch-count`)
                ]);

                if (!apsRes.ok || !cpeCountRes.ok || !routersRes.ok) throw new Error('Failed to load dashboard data');

                const allAps = await apsRes.json();
                const cpeCountData = await cpeCountRes.json();
                const allRouters = await routersRes.json();
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

                await this.loadTopStats();
            } catch (error) {
                console.error("Dashboard Load Error:", error);
            } finally {
                this.loading = false;
            }
        },

        async loadTopStats() {
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
            }
        },

        async loadRouterOptions() {
            try {
                const res = await fetch(`${this.apiBase}/api/routers`);
                if (res.ok) {
                    const routers = await res.json();
                    this.routerOptions = [{ value: 'all', label: 'Todos los Dispositivos' }];
                    routers.forEach(r => {
                        this.routerOptions.push({ value: r.host, label: r.hostname || r.host });
                    });
                }
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

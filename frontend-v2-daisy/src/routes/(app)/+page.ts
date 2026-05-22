export const ssr = false;

export const load = async ({ fetch }) => {
    try {
        const [summaryRes, settingsRes] = await Promise.all([
            fetch('/api/stats/dashboard-summary'),
            fetch('/api/settings/public')
        ]);

        const summary = summaryRes.ok ? await summaryRes.json() : null;
        const publicSettings = settingsRes.ok ? await settingsRes.json() : {};

        return {
            stats: summary?.stats || {
                cpes: { total_cpes: 0, active: 0, offline: 0, disabled: 0 },
                switches: { total_switches: 0, online: 0, offline: 0 },
                tickets: { open_tickets: 0, resolved_tickets: 0, pending_tickets: 0, total_tickets: 0, support_tickets: 0, installation_tickets: 0 },
                routers: { total_routers: 0, online: 0, offline: 0 },
                aps: { total_aps: 0, online: 0, offline: 0 }
            },
            tops: summary?.tops || {
                signal: [],
                airtime: [],
                consumption: [],
                offline: []
            },
            publicSettings,
            recentTickets: summary?.recent_tickets || [],
            routersList: summary?.routers_list || []
        };
    } catch (e) {
        console.error('Failed to load consolidated dashboard stats:', e);
        return {
            stats: {
                cpes: { total_cpes: 0, active: 0, offline: 0, disabled: 0 },
                switches: { total_switches: 0, online: 0, offline: 0 },
                tickets: { open_tickets: 0, resolved_tickets: 0, pending_tickets: 0, total_tickets: 0, support_tickets: 0, installation_tickets: 0 },
                routers: { total_routers: 0, online: 0, offline: 0 },
                aps: { total_aps: 0, online: 0, offline: 0 }
            },
            tops: {
                signal: [],
                airtime: [],
                consumption: [],
                offline: []
            },
            publicSettings: {},
            recentTickets: [],
            routersList: []
        };
    }
};

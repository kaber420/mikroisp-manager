// Deshabilitar SSR: el fetch de estadísticas requiere la cookie de sesión.
// En SSR el servidor de Node no tiene esa cookie, el backend devuelve 401
// y todos los valores caen en el fallback { total: 0 }.
// Con ssr = false el load() corre en el browser, el proxy de Vite envía
// la cookie y el backend responde correctamente.
export const ssr = false;

export const load = async ({ fetch }) => {
    try {
        const [cpeRes, switchRes, ticketsRes, routerRes, apRes] = await Promise.all([
            fetch('/api/stats/cpe-count'),
            fetch('/api/stats/switch-count'),
            fetch('/api/stats/tickets'),
            fetch('/api/stats/router-count'),
            fetch('/api/stats/ap-count')
        ]);

        return {
            stats: {
                cpes: cpeRes.ok ? await cpeRes.json() : { total_cpes: 0, active: 0 },
                switches: switchRes.ok ? await switchRes.json() : { total_switches: 0, online: 0 },
                tickets: ticketsRes.ok ? await ticketsRes.json() : { open_tickets: 0, resolved_tickets: 0 },
                routers: routerRes.ok ? await routerRes.json() : { total_routers: 0, online: 0 },
                aps: apRes.ok ? await apRes.json() : { total_aps: 0, online: 0 }
            }
        };
    } catch (e) {
        console.error('Failed to load dashboard stats:', e);
        return {
            stats: {
                cpes: { total_cpes: 0, active: 0 },
                switches: { total_switches: 0, online: 0 },
                tickets: { open_tickets: 0, resolved_tickets: 0 },
                routers: { total_routers: 0, online: 0 },
                aps: { total_aps: 0, online: 0 }
            }
        };
    }
};

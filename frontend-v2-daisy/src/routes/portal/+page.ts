import type { PageLoad } from './$types';
import { getPortalMe, getPortalTickets, getPortalAnnouncements } from '$lib/api/portal';

export const load: PageLoad = async () => {
    try {
        const [me, tickets, announcements] = await Promise.all([
            getPortalMe(),
            getPortalTickets(),
            getPortalAnnouncements()
        ]);

        return {
            me,
            tickets,
            announcements
        };
    } catch (error) {
        console.error('Error loading portal data:', error);
        return {
            me: null,
            tickets: { items: [], total: 0 },
            announcements: []
        };
    }
};

import type { PageLoad } from './$types';
import { getPortalMe, getPortalTickets } from '$lib/api/portal';

export const load: PageLoad = async () => {
    try {
        const [me, tickets] = await Promise.all([
            getPortalMe(),
            getPortalTickets()
        ]);

        return {
            me,
            tickets
        };
    } catch (error) {
        console.error('Error loading portal data:', error);
        return {
            me: null,
            tickets: []
        };
    }
};

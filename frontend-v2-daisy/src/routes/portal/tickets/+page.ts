import type { PageLoad } from './$types';
import { getPortalTickets } from '$lib/api/portal';

export const load: PageLoad = async () => {
    try {
        const response = await getPortalTickets(10, 0);
        return {
            tickets: response.items,
            total: response.total
        };
    } catch (error) {
        console.error('Error loading tickets:', error);
        return {
            tickets: [],
            total: 0
        };
    }
};

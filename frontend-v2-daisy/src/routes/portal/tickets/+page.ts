import type { PageLoad } from './$types';
import { getPortalTickets } from '$lib/api/portal';
import { getPublicSettings } from '$lib/api/settings';

export const load: PageLoad = async () => {
    try {
        const [response, publicSettings] = await Promise.all([
            getPortalTickets(10, 0),
            getPublicSettings()
        ]);
        return {
            tickets: response.items,
            total: response.total,
            publicSettings
        };
    } catch (error) {
        console.error('Error loading tickets:', error);
        return {
            tickets: [],
            total: 0,
            publicSettings: {}
        };
    }
};

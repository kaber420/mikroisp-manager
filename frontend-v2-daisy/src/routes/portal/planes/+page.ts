import type { PageLoad } from './$types';
import { getPortalPlanes } from '$lib/api/portal';

export const load: PageLoad = async () => {
    try {
        const planes = await getPortalPlanes();
        return {
            planes
        };
    } catch (error) {
        console.error('Error loading planes:', error);
        return {
            planes: []
        };
    }
};

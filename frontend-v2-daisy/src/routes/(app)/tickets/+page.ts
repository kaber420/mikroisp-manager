import { getTickets } from '$lib/api';
import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export const load: PageLoad = async () => {
    try {
        const tickets = await getTickets({ limit: 20, offset: 0 });
        return { tickets };
    } catch (e: any) {
        if (e?.response?.status === 401) {
            throw redirect(302, '/login');
        }
        return {
            tickets: {
                items: [],
                total: 0
            }
        };
    }
};

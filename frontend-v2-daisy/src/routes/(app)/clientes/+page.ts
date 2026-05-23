import { getClients } from '$lib/api';
import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export const load: PageLoad = async () => {
    try {
        const clients = await getClients({ page: 1, page_size: 10 });
        return { clients };
    } catch (e: any) {
        if (e?.response?.status === 401) {
            throw redirect(302, '/login');
        }
        // Devuelve estructura vacía para no romper la vista
        return {
            clients: {
                items: [],
                total: 0,
                page: 1,
                page_size: 10,
                total_pages: 1
            }
        };
    }
};

import { getCPEs } from '$lib/api';
import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export const load: PageLoad = async () => {
    try {
        const cpes = await getCPEs({ page: 1, page_size: 20 });
        return { cpes };
    } catch (e: any) {
        if (e?.response?.status === 401) {
            throw redirect(302, '/login');
        }
        return {
            cpes: {
                items: [],
                total: 0,
                page: 1,
                page_size: 20,
                total_pages: 1
            }
        };
    }
};

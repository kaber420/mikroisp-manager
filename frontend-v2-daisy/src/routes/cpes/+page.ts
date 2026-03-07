import { getCPEs, getPublicSettings } from '$lib/api';
import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export const load: PageLoad = async () => {
    try {
        const [cpes, publicSettings] = await Promise.all([
            getCPEs({ page: 1, page_size: 20 }),
            getPublicSettings()
        ]);
        return { cpes, publicSettings };
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

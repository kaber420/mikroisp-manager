import { error } from '@sveltejs/kit';
import { getRouter } from '$lib/api';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params }) => {
    try {
        const router = await getRouter(params.host);
        return { router };
    } catch (e: any) {
        throw error(404, {
            message: 'Router no encontrado o error de conexión'
        });
    }
};

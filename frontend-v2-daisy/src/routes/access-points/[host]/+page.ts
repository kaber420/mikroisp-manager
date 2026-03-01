import { error } from '@sveltejs/kit';
import { getAP } from '$lib/api';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params }) => {
    try {
        const ap = await getAP(params.host);
        return {
            ap
        };
    } catch (e: any) {
        throw error(404, {
            message: 'Access Point no encontrado o error de conexión'
        });
    }
};

import { redirect } from '@sveltejs/kit';
import { getBroadcastZones } from '$lib/api';
import type { PageLoad } from './$types';

export const load: PageLoad = async () => {
    try {
        const zones = await getBroadcastZones();
        return { zones };
    } catch (e: any) {
        if (e?.response?.status === 401) {
            throw redirect(302, '/login');
        }
        // Si falla la carga de zonas, devolver lista vacía
        return { zones: [] };
    }
};

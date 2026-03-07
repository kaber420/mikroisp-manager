import { getClient } from '$lib/api';
import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params }) => {
    const clientId = params.id;
    try {
        const client = await getClient(clientId);
        return { client };
    } catch (e: any) {
        const status = e?.response?.status ?? 500;
        throw error(status, `No se pudo cargar el cliente: ${e?.message ?? 'Error desconocido'}`);
    }
};

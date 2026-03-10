import { getTicket } from '$lib/api';
import { redirect, error } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params }) => {
    try {
        const ticket = await getTicket(params.id);
        return { ticket };
    } catch (e: any) {
        if (e?.response?.status === 401) {
            throw redirect(302, '/login');
        }
        if (e?.response?.status === 404) {
            throw error(404, 'Ticket no encontrado');
        }
        throw error(500, 'Error al cargar el ticket');
    }
};

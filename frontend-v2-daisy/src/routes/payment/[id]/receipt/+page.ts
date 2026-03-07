import { getPaymentReceipt } from '$lib/api';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params }) => {
    const paymentId = parseInt(params.id);
    const receiptData = await getPaymentReceipt(paymentId);
    
    return {
        receipt: receiptData
    };
};

export interface Client {
    id: string;
    name: string;
    dni?: string;
    phone?: string;
    phone_number?: string;
    whatsapp_number?: string;
    email?: string;
    address?: string;
    notes?: string;
    coordinates?: string;
    telegram_contact?: string;
    billing_day?: number;
    status: 'active' | 'inactive' | 'suspended';
    service_status: 'active' | 'inactive' | 'suspended';
    cpe_count: number;
    created_at: string;
    zona_id?: number;
}

export interface ClientCreate {
    name: string;
    dni?: string;
    phone?: string;
    phone_number?: string;
    whatsapp_number?: string;
    email?: string;
    address?: string;
    notes?: string;
    telegram_contact?: string;
    billing_day?: number;
    service_status?: string;
    zona_id?: number;
}

export interface ClientService {
    id: number;
    client_id: string;
    service_type: 'pppoe' | 'simple_queue';
    status: 'active' | 'suspended' | 'inactive';
    router_host: string;
    pppoe_username?: string;
    ip_address?: string;
    plan_name?: string;
    plan_price?: number;
    billing_day?: number;
    notes?: string;
}

export interface Payment {
    id: number;
    monto: number;
    mes_correspondiente: string;
    fecha_pago: string;
    metodo_pago?: string;
    notas?: string;
}

export interface PaymentCreate {
    monto: number;
    mes_correspondiente: string;
    metodo_pago?: string;
    notas?: string;
}

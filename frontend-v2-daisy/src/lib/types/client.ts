export interface Client {
    id: string;
    name: string;
    dni?: string;
    phone?: string;
    email?: string;
    address?: string;
    status: 'active' | 'inactive' | 'suspended';
    created_at: string;
    zona_id?: number;
}

export interface ClientCreate {
    name: string;
    dni?: string;
    phone?: string;
    email?: string;
    address?: string;
    zona_id?: number;
}

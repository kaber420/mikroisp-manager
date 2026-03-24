export interface AP {
    id: string;
    host: string;
    hostname?: string;
    model?: string;
    last_status?: string;
    is_enabled: boolean;
    zona_id?: number;
}

export interface CPE {
    id: string;
    name: string;
    host: string;
    client_id?: string;
    plan_id?: string;
    last_status?: string;
    signal?: number;
    uptime?: string;
}

export interface Plan {
    id: string;
    name: string;
    price: number;
    download_limit: number;
    upload_limit: number;
    is_active: boolean;
}

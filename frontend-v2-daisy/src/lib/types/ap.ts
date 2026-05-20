export interface AP {
    id: string;
    host: string;
    hostname?: string;
    model?: string;
    last_status?: string;
    is_enabled: boolean;
    zona_id?: number;
    username: string;
    password?: string;
    vendor?: string;
    ssh_port?: number;
    api_port?: number | null;
    is_provisioned?: boolean;
    zona_nombre?: string;
}

export type APCreate = Omit<AP, "id"> & { role?: string };
export type APUpdate = Partial<Omit<AP, "id" | "host">> & { role?: string };
export type APValidate = {
    host: string;
    username: string;
    password?: string;
    vendor: string;
    api_port?: number | null;
};

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

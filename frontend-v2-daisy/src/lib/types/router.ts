export interface Router {
    id: string;
    host: string;
    hostname?: string;
    username: string; // Faltaba
    password?: string;
    ssh_port: number; // Faltaba
    api_port: number; // Faltaba
    model?: string;
    firmware?: string;
    last_status?: 'online' | 'offline' | 'unknown' | string;
    is_enabled: boolean;
    is_provisioned: boolean;
    vendor?: string;
    wan_interface?: string | null; // Faltaba
    zona_id?: number | null; // Faltaba
    zona_nombre?: string;
}

export interface RouterCreate {
    host: string;
    username: string;
    password?: string;
    ssh_port: number;
    api_port: number;
    is_enabled: boolean;
    vendor: string;
    is_provisioned: boolean;
    zona_id?: number;
}

export interface RouterUpdate {
    username?: string;
    password?: string;
    ssh_port?: number;
    api_port?: number;
    is_enabled?: boolean;
    wan_interface?: string | null;
    vendor?: string;
    is_provisioned?: boolean;
    zona_id?: number | null;
}

export interface RouterHistoryPoint {
    timestamp: string;
    cpu_load?: number;
    free_memory?: number;
    total_memory?: number;
    uptime?: string;
    temperature?: number;
    voltage?: number;
    wan_tx_bytes?: number;
    wan_rx_bytes?: number;
    wan_tx_bps?: number;
    wan_rx_bps?: number;
    total_disk?: number;
    free_disk?: number;
}

export interface InterfaceData {
    id?: string;
    ".id"?: string;
    name: string;
    type: string;
    disabled?: boolean | string;
    running?: boolean | string;
    "mac-address"?: string;
    "rx-byte"?: number;
    "tx-byte"?: number;
    uptime?: string;
    comment?: string;
}

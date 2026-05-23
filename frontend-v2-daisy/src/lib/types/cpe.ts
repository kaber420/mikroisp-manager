export interface CPE {
    id?: string;
    ".id"?: string;
    name: string;
    host: string;
    comment?: string;
    disabled?: boolean | string;
    running?: boolean | string;
    last_status?: string;
    signal?: number;
    "mac-address"?: string;
    address?: string;
}

export interface CPEStats {
    total_cpes: number;
    active: number;
    offline: number;
}

export interface CPEGlobalInfo {
    cpe_mac: string;
    cpe_hostname?: string | null;
    ip_address?: string | null;
    signal?: number | null;
    signal_chain0?: number | null;
    signal_chain1?: number | null;
    noisefloor?: number | null;
    dl_capacity?: number | null;
    ul_capacity?: number | null;
    throughput_rx_kbps?: number | null;
    throughput_tx_kbps?: number | null;
    total_rx_bytes?: number | null;
    total_tx_bytes?: number | null;
    cpe_uptime?: number | null;
    eth_plugged?: boolean | null;
    eth_speed?: number | null;
    ssid?: string | null;
    band?: string | null;
    ap_host?: string | null;
    ap_hostname?: string | null;
    status?: string | null;  // 'active', 'offline', 'disabled'
    is_enabled?: boolean | null;
}

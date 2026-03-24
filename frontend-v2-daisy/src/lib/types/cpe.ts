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

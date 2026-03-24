export interface Zona {
    id: number;
    nombre: string;
    descripcion?: string;
    parent_id?: number | null;
}

export interface ZonaCreate {
    nombre: string;
    descripcion?: string;
    parent_id?: number | null;
}

export interface ZonaUpdate {
    nombre?: string;
    descripcion?: string;
    parent_id?: number | null;
}

export interface ZonaDetail extends Zona {
    infraestructura_count?: number;
    clientes_count?: number;
    documentos: ZonaDocumento[];
    notes: ZonaNote[];
    rack_layout?: any;
    infraestructura?: ZonaInfra;
    direccion?: string;
    coordenadas_gps?: string;
}

export interface ZonaInfra {
    id: string;
    type: 'router' | 'switch' | 'ap';
    name: string;
    host: string;
    direccion_ip_gestion?: string | null;
    gateway_predeterminado?: string | null;
    servidores_dns?: string | null;
    vlans_utilizadas?: string | null;
    equipos_criticos?: string | null;
    proximo_mantenimiento?: string | null;
}

export interface ZonaNote {
    id: string;
    title: string;
    content: string;
    is_encrypted: boolean;
    created_at: string;
    updated_at: string;
    author: string;
}

export interface ZonaNoteCreate {
    title: string;
    content: string | null;
    is_encrypted: boolean;
}

export interface ZonaDocumento {
    id: string;
    filename: string;
    nombre_original: string;
    tipo: 'pdf' | 'imagen' | 'otro';
    url: string;
    creado_en: string;
    descripcion?: string;
}

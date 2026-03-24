export interface Plan {
    id: string;
    nombre: string;
    precio: number;
    velocidad_bajada: number; // en Mbps
    velocidad_subida: number;   // en Mbps
    descripcion?: string;
    is_active: boolean;
}

export interface PlanCreate {
    nombre: string;
    precio: number;
    velocidad_bajada: number;
    velocidad_subida: number;
    descripcion?: string;
}

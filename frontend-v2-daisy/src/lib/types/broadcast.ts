export interface BroadcastMessage {
    id: string;
    title: string;
    content: string;
    type: 'info' | 'warning' | 'critical';
    target_zone_ids?: number[];
    is_active: boolean;
    created_at: string;
}

export type BroadcastTargetType = "clients" | "technicians";

export interface BroadcastRequest {
    message: string;
    target_type: BroadcastTargetType;
    image_url?: string | null;
    local_image_path?: string | null;
    zone_ids?: number[];
    staff_roles?: string[];
}


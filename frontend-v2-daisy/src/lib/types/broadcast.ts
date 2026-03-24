export interface BroadcastMessage {
    id: string;
    title: string;
    content: string;
    type: 'info' | 'warning' | 'critical';
    target_zone_ids?: number[];
    is_active: boolean;
    created_at: string;
}

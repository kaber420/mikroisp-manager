export interface PortalAnnouncement {
    id: string;
    title: string;
    content: string;
    priority: 'low' | 'normal' | 'high';
    is_published: boolean;
    publish_at?: string;
}

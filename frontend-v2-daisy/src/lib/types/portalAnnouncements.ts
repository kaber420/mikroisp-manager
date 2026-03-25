export interface PortalAnnouncement {
    id: string;
    title: string;
    content: string;
    image_url: string | null;
    type: 'info' | 'promotion' | 'critical' | 'offer' | 'notice' | 'holiday' | 'alert';
    priority: number;
    start_date: string;
    end_date: string | null;
    is_active: boolean;
    created_at?: string;
}

export interface PortalAnnouncementCreate {
    title: string;
    content: string;
    image_url?: string | null;
    type?: string;
    priority?: number;
    start_date?: string;
    end_date?: string | null;
    is_active?: boolean;
}

export interface PortalAnnouncementUpdate extends Partial<PortalAnnouncementCreate> {}

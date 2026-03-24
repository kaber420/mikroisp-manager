export type TicketStatus = 'open' | 'pending' | 'resolved' | 'closed';
export type TicketPriority = 'low' | 'normal' | 'high' | 'urgent';
export type TicketType = 'support' | 'installation';

export interface Ticket {
    id: string;
    ticket_id?: number;
    client_id: string;
    client_name?: string;
    assigned_tech_id?: string;
    assigned_tech_username?: string;
    subject: string;
    description: string;
    status: TicketStatus;
    priority: TicketPriority;
    ticket_type: TicketType;
    created_at: string;
    updated_at: string;
    scheduled_at?: string | null;
    coordinates?: string | null;
    address_notes?: string | null;
    messages: TicketMessage[];
}

export interface TicketMessage {
    id: string;
    ticket_id: string;
    sender_id: string;
    sender_name: string;
    sender_type: 'tech' | 'client' | 'system';
    content: string;
    media_url?: string;
    created_at: string;
}

export interface TicketCreate {
    client_id: string;
    subject: string;
    description: string;
    priority: TicketPriority;
    ticket_type: TicketType;
    scheduled_at?: string | null;
    coordinates?: string | null;
    address_notes?: string | null;
}

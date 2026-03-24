export interface User {
    id: string;
    username: string;
    email: string;
    role: 'admin' | 'tecnico' | 'cobranza';
    full_name: string;
    is_active: boolean;
    is_superuser: boolean;
    telegram_chat_id: string;
    receive_alerts: boolean;
    receive_device_down_alerts: boolean;
    receive_announcements: boolean;
}

export interface UserCreate {
    username: string;
    email: string;
    password?: string;
    role: string;
    full_name: string;
    is_active: boolean;
    telegram_chat_id: string | null;
    receive_alerts: boolean;
    receive_device_down_alerts: boolean;
    receive_announcements: boolean;
}

export interface UserUpdate extends Partial<UserCreate> {
    password?: string;
}

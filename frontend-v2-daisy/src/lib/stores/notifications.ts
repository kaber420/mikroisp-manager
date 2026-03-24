import { writable } from 'svelte/store';

export type NotificationType = 'success' | 'error' | 'info' | 'warning';

export interface Notification {
    id: number;
    message: string;
    type: NotificationType;
}

function createNotificationStore() {
    const { subscribe, update } = writable<Notification[]>([]);

    function add(message: string, type: NotificationType = 'info') {
        const id = Date.now();
        update(n => [...n, { id, message, type }]);
        setTimeout(() => {
            update(n => n.filter(item => item.id !== id));
        }, 5000);
    }

    return {
        subscribe,
        success: (msg: string) => add(msg, 'success'),
        error: (msg: string) => add(msg, 'error'),
        info: (msg: string) => add(msg, 'info'),
        warning: (msg: string) => add(msg, 'warning')
    };
}

export const notify = createNotificationStore();

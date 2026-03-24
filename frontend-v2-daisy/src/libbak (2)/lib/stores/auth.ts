import { writable } from 'svelte/store';

export interface User {
    id: string;
    username: string;
    email?: string;
    role?: string;
    is_active?: boolean;
}

export const user = writable<User | null>(null);
export const isAuthenticated = writable<boolean>(false);
export type SessionStatus = 'idle' | 'active' | 'warning' | 'error';
export const sessionState = writable<SessionStatus>('active');

export function setUser(userData: User | null) {
    user.set(userData);
    isAuthenticated.set(!!userData);
}

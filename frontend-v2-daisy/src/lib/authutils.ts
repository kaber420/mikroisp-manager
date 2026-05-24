import { setUser, sessionState } from './stores/auth';
import { securityApi } from './api';

export async function initSession(pathname: string) {
    // 1. Intentar recuperar del localStorage para carga inmediata
    const savedUser = localStorage.getItem('user');
    if (!savedUser) {
        // No hay sesión en el navegador, redirigir inmediatamente
        clearSession();
        window.location.href = '/login';
        return;
    }

    try {
        setUser(JSON.parse(savedUser));
    } catch (e) {
        console.error("Failed to parse user session", e);
        clearSession();
        window.location.href = '/login';
        return;
    }

    // 2. Validar con el backend en segundo plano (silencioso)
    try {
        const userData = await securityApi.getMe();
        setUser(userData);
        sessionState.set('active');
        localStorage.setItem('user', JSON.stringify(userData));
    } catch (err: any) {
        // Si el backend dice que no hay sesión, limpiar todo y redirigir
        if (err.response?.status === 401) {
            sessionState.set('error');
            clearSession();
            window.location.href = '/login';
        }
    }
}

export function clearSession() {
    localStorage.removeItem('user');
    setUser(null);
}

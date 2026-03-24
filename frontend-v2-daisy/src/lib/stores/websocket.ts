import { writable } from 'svelte/store';
import { browser } from '$app/environment';

export const serverConnected = writable(false);

let socket: WebSocket | null = null;
let reconnectTimer: any = null;

function getCookie(name: string) {
    if (!browser) return undefined;
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop()?.split(';').shift();
    return undefined;
}

export function connect() {
    if (!browser || socket) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    
    // El backend real tiene el endpoint en /ws/dashboard (visto en main.py)
    const url = `${protocol}//${host}/ws/dashboard`;
    
    socket = new WebSocket(url);

    socket.onopen = () => {
        console.log("WebSocket connected to /ws/dashboard channel");
        serverConnected.set(true);
        if (reconnectTimer) {
            clearInterval(reconnectTimer);
            reconnectTimer = null;
        }
    };

    socket.onclose = (event) => {
        console.log(`WebSocket closed: code=${event.code}, reason=${event.reason}`);
        serverConnected.set(false);
        socket = null;
        // Attempt reconnect every 5 seconds
        if (!reconnectTimer) {
            reconnectTimer = setInterval(connect, 5000);
        }
    };

    socket.onerror = (error) => {
        console.error("WebSocket error:", error);
        serverConnected.set(false);
    };
}

export function disconnect() {
    if (reconnectTimer) {
        clearInterval(reconnectTimer);
        reconnectTimer = null;
    }
    if (socket) {
        socket.close();
        socket = null;
    }
    serverConnected.set(false);
}

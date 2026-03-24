import { writable } from 'svelte/store';
import { browser } from '$app/environment';

function createTheme() {
    const { subscribe, set, update } = writable({
        current: 'light',
        lavaLampActive: true
    });

    return {
        subscribe,
        init: () => {
            if (!browser) return;
            const savedTheme = localStorage.getItem('theme') || 'light';
            const savedLava = localStorage.getItem('lavaLamp') !== 'false';
            
            set({
                current: savedTheme,
                lavaLampActive: savedLava
            });
            
            document.documentElement.setAttribute('data-theme', savedTheme);
        },
        toggle: () => {
            update(t => {
                const next = t.current === 'light' ? 'dark' : 'light';
                localStorage.setItem('theme', next);
                document.documentElement.setAttribute('data-theme', next);
                return { ...t, current: next };
            });
        },
        setTheme: (themeName: string) => {
            localStorage.setItem('theme', themeName);
            document.documentElement.setAttribute('data-theme', themeName);
            update(t => ({ ...t, current: themeName }));
        },
        toggleLavaLamp: () => {
            update(t => {
                const next = !t.lavaLampActive;
                localStorage.setItem('lavaLamp', String(next));
                return { ...t, lavaLampActive: next };
            });
        }
    };
}

export const theme = createTheme();

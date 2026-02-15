/**
 * AppearanceSettings.js
 * Alpine.js component for theme selection (client-side only, no API)
 */

document.addEventListener('alpine:init', () => {
    Alpine.data('appearanceSettings', () => ({
        currentTheme: localStorage.getItem('umanager-theme') || 'classic',

        setTheme(theme) {
            const allowed = ['classic', 'modern'];
            if (!allowed.includes(theme)) return;

            this.currentTheme = theme;
            localStorage.setItem('umanager-theme', theme);

            if (theme === 'modern') {
                document.body.classList.add('theme-modern');
            } else {
                document.body.classList.remove('theme-modern');
            }
        }
    }));
});

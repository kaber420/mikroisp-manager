const plugin = require('tailwindcss/plugin');

/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: "class",
    content: [
        "./templates/**/*.html",
        "./static/js/**/*.js",
    ],
    theme: {
        extend: {
            fontFamily: {
                sans: ["Inter", "sans-serif"],
            },
            colors: {
                // Bridge: clases legacy → tokens semánticos DaisyUI
                'surface-1': 'oklch(var(--b2) / <alpha-value>)',
                'surface-2': 'oklch(var(--b3) / <alpha-value>)',
                'surface-3': 'oklch(var(--n) / <alpha-value>)',
                'background': 'oklch(var(--b1) / <alpha-value>)',
                'text-primary': 'oklch(var(--bc) / <alpha-value>)',
                'text-secondary': 'oklch(var(--bc) / 0.6)',
                'border-color': 'oklch(var(--bc) / 0.1)',
                'danger': 'oklch(var(--er) / <alpha-value>)',
            },
        },
    },
    plugins: [
        require('daisyui'),

        // Componentes custom de la app (garantiza inclusión en output)
        plugin(function ({ addComponents }) {
            addComponents({
                /* Data Table */
                '.data-table': {
                    width: '100%',
                    fontSize: '0.875rem',
                    textAlign: 'left',
                    borderCollapse: 'collapse',
                },
                '.data-table thead': {
                    backgroundColor: 'oklch(var(--b3))',
                },
                '.data-table th': {
                    padding: '0.75rem 1rem',
                    fontWeight: '600',
                    color: 'oklch(var(--bc) / 0.7)',
                    fontSize: '0.75rem',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                },
                '.data-table td': {
                    padding: '0.75rem 1rem',
                    borderBottom: '1px solid oklch(var(--bc) / 0.05)',
                },
                '.data-table tbody tr:hover': {
                    backgroundColor: 'oklch(var(--b3) / 0.5)',
                },
                /* Progress bar */
                '.progress-bar': {
                    width: '100%',
                    height: '0.5rem',
                    backgroundColor: 'oklch(var(--b3))',
                    borderRadius: '9999px',
                    overflow: 'hidden',
                },
                '.progress-value': {
                    height: '100%',
                    backgroundColor: 'oklch(var(--p))',
                    borderRadius: '9999px',
                    transition: 'width 0.3s ease',
                },
            });
        }),
    ],
    daisyui: {
        themes: ["dark", "light", "dracula", "cyberpunk", "cupcake", "dim"]
    }
}

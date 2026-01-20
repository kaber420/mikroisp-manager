/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: "class",
    content: [
        "./templates/**/*.html",
        "./static/js/**/*.js",
    ],
    theme: {
        extend: {
            colors: {
                primary: { DEFAULT: '#3B82F6', hover: '#2563EB' },
                background: '#0A0A0A',
                'surface-1': '#1E293B',
                'surface-2': '#334155',
                'text-primary': '#F1F5F9',
                'text-secondary': '#94A3B8',
                'border-color': '#334155',
                success: '#22C55E',
                danger: '#EF4444',
                warning: '#EAB308',
                orange: '#F97316',
            },
            fontFamily: {
                sans: ["Inter", "sans-serif"],
            },
        },
    },
    plugins: [],
}

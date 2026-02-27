import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig, loadEnv } from 'vite';
import path from 'path';

export default defineConfig(({ mode }) => {
    const envDir = path.resolve(process.cwd(), '..');
    const env = loadEnv(mode, envDir, '');
    const port = env.UVICORN_PORT || '7777';
    const backendUrl = `http://localhost:${port}`;

    return {
        plugins: [tailwindcss(), sveltekit()],
        server: {
            proxy: {
                '/api': {
                    target: backendUrl,
                    changeOrigin: true,
                    // Sin esto las cookies del backend no llegan al browser
                    cookieDomainRewrite: 'localhost',
                },
                '/auth': {
                    target: backendUrl,
                    changeOrigin: true,
                    cookieDomainRewrite: 'localhost',
                },
                '/ws': {
                    target: backendUrl.replace('http', 'ws'),
                    ws: true,
                    changeOrigin: true,
                }
            }
        },
        define: {
            '__BACKEND_URL__': JSON.stringify(backendUrl)
        }
    };
});

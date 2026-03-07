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
            host: true, // Allow connections from network IPs
            proxy: {
                '/api': {
                    target: backendUrl,
                    changeOrigin: true,
                    ws: true,
                    // Sin esto las cookies del backend no llegan al browser
                    cookieDomainRewrite: 'localhost',
                    configure: (proxy: any, options: any) => {
                        proxy.on('proxyReq', (proxyReq: any, req: any, res: any) => {
                            if (req.headers.origin) {
                                proxyReq.setHeader('Origin', req.headers.origin);
                            }
                            if (req.headers.referer) {
                                proxyReq.setHeader('Referer', req.headers.referer);
                            }
                        });
                    }
                },
                '/auth': {
                    target: backendUrl,
                    changeOrigin: true,
                    cookieDomainRewrite: 'localhost',
                    configure: (proxy: any, options: any) => {
                        proxy.on('proxyReq', (proxyReq: any, req: any, res: any) => {
                            if (req.headers.origin) {
                                proxyReq.setHeader('Origin', req.headers.origin);
                            }
                            if (req.headers.referer) {
                                proxyReq.setHeader('Referer', req.headers.referer);
                            }
                        });
                    }
                },
                '/users': {
                    target: backendUrl,
                    changeOrigin: true,
                    cookieDomainRewrite: 'localhost',
                    configure: (proxy: any, options: any) => {
                        proxy.on('proxyReq', (proxyReq: any, req: any, res: any) => {
                            if (req.headers.origin) {
                                proxyReq.setHeader('Origin', req.headers.origin);
                            }
                            if (req.headers.referer) {
                                proxyReq.setHeader('Referer', req.headers.referer);
                            }
                        });
                    }
                },
                '/ws': {
                    target: backendUrl.replace('http', 'ws'),
                    ws: true,
                    changeOrigin: true,
                },
                '/setup': {
                    target: backendUrl,
                    changeOrigin: true,
                    cookieDomainRewrite: 'localhost',
                    configure: (proxy: any, options: any) => {
                        proxy.on('proxyReq', (proxyReq: any, req: any, res: any) => {
                            if (req.headers.origin) {
                                proxyReq.setHeader('Origin', req.headers.origin);
                            }
                            if (req.headers.referer) {
                                proxyReq.setHeader('Referer', req.headers.referer);
                            }
                        });
                    }
                }
            }
        },
        define: {
            '__BACKEND_URL__': JSON.stringify(backendUrl)
        }
    };
});

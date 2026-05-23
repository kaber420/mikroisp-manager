import adapter from '@sveltejs/adapter-static';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	kit: {
		// adapter-static genera archivos HTML/JS/CSS puros en build/
		// que FastAPI puede servir directamente sin un servidor Node.
		// fallback: 'index.html' es necesario para modo SPA (client-side routing).
		adapter: adapter({
			pages: 'build',
			assets: 'build',
			fallback: 'index.html',
			precompress: true,
			strict: false
		}),
		prerender: {
			entries: ['*'],
			handleHttpError: 'warn',
			handleMissingId: 'warn',
			handleUnseenRoutes: 'ignore'
		}
	}
};

export default config;

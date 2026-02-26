import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';
import fs from 'fs';
import path from 'path';

// Helper to load .env from parent directory
function loadPythonEnv() {
	const envPath = path.resolve(__dirname, '../.env');
	const env = {};
	if (fs.existsSync(envPath)) {
		const content = fs.readFileSync(envPath, 'utf8');
		content.split('\n').forEach(line => {
			const match = line.match(/^([^#=]+)=(.*)$/);
			if (match) {
				let val = match[2].trim();
				if (val.startsWith('"') && val.endsWith('"')) { val = val.slice(1, -1); }
				env[match[1].trim()] = val;
			}
		});
	}
	return env;
}

const pyEnv = loadPythonEnv();
const uvicornPort = pyEnv.UVICORN_PORT || '7777';
// Use standard loopback 127.0.0.1 (not 127.0.0.0, which is invalid to bind/connect)
const uvicornUrl = `http://127.0.0.1:${uvicornPort}`;

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	server: {
		host: '0.0.0.0', // Listen on all network interfaces
		port: 5173,
		proxy: {
			'/api': uvicornUrl,
			'/auth': uvicornUrl
		}
	}
});

import fs from 'fs';
import path from 'path';

export function loadPythonEnv() {
    const envPath = path.resolve('../.env');
    const env = {};
    if (fs.existsSync(envPath)) {
        const content = fs.readFileSync(envPath, 'utf8');
        content.split('\n').forEach(line => {
            const match = line.match(/^([^#=]+)=(.*)$/);
            if (match) {
                let val = match[2].trim();
                // strip quotes
                if (val.startsWith('"') && val.endsWith('"')) {
                   val = val.slice(1, -1);
                }
                env[match[1].trim()] = val;
            }
        });
    }
    return env;
}

#!/bin/bash
set -e

# Cambiar al directorio raíz si no estamos ahí
cd "$(dirname "$0")/.."

echo "⚙️ Compilando Frontend SvelteKit..."
cd frontend-v2-daisy
pnpm install
pnpm build
cd ..

echo "🐳 Compilando imágenes Docker..."
docker build -t omniwisp-frontend:latest -f frontend-v2-daisy/Dockerfile.frontend ./frontend-v2-daisy
docker build -t omniwisp-backend:latest -f Dockerfile.backend .

echo "✅ Compilación de imágenes finalizada con éxito."

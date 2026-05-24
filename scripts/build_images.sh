#!/bin/bash
# Salir si ocurre algún error
set -e

# Configuración (Reemplaza con tu usuario de Docker Hub si deseas)
DOCKER_USER="tu_usuario_dockerhub"

# Solicitar versión si no se pasa como argumento
if [ -z "$1" ]; then
    read -p "🏷️  Ingresa la versión de la imagen (ej: v1.0.0): " VERSION
else
    VERSION=$1
fi

echo "=========================================================="
echo "📦 GENERANDO IMÁGENES OMNIWISP PRO ($VERSION)"
echo "=========================================================="

# 1. Compilar Frontend localmente
echo "⚙️  Compilando Frontend localmente con pnpm..."
cd frontend-v2-daisy
pnpm build
cd ..

# 2. Generar imagen del Frontend
echo "🖥️  Generando imagen Docker del Frontend..."
docker build -t $DOCKER_USER/omniwisp-frontend:$VERSION -f frontend-v2-daisy/Dockerfile.frontend ./frontend-v2-daisy
docker tag $DOCKER_USER/omniwisp-frontend:$VERSION $DOCKER_USER/omniwisp-frontend:latest

# 3. Generar imagen del Backend
echo "⚡ Generando imagen Docker del Backend..."
docker build -t $DOCKER_USER/omniwisp-backend:$VERSION -f Dockerfile.backend .
docker tag $DOCKER_USER/omniwisp-backend:$VERSION $DOCKER_USER/omniwisp-backend:latest

echo "=========================================================="
echo "🎉 ¡IMÁGENES GENERADAS CON ÉXITO!"
echo "----------------------------------------------------------"
echo " Backend:  $DOCKER_USER/omniwisp-backend:$VERSION"
echo " Frontend: $DOCKER_USER/omniwisp-frontend:$VERSION"
echo "=========================================================="
echo "👉 Para subirlas a Docker Hub:"
echo "   docker login"
echo "   docker push $DOCKER_USER/omniwisp-backend:$VERSION"
echo "   docker push $DOCKER_USER/omniwisp-backend:latest"
echo "   docker push $DOCKER_USER/omniwisp-frontend:$VERSION"
echo "   docker push $DOCKER_USER/omniwisp-frontend:latest"
echo "=========================================================="

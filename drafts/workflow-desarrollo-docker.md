# 🐳 Guía de Workflow: Desarrollo Local, Pruebas en Docker y Generación de Imágenes

Esta guía establece un flujo de trabajo sencillo y directo para OmniWISP Pro. Sin configuraciones complejas: desarrollas en local para máxima velocidad, pruebas en Docker compartiendo las carpetas del host, y ejecutas un script simple para compilar tus imágenes cuando estén listas.

---

## 🛠️ 1. Desarrollo Diario en Local (Nativo)

Para programar con la mayor velocidad, ejecuta la aplicación nativamente en tu máquina local.

1. **Levantar bases de datos y servicios en Docker**:
   Levanta únicamente Postgres, Redict y Livekit en segundo plano para dar soporte a tu app:
   ```bash
   docker compose up -d postgres redict livekit
   ```

2. **Ejecutar el Backend**:
   Activa tu entorno virtual de Python y arranca FastAPI:
   ```bash
   source .venv/bin/activate
   uvicorn app.main:app --host 127.0.0.1 --port 7777 --reload
   ```

3. **Ejecutar el Frontend**:
   Arranca el entorno de desarrollo de SvelteKit/Vite:
   ```bash
   cd frontend-v2-daisy
   pnpm dev
   ```
   *Vite se conecta automáticamente a tu backend local redirigiendo las llamadas de `/api` y `/ws` al puerto 7777.*

---

## 🐳 2. Pruebas Rápidas en Docker (Compartiendo Carpetas)

Cuando quieras verificar que todo corre bien dentro de un contenedor Docker, no necesitas reconstruir la imagen cada vez que hagas un cambio. Simplemente **compartimos las carpetas locales** con los contenedores.

### Backend (FastAPI)
Tu `docker-compose.yml` ya tiene esto configurado compartiendo la carpeta raíz actual:
```yaml
backend:
  # ...
  volumes:
    - .:/app
```
Esto monta tu código del host en el contenedor, permitiendo que `uvicorn` detecte y aplique tus cambios al instante dentro de Docker.

### Frontend (Nginx)
Para probar el frontend en Docker sin reconstruir la imagen del contenedor cada vez que edites el código, solo comparte la carpeta `build/` generada localmente:

1. Agrega el volumen al servicio `frontend` en tu `docker-compose.yml`:
   ```yaml
   frontend:
     image: nginx:alpine
     ports:
       - "80:80"
     volumes:
       - ./frontend-v2-daisy/build:/usr/share/nginx/html
       - ./frontend-v2-daisy/nginx.conf:/etc/nginx/conf.d/default.conf
   ```

2. Ahora, cuando hagas un cambio en tu frontend, simplemente compílalo localmente:
   ```bash
   cd frontend-v2-daisy && pnpm build && cd ..
   ```
   El contenedor de Nginx servirá los nuevos archivos estáticos inmediatamente gracias a la carpeta compartida, sin necesidad de reconstruir la imagen Docker.

3. Para levantar todo el stack de prueba compartiendo carpetas:
   ```bash
   docker compose up
   ```

---

## 🚀 3. Script para Generar Imágenes de Producción

Cuando consideres que todo funciona perfectamente y desees generar las imágenes del Backend y Frontend listas para subir a Docker Hub, utilizaremos este script simple.

### Script: `scripts/build_images.sh`

Este script compila el frontend localmente y construye ambas imágenes Docker utilizando tus Dockerfiles existentes:

```bash
#!/bin/bash
# Salir si ocurre algún error
set -e

# Configuración (Reemplaza con tu usuario de Docker Hub)
DOCKER_USER="tu_usuario_dockerhub"

# Solicitar versión
if [ -z "$1" ]; then
    read -p "🏷️  Ingresa la versión de la imagen (ej: v1.0.0): " VERSION
else
    VERSION=$1
fi

echo "=========================================================="
echo "📦 GENERANDO IMÁGENES OMNIWISP PRO ($VERSION)"
echo "=========================================================="

# 1. Compilar Frontend localmente
echo "⚙️  Compilando Frontend localmente..."
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
```

---

Con esto tienes el flujo de trabajo más simple y directo posible: programas en local, compartes las carpetas con Docker para probar de forma rápida, y ejecutas el script para generar las imágenes listas para Docker Hub.

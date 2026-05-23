#!/bin/bash
# scripts/install.sh - Instalador silencioso y no interactivo para el host

set -e

# Asegurar que estamos en el directorio raíz del proyecto
cd "$(dirname "$0")/.."

echo "📡 Iniciando instalador de OmniWISP Pro..."

# 1. Verificar requisitos previos del sistema
echo "🔍 Verificando dependencias del sistema..."

if ! [ -x "$(command -v docker)" ]; then
    echo "❌ Error: Docker no está instalado en este sistema. Por favor, instálelo y vuelva a ejecutar." >&2
    exit 1
else
    echo "✅ Docker está instalado."
fi

if ! docker compose version >/dev/null 2>&1; then
    echo "❌ Error: La CLI de 'docker compose' (V2) no está disponible. Por favor, instálela y vuelva a ejecutar." >&2
    exit 1
else
    echo "✅ Docker Compose está listo."
fi

# 2. Pre-crear directorios persistentes en el host para evitar problemas de permisos
echo "📁 Preparando estructura de directorios en el host..."
mkdir -p data logs backups data/db data/uploads

# Asegurar que el usuario actual es dueño de las carpetas
chmod -R 775 data logs backups

# 3. Inicializar entorno virtual de Python (.venv) en el host para el Launcher
echo "🐍 Configurando entorno virtual de Python para el Launcher..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "✅ Entorno virtual .venv creado."
else
    echo "✅ Entorno virtual .venv ya existente."
fi

# Activar entorno virtual
source .venv/bin/activate

# Instalar dependencias requeridas para el launcher
echo "📦 Instalando dependencias de Python del Launcher..."
pip install --upgrade pip
pip install -r requirements.txt

echo "🚀 [Instalación Finalizada] OmniWISP está listo para ejecutarse."
echo "👉 Use 'python launcher.py' para arrancar el Launcher TUI guiado."

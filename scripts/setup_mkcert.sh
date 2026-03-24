#!/bin/bash
# scripts/setup_mkcert.sh
# Automates the installation of mkcert on Linux (Debian/Ubuntu/CentOS/Fedora)
# Requires sudo privileges.

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🔧 Iniciando instalación de mkcert...${NC}"

# 1. Detect OS and install dependencies
if [ -f /etc/debian_version ]; then
    echo "Sujeto: Debian/Ubuntu detects. Installing libnss3-tools..."
    sudo apt-get update -qq
    sudo apt-get install -y -qq libnss3-tools curl
elif [ -f /etc/redhat-release ]; then
    echo "Sujeto: RHEL/CentOS/Fedora detected. Installing nss-tools..."
    sudo dnf install -y -q nss-tools curl
else
    echo -e "${YELLOW}SO no detectado automáticamente. Asegúrate de tener nss-tools instalado.${NC}"
fi

# 2. Download mkcert binary
MKCERT_VERSION="v1.4.4" # Latest stable as of writing
ARCH="amd64"
if [[ "$(uname -m)" == "aarch64" ]]; then
    ARCH="arm64"
fi

echo -e "Descargando mkcert ${MKCERT_VERSION} para ${ARCH}..."
URL="https://github.com/FiloSottile/mkcert/releases/download/${MKCERT_VERSION}/mkcert-${MKCERT_VERSION}-linux-${ARCH}"

# Download to a temporary file
TMP_BIN="/tmp/mkcert_bin"
curl -L "$URL" -o "$TMP_BIN"

# 3. Install binary
echo "Instalando binario en /usr/local/bin/mkcert..."
sudo mv "$TMP_BIN" /usr/local/bin/mkcert
sudo chmod +x /usr/local/bin/mkcert

# 4. Run mkcert install
echo -e "${GREEN}Configurando la CA local (mkcert -install)...${NC}"
mkcert -install

echo -e "\n${GREEN}🎉 mkcert instalado y configurado correctamente!${NC}"
echo "Ahora puedes ejecutar 'python launcher.py setup' para habilitar HTTPS."

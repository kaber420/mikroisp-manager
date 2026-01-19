#!/bin/bash
# scripts/apply_caddy_config.sh
# Applies the locally generated Caddyfile and certificates to the system Caddy service.
# Requires sudo.

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SOURCE_CADDYFILE="$PROJECT_ROOT/Caddyfile"
TARGET_CADDYFILE="/etc/caddy/Caddyfile"

echo -e "${GREEN}🔧 Applying Caddy Configuration...${NC}"

# 1. Install Caddy if missing
if ! command -v caddy &> /dev/null; then
    echo "Installing Caddy..."
    if [ -f /etc/debian_version ]; then
        sudo apt-get update -qq
        sudo apt-get install -y -qq debian-keyring debian-archive-keyring apt-transport-https curl
        curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg 2>/dev/null || true
        curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list > /dev/null
        sudo apt-get update -qq
        sudo apt-get install -y -qq caddy
    elif [ -f /etc/redhat-release ]; then
        sudo dnf install -y -q 'dnf-command(copr)'
        sudo dnf copr enable -y @caddy/caddy
        sudo dnf install -y -q caddy
    else
        echo -e "${RED}Unsupported OS for automatic install. Please install Caddy manually.${NC}"
        exit 1
    fi
    sudo systemctl enable caddy
fi

# 2. Copy Caddyfile
if [ ! -f "$SOURCE_CADDYFILE" ]; then
    echo -e "${RED}Error: Source Caddyfile not found at $SOURCE_CADDYFILE${NC}"
    exit 1
fi

echo "Copying Caddyfile to $TARGET_CADDYFILE..."
sudo cp "$SOURCE_CADDYFILE" "$TARGET_CADDYFILE"

# 3. Grant Permissions for Certificates
# Launcher generates certs in data/certs. Caddy needs to read them.
# We will add the 'caddy' user to the current user's group, or use setfacl.
# Simplest robust approach: grant read access to the specific cert files.

APP_USER=$(stat -c '%U' "$SOURCE_CADDYFILE")
DATA_CERTS="$PROJECT_ROOT/data/certs"

if [ -d "$DATA_CERTS" ]; then
    echo "Configuring certificate permissions..."
    # Ensure caddy can traverse to the certs. 
    # This is tricky if parent dirs are 700.
    # Alternative: Copy certs to /etc/caddy/certs/
    
    TARGET_CERTS_DIR="/etc/caddy/certs"
    sudo mkdir -p "$TARGET_CERTS_DIR"
    sudo cp "$DATA_CERTS"/*.pem "$TARGET_CERTS_DIR/" 2>/dev/null || true
    sudo chown -R caddy:caddy "$TARGET_CERTS_DIR"
    sudo chmod 600 "$TARGET_CERTS_DIR"/*
    
    # Update Caddyfile to point to new cert location? 
    # The source Caddyfile has absolute paths to user dir.
    # We should probably sed replace them.
    
    sudo sed -i "s|$DATA_CERTS|$TARGET_CERTS_DIR|g" "$TARGET_CADDYFILE"
    echo "Certificates copied to $TARGET_CERTS_DIR and Caddyfile updated."
fi

# 4. Restart Caddy
echo "Restarting Caddy..."
if sudo systemctl restart caddy; then
    echo -e "${GREEN}✅ Caddy restarted successfully!${NC}"
else
    echo -e "${RED}❌ Caddy failed to restart. Check logs: sudo journalctl -u caddy -e${NC}"
    exit 1
fi

#!/bin/bash
# scripts/apply_caddy_config.sh
# Applies the locally generated Caddyfile and certificates to the system Caddy service.
# Uses ACLs to allow Caddy to read certificates directly from the project directory.
# Requires sudo.

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SOURCE_CADDYFILE="$PROJECT_ROOT/Caddyfile"
TARGET_CADDYFILE="/etc/caddy/Caddyfile"
DATA_CERTS="$PROJECT_ROOT/data/certs"

echo -e "${GREEN}🔧 Applying Caddy Configuration (ACL Mode)...${NC}"

# 1. Install Caddy if missing
if ! command -v caddy &> /dev/null; then
    echo "Installing Caddy..."
    if [ -f /etc/debian_version ]; then
        sudo apt-get update -qq
        sudo apt-get install -y -qq debian-keyring debian-archive-keyring apt-transport-https curl acl
        curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg 2>/dev/null || true
        curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list > /dev/null
        sudo apt-get update -qq
        sudo apt-get install -y -qq caddy
    elif [ -f /etc/redhat-release ]; then
        sudo dnf install -y -q 'dnf-command(copr)' acl
        sudo dnf copr enable -y @caddy/caddy
        sudo dnf install -y -q caddy
    else
        echo -e "${RED}Unsupported OS for automatic install. Please install Caddy manually.${NC}"
        exit 1
    fi
    sudo systemctl enable caddy
fi

# 2. Ensure ACL tools are installed
if ! command -v setfacl &> /dev/null; then
    echo -e "${YELLOW}Installing ACL tools...${NC}"
    if [ -f /etc/debian_version ]; then
        sudo apt-get install -y -qq acl
    elif [ -f /etc/redhat-release ]; then
        sudo dnf install -y -q acl
    fi
fi

# 3. Ensure Caddy can bind to privileged ports (80/443)
CADDY_BIN=$(which caddy)
if [ -n "$CADDY_BIN" ]; then
    CURRENT_CAP=$(getcap "$CADDY_BIN" 2>/dev/null || echo "")
    if [[ ! "$CURRENT_CAP" =~ "cap_net_bind_service" ]]; then
        echo -e "${YELLOW}Granting Caddy permission to bind to privileged ports...${NC}"
        sudo setcap 'cap_net_bind_service=+ep' "$CADDY_BIN"
    fi
fi

# 4. Copy Caddyfile (without modifying paths - they point to project directory)
if [ ! -f "$SOURCE_CADDYFILE" ]; then
    echo -e "${RED}Error: Source Caddyfile not found at $SOURCE_CADDYFILE${NC}"
    exit 1
fi

echo "Copying Caddyfile to $TARGET_CADDYFILE..."
sudo cp "$SOURCE_CADDYFILE" "$TARGET_CADDYFILE"

# 5. Grant Caddy access via ACLs (traverse directories + read certs)
echo "Configuring ACL permissions for Caddy..."

# Build the path hierarchy from root to data/certs
# We need to grant execute (+x) permission on each parent directory
PATH_TO_TRAVERSE="$PROJECT_ROOT/data/certs"
CURRENT_PATH=""

# Traverse each component of the path
IFS='/' read -ra PATH_PARTS <<< "$PATH_TO_TRAVERSE"
for part in "${PATH_PARTS[@]}"; do
    if [ -n "$part" ]; then
        CURRENT_PATH="$CURRENT_PATH/$part"
        if [ -d "$CURRENT_PATH" ]; then
            sudo setfacl -m u:caddy:x "$CURRENT_PATH" 2>/dev/null || {
                echo -e "${YELLOW}Warning: Could not set ACL on $CURRENT_PATH${NC}"
            }
        fi
    fi
done

# Grant read access to certificate files
if [ -d "$DATA_CERTS" ]; then
    for cert_file in "$DATA_CERTS"/*.pem; do
        if [ -f "$cert_file" ]; then
            sudo setfacl -m u:caddy:r "$cert_file" 2>/dev/null || {
                echo -e "${YELLOW}Warning: Could not set ACL on $cert_file${NC}"
            }
        fi
    done
    echo -e "${GREEN}✅ ACL permissions configured for certificates in $DATA_CERTS${NC}"
else
    echo -e "${YELLOW}⚠️  Certificate directory not found: $DATA_CERTS${NC}"
    echo "   Certificates will be created when you run the launcher."
fi

# 6. Validate Caddyfile
echo "Validating Caddyfile..."
if sudo caddy validate --config "$TARGET_CADDYFILE" 2>/dev/null; then
    echo -e "${GREEN}✅ Caddyfile is valid${NC}"
else
    echo -e "${RED}❌ Caddyfile validation failed. Check syntax.${NC}"
    exit 1
fi

# 7. Restart Caddy
echo "Restarting Caddy..."
if sudo systemctl restart caddy; then
    echo -e "${GREEN}✅ Caddy restarted successfully!${NC}"
else
    echo -e "${RED}❌ Caddy failed to restart. Check logs: sudo journalctl -u caddy -e${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}🎉 Caddy configuration applied successfully!${NC}"
echo "   - Caddyfile: $TARGET_CADDYFILE"
echo "   - Certificates read from: $DATA_CERTS"
echo ""
echo "   To verify: sudo systemctl status caddy"

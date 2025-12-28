#!/bin/bash
# =============================================================================
# µMonitor Pro - Instalador de Proxy Inverso (Caddy + mDNS)
# =============================================================================
# Uso: sudo bash install_proxy.sh
# =============================================================================

set -e

# --- Colores ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# --- Variables por defecto ---
DEFAULT_HOSTNAME="umonitor"
DEFAULT_APP_PORT="7777"
DEFAULT_HTTP_PORT="80"
DEFAULT_HTTPS_PORT="443"
CADDYFILE_PATH="/etc/caddy/Caddyfile"
SSL_DIR="/etc/ssl/umonitor"

# Detectar directorio de la app (donde está el .env)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$APP_DIR/.env"

# --- Funciones de utilidad ---
print_header() {
    echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "Este script debe ejecutarse como root (sudo)"
        echo "Uso: sudo bash $0"
        exit 1
    fi
}

detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$ID
        OS_VERSION=$VERSION_ID
    else
        print_error "No se pudo detectar el sistema operativo"
        exit 1
    fi
    
    case $OS in
        ubuntu|debian|linuxmint|pop)
            PKG_MANAGER="apt"
            ;;
        fedora|centos|rhel|rocky|almalinux)
            PKG_MANAGER="dnf"
            ;;
        arch|manjaro)
            PKG_MANAGER="pacman"
            ;;
        *)
            print_error "Sistema operativo no soportado: $OS"
            exit 1
            ;;
    esac
    
    print_info "Sistema detectado: $OS $OS_VERSION (usando $PKG_MANAGER)"
}

get_local_ip() {
    # Obtener IP local principal
    LOCAL_IP=$(hostname -I | awk '{print $1}')
    echo "$LOCAL_IP"
}

# --- Instaladores ---
install_caddy() {
    print_info "Instalando Caddy..."
    
    case $PKG_MANAGER in
        apt)
            apt-get update -qq
            apt-get install -y -qq debian-keyring debian-archive-keyring apt-transport-https curl
            curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg 2>/dev/null || true
            curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list > /dev/null
            apt-get update -qq
            apt-get install -y -qq caddy
            ;;
        dnf)
            dnf install -y -q 'dnf-command(copr)'
            dnf copr enable -y @caddy/caddy
            dnf install -y -q caddy
            ;;
        pacman)
            pacman -Sy --noconfirm caddy
            ;;
    esac
    
    systemctl enable caddy
    print_success "Caddy instalado correctamente"
}

install_avahi() {
    print_info "Instalando Avahi (mDNS para dominios .local)..."
    
    case $PKG_MANAGER in
        apt)
            apt-get install -y -qq avahi-daemon libnss-mdns
            ;;
        dnf)
            dnf install -y -q avahi avahi-tools nss-mdns
            ;;
        pacman)
            pacman -Sy --noconfirm avahi nss-mdns
            ;;
    esac
    
    systemctl enable avahi-daemon
    systemctl start avahi-daemon
    print_success "Avahi instalado y activo"
}

install_mkcert() {
    print_info "Instalando mkcert para certificados locales..."
    
    case $PKG_MANAGER in
        apt)
            apt-get install -y -qq libnss3-tools
            ;;
        dnf)
            dnf install -y -q nss-tools
            ;;
        pacman)
            pacman -Sy --noconfirm nss
            ;;
    esac
    
    # Descargar mkcert
    MKCERT_VERSION="v1.4.4"
    ARCH=$(uname -m)
    case $ARCH in
        x86_64) MKCERT_ARCH="amd64" ;;
        aarch64) MKCERT_ARCH="arm64" ;;
        armv7l) MKCERT_ARCH="arm" ;;
        *) print_error "Arquitectura no soportada: $ARCH"; exit 1 ;;
    esac
    
    curl -sL "https://github.com/FiloSottile/mkcert/releases/download/${MKCERT_VERSION}/mkcert-${MKCERT_VERSION}-linux-${MKCERT_ARCH}" -o /usr/local/bin/mkcert
    chmod +x /usr/local/bin/mkcert
    
    print_success "mkcert instalado"
}

# --- Configuradores ---
configure_hostname() {
    local new_hostname=$1
    
    print_info "Configurando hostname: $new_hostname"
    
    hostnamectl set-hostname "$new_hostname"
    
    # Actualizar /etc/hosts
    if ! grep -q "$new_hostname" /etc/hosts; then
        echo "127.0.1.1   $new_hostname $new_hostname.local" >> /etc/hosts
    fi
    
    # Reiniciar Avahi para que detecte el nuevo nombre
    systemctl restart avahi-daemon
    
    print_success "Hostname configurado: $new_hostname.local"
}

generate_self_signed_cert() {
    local hostname=$1
    
    print_info "Generando certificado auto-firmado..."
    
    mkdir -p "$SSL_DIR"
    
    # Incluir IP local y hostname en el certificado (SAN)
    LOCAL_IP=$(get_local_ip)
    
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$SSL_DIR/server.key" \
        -out "$SSL_DIR/server.crt" \
        -subj "/CN=$hostname.local/O=uMonitor Pro/C=US" \
        -addext "subjectAltName=DNS:$hostname.local,DNS:localhost,IP:127.0.0.1,IP:$LOCAL_IP" \
        2>/dev/null
    
    # IMPORTANTE: Cambiar propietario a caddy para que pueda leer los certificados
    chown caddy:caddy "$SSL_DIR/server.key" "$SSL_DIR/server.crt"
    chmod 600 "$SSL_DIR/server.key"
    chmod 644 "$SSL_DIR/server.crt"
    
    print_success "Certificado generado en $SSL_DIR/"
    print_warning "Los navegadores mostrarán advertencia 'No seguro'"
}

generate_mkcert_cert() {
    local hostname=$1
    
    print_info "Generando certificado con mkcert..."
    
    mkdir -p "$SSL_DIR"
    
    # Instalar CA de mkcert
    mkcert -install 2>/dev/null
    
    # Generar certificado
    cd "$SSL_DIR"
    mkcert "$hostname.local" localhost 127.0.0.1 $(get_local_ip) 2>/dev/null
    
    # Renombrar archivos
    mv "$hostname.local+3.pem" server.crt
    mv "$hostname.local+3-key.pem" server.key
    
    # IMPORTANTE: Cambiar propietario a caddy para que pueda leer los certificados
    chown caddy:caddy server.key server.crt
    chmod 600 server.key
    chmod 644 server.crt
    
    print_success "Certificado mkcert generado"
    
    # Mostrar ubicación del CA
    CA_ROOT=$(mkcert -CAROOT)
    print_info "CA raíz ubicada en: $CA_ROOT"
    echo ""
    echo -e "${YELLOW}Para que otros dispositivos confíen en los certificados:${NC}"
    echo "1. Copia el archivo: $CA_ROOT/rootCA.pem"
    echo "2. Instálalo como 'Autoridad de Certificación' en cada dispositivo"
}

create_caddyfile() {
    local hostname=$1
    local app_port=$2
    local ssl_type=$3
    
    print_info "Creando configuración de Caddy..."
    
    # Backup si existe
    if [[ -f "$CADDYFILE_PATH" ]]; then
        cp "$CADDYFILE_PATH" "$CADDYFILE_PATH.backup.$(date +%Y%m%d%H%M%S)"
    fi
    
    case $ssl_type in
        "none")
            cat > "$CADDYFILE_PATH" << EOF
# µMonitor Pro - Configuración Caddy (HTTP)
# Generado automáticamente por install_proxy.sh

:${DEFAULT_HTTP_PORT} {
    reverse_proxy localhost:${app_port}
    
    # Headers de seguridad
    header {
        X-Content-Type-Options nosniff
        X-Frame-Options DENY
        Referrer-Policy strict-origin-when-cross-origin
    }
    
    # Logs
    log {
        output file /var/log/caddy/umonitor.log
        format console
    }
}
EOF
            ;;
        "self-signed"|"mkcert")
            cat > "$CADDYFILE_PATH" << EOF
# µMonitor Pro - Configuración Caddy (HTTPS con certificado local)
# Generado automáticamente por install_proxy.sh

{
    # Desactivar HTTPS automático (usamos certificados locales)
    auto_https off
}

:${DEFAULT_HTTP_PORT} {
    # Redirección HTTP → HTTPS
    redir https://{host}{uri} permanent
}

:${DEFAULT_HTTPS_PORT} {
    # Certificado local
    tls ${SSL_DIR}/server.crt ${SSL_DIR}/server.key
    
    reverse_proxy localhost:${app_port}
    
    # Headers de seguridad
    header {
        X-Content-Type-Options nosniff
        X-Frame-Options DENY
        Referrer-Policy strict-origin-when-cross-origin
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
    }
    
    # Logs
    log {
        output file /var/log/caddy/umonitor.log
        format console
    }
}
EOF
            ;;
        "letsencrypt")
            # Para Let's Encrypt necesitamos un dominio real
            cat > "$CADDYFILE_PATH" << EOF
# µMonitor Pro - Configuración Caddy (HTTPS con Let's Encrypt)
# Generado automáticamente por install_proxy.sh
# NOTA: Reemplaza TUDOMINIO.COM con tu dominio real

TUDOMINIO.COM {
    reverse_proxy localhost:${app_port}
    
    # Headers de seguridad
    header {
        X-Content-Type-Options nosniff
        X-Frame-Options DENY
        Referrer-Policy strict-origin-when-cross-origin
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
    }
    
    # Logs
    log {
        output file /var/log/caddy/umonitor.log
        format console
    }
}
EOF
            print_warning "Edita $CADDYFILE_PATH y reemplaza TUDOMINIO.COM"
            ;;
    esac
    
    # Crear directorio de logs
    mkdir -p /var/log/caddy
    chown caddy:caddy /var/log/caddy
    
    # Formatear Caddyfile para evitar warnings
    caddy fmt --overwrite "$CADDYFILE_PATH" 2>/dev/null || true
    
    print_success "Caddyfile creado en $CADDYFILE_PATH"
}

configure_firewall() {
    print_info "Configurando firewall..."
    
    if command -v ufw &> /dev/null; then
        ufw allow 80/tcp comment 'HTTP - Caddy'
        ufw allow 443/tcp comment 'HTTPS - Caddy'
        print_success "Reglas UFW añadidas (puertos 80, 443)"
    elif command -v firewall-cmd &> /dev/null; then
        firewall-cmd --permanent --add-service=http
        firewall-cmd --permanent --add-service=https
        firewall-cmd --reload
        print_success "Reglas firewalld añadidas"
    else
        print_warning "No se detectó firewall (ufw/firewalld)"
    fi
}

update_env_file() {
    local hostname=$1
    local app_port=$2
    
    print_info "Actualizando configuración de la aplicación (.env)..."
    
    # Verificar si existe el archivo .env
    if [[ ! -f "$ENV_FILE" ]]; then
        print_warning "No se encontró .env en $ENV_FILE - omitiendo actualización"
        return
    fi
    
    LOCAL_IP=$(get_local_ip)
    
    # Construir nuevos valores de ALLOWED_HOSTS y ALLOWED_ORIGINS
    NEW_HOSTS="$LOCAL_IP,$hostname.local,localhost,127.0.0.1,localhost:$app_port,127.0.0.1:$app_port,$LOCAL_IP:$app_port"
    NEW_ORIGINS="http://localhost:$app_port,http://127.0.0.1:$app_port,http://$LOCAL_IP:$app_port,https://localhost,https://127.0.0.1,https://$LOCAL_IP,https://$hostname.local"
    
    # Actualizar ALLOWED_HOSTS
    if grep -q "^ALLOWED_HOSTS=" "$ENV_FILE"; then
        sed -i "s|^ALLOWED_HOSTS=.*|ALLOWED_HOSTS=$NEW_HOSTS|" "$ENV_FILE"
    else
        echo "ALLOWED_HOSTS=$NEW_HOSTS" >> "$ENV_FILE"
    fi
    
    # Actualizar ALLOWED_ORIGINS
    if grep -q "^ALLOWED_ORIGINS=" "$ENV_FILE"; then
        sed -i "s|^ALLOWED_ORIGINS=.*|ALLOWED_ORIGINS=$NEW_ORIGINS|" "$ENV_FILE"
    else
        echo "ALLOWED_ORIGINS=$NEW_ORIGINS" >> "$ENV_FILE"
    fi
    
    # Cambiar a modo producción para que las cookies funcionen con HTTPS
    if grep -q "^APP_ENV=" "$ENV_FILE"; then
        sed -i "s|^APP_ENV=.*|APP_ENV=production|" "$ENV_FILE"
    else
        echo "APP_ENV=production" >> "$ENV_FILE"
    fi
    
    print_success "Archivo .env actualizado"
    print_info "ALLOWED_HOSTS: $NEW_HOSTS"
    print_info "APP_ENV: production (cookies seguras habilitadas)"
}

start_services() {
    print_info "Iniciando servicios..."
    
    systemctl restart caddy
    systemctl restart avahi-daemon
    
    # Verificar estado
    if systemctl is-active --quiet caddy; then
        print_success "Caddy está activo"
    else
        print_error "Caddy no pudo iniciar"
        systemctl status caddy --no-pager
    fi
    
    if systemctl is-active --quiet avahi-daemon; then
        print_success "Avahi está activo"
    else
        print_error "Avahi no pudo iniciar"
    fi
}

show_summary() {
    local hostname=$1
    local ssl_type=$2
    
    print_header "🎉 INSTALACIÓN COMPLETADA"
    
    LOCAL_IP=$(get_local_ip)
    
    echo -e "Tu servidor está accesible en:\n"
    
    case $ssl_type in
        "none")
            echo -e "  ${GREEN}➜ http://$hostname.local${NC}"
            echo -e "  ${GREEN}➜ http://$LOCAL_IP${NC}"
            ;;
        "self-signed"|"mkcert")
            echo -e "  ${GREEN}➜ https://$hostname.local${NC}"
            echo -e "  ${GREEN}➜ https://$LOCAL_IP${NC}"
            ;;
        "letsencrypt")
            echo -e "  ${GREEN}➜ https://TUDOMINIO.COM${NC} (edita el Caddyfile)"
            ;;
    esac
    
    echo ""
    echo -e "${CYAN}Comandos útiles:${NC}"
    echo "  Ver estado:    sudo systemctl status caddy"
    echo "  Ver logs:      sudo journalctl -u caddy -f"
    echo "  Editar config: sudo nano $CADDYFILE_PATH"
    echo "  Recargar:      sudo systemctl reload caddy"
    echo ""
    echo -e "${YELLOW}⚠️  IMPORTANTE: Reinicia tu aplicación para aplicar los cambios en .env${NC}"
    echo -e "  cd $APP_DIR && python launcher.py"
    echo ""
    
    if [[ "$ssl_type" == "mkcert" ]]; then
        CA_ROOT=$(mkcert -CAROOT 2>/dev/null || echo "/root/.local/share/mkcert")
        echo -e "${YELLOW}⚠️  Para que otros dispositivos confíen en el certificado:${NC}"
        echo "  Copia: $CA_ROOT/rootCA.pem"
        echo "  Instálalo como CA de confianza en cada dispositivo"
        echo ""
    fi
}

uninstall() {
    print_header "🗑️  DESINSTALACIÓN"
    
    read -p "¿Estás seguro de que quieres desinstalar? (s/N): " confirm
    if [[ "$confirm" != "s" && "$confirm" != "S" ]]; then
        echo "Cancelado."
        exit 0
    fi
    
    print_info "Deteniendo servicios..."
    systemctl stop caddy 2>/dev/null || true
    
    print_info "Desinstalando paquetes..."
    case $PKG_MANAGER in
        apt)
            apt-get remove -y caddy avahi-daemon libnss-mdns
            rm -f /etc/apt/sources.list.d/caddy-stable.list
            rm -f /usr/share/keyrings/caddy-stable-archive-keyring.gpg
            ;;
        dnf)
            dnf remove -y caddy avahi
            ;;
        pacman)
            pacman -Rs --noconfirm caddy avahi nss-mdns
            ;;
    esac
    
    print_info "Limpiando archivos..."
    rm -rf "$SSL_DIR"
    rm -f /usr/local/bin/mkcert
    rm -rf /var/log/caddy
    
    print_success "Desinstalación completada"
    print_info "El Caddyfile se conservó en $CADDYFILE_PATH.backup.*"
}

# --- Menú principal ---
show_menu() {
    print_header "µMonitor Pro - Instalador de Proxy Inverso"
    
    echo "Este script instalará y configurará:"
    echo "  • Caddy (proxy inverso moderno)"
    echo "  • Avahi (para dominios .local)"
    echo "  • Certificados SSL (opcional)"
    echo ""
    
    echo -e "${CYAN}Selecciona una opción:${NC}"
    echo ""
    echo "  1) Instalación completa (recomendado)"
    echo "  2) Solo instalar Caddy"
    echo "  3) Solo instalar Avahi (mDNS)"
    echo "  4) Solo generar certificados"
    echo "  5) Desinstalar todo"
    echo "  0) Salir"
    echo ""
    read -p "Opción [1]: " choice
    choice=${choice:-1}
    
    case $choice in
        1) full_install ;;
        2) install_caddy_only ;;
        3) install_avahi_only ;;
        4) generate_certs_only ;;
        5) uninstall ;;
        0) exit 0 ;;
        *) print_error "Opción inválida"; show_menu ;;
    esac
}

full_install() {
    print_header "INSTALACIÓN COMPLETA"
    
    # 1. Hostname
    echo ""
    read -p "Nombre del servidor (sin .local) [$DEFAULT_HOSTNAME]: " hostname
    hostname=${hostname:-$DEFAULT_HOSTNAME}
    
    # Validar hostname
    if [[ ! "$hostname" =~ ^[a-zA-Z][a-zA-Z0-9-]*$ ]]; then
        print_error "Hostname inválido. Solo letras, números y guiones."
        exit 1
    fi
    
    # 2. Puerto de la app
    echo ""
    read -p "Puerto de la aplicación web [$DEFAULT_APP_PORT]: " app_port
    app_port=${app_port:-$DEFAULT_APP_PORT}
    
    # 3. Tipo de SSL
    echo ""
    echo -e "${CYAN}Tipo de certificado SSL:${NC}"
    echo "  1) Sin SSL (HTTP) - Solo para pruebas locales"
    echo "  2) Auto-firmado - Advertencia en navegador"
    echo "  3) mkcert (CA local) - Sin advertencia si instalas CA"
    echo "  4) Let's Encrypt - Requiere dominio público"
    echo ""
    read -p "Opción [2]: " ssl_choice
    ssl_choice=${ssl_choice:-2}
    
    case $ssl_choice in
        1) ssl_type="none" ;;
        2) ssl_type="self-signed" ;;
        3) ssl_type="mkcert" ;;
        4) ssl_type="letsencrypt" ;;
        *) ssl_type="self-signed" ;;
    esac
    
    # 4. Confirmar
    echo ""
    echo -e "${YELLOW}━━━ Resumen de configuración ━━━${NC}"
    echo "  Hostname:    $hostname.local"
    echo "  Puerto app:  $app_port"
    echo "  SSL:         $ssl_type"
    echo "  IP local:    $(get_local_ip)"
    echo ""
    read -p "¿Continuar? (S/n): " confirm
    if [[ "$confirm" == "n" || "$confirm" == "N" ]]; then
        echo "Cancelado."
        exit 0
    fi
    
    # 5. Ejecutar instalación
    echo ""
    detect_os
    install_caddy
    install_avahi
    configure_hostname "$hostname"
    
    case $ssl_type in
        "self-signed")
            generate_self_signed_cert "$hostname"
            ;;
        "mkcert")
            install_mkcert
            generate_mkcert_cert "$hostname"
            ;;
    esac
    
    create_caddyfile "$hostname" "$app_port" "$ssl_type"
    configure_firewall
    update_env_file "$hostname" "$app_port"
    start_services
    show_summary "$hostname" "$ssl_type"
}

install_caddy_only() {
    detect_os
    install_caddy
    print_success "Caddy instalado. Configura manualmente: $CADDYFILE_PATH"
}

install_avahi_only() {
    detect_os
    install_avahi
    read -p "¿Cambiar hostname? (s/N): " change
    if [[ "$change" == "s" || "$change" == "S" ]]; then
        read -p "Nuevo hostname: " new_host
        configure_hostname "$new_host"
    fi
}

generate_certs_only() {
    read -p "Hostname (sin .local): " hostname
    echo ""
    echo "Tipo de certificado:"
    echo "  1) Auto-firmado"
    echo "  2) mkcert"
    read -p "Opción [1]: " choice
    
    detect_os
    
    if [[ "$choice" == "2" ]]; then
        install_mkcert
        generate_mkcert_cert "$hostname"
    else
        generate_self_signed_cert "$hostname"
    fi
}

# --- Entry Point ---
main() {
    check_root
    detect_os
    show_menu
}

main "$@"

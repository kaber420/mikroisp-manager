# launcher.py
import sys
import os
import getpass
import multiprocessing
import logging
import time
import uuid
import secrets
import sqlite3
from dotenv import load_dotenv
from cryptography.fernet import Fernet
import shutil
import subprocess
import socket

# --- Imports de la App ---
from passlib.context import CryptContext
from sqlmodel import Session, select
# Motor Síncrono
from app.db.engine_sync import sync_engine, create_sync_db_and_tables
from app.models.user import User
# Inicializador de tablas Legacy (Vital)
from app.db.init_db import setup_databases

# --- Constante ---
ENV_FILE = ".env"

# --- Configuración del logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [Launcher] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def get_lan_ip():
    """Detects the primary LAN IP (not localhost)."""
    try:
        # Connect to a public DNS (doesn't send data) to get the interface IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        # 1.1.1.1 is Cloudflare DNS, 80 is port (doesn't matter if unreachable)
        s.connect(('1.1.1.1', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def is_caddy_running():
    """Checks if Caddy service is active or process is running."""
    # Method 1: Check systemd service (Linux only)
    if shutil.which("systemctl"):
        try:
            res = subprocess.run(
                ["systemctl", "is-active", "--quiet", "caddy"], 
                capture_output=True
            )
            if res.returncode == 0:
                return True
        except Exception:
            pass

    # Method 2: Check process list (Cross-platform fallback)
    # Simple check if "caddy" is in process list
    try:
        # This is a rough check. For nicer matching import psutil if available,
        # but standard lib approach:
        # pgrep is distinct to linux/unix
        if shutil.which("pgrep"):
            res = subprocess.run(["pgrep", "-x", "caddy"], capture_output=True)
            if res.returncode == 0:
                return True
    except Exception:
        pass
    
    return False


def apply_caddy_config(silent: bool = False) -> bool:
    """
    Applies the Caddy configuration by running the apply_caddy_config.sh script.
    Uses ACLs to grant Caddy read access to certificates in the project directory.
    
    This only needs to run once after generating certificates - ACLs persist.
    
    Args:
        silent: If True, suppresses some output messages
    
    Returns:
        True if configuration was applied successfully, False otherwise
    """
    script_path = os.path.join(os.path.dirname(__file__), "scripts", "apply_caddy_config.sh")
    
    if not os.path.exists(script_path):
        if not silent:
            logging.warning(f"Caddy config script not found: {script_path}")
        return False
    
    if not sys.platform.startswith("linux"):
        if not silent:
            logging.info("Caddy auto-config only available on Linux")
        return False
    
    if not silent:
        print("\n🔧 Aplicando configuración de Caddy (ACLs)...")
    
    try:
        # Run with sudo - requires user to enter password
        result = subprocess.run(
            ["sudo", "bash", script_path],
            capture_output=False,
            text=True
        )
        
        if result.returncode == 0:
            if not silent:
                logging.info("Caddy configuration applied successfully")
            return True
        else:
            if not silent:
                logging.warning("Caddy configuration script returned non-zero exit code")
            return False
            
    except FileNotFoundError:
        if not silent:
            logging.error("sudo not found - cannot apply Caddy configuration")
        return False
    except Exception as e:
        if not silent:
            logging.error(f"Error applying Caddy configuration: {e}")
        return False


def generate_caddyfile(hosts: list, app_port: int, ssl_cert_path: str = "", ssl_key_path: str = ""):
    """
    Generate Caddyfile for the reverse proxy configuration.
    
    Args:
        hosts: List of hostnames/IPs to configure
        app_port: Backend application port
        ssl_cert_path: Path to SSL certificate (if SSL enabled)
        ssl_key_path: Path to SSL private key (if SSL enabled)
    """
    use_ssl = bool(ssl_cert_path and ssl_key_path)
    
    # Build the Caddyfile content
    lines = [
        "# µMonitor Pro - Caddyfile",
        "# Generado automáticamente por launcher.py",
        "{",
        "    admin off",
        "    auto_https off" if use_ssl else "    # HTTPS automático deshabilitado",
        "}",
        "",
    ]
    
    # Security block for uploads (force downloads, prevent script execution)
    uploads_security_block = """
    # Seguridad para uploads: forzar descarga y prevenir ejecución
    @uploads path /data/uploads/*
    header @uploads {
        Content-Disposition "attachment"
        X-Content-Type-Options "nosniff"
        Content-Type "application/octet-stream"
    }
"""
    
    if use_ssl:
        # HTTPS configuration
        lines.append("# Redirección HTTP → HTTPS")
        lines.append(":80 {")
        lines.append("    redir https://{host}{uri} permanent")
        lines.append("}")
        lines.append("")
        
        # HTTPS block for each host
        lines.append(":443 {")
        lines.append(f"    tls {ssl_cert_path} {ssl_key_path}")
        lines.append(f"    reverse_proxy localhost:{app_port}")
        lines.append("")
        lines.append("    # Headers de seguridad globales")
        lines.append("    header {")
        lines.append('        X-Content-Type-Options nosniff')
        lines.append('        X-Frame-Options DENY')
        lines.append('        Referrer-Policy strict-origin-when-cross-origin')
        lines.append('        Strict-Transport-Security "max-age=31536000; includeSubDomains"')
        lines.append("    }")
        lines.append(uploads_security_block)
        lines.append("}")
    else:
        # HTTP only configuration
        lines.append(":80 {")
        lines.append(f"    reverse_proxy localhost:{app_port}")
        lines.append("")
        lines.append("    # Headers de seguridad globales")
        lines.append("    header {")
        lines.append('        X-Content-Type-Options nosniff')
        lines.append('        X-Frame-Options DENY')
        lines.append('        Referrer-Policy strict-origin-when-cross-origin')
        lines.append("    }")
        lines.append(uploads_security_block)
        lines.append("}")
    
    # Write to project root
    caddyfile_path = os.path.join(os.path.dirname(__file__), "Caddyfile")
    try:
        with open(caddyfile_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        logging.info(f"Caddyfile generated: {caddyfile_path}")
        return True
    except IOError as e:
        logging.error(f"Failed to write Caddyfile: {e}")
        return False


def run_setup_wizard():
    """
    Asistente de configuración mejorado.
    
    Configura:
    - Puerto de la aplicación
    - Detección automática de IP LAN
    - Dominio personalizado (opcional)
    - HTTPS con certificados locales (opcional)
    - Generación de Caddyfile
    """
    logging.info(f"Configurando '{ENV_FILE}'...")
    print("\n" + "=" * 60)
    print("    💻 Configuración de µMonitor Pro")
    print("=" * 60)
    
    # Cargar valores previos si existen
    load_dotenv(ENV_FILE, encoding="utf-8")
    default_port = os.getenv("UVICORN_PORT", "7777")
    
    # 1. PREGUNTAR PUERTO
    print("\n📡 CONFIGURACIÓN DE RED")
    print("-" * 40)
    while True:
        port_input = input(f"¿En qué puerto deseas ejecutar la web? (Default: {default_port}): ").strip()
        if not port_input:
            port = int(default_port)
            break
        if port_input.isdigit() and 1024 <= int(port_input) <= 65535:
            port = int(port_input)
            break
        print("❌ Puerto inválido. Usa un número entre 1024 y 65535.")

    # 2. DETECCIÓN DE IP LAN
    lan_ip = get_lan_ip()
    print(f"ℹ️  IP Local detectada: {lan_ip}")
    
    # 3. DOMINIO PERSONALIZADO (opcional)
    custom_domain = input("🌐 Dominio personalizado (opcional, Enter para omitir): ").strip()
    
    # 4. CONSTRUIR LISTA DE HOSTS
    hosts = ["localhost", "127.0.0.1"]
    if lan_ip != "127.0.0.1":
        hosts.append(lan_ip)
    if custom_domain:
        hosts.append(custom_domain)
    
    # 5. BASE DE DATOS (Fija en data/db/)
    db_dir = os.path.join("data", "db")
    os.makedirs(db_dir, exist_ok=True)
    print(f"✓ Base de datos configurada en: data/db/inventory.sqlite")
    
    # 6. CONFIGURACIÓN SSL (opcional)
    print("\n🔒 CONFIGURACIÓN DE SEGURIDAD")
    print("-" * 40)
    use_ssl = False
    ssl_cert_path = ""
    ssl_key_path = ""
    
    use_ssl_input = input("¿Habilitar HTTPS con certificados locales? (s/N): ").strip().lower()
    if use_ssl_input in ['s', 'si', 'y', 'yes']:
        try:
            from app.services.pki_service import PKIService
            
            # Verificar que mkcert esté disponible
            if PKIService.verify_mkcert_available():
                print("⚙️  Configurando PKI...")
                
                # Sincronizar CA
                sync_result = PKIService.sync_ca_files()
                if sync_result.get("status") == "error":
                    print(f"⚠️  Advertencia: {sync_result.get('message')}")
                
                # Determinar host principal para el certificado
                primary_host = custom_domain if custom_domain else lan_ip
                
                # Generar certificados
                success, key_pem, cert_pem = PKIService.generate_full_cert_pair(primary_host)
                
                if success:
                    # Guardar certificados en data/certs
                    certs_dir = os.path.join("data", "certs")
                    os.makedirs(certs_dir, exist_ok=True)
                    
                    ssl_cert_path = os.path.join(certs_dir, f"{primary_host}.pem")
                    ssl_key_path = os.path.join(certs_dir, f"{primary_host}-key.pem")
                    
                    # Usar rutas absolutas para Caddy
                    abs_cert_path = os.path.abspath(ssl_cert_path)
                    abs_key_path = os.path.abspath(ssl_key_path)
                    
                    with open(ssl_cert_path, "w") as f:
                        f.write(cert_pem)
                    with open(ssl_key_path, "w") as f:
                        f.write(key_pem)
                    
                    print(f"✅ Certificados generados para {primary_host}")
                    use_ssl = True
                    ssl_cert_path = abs_cert_path
                    ssl_key_path = abs_key_path
                else:
                    print(f"⚠️  Error generando certificados: {cert_pem}")
                    print("   Continuando sin HTTPS...")
            else:
                print("⚠️  mkcert no está instalado. Ejecuta primero:")
                print("   sudo bash scripts/install_proxy.sh")
                print("   Continuando sin HTTPS...")
        except ImportError:
            print("⚠️  PKIService no disponible. Continuando sin HTTPS...")
        except Exception as e:
            print(f"⚠️  Error configurando SSL: {e}")
            print("   Continuando sin HTTPS...")
    
    # 7. GENERAR CADDYFILE (si SSL está habilitado)
    if use_ssl:
        if generate_caddyfile(hosts, port, ssl_cert_path, ssl_key_path):
            print("✅ Caddyfile generado.")
            
            # 7b. APLICAR CONFIGURACIÓN DE CADDY AUTOMÁTICAMENTE
            print("\n🔄 Configurando Caddy automáticamente...")
            print("   (Se aplicarán ACLs para que Caddy lea los certificados)")
            try:
                if apply_caddy_config(silent=False):
                    print("✅ Caddy configurado correctamente.")
                else:
                    print("⚠️  No se pudo configurar Caddy automáticamente.")
                    print("   Puedes hacerlo manualmente con: sudo ./scripts/apply_caddy_config.sh")
            except KeyboardInterrupt:
                print("\n⚠️  Configuración de Caddy cancelada.")
                print("   Puedes hacerlo manualmente después con: sudo ./scripts/apply_caddy_config.sh")
        else:
            print("⚠️  No se pudo generar el Caddyfile.")
    
    # 8. CONSTRUIR ALLOWED_HOSTS y ALLOWED_ORIGINS
    # ALLOWED_HOSTS: sin esquema, incluye puerto para acceso directo
    hosts_with_port = [f"{h}:{port}" for h in hosts]
    allowed_hosts = ",".join(hosts + hosts_with_port)
    
    # ALLOWED_ORIGINS: con esquema HTTP y HTTPS si aplica
    origins = [f"http://{h}:{port}" for h in hosts]
    if use_ssl:
        # Agregar orígenes HTTPS (puerto 443 por defecto)
        origins += [f"https://{h}" for h in hosts]
    allowed_origins = ",".join(origins)
    
    # 9. CLAVES (Generar solo si faltan)
    secret_key = os.getenv("SECRET_KEY") or secrets.token_hex(32)
    encrypt_key = os.getenv("ENCRYPTION_KEY") or Fernet.generate_key().decode()
    
    # 10. DETERMINAR ENTORNO
    app_env = "production" if use_ssl else "development"
    
    # 11. GUARDAR .env
    print("\n📝 GUARDANDO CONFIGURACIÓN")
    print("-" * 40)
    try:
        with open(ENV_FILE, "w", encoding="utf-8") as f:
            f.write(f"# Configuración de µMonitor Pro\n")
            f.write(f"UVICORN_PORT={port}\n")
            f.write(f"SECRET_KEY=\"{secret_key}\"\n")
            f.write(f"ENCRYPTION_KEY=\"{encrypt_key}\"\n")
            f.write(f"APP_ENV={app_env}\n")
            f.write(f"ALLOWED_ORIGINS={allowed_origins}\n")
            f.write(f"ALLOWED_HOSTS={allowed_hosts}\n")
            f.write(f"# Flutter Mobile App Development (set to true to enable)\n")
            f.write(f"FLUTTER_DEV=false\n")
        
        print(f"✅ Archivo .env guardado exitosamente")
        print(f"   Puerto: {port}")
        print(f"   Hosts permitidos: {', '.join(hosts)}")
        print(f"   HTTPS: {'Habilitado' if use_ssl else 'Deshabilitado'}")
        print(f"   Entorno: {app_env}\n")
        
    except IOError as e:
        print(f"❌ Error guardando .env: {e}")
        sys.exit(1)

def check_and_create_first_user():
    """
    Verifica/Crea el usuario admin (Compatible con SQLModel).
    """
    try:
        # 1. Crear tablas modernas
        create_sync_db_and_tables()
        # 2. Crear tablas legacy (Settings, etc.)
        setup_databases()
        
        with Session(sync_engine) as session:
            if session.exec(select(User)).first():
                logging.info("Sistema validado (Usuarios existentes).")
                return

            print("=" * 60)
            print("🔐 CREACIÓN DEL ADMINISTRADOR")
            print("=" * 60)
            
            username = input("👤 Usuario: ").strip()
            while not username: username = input("👤 Usuario: ").strip()
            
            email = input("📧 Email: ").strip()
            while not email: email = input("📧 Email: ").strip()
            
            while True:
                password = getpass.getpass("🔑 Contraseña: ")
                if len(password) >= 6:
                    if getpass.getpass("🔑 Confirmar: ") == password: break
                    print("❌ No coinciden.")
                else:
                    print("❌ Mínimo 6 caracteres.")

            hashed_password = pwd_context.hash(password)

            new_user = User(
                id=uuid.uuid4(),
                email=email,
                username=username,
                hashed_password=hashed_password,
                role="admin",
                is_active=True,
                is_superuser=True,
                is_verified=True
            )
            session.add(new_user)
            session.commit()
            print(f"\n✅ Administrador '{username}' creado exitosamente.\n")

    except Exception as e:
        logging.critical(f"Error inicializando BD: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def start_api_server():
    from uvicorn import Config, Server
    from app.main import app as fastapi_app
    
    # Recargar ENV por si cambió el puerto
    load_dotenv(ENV_FILE, override=True)
    
    host = os.getenv("UVICORN_HOST", "0.0.0.0")
    port = int(os.getenv("UVICORN_PORT", 7777))

    config = Config(
        app=fastapi_app, 
        host=host, 
        port=port, 
        log_level="info",
        server_header=False  # --- SEGURIDAD: No revelar 'server: uvicorn' ---
    )
    try:
        Server(config).run()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    # A. Si el usuario pide configurar O si no existe el archivo .env
    if "--config" in sys.argv or not os.path.exists(ENV_FILE):
        run_setup_wizard()
        # Si usamos el flag --config, salimos para que el usuario reinicie limpio si quiere
        if "--config" in sys.argv:
            print("Reinicia el launcher para aplicar los cambios.")
            sys.exit(0)

    # B. Cargar configuración
    load_dotenv(ENV_FILE)
    
    # C. Inicializar BD y Usuario
    check_and_create_first_user()

    # --- Verificación de HTTPS (Caddy) ---
    is_production = os.getenv("APP_ENV") == "production"
    caddy_active = is_caddy_running()
    
    # Si SSL está habilitado pero Caddy no está corriendo, mostrar advertencia
    if is_production and not caddy_active:
        print("\n⚠️  HTTPS configurado pero Caddy no está activo.")
        print("   Ejecuta: sudo systemctl start caddy")

    # D. Arrancar
    port = os.getenv("UVICORN_PORT", "7777")
    lan_ip = get_lan_ip()
    hostname = socket.gethostname()
    
    print("-" * 60)
    if is_production and caddy_active:
        print(f"🚀 µMonitor Pro (Modo Producción - HTTPS)")
        print(f"   🏠 Local:     https://{hostname}.local")
        print(f"   📡 Network:   https://{lan_ip}")
        print(f"   🔌 Management: http://localhost:{port}")
    else:
        print(f"🚀 µMonitor Pro (Modo Desarrollo/Local)")
        print(f"   🔌 Local:     http://localhost:{port}")
        print(f"   📡 Network:   http://{lan_ip}:{port}")
        print(f"   ⚠️  HTTPS no activo. Algunas funciones pueden limitarse.")
    
    print("-" * 60)
    print(f"ℹ️  Para reconfigurar puerto base: python launcher.py --config")
    print("-" * 60)
    
    
    from app.scheduler import run_scheduler
    
    p_api = multiprocessing.Process(target=start_api_server, name="API")
    p_scheduler = multiprocessing.Process(target=run_scheduler, name="Scheduler")

    try:
        p_api.start()
        time.sleep(2)
        p_scheduler.start()
        
        p_api.join()
        p_scheduler.join()
    except KeyboardInterrupt:
        print("\n🛑 Apagando...")
        for p in [p_api, p_scheduler]:
            if p.is_alive(): p.terminate()
        sys.exit(0)

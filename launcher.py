# launcher.py
import getpass
import logging
import multiprocessing
import os
import secrets
import shutil
import socket
import subprocess
import sys
import time
import uuid

from cryptography.fernet import Fernet
from dotenv import load_dotenv

# --- Imports de la App ---
from passlib.context import CryptContext
from sqlmodel import Session, select

# Motor Síncrono
from app.db.engine_sync import create_sync_db_and_tables, sync_engine

# Inicializador de tablas Legacy (Vital)
from app.db.init_db import setup_databases
from app.models.user import User

# --- Constante ---
ENV_FILE = ".env"

# --- Configuración del logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [Launcher] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def get_lan_ip():
    """Detects the primary LAN IP (not localhost)."""
    try:
        # Connect to a public DNS (doesn't send data) to get the interface IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        # 1.1.1.1 is Cloudflare DNS, 80 is port (doesn't matter if unreachable)
        s.connect(("1.1.1.1", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def is_caddy_running():
    """Checks if Caddy service is active or process is running."""
    # Method 1: Check systemd service (Linux only)
    if sys.platform.startswith("linux") and shutil.which("systemctl"):
        try:
            res = subprocess.run(
                ["systemctl", "is-active", "--quiet", "caddy"], capture_output=True
            )
            if res.returncode == 0:
                return True
        except Exception:
            pass

    # Method 2: Process list (Cross-platform)
    try:
        if sys.platform == "win32":
            # Windows: use tasklist
            res = subprocess.run(["tasklist", "/FI", "IMAGENAME eq caddy.exe"], capture_output=True, text=True)
            if "caddy.exe" in res.stdout:
                return True
        else:
            # POSIX: use pgrep
            if shutil.which("pgrep"):
                res = subprocess.run(["pgrep", "-x", "caddy"], capture_output=True)
                if res.returncode == 0:
                    return True
    except Exception:
        pass

    return False


def apply_caddy_config(silent: bool = False) -> bool:
    """
    Applies the Caddy configuration.
    
    Linux: Runs the apply_caddy_config.sh script (requires sudo).
    Windows: Validates the Caddyfile and instructs user (or reloads if running).
    """
    caddyfile_path = os.path.join(os.path.dirname(__file__), "Caddyfile")
    
    # --- Windows Implementation ---
    if sys.platform == "win32":
        if not shutil.which("caddy"):
            if not silent:
                logging.warning("Caddy executable not found in PATH.")
            return False

        # Validate
        try:
            val_res = subprocess.run(["caddy", "validate", "--config", caddyfile_path], capture_output=True, text=True)
            if val_res.returncode != 0:
                if not silent:
                    logging.error(f"Caddyfile validation failed: {val_res.stderr}")
                return False
        except Exception as e:
            if not silent:
                logging.error(f"Could not validate Caddyfile: {e}")
            return False

        if not silent:
            logging.info("Caddyfile validated successfully.")
            
        # If running, try to reload
        if is_caddy_running():
            try:
                subprocess.run(["caddy", "reload", "--config", caddyfile_path], capture_output=True)
                if not silent:
                    logging.info("Caddy configuration reloaded.")
                return True
            except Exception:
                pass
        
        return True

    # --- Linux Implementation ---
    script_path = os.path.join(os.path.dirname(__file__), "scripts", "apply_caddy_config.sh")

    if not os.path.exists(script_path):
        if not silent:
            logging.warning(f"Caddy config script not found: {script_path}")
        return False

    if not silent:
        print("\n🔧 Aplicando configuración de Caddy (ACLs)...")

    try:
        # Run with sudo - requires user to enter password
        result = subprocess.run(["sudo", "bash", script_path], capture_output=False, text=True)

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

    # CORS block for mobile app preflight requests
    cors_block = """
    # CORS: Handle preflight OPTIONS requests for mobile app
    @cors_preflight method OPTIONS
    handle @cors_preflight {
        header Access-Control-Allow-Origin "*"
        header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, PATCH, OPTIONS"
        header Access-Control-Allow-Headers "Authorization, Content-Type, Accept, Origin, X-Requested-With"
        header Access-Control-Allow-Credentials "true"
        header Access-Control-Max-Age "86400"
        respond "" 204
    }

    # CORS headers for all other requests (mobile app support)
    header {
        Access-Control-Allow-Origin "*"
        Access-Control-Allow-Credentials "true"
    }
"""

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
        lines.append(cors_block)  # CORS support for mobile app
        lines.append(f"    reverse_proxy localhost:{app_port}")
        lines.append("")
        lines.append("    # Headers de seguridad globales")
        lines.append("    header {")
        lines.append("        X-Content-Type-Options nosniff")
        lines.append("        X-Frame-Options DENY")
        lines.append("        Referrer-Policy strict-origin-when-cross-origin")
        lines.append('        Strict-Transport-Security "max-age=31536000; includeSubDomains"')
        lines.append("    }")
        lines.append(uploads_security_block)
        lines.append("}")
    else:
        # HTTP only configuration
        lines.append(":80 {")
        lines.append(cors_block)  # CORS support for mobile app
        lines.append(f"    reverse_proxy localhost:{app_port}")
        lines.append("")
        lines.append("    # Headers de seguridad globales")
        lines.append("    header {")
        lines.append("        X-Content-Type-Options nosniff")
        lines.append("        X-Frame-Options DENY")
        lines.append("        Referrer-Policy strict-origin-when-cross-origin")
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
    except OSError as e:
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
        port_input = input(
            f"¿En qué puerto deseas ejecutar la web? (Default: {default_port}): "
        ).strip()
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
    print("✓ Base de datos configurada en: data/db/inventory.sqlite")

    # 6. CONFIGURACIÓN SSL (opcional)
    print("\n🔒 CONFIGURACIÓN DE SEGURIDAD")
    print("-" * 40)
    use_ssl = False
    ssl_cert_path = ""
    ssl_key_path = ""

    use_ssl_input = input("¿Habilitar HTTPS con certificados locales? (s/N): ").strip().lower()
    if use_ssl_input in ["s", "si", "y", "yes"]:
        try:
            from app.services.pki_service import PKIService

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
                print("⚠️  mkcert no está instalado o no se encuentra en el PATH.")
                if sys.platform == "win32":
                    print("   En Windows, instálalo con: choco install mkcert")
                    print("   O descárgalo desde: https://github.com/FiloSottile/mkcert/releases")
                else:
                    print("   Asegúrate de tener 'mkcert' instalado.")
                print("   Continuando sin HTTPS...")
        except ImportError:
            print("⚠️  PKIService no disponible. Continuando sin HTTPS...")
        except Exception as e:
            print(f"⚠️  Error configurando SSL: {e}")
            print("   Continuando sin HTTPS...")

    # 7. CONFIGURACIÓN DE WORKERS (rendimiento)
    print("\n⚡ CONFIGURACIÓN DE RENDIMIENTO")
    print("-" * 40)
    cpu_count = multiprocessing.cpu_count()
    recommended_workers = min(cpu_count * 2, 8)  # 2 per core, max 8
    default_workers = os.getenv("UVICORN_WORKERS", str(recommended_workers))
    
    print(f"ℹ️  CPUs detectados: {cpu_count}")
    print(f"   Recomendación: {recommended_workers} workers (2 por CPU, máx 8)")
    print(f"   Para >500 clientes concurrentes, considera aumentar este valor.")
    
    while True:
        workers_input = input(
            f"¿Número de workers de Uvicorn? (Default: {default_workers}): "
        ).strip()
        if not workers_input:
            workers = int(default_workers)
            break
        if workers_input.isdigit() and 1 <= int(workers_input) <= 32:
            workers = int(workers_input)
            break
        print("❌ Valor inválido. Usa un número entre 1 y 32.")

    # 8. GENERAR CADDYFILE (si SSL está habilitado)
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
                if sys.platform == "win32":
                    print("   En Windows, ejecuta manualmente: caddy run (o caddy reload)")
                else:
                    print("   Puedes hacerlo manualmente con: sudo ./scripts/apply_caddy_config.sh")
            except KeyboardInterrupt:
                print("\n⚠️  Configuración de Caddy cancelada.")
                if sys.platform == "win32":
                    print("   Recuerda ejecutar Caddy manualmente.")
                else:
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
            f.write("# Configuración de µMonitor Pro\n")
            f.write(f"UVICORN_PORT={port}\n")
            f.write(f'SECRET_KEY="{secret_key}"\n')
            f.write(f'ENCRYPTION_KEY="{encrypt_key}"\n')
            f.write(f"APP_ENV={app_env}\n")
            f.write(f"ALLOWED_ORIGINS={allowed_origins}\n")
            f.write(f"ALLOWED_HOSTS={allowed_hosts}\n")
            f.write(f"UVICORN_WORKERS={workers}\n")
            f.write("# Flutter Mobile App Development (set to true to enable)\n")
            f.write("FLUTTER_DEV=false\n")

        print("✅ Archivo .env guardado exitosamente")
        print(f"   Puerto: {port}")
        print(f"   Hosts permitidos: {', '.join(hosts)}")
        print(f"   HTTPS: {'Habilitado' if use_ssl else 'Deshabilitado'}")
        print(f"   Entorno: {app_env}\n")

    except OSError as e:
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
            while not username:
                username = input("👤 Usuario: ").strip()

            email = input("📧 Email: ").strip()
            while not email:
                email = input("📧 Email: ").strip()

            while True:
                password = getpass.getpass("🔑 Contraseña: ")
                if len(password) >= 6:
                    if getpass.getpass("🔑 Confirmar: ") == password:
                        break
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
                is_verified=True,
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
    import uvicorn

    # Recargar ENV por si cambió el puerto
    load_dotenv(ENV_FILE, override=True)

    host = os.getenv("UVICORN_HOST", "0.0.0.0")
    port = int(os.getenv("UVICORN_PORT", 7777))
    workers = int(os.getenv("UVICORN_WORKERS", 4))

    try:
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            workers=workers,
            log_level="info",
            server_header=False,  # --- SEGURIDAD: No revelar 'server: uvicorn' ---
            proxy_headers=True,  # --- PROXY: Confiar en headers (X-Forwarded-For) de Caddy ---
            forwarded_allow_ips="*",  # --- PROXY: Permitir IPs de cualquier proxy (Caddy es local) ---
        )
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
        if sys.platform == "win32":
            print("   Abre una terminal como Administrador y ejecuta: caddy run")
        else:
            print("   Ejecuta: sudo systemctl start caddy")

    # D. Arrancar logic
    port = os.getenv("UVICORN_PORT", "7777")
    lan_ip = get_lan_ip()
    hostname = socket.gethostname()
    
    # Process management
    caddy_process = None

    # Auto-start Caddy if needed and possible
    if is_production and not caddy_active:
        import ctypes
        is_admin = False
        try:
            is_admin = os.getuid() == 0 if sys.platform != "win32" else ctypes.windll.shell32.IsUserAnAdmin() != 0
        except AttributeError:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0 if sys.platform == "win32" else False

        if is_admin:
            print("🚀 Iniciando Caddy (Administrator)...")
            try:
                # Assuming Caddyfile is in the same dir
                caddy_cmd = ["caddy", "run", "--config", "Caddyfile"]
                # Use subprocess.Popen to run in background
                caddy_process = subprocess.Popen(caddy_cmd)
                caddy_active = True
                print("✅ Caddy iniciado correctamente.")
            except FileNotFoundError:
                print("❌ No se encontró el ejecutable 'caddy' en el PATH.")
            except Exception as e:
                print(f"❌ Error al iniciar Caddy: {e}")
        else:
            print("\n⚠️  ADVERTENCIA: Caddy no está corriendo y no tienes permisos de Administrador.")
            print("   Para que el launcher inicie Caddy automáticamente (puertos 80/443),")
            print("   debes ejecutar este script como Administrador/Root.")
            print("   O ejecuta 'caddy run' manualmente en otra terminal con permisos.")

    # Leer workers para mostrar en banner
    workers = os.getenv("UVICORN_WORKERS", "4")
    
    print("-" * 60)
    if is_production and caddy_active:
        print("🚀 µMonitor Pro (Modo Producción - HTTPS)")
        print(f"   🏠 Local:     https://{hostname}.local")
        print(f"   📡 Network:   https://{lan_ip}")
        print(f"   🔌 Management: http://localhost:{port}")
        print(f"   ⚡ Workers:   {workers}")
    else:
        print("🚀 µMonitor Pro (Modo Desarrollo/Local)")
        print(f"   🔌 Local:     http://localhost:{port}")
        print(f"   📡 Network:   http://{lan_ip}:{port}")
        print(f"   ⚡ Workers:   {workers}")
        if is_production:
             print("   ⚠️  HTTPS habilitado pero Caddy no responde. La web no cargará segura.")
        else:
             print("   ⚠️  HTTPS no activo. Algunas funciones pueden limitarse.")

    print("-" * 60)
    print("ℹ️  Para reconfigurar puerto base: python launcher.py --config")
    print("-" * 60)

    from app.scheduler import run_scheduler

    # Scheduler corre en subprocess, uvicorn en main process (para soportar workers)
    p_scheduler = multiprocessing.Process(target=run_scheduler, name="Scheduler")

    def cleanup():
        print("\n🛑 Apagando...")
        if caddy_process:
            print("   Terminando Caddy...")
            caddy_process.terminate()
        if p_scheduler.is_alive():
            p_scheduler.terminate()
            p_scheduler.join(timeout=5)

    try:
        p_scheduler.start()
        time.sleep(1)
        
        # Uvicorn corre en el proceso principal para soportar múltiples workers
        start_api_server()

    except KeyboardInterrupt:
        cleanup()
        sys.exit(0)
    finally:
        cleanup()
        sys.exit(0)


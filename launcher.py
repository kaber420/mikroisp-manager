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


def run_setup_wizard():
    """
    Asistente simplificado: Solo pregunta lo importante (Puerto).
    """
    logging.info(f"Configurando '{ENV_FILE}'...")
    print("\n--- Configuración de µMonitor Pro ---")
    
    # Cargar valores previos si existen
    load_dotenv(ENV_FILE, encoding="utf-8")
    default_port = os.getenv("UVICORN_PORT", "7777")
    
    # 1. PREGUNTAR PUERTO
    while True:
        port_input = input(f"¿En qué puerto deseas ejecutar la web? (Default: {default_port}): ").strip()
        if not port_input:
            port = default_port
            break
        if port_input.isdigit() and 1024 <= int(port_input) <= 65535:
            port = port_input
            break
        print("❌ Puerto inválido. Usa un número entre 1024 y 65535.")

    # 2. BASE DE DATOS (Fija en data/db/)
    db_dir = os.path.join("data", "db")
    os.makedirs(db_dir, exist_ok=True)
    print(f"✓ Base de datos configurada en: data/db/inventory.sqlite")
    
    allowed_hosts = f"localhost:{port},127.0.0.1:{port}"
    # Generar orígenes permitidos automáticamente
    hosts_list = [h.strip() for h in allowed_hosts.split(",")]
    origins_list = [f"http://{h}" for h in hosts_list]
    allowed_origins = ",".join(origins_list)

    # 4. CLAVES (Generar solo si faltan)
    secret_key = os.getenv("SECRET_KEY") or secrets.token_hex(32)
    encrypt_key = os.getenv("ENCRYPTION_KEY") or Fernet.generate_key().decode()

    # Guardar archivo (sin INVENTORY_DB_FILE ya que está hardcodeado en el código)
    try:
        with open(ENV_FILE, "w", encoding="utf-8") as f:
            f.write(f"# Configuración de µMonitor Pro\n")
            f.write(f"UVICORN_PORT={port}\n")
            f.write(f"SECRET_KEY=\"{secret_key}\"\n")
            f.write(f"ENCRYPTION_KEY=\"{encrypt_key}\"\n")
            f.write(f"APP_ENV=development\n")
            f.write(f"ALLOWED_ORIGINS={allowed_origins}\n")
            f.write(f"ALLOWED_HOSTS={allowed_hosts}\n")
            f.write(f"# Flutter Mobile App Development (set to true to enable)\n")
            f.write(f"FLUTTER_DEV=false\n")
        
        print(f"✅ Configuración guardada. Puerto seleccionado: {port}\n")
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

    config = Config(app=fastapi_app, host=host, port=port, log_level="info")
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

    # --- NUEVO: Verificación de HTTPS (Caddy) ---
    is_production = os.getenv("APP_ENV") == "production"
    caddy_active = is_caddy_running()
    
    # Si estamos en Linux y no detectamos producción O Caddy apagado
    # ofrecemos instalar/configurar.
    if sys.platform.startswith("linux") and (not is_production or not caddy_active):
        print("\n" + "!"*60)
        print("⚠️  HTTPS / SSL no detectado o no configurado.")
        print("   Para una experiencia segura y accesible desde la red,")
        print("   se recomienda instalar el proxy inverso (Caddy).")
        print("!"*60 + "\n")
        
        # Evitar preguntar si se pasó flag --no-setup o similar, 
        # pero aquí preguntamos siempre si falta config.
        try:
            resp = input("¿Deseas instalar/configurar HTTPS ahora? (S/n): ").strip().lower()
        except KeyboardInterrupt:
            resp = "n"

        if resp in ["", "s", "si", "y", "yes"]:
            print("\n🔧 Lanzando asistente de instalación (requiere sudo)...")
            script_path = os.path.join("scripts", "install_proxy.sh")
            # Verificar existencia del script
            if os.path.exists(script_path):
                try:
                    # Llamamos a sudo bash scripts/install_proxy.sh
                    # Nota: Esto pedirá password de sudo al usuario en la terminal
                    ret = subprocess.call(["sudo", "bash", script_path])
                    if ret == 0:
                        print("\n✅ Instalación de proxy finalizada.")
                        # Recargamos .env por si cambió a production
                        load_dotenv(ENV_FILE, override=True)
                        is_production = os.getenv("APP_ENV") == "production"
                        caddy_active = True # Asumimos éxito
                    else:
                        print("\n❌ La instalación no se completó correctamente.")
                except Exception as e:
                    print(f"\n❌ Error ejecutando script: {e}")
            else:
                print(f"\n❌ No se encontró el script: {script_path}")
        else:
            print("ℹ️  Omitiendo configuración HTTPS. Puedes hacerlo luego con:")
            print("    sudo bash scripts/install_proxy.sh")

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

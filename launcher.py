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

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def run_setup_wizard():
    """
    Asistente simplificado: Solo pregunta lo importante (Puerto).
    """
    logging.info(f"Configurando '{ENV_FILE}'...")
    print("\n--- Configuración de µMonitor Pro ---")
    
    # Cargar valores previos si existen
    load_dotenv(ENV_FILE, encoding="utf-8")
    default_port = os.getenv("UVICORN_PORT", "8000")
    
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
    port = int(os.getenv("UVICORN_PORT", 8000))

    config = Config(app=fastapi_app, host=host, port=port, log_level="info")
    Server(config).run()

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

    # D. Arrancar
    port = os.getenv("UVICORN_PORT", "7777")
    print("-" * 50)
    print(f"🚀 µMonitor Pro arrancando en: http://localhost:{port}")
    print(f"ℹ️  Para cambiar el puerto, usa: python launcher.py --config")
    print("-" * 50)
    
    
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

import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # App General
    APP_ENV: str = "development"
    SECRET_KEY: Optional[str] = None
    ENCRYPTION_KEY: Optional[str] = None
    
    # CORS y Hosts
    ALLOWED_ORIGINS: str = "http://localhost:8000"
    ALLOWED_HOSTS: str = "localhost,127.0.0.1"
    
    # Server configuration
    UVICORN_PORT: int = 8000
    UVICORN_WORKERS: int = 1
    FLUTTER_DEV: bool = False

    # Base de Datos
    DATABASE_URL: Optional[str] = None
    DATABASE_URL_SYNC: Optional[str] = None
    DEGRADED_MODE: bool = False  # Indica si estamos en modo de emergencia por fallo de servicios
    IS_FORCED_SQLITE: bool = False # Indica si se forzó por flag explicitly


    def __init__(self, **kwargs):
        # Asegurar carga de .env antes de cualquier lógica que dependa de él
        from dotenv import load_dotenv
        load_dotenv(".env")
        
        super().__init__(**kwargs)
        
        # 0. Leer configuración de servicios gestionada por la UI (data/services.json)
        from app.utils.services_config import read_services_config
        srv = read_services_config()
        
        if srv.get("db"):
            db_conf = srv["db"]
            if db_conf.get("provider") == "postgres":
                host = db_conf.get('host', 'localhost')
                port = db_conf.get('port', 5432)
                user = db_conf.get('user', 'postgres')
                db = db_conf.get('database', 'umanager_db')
                password = db_conf.get("password", "")
                
                auth = f"{user}:{password}@" if password else f"{user}@"
                url_sync = f"postgresql+psycopg://{auth}{host}:{port}/{db}"
                url_async = f"postgresql+asyncpg://{auth}{host}:{port}/{db}"
                self.DATABASE_URL = url_async
                self.DATABASE_URL_SYNC = url_sync

        if srv.get("cache"):
            cache_conf = srv["cache"]
            self.CACHE_BACKEND = cache_conf.get("provider", "memory")
            if self.CACHE_BACKEND == "redict":
                cache_host = cache_conf.get('host', 'localhost')
                cache_port = cache_conf.get('port', 6379)
                auth = f":{cache_conf['password']}@" if cache_conf.get("password") else ""
                self.REDICT_URL = f"redis://{auth}{cache_host}:{cache_port}/{cache_conf.get('db', 0)}"

        if srv.get("livekit"):
            lk_conf = srv["livekit"]
            if lk_conf.get("url"):
                self.LIVEKIT_URL = lk_conf["url"]
            if lk_conf.get("api_key"):
                self.LIVEKIT_API_KEY = lk_conf["api_key"]
            if lk_conf.get("api_secret"):
                self.LIVEKIT_API_SECRET = lk_conf["api_secret"]

        # 1. Comprobar si se forzó SQLite por bandera de launcher (Highest priority)
        if os.getenv("FORCE_SQLITE") == "true":
            self.IS_FORCED_SQLITE = True
            self.DATABASE_URL = None # Forzar recalculo a SQLite
            self.DATABASE_URL_SYNC = None

        if not self.DATABASE_URL:
            # Default to SQLite in data/db/
            DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
            DATABASE_FILE = os.path.join(DATA_DIR, "db", "inventory.sqlite")
            os.makedirs(os.path.dirname(DATABASE_FILE), exist_ok=True)
            self.DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_FILE}"
            
        if not self.DATABASE_URL_SYNC:
            DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
            DATABASE_FILE = os.path.join(DATA_DIR, "db", "inventory.sqlite")
            os.makedirs(os.path.dirname(DATABASE_FILE), exist_ok=True)
            self.DATABASE_URL_SYNC = f"sqlite:///{DATABASE_FILE}"

        # 2. Comprobar si se forzó Caché Local por bandera (Highest priority)
        if os.getenv("FORCE_LOCAL_CACHE") == "true":
            self.CACHE_BACKEND = "memory"


    # Caché y Redis
    CACHE_BACKEND: str = "memory"
    REDICT_URL: str = "redis://localhost:6379/0"

    # Monitoreo (APs, Routers, Switches)
    AP_MONITOR_UNSUBSCRIBE_TIMEOUT: int = 30
    MONITOR_UNSUBSCRIBE_TIMEOUT: int = 30
    ROUTER_HISTORY_INTERVAL: int = 300
    MONITOR_POLL_INTERVAL: float = 5.0
    SWITCH_MONITOR_UNSUBSCRIBE_TIMEOUT: int = 30
    SWITCH_HISTORY_INTERVAL: int = 300
    SWITCH_POLL_INTERVAL: float = 5.0

    # Bots Telegram
    CLIENT_BOT_TOKEN: Optional[str] = None
    TECH_BOT_TOKEN: Optional[str] = None
    MASTER_TECH_ID: str = "0"
    DATA_DIR: str = "data"

    # Admin Bootstrap
    ADMIN_EMAIL: Optional[str] = None
    ADMIN_PASSWORD: Optional[str] = None
    ADMIN_USERNAME: str = "admin"

    # LiveKit
    LIVEKIT_API_KEY: Optional[str] = None
    LIVEKIT_API_SECRET: Optional[str] = None
    LIVEKIT_URL: str = "ws://localhost:7880"

    def get_allowed_origins(self) -> list[str]:
        """
        Calcula dinámicamente la lista de orígenes permitidos para CORS y WebSockets.
        Incluye orígenes de configuración, puertos de desarrollo y detección de IP local.
        """
        import socket
        
        # 1. Orígenes base desde .env
        origins = self.ALLOWED_ORIGINS.split(",")
        
        # 2. Orígenes de desarrollo fijos
        dev_ports = [5173, 5174, 5175, 5176]
        for port in dev_ports:
            origins.append(f"http://localhost:{port}")
            origins.append(f"http://127.0.0.1:{port}")
            
        if self.FLUTTER_DEV:
            origins.append("http://localhost:33000")
            
        # 3. Detección dinámica de IP local (LAN)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                for port in dev_ports:
                    origins.append(f"http://{local_ip}:{port}")
                # También permitir el puerto de la aplicación en la IP local
                origins.append(f"http://{local_ip}:{self.UVICORN_PORT}")
        except Exception:
            pass
            
        # 4. Orígenes seguros adicionales
        origins.extend(["https://localhost", "https://127.0.0.1"])
        
        # Limpiar duplicados y normalizar
        return list(set(o.rstrip("/") for o in origins if o))

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
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

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

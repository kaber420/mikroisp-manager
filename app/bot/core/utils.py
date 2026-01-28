# app/bot/core/utils.py
import os
import logging
from sqlmodel import select, Session
from app.db.engine_sync import sync_engine as engine
from app.models.client import Client

logger = logging.getLogger(__name__)

def get_client_by_telegram_id(telegram_id: str):
    """
    Busca un cliente en la base de datos usando su ID de Telegram.
    """
    try:
        with Session(engine) as session:
            statement = select(Client).where(Client.telegram_contact == str(telegram_id))
            return session.exec(statement).first()
    except Exception as e:
        logger.error(f"Error en get_client_by_telegram_id: {e}")
        return None

def get_server_port() -> str:
    """
    Deduce el puerto del servidor API.
    """
    port = os.getenv("UVICORN_PORT")
    if port:
        return port

    try:
        # Intento de lectura de .env si no está en ENV
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        env_path = os.path.join(base_dir, ".env")
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    if line.strip().startswith("UVICORN_PORT="):
                        return line.split("=")[1].strip()
    except:
        pass

    return "8100"

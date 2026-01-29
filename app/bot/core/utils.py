# app/bot/core/utils.py
import os
import logging
import html
from sqlmodel import select, Session
from app.db.engine_sync import sync_engine as engine
from app.db.engine_sync import sync_engine as engine
from app.models.client import Client
from app.models.bot_user import BotUser
from datetime import datetime

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

def sanitize_input(text: str, max_length: int = 1000) -> str:
    """
    Sanitiza el texto de entrada del usuario:
    1. Trunca a max_length.
    2. Escapa caracteres HTML.
    3. Elimina espacios extra.
    """
    if not text:
        return ""
    
    # Truncate
    text = text[:max_length]
    
    # Escape HTML
    text = html.escape(text)
    
    return text.strip()
    return text.strip()

def get_bot_setting(key: str, default: str) -> str:
    """
    Obtiene un valor de configuracion del bot desde la DB (Sync).
    Retorna default si no existe o hay error.
    """
    try:
        from app.models.setting import Setting
        with Session(engine) as session:
            setting = session.get(Setting, key)
            if setting:
                return setting.value
            return default
    except Exception as e:
        logger.error(f"Error fetching setting {key}: {e}")
        return default

def upsert_bot_user(user, client_id: int = None):
    """
    Registra o actualiza la interacción de un usuario con el bot.
    user: telegram.User object
    """
    try:
        user_id = str(user.id)
        with Session(engine) as session:
            bot_user = session.get(BotUser, user_id)
            if not bot_user:
                bot_user = BotUser(
                    telegram_id=user_id,
                    first_name=user.first_name,
                    username=user.username,
                    is_client=bool(client_id),
                    client_id=client_id,
                    last_interaction=datetime.utcnow()
                )
            else:
                bot_user.first_name = user.first_name
                bot_user.username = user.username
                bot_user.last_interaction = datetime.utcnow()
                if client_id:
                    bot_user.is_client = True
                    bot_user.client_id = client_id
            
            session.add(bot_user)
            session.commit()
    except Exception as e:
        logger.error(f"Error upserting bot user {getattr(user, 'id', 'unknown')}: {e}")

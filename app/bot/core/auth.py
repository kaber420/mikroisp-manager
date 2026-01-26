# app/bot/core/auth.py
import logging
from telegram import Update
from telegram.ext import ContextTypes
from sqlmodel import select, Session
from app.db.engine_sync import sync_engine as engine
from app.models.user import User

logger = logging.getLogger(__name__)

async def check_authorization(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Verifica si el usuario de Telegram está autorizado (existe en la tabla Users).
    """
    user = update.effective_user
    if not user:
        return False
        
    telegram_id = str(user.id)
    
    try:
        with Session(engine) as session:
            # Buscar usuario con este telegram_chat_id
            statement = select(User).where(User.telegram_chat_id == telegram_id)
            db_user = session.exec(statement).first()
            
            if db_user and db_user.is_active:
                return True
                
            logger.warning(f"Intento de acceso no autorizado: {user.first_name} ID={telegram_id}")
            return False
            
    except Exception as e:
        logger.error(f"Error verificando autorización: {e}")
        return False
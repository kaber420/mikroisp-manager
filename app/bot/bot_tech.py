# Archivo: bot_tech.py

import logging
import os
import sys
import warnings
from dotenv import load_dotenv
from app.core.config import settings
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.warnings import PTBUserWarning

# Suppress PTB warnings before importing handlers that might trigger them
warnings.filterwarnings("ignore", category=PTBUserWarning)

# New Core Logic
from app.bot.core.config import DATA_DIR
from app.bot.core.auth import check_authorization
from app.bot.core.middleware import rate_limit

# Handlers
from app.bot.commands.ticket_manager import ticket_manager_conversation_handler
from app.bot.commands.location_cmd import location_conv_handler
from app.bot.commands.client_search import client_search_conversation_handler

load_dotenv()
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO,
    stream=sys.stdout
)
# Silenciar librerías ruidosas
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
TECH_BOT_TOKEN = settings.TECH_BOT_TOKEN

@rate_limit(limit=5, window=10)
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_authorization(update, context):
        await update.message.reply_text("❌ No estás autorizado para usar este bot.")
        return
    await update.message.reply_text(
        "🤖 **Bot de Técnicos 2.0**\n\n"
        "Comandos disponibles:\n"
        "/tickets - Gestionar tickets de soporte\n"
        "/cliente - Buscar información de clientes\n"
        "/here - Actualizar ubicación de un cliente\n",
        parse_mode="Markdown"
    )


def create_application(token):
    application = Application.builder().token(token).build()

    # Registrando Handlers
    application.add_handler(CommandHandler("start", start_command))
    
    # 1. Tickets
    application.add_handler(ticket_manager_conversation_handler)
    
    # 2. Location (/here)
    application.add_handler(location_conv_handler)
    
    # 3. Client Search (/cliente)
    application.add_handler(client_search_conversation_handler)
    
    return application

def main():
    logger.info("🚀 Iniciando Bot de Técnicos (Lightweight)...")
    if not TECH_BOT_TOKEN:
        logger.error("❌ No se encontró un TECH_BOT_TOKEN válido en el archivo .env")
        sys.exit(1)

    os.makedirs(DATA_DIR, exist_ok=True)

    application = create_application(TECH_BOT_TOKEN)

    logger.info("✅ Handlers registrados. Escuchando...")
    application.run_polling()

if __name__ == "__main__":
    main()
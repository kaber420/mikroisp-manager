# Archivo: bot_client/bot_client.py

import logging
import os
import sys
import warnings
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram.warnings import PTBUserWarning

# Suppress PTB warnings
warnings.filterwarnings("ignore", category=PTBUserWarning)

# Path hack removed as we run via -m
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from .commands.menu_handler import main_menu_conv_handler, handle_chat_messages

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
CLIENT_BOT_TOKEN = os.getenv("CLIENT_BOT_TOKEN")


def create_application(token):
    application = Application.builder().token(token).build()
    
    application.add_handler(main_menu_conv_handler)
    
    # Chat Handler (Global fallback for text that checks for active tickets)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_chat_messages))
    
    return application

def main():
    if not CLIENT_BOT_TOKEN:
        logger.error("❌ No CLIENT_BOT_TOKEN found.")
        sys.exit(1)
        
    application = create_application(CLIENT_BOT_TOKEN)
    logger.info("🌟 Bot de Clientes (Lightweight) iniciado.")
    application.run_polling()

if __name__ == "__main__":
    main()
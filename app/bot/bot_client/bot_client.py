# Archivo: bot_client/bot_client.py

import logging
import os
import sys
import warnings
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler
from telegram.warnings import PTBUserWarning

# Suppress PTB warnings
warnings.filterwarnings("ignore", category=PTBUserWarning)

# Path hack removed as we run via -m
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from .commands.menu_handler import main_menu_conv_handler, unknown_handler

load_dotenv()
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)
CLIENT_BOT_TOKEN = os.getenv("CLIENT_BOT_TOKEN")

def main():
    if not CLIENT_BOT_TOKEN:
        logger.error("❌ No CLIENT_BOT_TOKEN found.")
        sys.exit(1)
        
    application = Application.builder().token(CLIENT_BOT_TOKEN).build()
    
    application.add_handler(main_menu_conv_handler)
    application.add_handler(unknown_handler)
    
    logger.info("🌟 Bot de Clientes (Lightweight) iniciado.")
    application.run_polling()

if __name__ == "__main__":
    main()
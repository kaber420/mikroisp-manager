import os
from dotenv import load_dotenv
from app.core.config import settings

# Cargar variables de entorno
load_dotenv()

# Directorio base y datos
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, settings.DATA_DIR)

# Configuración del bot
BOT_TOKEN = getattr(settings, "CLIENT_BOT_TOKEN", "") # Fallback to CLIENT_BOT_TOKEN
MASTER_TECH_ID = settings.MASTER_TECH_ID
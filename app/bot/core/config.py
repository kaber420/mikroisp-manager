import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Directorio base y datos
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, os.getenv("DATA_DIR", "data"))

# Configuración del bot
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
MASTER_TECH_ID = os.getenv("MASTER_TECH_ID", "0")
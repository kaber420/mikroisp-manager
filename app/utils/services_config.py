import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Intentamos cargar cryptography para Fernet, si no está se maneja sin cifrado (fallback)
try:
    from cryptography.fernet import Fernet
except ImportError:
    Fernet = None

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
SERVICES_JSON = os.path.join(DATA_DIR, "services.json")


def get_fernet() -> Optional['Fernet']:
    if not Fernet:
        return None
    # Load key directly from environment (pydantic loads .env)
    key = os.environ.get("ENCRYPTION_KEY")
    if not key or len(key) != 44:
        return None
    try:
        return Fernet(key.encode())
    except Exception:
        return None


def encrypt_password(password: str) -> str:
    if not password:
        return password
    f = get_fernet()
    if f:
        try:
            return f.encrypt(password.encode()).decode()
        except Exception as e:
            logger.error(f"Failed to encrypt password: {e}")
            return password
    return password


def decrypt_password(encrypted: str) -> str:
    if not encrypted:
        return encrypted
    f = get_fernet()
    if f:
        try:
            return f.decrypt(encrypted.encode()).decode()
        except Exception:
            return encrypted
    return encrypted


def read_services_config() -> Dict[str, Any]:
    """
    Lee la configuración de servicios gestionada por la UI.
    Las contraseñas devueltas por esta función están descifradas para uso interno.
    """
    if not os.path.exists(SERVICES_JSON):
        return {}
    
    try:
        with open(SERVICES_JSON, "r") as f:
            data = json.load(f)
            
        # Descifrar passwords
        if "db" in data and "password" in data["db"]:
            data["db"]["password"] = decrypt_password(data["db"]["password"])
            
        if "cache" in data and "password" in data["cache"]:
            data["cache"]["password"] = decrypt_password(data["cache"]["password"])
            
        return data
    except Exception as e:
        logger.error(f"Error reading {SERVICES_JSON}: {e}")
        return {}


def write_services_config(config: Dict[str, Any]):
    """
    Escribe la configuración de servicios.
    Cifra las contraseñas antes de guardar.
    """
    os.makedirs(os.path.dirname(SERVICES_JSON), exist_ok=True)
    
    # Hacer una copia para no modificar el dict original que puede seguir usándose
    data = json.loads(json.dumps(config))
    
    # Cifrar passwords
    if "db" in data and "password" in data["db"]:
        data["db"]["password"] = encrypt_password(data["db"]["password"])
        
    if "cache" in data and "password" in data["cache"]:
        data["cache"]["password"] = encrypt_password(data["cache"]["password"])
        
    try:
        with open(SERVICES_JSON, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Error writing {SERVICES_JSON}: {e}")
        raise

# app/core/utils/security.py
import logging
import os

from cryptography.fernet import Fernet

# Cargar la clave de cifrado desde las variables de entorno
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
APP_ENV = os.getenv("APP_ENV", "development")

if not ENCRYPTION_KEY:
    if APP_ENV == "production":
        raise RuntimeError(
            "FATAL: ENCRYPTION_KEY no está configurada. "
            "Esta clave es OBLIGATORIA en producción para cifrar credenciales de dispositivos."
        )
    logging.warning(
        "ENCRYPTION_KEY no está configurada. El cifrado de contraseñas está DESHABILITADO."
    )
    cipher_suite = None
else:
    try:
        cipher_suite = Fernet(ENCRYPTION_KEY.encode())
    except Exception as e:
        if APP_ENV == "production":
            raise RuntimeError(
                f"FATAL: ENCRYPTION_KEY inválida: {e}. "
                'Genera una clave válida con: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
            )
        logging.error(f"Error al inicializar Fernet con ENCRYPTION_KEY: {e}")
        logging.error("Asegúrate de que ENCRYPTION_KEY sea una clave válida de Fernet.")
        cipher_suite = None


def encrypt_data(data: str) -> str:
    """Cifra un string."""
    if not cipher_suite or not data:
        return data
    try:
        encrypted_bytes = cipher_suite.encrypt(data.encode())
        return encrypted_bytes.decode()
    except Exception as e:
        logging.error(f"Error al cifrar datos: {e}")
        return data  # Devolver en claro como fallback de error


def decrypt_data(token: str) -> str:
    """Descifra un token (string)."""
    if not cipher_suite or not token:
        return token
    try:
        # Intentar decodificar
        decrypted_bytes = cipher_suite.decrypt(token.encode())
        return decrypted_bytes.decode()
    except Exception:
        # Si falla (ej. es un password en texto plano antiguo), devolver el original
        logging.warning("No se pudo descifrar un token. Asumiendo que es texto plano antiguo.")
        return token

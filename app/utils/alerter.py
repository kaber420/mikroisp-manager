# app/utils/alerter.py

import httpx
import logging

from .settings_utils import get_setting_sync

logger = logging.getLogger(__name__)


def send_telegram_alert(message: str):
    """
    Envía un mensaje de texto a un chat específico de Telegram a través de un bot.
    Ahora lee la configuración (token y chat_id) directamente desde la base de datos.

    Args:
        message (str): El texto del mensaje que se va a enviar. Soporta formato Markdown.
    """
    bot_token = get_setting_sync("telegram_bot_token")
    chat_id = get_setting_sync("telegram_chat_id")

    if not bot_token or not chat_id:
        logger.warning(f"Telegram no configurado. Alerta no enviada: {message}")
        return

    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}

    try:
        response = httpx.post(api_url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("Alerta enviada exitosamente a Telegram.")

    except httpx.HTTPStatusError as e:
        logger.error(f"Error crítico: No se pudo enviar la alerta de Telegram. Causa: {e}")
    except httpx.RequestError as e:
        logger.error(f"Error crítico: No se pudo enviar la alerta de Telegram. Causa: {e}")


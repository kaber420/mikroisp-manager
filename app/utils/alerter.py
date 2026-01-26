# app/utils/alerter.py

import httpx
import logging

from .settings_utils import get_setting_sync
from ..db.base import get_db_connection

logger = logging.getLogger(__name__)


def send_telegram_alert(message: str, alert_type: str = "system"):
    """
    Envía un mensaje de texto a los usuarios suscritos vía Telegram.

    Args:
        message (str): El texto del mensaje.
        alert_type (str): Tipo de alerta ('system', 'device', 'announcement').
                          - 'system': Para APs/Routers caídos (users.receive_alerts)
                          - 'device': Para CPEs caídos (users.receive_device_down_alerts)
                          - 'announcement': Para anuncios admin (users.receive_announcements)
    """
    bot_token = get_setting_sync("telegram_bot_token")
    if not bot_token:
        logger.warning(
            f"Telegram Bot Token no configurado. Alerta no enviada: {message}"
        )
        return

    # Determinar qué columna de preferencia verificar
    pref_column = "receive_alerts"
    if alert_type == "device":
        pref_column = "receive_device_down_alerts"
    elif alert_type == "announcement":
        pref_column = "receive_announcements"

    # Obtener usuarios destinatarios
    chat_ids = set()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Seleccionar chat_id de usuarios que tienen la preferencia activa Y tienen chat_id configurado
        query = f"SELECT telegram_chat_id FROM users WHERE {pref_column} = 1 AND telegram_chat_id IS NOT NULL AND telegram_chat_id != ''"
        cursor.execute(query)
        rows = cursor.fetchall()
        chat_ids = set(row[0] for row in rows)
        conn.close()
    except Exception as e:
        logger.error(f"Error obteniendo destinatarios de alertas: {e}")
        return

    if not chat_ids:
        logger.info(f"No hay usuarios suscritos para alertas de tipo '{alert_type}'.")
        return

    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    # Enviar a cada destinatario
    for chat_id in chat_ids:
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        try:
            response = httpx.post(api_url, json=payload, timeout=10)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error(f"Error enviando alerta a {chat_id}: {e}")
        except httpx.RequestError as e:
            logger.error(f"Error de conexión enviando alerta a {chat_id}: {e}")

    logger.info(f"Alerta ({alert_type}) enviada a {len(chat_ids)} destinatarios.")

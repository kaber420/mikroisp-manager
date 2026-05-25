# app/utils/alerter.py

import asyncio
import httpx
import logging

logger = logging.getLogger(__name__)


async def send_telegram_alert(message: str, alert_type: str = "system"):
    """
    Envía un mensaje de texto a los usuarios suscritos vía Telegram de forma asíncrona.

    Args:
        message (str): El texto del mensaje.
        alert_type (str): Tipo de alerta ('system', 'device', 'announcement').
                          - 'system': Para APs/Routers caídos (users.receive_alerts)
                          - 'device': Para CPEs caídos (users.receive_device_down_alerts)
                          - 'announcement': Para anuncios admin (users.receive_announcements)
    """
    # Importar dentro de la función para evitar dependencias circulares durante la inicialización
    from sqlmodel import select
    from app.db.engine import async_session_maker
    from app.models.setting import Setting
    from app.models.user import User

    # Determinar qué columna de preferencia verificar
    pref_column = "receive_alerts"
    if alert_type == "device":
        pref_column = "receive_device_down_alerts"
    elif alert_type == "announcement":
        pref_column = "receive_announcements"

    chat_ids = set()
    bot_token = None

    try:
        async with async_session_maker() as session:
            # 1. Obtener bot token
            setting_res = await session.get(Setting, "telegram_bot_token")
            if setting_res:
                bot_token = setting_res.value

            if not bot_token:
                logger.warning(
                    f"Telegram Bot Token no configurado. Alerta no enviada: {message}"
                )
                return

            # 2. Obtener usuarios destinatarios
            statement = select(User.telegram_chat_id).where(
                getattr(User, pref_column) == True,
                User.telegram_chat_id != None,
                User.telegram_chat_id != ""
            )
            results = (await session.exec(statement)).all()
            chat_ids = set(results)
    except Exception as e:
        logger.error(f"Error consultando base de datos para envío de alertas: {e}")
        return

    if not chat_ids:
        logger.info(f"No hay usuarios suscritos para alertas de tipo '{alert_type}'.")
        return

    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    # Enviar a todos los destinatarios de forma concurrente
    async with httpx.AsyncClient() as client:
        tasks = [
            client.post(
                api_url,
                json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"},
                timeout=10
            )
            for chat_id in chat_ids
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for chat_id, result in zip(chat_ids, results):
            if isinstance(result, Exception):
                logger.error(f"Error de conexión enviando alerta a {chat_id}: {result}")
            elif result.is_error:
                logger.error(f"Error HTTP({result.status_code}) enviando alerta a {chat_id}: {result.text}")

    logger.info(f"Alerta ({alert_type}) enviada a {len(chat_ids)} destinatarios de forma concurrente.")


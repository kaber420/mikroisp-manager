import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from app.db.engine import engine
from sqlmodel import select
from app.models.setting import Setting
# Use async engine/session if possible, but for a script sync or async run is fine.
# We will use the async session from engine.py if available, or just a sync session wrapper.

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

DEFAULT_SETTINGS = [
    {"key": "bot_welcome_msg_client", "value": "¡Hola de nuevo, {name}! 👋\n\n¿En qué podemos ayudarte?"},
    {"key": "bot_welcome_msg_guest", "value": "Hola, bienvenido. 👋\n\nParece que tu cuenta de Telegram no está vinculada.\nPor favor, comparte este ID con soporte:\n`{user_id}`"},
    {"key": "bot_val_btn_report", "value": "📞 Reportar Falla / Solicitar Ayuda"},
    {"key": "bot_val_btn_status", "value": "📋 Ver Mis Tickets"},
    {"key": "bot_val_btn_agent", "value": "🙋 Solicitar Agente Humano"},
    {"key": "bot_val_btn_wifi", "value": "🔑 Solicitar Cambio Clave WiFi"},
]

async def seed_settings():
    # We need to import the async_session_maker or engine
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        print("Checking existing settings...")
        for item in DEFAULT_SETTINGS:
            key = item["key"]
            value = item["value"]
            
            # Check if exists
            result = await session.get(Setting, key)
            if not result:
                print(f"Creating setting: {key}")
                new_setting = Setting(key=key, value=value)
                session.add(new_setting)
            else:
                print(f"Setting exists: {key}")
        
        await session.commit()
        print("Seed completed.")

if __name__ == "__main__":
    asyncio.run(seed_settings())

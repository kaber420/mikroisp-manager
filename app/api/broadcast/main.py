from typing import List, Literal, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import select
from pydantic import BaseModel
from telegram import Bot
from telegram.error import TelegramError
import asyncio
import logging

from ...core.users import require_admin
from ..settings.main import get_settings_service
from ...models.client import Client
from ...models.bot_user import BotUser
from ...services.settings_service import SettingsService

router = APIRouter()
logger = logging.getLogger(__name__)

class BroadcastRequest(BaseModel):
    message: str
    target_group: Literal["all_clients", "prospects", "all"]
    image_url: Optional[str] = None

async def send_broadcast_task(token: str, chat_ids: List[str], message: str, image_url: Optional[str] = None):
    """
    Background task to send messages.
    """
    bot = Bot(token=token)
    logger.info(f"Starting broadcast to {len(chat_ids)} recipients.")
    
    success_count = 0
    fail_count = 0
    
    for chat_id in chat_ids:
        try:
            if image_url:
                await bot.send_photo(chat_id=chat_id, photo=image_url, caption=message)
            else:
                await bot.send_message(chat_id=chat_id, text=message)
            success_count += 1
            # Rate limiting safety (20 msgs/sec is generic limit, 0.05s sleep)
            await asyncio.sleep(0.05) 
        except Exception as e:
            fail_count += 1
            logger.error(f"Failed to send to {chat_id}: {e}")
            
    logger.info(f"Broadcast finished. Success: {success_count}, Fail: {fail_count}")

@router.post("/send")
async def send_broadcast(
    request: BroadcastRequest,
    background_tasks: BackgroundTasks,
    settings: SettingsService = Depends(get_settings_service),
    current_user = Depends(require_admin)
):
    # Get Token
    token = await settings.get_setting_value("client_bot_token")
    if not token:
        raise HTTPException(status_code=400, detail="Client Bot Token not configured")
        
    # Gather Recipients
    chat_ids = set()
    
    # We use the session from settings service
    # Make sure to clone or use it properly. SettingsService uses an injected AsyncSession.
    
    session = settings.session
    
    if request.target_group in ["all_clients", "all"]:
         result = await session.execute(select(Client.telegram_contact).where(Client.telegram_contact != None))
         # Filter out empty/None
         valid_contacts = [c for c in result.scalars().all() if c and c.strip()]
         chat_ids.update(valid_contacts)
         
    if request.target_group in ["prospects", "all"]:
         # Prospects are users NOT in clients table (handled by BotUser with is_client=False)
         result = await session.execute(select(BotUser.telegram_id).where(BotUser.is_client == False))
         chat_ids.update(result.scalars().all())
             
    if not chat_ids:
        raise HTTPException(status_code=404, detail="No recipients found for the selected group")
        
    # Send in background
    background_tasks.add_task(send_broadcast_task, token, list(chat_ids), request.message, request.image_url)
    
    return {
        "status": "queued", 
        "recipient_count": len(chat_ids),
        "target": request.target_group
    }

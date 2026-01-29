from typing import List, Literal, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import select, col
from pydantic import BaseModel
from telegram import Bot
import asyncio
import logging

from ...core.users import require_admin
from ..settings.main import get_settings_service
from ...models.client import Client
from ...models.service import ClientService
from ...models.router import Router
from ...models.user import User
from ...models.zona import Zona
from ...services.settings_service import SettingsService

router = APIRouter()
logger = logging.getLogger(__name__)

class BroadcastRequest(BaseModel):
    message: str
    target_type: Literal["clients", "technicians"]
    zone_ids: Optional[List[int]] = None
    staff_roles: Optional[List[str]] = None
    image_url: Optional[str] = None

async def send_broadcast_task(token: str, chat_ids: List[str], message: str, image_url: Optional[str] = None):
    """
    Background task to send messages.
    """
    if not chat_ids:
        return

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

@router.get("/zones")
async def get_broadcast_zones(
    settings: SettingsService = Depends(get_settings_service),
    current_user = Depends(require_admin)
):
    """Gets a list of zones that have at least one client with a linked Telegram account."""
    session = settings.session
    
    # We want zones that have routers, which have services, which have clients with telegram_contact
    # This query allows the frontend to show only relevant zones
    statement = (
        select(Zona.id, Zona.nombre)
        .join(Router, Router.zona_id == Zona.id)
        .join(ClientService, ClientService.router_host == Router.host)
        .join(Client, ClientService.client_id == Client.id)
        .where(Client.telegram_contact != None)
        .distinct()
    )
    
    result = await session.execute(statement)
    zones = [{"id": r[0], "name": r[1]} for r in result.all()]
    return zones

@router.post("/send")
async def send_broadcast(
    request: BroadcastRequest,
    background_tasks: BackgroundTasks,
    settings: SettingsService = Depends(get_settings_service),
    current_user = Depends(require_admin)
):
    # Get Tokens
    client_bot_token = await settings.get_setting_value("client_bot_token")
    tech_bot_token = await settings.get_setting_value("tech_bot_token") # Assuming this setting exists or will use env var
    
    if request.target_type == "clients" and not client_bot_token:
        raise HTTPException(status_code=400, detail="Client Bot Token not configured")
        
    # Gather Recipients
    chat_ids = set()
    session = settings.session
    token_to_use = client_bot_token
    
    if request.target_type == "clients":
        # Base query for clients with telegram
        query = (
            select(Client.telegram_contact)
            .where(Client.telegram_contact != None)
        )
        
        # If specific zones are selected, join tables to filter
        if request.zone_ids:
            query = (
                query
                .join(ClientService, ClientService.client_id == Client.id)
                .join(Router, ClientService.router_host == Router.host)
                .where(col(Router.zona_id).in_(request.zone_ids))
            )
            
        result = await session.execute(query)
        # Clean up and add to set
        valid_contacts = [c for c in result.scalars().all() if c and c.strip()]
        chat_ids.update(valid_contacts)
        
    elif request.target_type == "technicians":

        import os
        if not tech_bot_token:
             # Fallback to env var mainly for dev/legacy
             tech_bot_token = os.getenv("TECH_BOT_TOKEN")
             
        if not tech_bot_token:
             raise HTTPException(status_code=400, detail="Tech Bot Token not configured")
             
        token_to_use = tech_bot_token
        
        # Get users with telegram_chat_id
        statement = select(User.telegram_chat_id).where(User.telegram_chat_id != None)
        
        # Filter by roles if provided
        if request.staff_roles:
            statement = statement.where(col(User.role).in_(request.staff_roles))

        result = await session.execute(statement)
        valid_contacts = [c for c in result.scalars().all() if c and c.strip()]
        chat_ids.update(valid_contacts)
             
    if not chat_ids:
        raise HTTPException(status_code=404, detail="No recipients found for the selected criteria")
        
    # Send in background
    background_tasks.add_task(send_broadcast_task, token_to_use, list(chat_ids), request.message, request.image_url)
    
    return {
        "status": "queued", 
        "recipient_count": len(chat_ids),
        "target": request.target_type
    }

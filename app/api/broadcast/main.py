from typing import List, Literal, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File
from sqlmodel import select, col
from pydantic import BaseModel
from telegram import Bot
from telegram import InputFile as TelegramInputFile
import asyncio
import logging
import os
import uuid
from pathlib import Path

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

# Temp directory for broadcast images
BROADCAST_UPLOAD_DIR = Path("/tmp/umanager_broadcasts")
BROADCAST_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

class BroadcastRequest(BaseModel):
    message: str
    target_type: Literal["clients", "technicians"]
    zone_ids: Optional[List[int]] = None
    staff_roles: Optional[List[str]] = None
    image_url: Optional[str] = None
    local_image_path: Optional[str] = None  # Path to uploaded temp file

async def send_broadcast_task(
    token: str, 
    chat_ids: List[str], 
    message: str, 
    image_url: Optional[str] = None,
    local_image_path: Optional[str] = None
):
    """
    Background task to send messages.
    Uses file_id caching for efficient image broadcasts.
    """
    if not chat_ids:
        return

    bot = Bot(token=token)
    logger.info(f"Starting broadcast to {len(chat_ids)} recipients.")
    
    success_count = 0
    fail_count = 0
    cached_file_id: Optional[str] = None
    
    try:
        for i, chat_id in enumerate(chat_ids):
            try:
                if local_image_path and os.path.exists(local_image_path):
                    # First send: upload file and cache file_id
                    if cached_file_id is None:
                        with open(local_image_path, "rb") as f:
                            sent_msg = await bot.send_photo(
                                chat_id=chat_id, 
                                photo=f, 
                                caption=message
                            )
                        # Extract file_id from the largest photo size
                        if sent_msg.photo:
                            cached_file_id = sent_msg.photo[-1].file_id
                            logger.info(f"Cached file_id: {cached_file_id[:20]}...")
                    else:
                        # Subsequent sends: use cached file_id (instant)
                        await bot.send_photo(
                            chat_id=chat_id, 
                            photo=cached_file_id, 
                            caption=message
                        )
                elif image_url:
                    # URL-based send (legacy)
                    await bot.send_photo(chat_id=chat_id, photo=image_url, caption=message)
                else:
                    await bot.send_message(chat_id=chat_id, text=message)
                    
                success_count += 1
                # Rate limiting safety (20 msgs/sec is generic limit, 0.05s sleep)
                await asyncio.sleep(0.05)
                
            except Exception as e:
                fail_count += 1
                logger.error(f"Failed to send to {chat_id}: {e}")
    finally:
        # Cleanup temp file
        if local_image_path and os.path.exists(local_image_path):
            try:
                os.remove(local_image_path)
                logger.info(f"Cleaned up temp file: {local_image_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file: {e}")
            
    logger.info(f"Broadcast finished. Success: {success_count}, Fail: {fail_count}")

@router.post("/upload")
async def upload_broadcast_image(
    file: UploadFile = File(...),
    current_user = Depends(require_admin)
):
    """
    Upload an image for broadcast. Returns the temp file path.
    """
    # Validate extension
    ext = Path(file.filename).suffix.lower() if file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Tipo de archivo no permitido. Usa: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Read and validate size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400, 
            detail=f"Archivo demasiado grande. Máximo: {MAX_FILE_SIZE // (1024*1024)}MB"
        )
    
    # Save to temp directory with unique name
    unique_name = f"{uuid.uuid4().hex}{ext}"
    temp_path = BROADCAST_UPLOAD_DIR / unique_name
    
    with open(temp_path, "wb") as f:
        f.write(content)
    
    logger.info(f"Saved broadcast image to {temp_path}")
    
    return {
        "temp_path": str(temp_path),
        "filename": file.filename,
        "size": len(content)
    }


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
    background_tasks.add_task(
        send_broadcast_task, 
        token_to_use, 
        list(chat_ids), 
        request.message, 
        request.image_url,
        request.local_image_path
    )
    
    return {
        "status": "queued", 
        "recipient_count": len(chat_ids),
        "target": request.target_type
    }

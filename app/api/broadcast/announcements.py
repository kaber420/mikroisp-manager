# app/api/broadcast/announcements.py
import uuid
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.engine import get_session
from ...models.portal_announcement import PortalAnnouncement
from app.core.security import require_admin
from ...schemas.portal_announcement import (
    PortalAnnouncementCreate,
    PortalAnnouncementRead,
    PortalAnnouncementUpdate,
)

router = APIRouter(prefix="/announcements", tags=["Broadcast - CMS"])

@router.get("/", response_model=List[PortalAnnouncementRead])
async def list_announcements(
    skip: int = 0,
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
    current_user = Depends(require_admin)
):
    """Lista todos los anuncios (incluso inactivos) para la gestión del administrador."""
    query = select(PortalAnnouncement).order_by(desc(PortalAnnouncement.created_at)).offset(skip).limit(limit)
    result = await session.execute(query)
    return result.scalars().all()

@router.get("/{announcement_id}", response_model=PortalAnnouncementRead)
async def get_announcement(
    announcement_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user = Depends(require_admin)
):
    """Obtiene un anuncio específico."""
    announcement = await session.get(PortalAnnouncement, announcement_id)
    if not announcement:
        raise HTTPException(status_code=404, detail="Anuncio no encontrado")
    return announcement

@router.post("/", response_model=PortalAnnouncementRead, status_code=status.HTTP_201_CREATED)
async def create_announcement(
    announcement_in: PortalAnnouncementCreate,
    session: AsyncSession = Depends(get_session),
    current_user = Depends(require_admin)
):
    """Crea un nuevo anuncio para el portal."""
    announcement = PortalAnnouncement(**announcement_in.dict())
    session.add(announcement)
    await session.commit()
    await session.refresh(announcement)
    return announcement

@router.put("/{announcement_id}", response_model=PortalAnnouncementRead)
async def update_announcement(
    announcement_id: uuid.UUID,
    announcement_in: PortalAnnouncementUpdate,
    session: AsyncSession = Depends(get_session),
    current_user = Depends(require_admin)
):
    """Actualiza un anuncio existente."""
    announcement = await session.get(PortalAnnouncement, announcement_id)
    if not announcement:
        raise HTTPException(status_code=404, detail="Anuncio no encontrado")
    
    update_data = announcement_in.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(announcement, key, value)
        
    session.add(announcement)
    await session.commit()
    await session.refresh(announcement)
    return announcement

@router.delete("/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_announcement(
    announcement_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user = Depends(require_admin)
):
    """Elimina permanentemente un anuncio."""
    announcement = await session.get(PortalAnnouncement, announcement_id)
    if not announcement:
        raise HTTPException(status_code=404, detail="Anuncio no encontrado")
        
    await session.delete(announcement)
    await session.commit()

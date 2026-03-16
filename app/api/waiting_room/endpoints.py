from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, desc
from datetime import datetime
import uuid
from typing import List

from app.core.security import require_admin
from app.db.engine import get_session
from app.models.user import User
from app.models.waiting_room import WaitingRoomConfig

router = APIRouter()

@router.get("/active", response_model=WaitingRoomConfig)
async def get_active_waiting_room(session: AsyncSession = Depends(get_session)):
    """
    Obtiene la configuración activa actual para la sala de espera.
    (Público / Para clientes en cola)
    """
    now = datetime.utcnow()
    
    # Buscar configuraciones activas
    query = select(WaitingRoomConfig).where(WaitingRoomConfig.is_active == True)
    
    result = await session.execute(query)
    configs = result.scalars().all()
    
    # Lógica simple: priorizar las que están en fecha válida, sino la última activa general.
    valid_configs = []
    for config in configs:
        if config.start_date and config.end_date:
            if config.start_date <= now <= config.end_date:
                valid_configs.append(config)
        elif not config.start_date and not config.end_date:
            valid_configs.append(config)
            
    if not valid_configs:
        raise HTTPException(status_code=404, detail="No active waiting room configuration found")
        
    # Ordenar por fecha de creación descendente (la más reciente primero)
    valid_configs.sort(key=lambda x: x.created_at, reverse=True)
    return valid_configs[0]

@router.get("/", response_model=List[WaitingRoomConfig])
async def list_waiting_rooms(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session)
):
    """(Admin) Lista configuraciones."""
    result = await session.execute(
        select(WaitingRoomConfig).order_by(desc(WaitingRoomConfig.created_at)).offset(skip).limit(limit)
    )
    return result.scalars().all()

@router.post("/", response_model=WaitingRoomConfig)
async def create_waiting_room(
    config_in: WaitingRoomConfig,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session)
):
    """(Admin) Crea una configuración."""
    config_in.id = uuid.uuid4()
    config_in.created_at = datetime.utcnow()
    config_in.updated_at = datetime.utcnow()
    
    session.add(config_in)
    await session.commit()
    await session.refresh(config_in)
    return config_in

@router.put("/{config_id}", response_model=WaitingRoomConfig)
async def update_waiting_room(
    config_id: uuid.UUID,
    config_in: dict, # Using dict to allow partial updates for simplicity here
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session)
):
    """(Admin) Actualiza una configuración."""
    config = await session.get(WaitingRoomConfig, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
        
    for key, value in config_in.items():
        if hasattr(config, key) and key not in ["id", "created_at"]:
            setattr(config, key, value)
            
    config.updated_at = datetime.utcnow()
    session.add(config)
    await session.commit()
    await session.refresh(config)
    return config

@router.delete("/{config_id}")
async def delete_waiting_room(
    config_id: uuid.UUID,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session)
):
    """(Admin) Elimina una configuración."""
    config = await session.get(WaitingRoomConfig, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
        
    await session.delete(config)
    await session.commit()
    return {"status": "deleted"}

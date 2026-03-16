from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Optional
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from datetime import datetime

from app.core.security import current_active_user
from app.db.engine import get_session
from app.models.user import User
from app.models.ticket import Ticket
from app.models.video_session import VideoSessionLog
from app.services.livekit_service import create_room_token
from app.core.config import settings

router = APIRouter()

@router.get("/token/{ticket_id}")
async def get_livekit_token(
    ticket_id: str,
    current_user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Obtiene un Token JWT para entrar a la sala de videollamada del ticket.
    Solo puede ser solicitado por el técnico asignado.
    """
    
    # 1. Buscar el Ticket
    result = await session.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
        
    # 3. Autoasignar ticket si aún no tiene técnico (el técnico lo está reclamando)
    if ticket.assigned_tech_id is None:
        ticket.assigned_tech_id = current_user.id
        ticket.status = "pending"
        session.add(ticket)
        await session.commit()
    elif str(ticket.assigned_tech_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Ya tiene otro técnico asignado")

    # 4. Generar token
    room_name = f"ticket_{ticket.id}"
    token = create_room_token(
        room_name=room_name,
        participant_identity=str(current_user.id),
        participant_name=getattr(current_user, 'name', None) or current_user.username,
        is_tech=True
    )
    
    # 4. Registrar o actualizar la sesión de video en DB
    session_result = await session.execute(
        select(VideoSessionLog)
        .where(VideoSessionLog.ticket_id == ticket.id)
        .where(VideoSessionLog.tech_id == current_user.id)
    )
    video_log = session_result.scalar_one_or_none()
    
    if not video_log:
        video_log = VideoSessionLog(
            ticket_id=ticket.id,
            tech_id=current_user.id,
            room_name=room_name,
            started_at=datetime.utcnow()
        )
        session.add(video_log)
        await session.commit()
    
    return {"token": token, "room": room_name, "server_url": settings.LIVEKIT_URL}

@router.post("/webhook")
async def livekit_webhook(background_tasks: BackgroundTasks):
    """
    Endpoint para recibir eventos automáticos de LiveKit (Webhooks).
    Ejemplos: 'participant_joined', 'participant_left', 'room_finished'.
    Las verificaciones y cierres de tickets se delegan a tareas en segundo plano.
    """
    # TODO: Implementar validación del secret del webhook de Livekit
    # Y parsear el payload
    
    # Para procesos rápidos y simples como cerrar el log en DB
    # Las Background Tasks de FastAPI son excelentes:
    # background_tasks.add_task(cerrar_sesion_en_db, event_data)
    
    return {"status": "received"}

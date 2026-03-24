from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from datetime import datetime, timedelta
import logging

from app.db.session import SessionLocal
from app.models.ticket import Ticket
from app.api.websockets.support_pool import pool_manager

logger = logging.getLogger(__name__)

async def check_expired_support_waiters():
    """
    Tarea programada para revisar clientes que llevan más de X tiempo en el pool de espera.
    Cambia su estado a NO_ATENDIDA/TIMEOUT y les notifica vía WS si siguen conectados.
    """
    timeout_minutes = 5 # Configurable
    timeout_threshold = datetime.utcnow() - timedelta(minutes=timeout_minutes)
    
    async with SessionLocal() as session:
        # Buscar tickets ESPERANDO que superen el tiempo
        query = (
            select(Ticket)
            .where(Ticket.status == "waiting")
            .where(Ticket.channel == "video_call")
            .where(Ticket.created_at < timeout_threshold)
        )
        result = await session.execute(query)
        expired_tickets = result.scalars().all()
        
        for ticket in expired_tickets:
            # 1. Marcar como caducado / timeout
            ticket.status = "timeout"
            
            # 2. Notificar al cliente vía WebSocket (si sigue ahí)
            if str(ticket.id) in pool_manager.waiting_clients:
                client_ws = pool_manager.waiting_clients[str(ticket.id)]
                try:
                    await client_ws.send_json({
                        "action": "timeout", 
                        "message": "Nuestros técnicos están ocupados en este momento. Por favor intente más tarde."
                    })
                except Exception as e:
                    logger.error(f"Error enviando timeout WS a {ticket.id}: {e}")
                    
                # Desconectar y limpiar del pool
                pool_manager.disconnect_client(str(ticket.id))
                
        if expired_tickets:
            await session.commit()
            # 3. Notificar a los técnicos para refrescar la vista del dashboard
            await pool_manager.broadcast_pool_update()
            logger.info(f"Limpiados {len(expired_tickets)} tickets por timeout en el pool de video.")

# Registrar la función si hay un scheduler de la app
def setup_support_jobs(scheduler: AsyncIOScheduler):
    # Corre cada 1 minuto
    scheduler.add_job(
        check_expired_support_waiters, 
        "interval", 
        max_instances=1,
        minutes=1,
        id="support_pool_timeout_job",
        replace_existing=True
    )

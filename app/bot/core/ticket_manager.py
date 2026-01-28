# core/ticket_manager.py
"""
Módulo centralizado para la lógica de negocio y acceso a datos de los tickets.
Refactorizado para usar SQLModel y la base de datos principal inventory.sqlite.
"""

import logging
import httpx
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlmodel import select, Session, col
from app.db.engine_sync import sync_engine as engine
from app.models.ticket import Ticket, TicketMessage
from app.models.client import Client
from app.models.user import User

# Configuración del logger
logger = logging.getLogger(__name__)

TicketDict = Dict[str, Any]

def crear_ticket(
    cliente_external_id: str,
    cliente_plataforma: str,
    cliente_nombre: str,
    cliente_ip_cpe: str,
    tipo_solicitud: str,
    descripcion: str
) -> Optional[str]:
    """Crea un nuevo ticket en la base de datos principal."""
    logger.info(f"Creando nuevo ticket: {tipo_solicitud} para {cliente_external_id}@{cliente_plataforma}")
    
    try:
        with Session(engine) as session:
            statement = select(Client).where(
                (Client.telegram_contact == cliente_external_id) | 
                (Client.whatsapp_number == cliente_external_id)
            )
            client = session.exec(statement).first()
            
            if not client:
                logger.info(f"Cliente no encontrado, creando provisional: {cliente_nombre}")
                client = Client(
                    name=cliente_nombre,
                    telegram_contact=cliente_external_id if cliente_plataforma == 'telegram' else None,
                    whatsapp_number=cliente_external_id if cliente_plataforma == 'whatsapp' else None,
                    notes=f"ID externo: {cliente_external_id} ({cliente_plataforma})"
                )
                session.add(client)
                session.commit()
                session.refresh(client)
            
            new_ticket = Ticket(
                client_id=client.id,
                subject=tipo_solicitud,
                description=descripcion,
                status="open",
                priority="normal"
            )
            session.add(new_ticket)
            session.commit()
            session.refresh(new_ticket)
            
            return str(new_ticket.id)

    except Exception as e:
        logger.error(f"❌ Error al crear ticket: {e}", exc_info=True)
        return None


def obtener_ticket_por_id(ticket_id: str) -> Optional[TicketDict]:
    """Obtiene un ticket por su UUID."""
    try:
        with Session(engine) as session:
            statement = select(Ticket).where(Ticket.id == ticket_id)
            ticket = session.exec(statement).first()
            
            if ticket:
                # Need to fetch client name manually or join
                client = session.get(Client, ticket.client_id)
                tech = session.get(User, ticket.assigned_tech_id) if ticket.assigned_tech_id else None
                
                # Manual serialization to match the expected Dict format of the old bot
                return {
                    "id": str(ticket.id),
                    "cliente_nombre": client.name if client else "Desconocido",
                    "cliente_external_id": client.telegram_contact if client else "N/A",
                    "cliente_plataforma": "Telegram" if client and client.telegram_contact else "Unknown", 
                    "cliente_ip_cpe": "N/A", # Not stored on Ticket anymore, maybe on Client?
                    "tipo_solicitud": ticket.subject,
                    "estado": ticket.status,
                    "tecnico_asignado": tech.username if tech else None,
                    "fecha_creacion": ticket.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    "fecha_actualizacion": ticket.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                    "descripcion": ticket.description,
                    "respuesta_tecnico": "" # TODO: Fetch last message from tech?
                }
            else:
                return None
    except Exception as e:
        logger.error(f"Error buscando ticket {ticket_id}: {e}")
        return None

def agregar_respuesta_a_ticket(ticket_id: str, mensaje: str, autor_tipo: str, autor_id: str = None) -> bool:
    """Agrega un mensaje al ticket."""
    try:
        with Session(engine) as session:
            statement = select(Ticket).where(Ticket.id == ticket_id)
            ticket = session.exec(statement).first()
            if not ticket: return False
            
            # If autor_type is 'tech', treat autor_id as telegram_id and find User UUID?
            # Or assume the caller passed the correct UUID?
            # To be safe, let's just store simple strings in TicketMessage.sender_id for now if schema allows, 
            # OR logic to look up UUID.
            # TicketMessage.sender_id is str.
            
            new_message = TicketMessage(
                ticket_id=ticket.id,
                sender_type=autor_tipo,
                sender_id=autor_id,
                content=mensaje
            )
            session.add(new_message)
            
            ticket.updated_at = datetime.utcnow()
            # Generic logic: if client replies, open. If tech replies, pending/resolved?
            # Let's keep it simple.
            
            session.add(ticket)
            session.add(ticket)
            session.commit()
            
            # --- REAL-TIME NOTIFICATION ---
            try:
                # Fire and forget notification to the main API
                # This tells the WebSocket manager to broadcast "db_updated"
                with httpx.Client(timeout=1.0) as client:
                    client.post("http://127.0.0.1:8000/api/internal/notify-monitor-update")
            except Exception as e:
                # Non-blocking error logging
                logger.warning(f"Failed to notify web monitor: {e}")

            return True
            
    except Exception as e:
        logger.error(f"Error agregando respuesta: {e}")
        return False

def asignar_ticket_a_tecnico(ticket_id: str, tecnico_telegram_id: str) -> bool:
    """Asigna el ticket al usuario que coincida con el telegram_id."""
    try:
        with Session(engine) as session:
            # 1. Find Author
            user_stmt = select(User).where(User.telegram_chat_id == tecnico_telegram_id)
            user = session.exec(user_stmt).first()
            if not user:
                logger.error(f"Usuario con telegram_id {tecnico_telegram_id} no encontrado.")
                return False
                
            # 2. Find Ticket
            ticket_stmt = select(Ticket).where(Ticket.id == ticket_id)
            ticket = session.exec(ticket_stmt).first()
            if not ticket: return False
            
            # 3. Assign
            ticket.assigned_tech_id = user.id
            ticket.status = "en_revision" # or 'in_progress'
            ticket.updated_at = datetime.utcnow()
            
            session.add(ticket)
            session.commit()
            return True
    except Exception as e:
        logger.error(f"Error asignando ticket: {e}")
        return False

def auto_asignar_ticket_a_tecnico(ticket_id: str, tecnico_telegram_id: str) -> bool:
    return asignar_ticket_a_tecnico(ticket_id, tecnico_telegram_id)

def actualizar_estado_ticket(ticket_id: str, nuevo_estado: str, tecnico_telegram_id: str = None) -> bool:
    try:
        with Session(engine) as session:
            ticket = session.get(Ticket, ticket_id)
            if not ticket: return False
            
            ticket.status = nuevo_estado
            ticket.updated_at = datetime.utcnow()
            session.add(ticket)
            session.commit()
            return True
    except Exception as e:
        logger.error(f"Error actualizando estado: {e}")
        return False

def obtener_tickets(
    estado: Optional[str] = None,
    dias: Optional[int] = None,
    limit: int = 10,
    offset: int = 0
) -> tuple[List[TicketDict], int]:
    try:
        with Session(engine) as session:
            query = select(Ticket)
            
            if estado and estado != 'todos':
                query = query.where(Ticket.status == estado)
                
            if dias:
                date_limit = datetime.utcnow() - timedelta(days=dias)
                query = query.where(Ticket.created_at >= date_limit)
            
            # Count total
            # (Simplification: fetch all for count is inefficient but fast for small db)
            total_count = len(session.exec(query).all())
            
            # Paging
            query = query.offset(offset).limit(limit).order_by(Ticket.created_at.desc())
            results = session.exec(query).all()
            
            tickets_list = []
            for t in results:
                # Helper to format dict
                # Need client name
                client = session.get(Client, t.client_id)
                tickets_list.append({
                    "id": str(t.id), # UUID as string
                    "cliente_nombre": client.name if client else "Unknown",
                    "estado": t.status,
                    "fecha_creacion": t.created_at.strftime('%Y-%m-%d'),
                    # Add other fields needed for UI lists
                })
                
            return tickets_list, total_count
    except Exception as e:
        logger.error(f"Error listando tickets: {e}")
        return [], 0

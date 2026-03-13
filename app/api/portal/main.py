# app/api/portal/main.py
import uuid as uuid_pkg
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select, col, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...db.engine import get_session
from ...models.user import User
from ...models.client import Client
from ...models.ticket import Ticket, TicketMessage
from ...models.service import ClientService
from ...models.plan import Plan
from ...core.users import current_active_user

from .models import (
    PortalClientRead,
    PortalTicketRead,
    PortalTicketCreate,
    PortalPlanRead,
    PortalTicketMessageRead,
    PortalTicketMessageCreate,
    PortalTicketListResponse
)
from ...models.portal_announcement import PortalAnnouncement
from ...schemas.portal_announcement import PortalAnnouncementRead

router = APIRouter(prefix="/portal", tags=["Portal de Clientes"])

@router.get("/me", response_model=PortalClientRead)
async def get_portal_me(
    current_user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session)
):
    """Obtiene el perfil del cliente asociado al usuario actual."""
    if not current_user.client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with a client profile."
        )
    
    client = await session.get(Client, current_user.client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client profile not found.")
    
    return PortalClientRead(
        id=client.id,
        name=client.name,
        address=client.address,
        phone_number=client.phone_number,
        email=client.email,
        service_status=client.service_status,
        billing_day=client.billing_day
    )

@router.get("/tickets", response_model=PortalTicketListResponse)
async def list_portal_tickets(
    limit: int = 10,
    offset: int = 0,
    current_user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session)
):
    """Lista los tickets de soporte del cliente actual."""
    if not current_user.client_id:
        raise HTTPException(status_code=403, detail="Not a client user")
    
    count_query = select(func.count()).select_from(Ticket).where(Ticket.client_id == current_user.client_id)
    total_count = (await session.exec(count_query)).one()
    
    query = (
        select(Ticket)
        .where(Ticket.client_id == current_user.client_id)
        .options(selectinload(Ticket.messages))
        .order_by(desc(Ticket.updated_at))
        .offset(offset)
        .limit(limit)
    )
    results = await session.exec(query)
    tickets = results.all()
    
    responses = []
    for t in tickets:
        msgs = [
            PortalTicketMessageRead(
                id=m.id,
                sender_type=m.sender_type,
                sender_id=m.sender_id,
                content=m.content,
                created_at=m.created_at,
                media_url=m.media_url
            ) for m in sorted(t.messages, key=lambda x: x.created_at)
        ]
        
        assigned_tech_name = None
        if t.assigned_tech_id:
            # Note: Might be faster to join upfront, but since it's portal (few tickets), querying here is okay.
            tech = await session.get(User, t.assigned_tech_id)
            if tech:
                assigned_tech_name = tech.username
        
        responses.append(PortalTicketRead(
            id=t.id,
            ticket_id=t.ticket_id,
            subject=t.subject,
            description=t.description,
            status=t.status,
            priority=t.priority,
            created_at=t.created_at,
            updated_at=t.updated_at,
            ticket_type=t.ticket_type,
            assigned_tech_name=assigned_tech_name,
            messages=msgs
        ))
    return PortalTicketListResponse(items=responses, total=total_count)

@router.post("/tickets/{ticket_id}/messages", response_model=PortalTicketMessageRead)
async def create_portal_ticket_message(
    ticket_id: uuid_pkg.UUID,
    message_in: PortalTicketMessageCreate,
    current_user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session)
):
    """Agrega un mensaje a un ticket existente del cliente."""
    if not current_user.client_id:
        raise HTTPException(status_code=403, detail="Not a client user")
        
    ticket = await session.get(Ticket, ticket_id)
    if not ticket or ticket.client_id != current_user.client_id:
        raise HTTPException(status_code=404, detail="Ticket not found")
        
    new_message = TicketMessage(
        ticket_id=ticket.id,
        sender_type="client",
        sender_id=str(current_user.id),
        content=message_in.content,
        created_at=datetime.utcnow()
    )
    
    # Optionally update ticket updated_at and status if needed
    ticket.updated_at = datetime.utcnow()
    # If ticket was closed, maybe reopen it? We leave custom logic out for now unless requested
    
    session.add(new_message)
    session.add(ticket)
    await session.commit()
    await session.refresh(new_message)
    
    return PortalTicketMessageRead(
        id=new_message.id,
        sender_type=new_message.sender_type,
        sender_id=new_message.sender_id,
        content=new_message.content,
        created_at=new_message.created_at,
        media_url=new_message.media_url
    )

@router.post("/tickets", response_model=PortalTicketRead)
async def create_portal_ticket(
    ticket_in: PortalTicketCreate,
    current_user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session)
):
    """Crea un nuevo ticket de soporte para el cliente actual."""
    if not current_user.client_id:
        raise HTTPException(status_code=403, detail="Not a client user")
        
    new_ticket = Ticket(
        client_id=current_user.client_id,
        subject=ticket_in.subject,
        description=ticket_in.description,
        priority=ticket_in.priority,
        ticket_type="support", # Siempre forzar a "support"
        status="open",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    session.add(new_ticket)
    await session.commit()
    await session.refresh(new_ticket)
    
    return PortalTicketRead(
        id=new_ticket.id,
        ticket_id=new_ticket.ticket_id,
        subject=new_ticket.subject,
        description=new_ticket.description,
        status=new_ticket.status,
        priority=new_ticket.priority,
        created_at=new_ticket.created_at,
        updated_at=new_ticket.updated_at,
        ticket_type=new_ticket.ticket_type,
        messages=[]
    )

@router.get("/planes", response_model=List[PortalPlanRead])
async def list_portal_planes(
    current_user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session)
):
    """Obtiene los planes y servicios activos del cliente actual."""
    if not current_user.client_id:
        raise HTTPException(status_code=403, detail="Not a client user")
    
    # Get client services
    query = select(ClientService).where(ClientService.client_id == current_user.client_id)
    results = await session.exec(query)
    services = results.all()
    
    responses = []
    for s in services:
        plan_name = "Plan Personalizado"
        max_limit = "Desconocido"
        price = 0.0
        
        if s.plan_id:
            plan = await session.get(Plan, s.plan_id)
            if plan:
                plan_name = plan.name
                max_limit = plan.max_limit
                price = plan.price
        
        responses.append(PortalPlanRead(
            id=s.id, # Usamos el ID del servicio como referencia para la vista del portal
            name=plan_name,
            max_limit=max_limit,
            price=price,
            status=s.status,
            pppoe_username=s.pppoe_username,
            ip_address=s.ip_address
        ))
    return responses

@router.get("/announcements", response_model=List[PortalAnnouncementRead])
async def list_active_announcements(
    current_user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session)
):
    """Obtiene los anuncios del CMS que están activos y dentro del rango de fecha válido para el portal."""
    if not current_user.client_id:
        raise HTTPException(status_code=403, detail="Not a client user")
        
    now = datetime.utcnow()
    
    query = (
        select(PortalAnnouncement)
        .where(PortalAnnouncement.is_active == True)
        .where(PortalAnnouncement.start_date <= now)
        .order_by(desc(PortalAnnouncement.priority), desc(PortalAnnouncement.created_at))
    )
    result = await session.execute(query)
    announcements = result.scalars().all()
    
    # Filtrar en Python por end_date (si lo hiciéramos en SQL usaríamos una condición OR, pero esto es simple)
    valid_announcements = []
    for ann in announcements:
        if ann.end_date is None or ann.end_date >= now:
            valid_announcements.append(ann)
            
    return valid_announcements

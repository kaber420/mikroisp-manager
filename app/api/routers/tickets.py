# app/api/routers/tickets.py

import uuid as uuid_pkg
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select, col, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...db.engine import get_session
from ...models.user import User
from ...models.client import Client
from ...models.ticket import Ticket, TicketMessage
from ...core.users import require_technician, current_active_user

# Models Pydantic (Internal for API)
from pydantic import BaseModel

class TicketCreate(BaseModel):
    client_id: uuid_pkg.UUID
    subject: str
    description: str
    priority: str = "normal"

class TicketUpdateStatus(BaseModel):
    status: str

class TicketReply(BaseModel):
    content: str
    media_url: Optional[str] = None

class TicketMessageRead(BaseModel):
    id: uuid_pkg.UUID
    sender_type: str
    sender_id: Optional[str]
    content: str
    created_at: datetime
    media_url: Optional[str]

class TicketRead(BaseModel):
    id: uuid_pkg.UUID
    ticket_id: int
    subject: str
    description: str
    status: str
    priority: str
    client_name: str
    assigned_tech_id: Optional[uuid_pkg.UUID]
    assigned_tech_username: Optional[str]
    created_at: datetime
    updated_at: datetime
    messages: List[TicketMessageRead] = []

router = APIRouter(prefix="/tickets", tags=["Tickets"])

@router.get("/", response_model=List[TicketRead])
async def list_tickets(
    status_filter: Optional[str] = None,
    client_id: Optional[uuid_pkg.UUID] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(require_technician),
    session: AsyncSession = Depends(get_session)
):
    query = select(Ticket).options(selectinload(Ticket.messages))
    
    if status_filter and status_filter != 'todos':
        query = query.where(Ticket.status == status_filter)
    
    if client_id:
        query = query.where(Ticket.client_id == client_id)

    # Search Logic
    if search:
        search_term = f"%{search}%"
        # We need to join with Client to search client names
        # But `select(Ticket)` is the base.
        # To filter by client name, we need a join or subquery.
        # Let's try a join.
        # Note: SQLModel select(Ticket) returns Ticket objects.
        # If we join, we must be careful with what is returned.
        # But we can just add where clauses if we join correctly.
        
        # A simple approach for subject/description first:
        # query = query.where(col(Ticket.subject).ilike(search_term) | col(Ticket.description).ilike(search_term))
        
        # To include client name:
        query = query.join(Client, isouter=True).where(
            col(Ticket.subject).ilike(search_term) | 
            col(Ticket.description).ilike(search_term) |
            col(Client.name).ilike(search_term)
        )

    query = query.order_by(desc(Ticket.updated_at)).offset(offset).limit(limit)
    
    result = await session.exec(query)
    tickets = result.all()
    
    # Enrichment (getting client names and tech names)
    ticket_responses = []
    
    client_ids = {t.client_id for t in tickets}
    tech_ids = {t.assigned_tech_id for t in tickets if t.assigned_tech_id}
    
    clients = {}
    if client_ids:
        c_res = await session.exec(select(Client).where(col(Client.id).in_(client_ids)))
        clients = {c.id: c.name for c in c_res.all()}
        
    techs = {}
    if tech_ids:
        u_res = await session.exec(select(User).where(col(User.id).in_(tech_ids)))
        techs = {u.id: u.username for u in u_res.all()}

    for t in tickets:
        msgs = [
            TicketMessageRead(
                id=m.id,
                sender_type=m.sender_type,
                sender_id=m.sender_id,
                content=m.content,
                created_at=m.created_at,
                media_url=m.media_url
            ) for m in sorted(t.messages, key=lambda x: x.created_at)
        ]
        
        ticket_responses.append(TicketRead(
            id=t.id,
            ticket_id=t.ticket_id,
            subject=t.subject,
            description=t.description,
            status=t.status,
            priority=t.priority,
            client_name=clients.get(t.client_id, "Unknown"),
            assigned_tech_id=t.assigned_tech_id,
            assigned_tech_username=techs.get(t.assigned_tech_id),
            created_at=t.created_at,
            updated_at=t.updated_at,
            messages=msgs
        ))
        
    return ticket_responses

@router.get("/{ticket_id}", response_model=TicketRead)
async def get_ticket_detail(
    ticket_id: uuid_pkg.UUID,
    current_user: User = Depends(require_technician),
    session: AsyncSession = Depends(get_session)
):
    query = select(Ticket).where(Ticket.id == ticket_id).options(selectinload(Ticket.messages))
    result = await session.exec(query)
    ticket = result.first()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
        
    client = await session.get(Client, ticket.client_id)
    tech = None
    if ticket.assigned_tech_id:
        tech = await session.get(User, ticket.assigned_tech_id)
        
    msgs = [
            TicketMessageRead(
                id=m.id,
                sender_type=m.sender_type,
                sender_id=m.sender_id,
                content=m.content,
                created_at=m.created_at,
                media_url=m.media_url
            ) for m in sorted(ticket.messages, key=lambda x: x.created_at)
    ]
    
    return TicketRead(
        id=ticket.id,
        ticket_id=ticket.ticket_id,
        subject=ticket.subject,
        description=ticket.description,
        status=ticket.status,
        priority=ticket.priority,
        client_name=client.name if client else "Unknown",
        assigned_tech_id=ticket.assigned_tech_id,
        assigned_tech_username=tech.username if tech else None,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        messages=msgs
    )

@router.post("/", response_model=TicketRead)
async def create_ticket(
    ticket_in: TicketCreate,
    current_user: User = Depends(require_technician),
    session: AsyncSession = Depends(get_session)
):
    # Verify client
    client = await session.get(Client, ticket_in.client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
        
    new_ticket = Ticket(
        client_id=ticket_in.client_id,
        subject=ticket_in.subject,
        description=ticket_in.description,
        priority=ticket_in.priority,
        status="open",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    session.add(new_ticket)
    await session.commit()
    await session.refresh(new_ticket)
    
    return TicketRead(
        id=new_ticket.id,
        ticket_id=new_ticket.ticket_id,
        subject=new_ticket.subject,
        description=new_ticket.description,
        status=new_ticket.status,
        priority=new_ticket.priority,
        client_name=client.name,
        assigned_tech_id=new_ticket.assigned_tech_id,
        assigned_tech_username=None,
        created_at=new_ticket.created_at,
        updated_at=new_ticket.updated_at,
        messages=[]
    )

@router.post("/{ticket_id}/reply")
async def reply_ticket(
    ticket_id: uuid_pkg.UUID,
    reply: TicketReply,
    current_user: User = Depends(require_technician),
    session: AsyncSession = Depends(get_session)
):
    ticket = await session.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
        
    # Ownership Logic: Block if assigned to someone else
    if ticket.assigned_tech_id and ticket.assigned_tech_id != current_user.id:
        raise HTTPException(
            status_code=403, 
            detail=f"This ticket is assigned to another technician."
        )

    # Auto-claim if unassigned
    if not ticket.assigned_tech_id:
        ticket.assigned_tech_id = current_user.id

    # Create message
    new_msg = TicketMessage(
        ticket_id=ticket.id,
        sender_type="tech",
        sender_id=str(current_user.id), # Store User UUID as string
        content=reply.content,
        media_url=reply.media_url,
        created_at=datetime.utcnow()
    )
    
    session.add(new_msg)
    
    # Update ticket timestamp and possibly status
    ticket.updated_at = datetime.utcnow()
    # Optionally change status if it was 'open' to 'pending'
    if ticket.status == 'open':
        ticket.status = 'pending'
        
    session.add(ticket)
    await session.commit()

    # --- Telegram Notification Logic ---
    print(f"DEBUG TIM: Trying to notify client {ticket.client_id}")
    try:
        # Fetch client to get telegram_contact
        client = await session.get(Client, ticket.client_id)
        
        if not client:
             print("DEBUG TIM: Client not found in DB")
        else:
             print(f"DEBUG TIM: Client found. Contact: {client.telegram_contact}")

        # Check if client exists and has telegram contact
        if client and client.telegram_contact:
            from ...utils.settings_utils import get_setting_sync
            from telegram import Bot
            
            TOKEN = get_setting_sync("client_bot_token")
            print(f"DEBUG TIM: Token found? {'Yes' if TOKEN else 'No'}")
            
            if TOKEN:
                try:
                    bot = Bot(token=TOKEN)
                    
                    # Determine display ID (use UUID short if ticket_id is 0)
                    display_id = str(ticket.ticket_id)
                    if ticket.ticket_id == 0:
                        display_id = str(ticket.id)[-6:]

                    # Format message for the user
                    msg_text = (
                        f"🔔 *Nueva respuesta de soporte*\n"
                        f"Ticket: `#{display_id}`\n\n"
                        f"{reply.content}"
                    )
                    
                    print(f"DEBUG TIM: Sending message to {client.telegram_contact}")
                    await bot.send_message(
                        chat_id=client.telegram_contact,
                        text=msg_text,
                        parse_mode="Markdown"
                    )
                    print("DEBUG TIM: Message sent successfully")
                except Exception as inner_e:
                     print(f"DEBUG TIM: Error inside bot send: {inner_e}")
                     import logging
                     logger = logging.getLogger(__name__)
                     logger.error(f"Error sending Telegram notification (inner): {inner_e}")
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in Telegram notification flow: {e}")

    # -----------------------------------
    
    # --- REAL-TIME NOTIFICATION ---
    import httpx
    import os
    try:
        # Notify the web monitor so other sessions update
        params = {"ticket_id": str(ticket.id)}
        # No message/level here to avoid showing a toast to the person who just sent it
        # The frontend will check the ticket_id and refresh if open
        port = os.getenv("UVICORN_PORT", "8100")
        async with httpx.AsyncClient(timeout=1.0) as client:
            await client.post(f"http://127.0.0.1:{port}/api/internal/notify-monitor-update", json=params)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to notify web monitor on tech reply: {e}")
    # -----------------------------------
    
    return {"status": "success", "message": "Reply added"}

@router.put("/{ticket_id}/status")
async def update_ticket_status(
    ticket_id: uuid_pkg.UUID,
    status_in: TicketUpdateStatus,
    current_user: User = Depends(require_technician),
    session: AsyncSession = Depends(get_session)
):
    ticket = await session.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
        
    # Ownership Check
    if ticket.assigned_tech_id and ticket.assigned_tech_id != current_user.id:
         raise HTTPException(
            status_code=403, 
            detail=f"This ticket is assigned to another technician."
        )

    ticket.status = status_in.status
    ticket.updated_at = datetime.utcnow()
    
    # Logic:
    # 1. If status is 'open', Release ticket (clear assigned_tech_id)
    # 2. If status is NOT 'open', ensure assigned_tech_id is set (Auto-claim)
    
    if ticket.status == 'open':
        # Release ticket
        ticket.assigned_tech_id = None
    else:
        # If resolving/pending, ensure assigned_tech is set to current user if it was None
        if not ticket.assigned_tech_id:
            ticket.assigned_tech_id = current_user.id
        
    session.add(ticket)
    await session.commit()
    
    return {"status": "success", "new_status": ticket.status}

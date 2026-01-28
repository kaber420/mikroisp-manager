# Archivo: bot_client/commands/menu_handler.py

import logging
import os
import sys
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ContextTypes, CommandHandler, MessageHandler, ConversationHandler, filters
)
from sqlmodel import select, Session
from app.db.engine_sync import sync_engine as engine
from app.models.client import Client

# Add path to find core modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from core.ticket_manager import crear_ticket, obtener_tickets, agregar_respuesta_a_ticket

logger = logging.getLogger(__name__)

# Estados
(MENU_PRINCIPAL, AWAITING_FALLA) = range(2)
BTN_REPORTAR = "📞 Reportar Falla / Solicitar Ayuda"
BTN_VER_ESTADO = "📋 Ver Mis Tickets"
BTN_SOLICITAR_AGENTE = "🙋 Solicitar Agente Humano"

def get_main_keyboard_markup() -> ReplyKeyboardMarkup:
    keyboard = [[BTN_REPORTAR], [BTN_VER_ESTADO], [BTN_SOLICITAR_AGENTE]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_client_by_telegram_id(telegram_id: str):
    try:
        with Session(engine) as session:
            statement = select(Client).where(
                (Client.telegram_contact == telegram_id) | 
                (Client.whatsapp_number == telegram_id)
            )
            return session.exec(statement).first()
    except Exception as e:
        logger.error(f"Error lookup client: {e}")
        return None

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    user_id = str(user.id)
    client = get_client_by_telegram_id(user_id)

    if client:
        await update.message.reply_text(
            f"¡Hola de nuevo, {client.name}! 👋\n\n¿En qué podemos ayudarte?",
            reply_markup=get_main_keyboard_markup()
        )
        return MENU_PRINCIPAL
    else:
        mensaje_registro = (
            "Hola, bienvenido. 👋\n\n"
            "Parece que tu cuenta de Telegram no está vinculada.\n"
            "Por favor, comparte este ID con soporte:\n"
            f"`{user_id}`"
        )
        await update.message.reply_text(mensaje_registro, parse_mode="Markdown")
        return ConversationHandler.END

async def reportar_falla(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Por favor, describe tu problema detalladamente:", reply_markup=ReplyKeyboardRemove())
    return AWAITING_FALLA

async def guardar_solicitud(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    descripcion = update.message.text
    user_id = str(update.effective_user.id)
    user_name = update.effective_user.first_name
    
    # Intenta buscar nombre real
    client = get_client_by_telegram_id(user_id)
    client_name = client.name if client else user_name
    
    # Crear ticket
    ticket_id = crear_ticket(
        cliente_external_id=user_id, 
        cliente_plataforma='telegram',
        cliente_nombre=client_name, 
        cliente_ip_cpe="N/A",
        tipo_solicitud='Soporte General', 
        descripcion=descripcion
    )

    if ticket_id:
        # Visual ID adjustment (last 6 chars?)
        short_id = ticket_id[-6:]
        await update.message.reply_text(
            f"✅ Solicitud recibida. Ticket: `{short_id}`.", 
            parse_mode="Markdown", 
            reply_markup=get_main_keyboard_markup()
        )
    else:
        await update.message.reply_text("❌ Error al crear ticket.", reply_markup=get_main_keyboard_markup())
    
    return MENU_PRINCIPAL

async def ver_estado(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # This logic needs to be robust: obtener_tickets filter by client via telegram_contact?
    # core.ticket_manager.obtener_tickets currently filters by parameters passed.
    # But I need to filter by CLIENT ID, not external_id inside the table (Ticket table has client_id UUID).
    # My refactored obter_tickets uses `estado` and `dias`. It DOES NOT support client filtering yet?
    # Wait, I checked `core/ticket_manager.py` and it ignored `cliente_external_id` argument in the implementation?!
    # I need to fix `obtener_tickets` in `core` to support finding tickets for a client!
    # Or just implement custom query here.
    
    user_id = str(update.effective_user.id)
    client = get_client_by_telegram_id(user_id)
    if not client:
        await update.message.reply_text("No encontrado.", reply_markup=get_main_keyboard_markup())
        return MENU_PRINCIPAL
        
    # Custom query because `obtener_tickets` might be limited
    try:
        with Session(engine) as session:
            # Import Ticket locally
            from app.models.ticket import Ticket
            tickets = session.exec(select(Ticket).where(Ticket.client_id == client.id).limit(5).order_by(Ticket.created_at.desc())).all()
            
            if not tickets:
                await update.message.reply_text("No tienes tickets recientes.", reply_markup=get_main_keyboard_markup())
                return MENU_PRINCIPAL
                
            msg = "📋 **Mis Tickets**:\n\n"
            emojis = {'open': '🟢', 'pending': '🟡', 'resolved': '🔵', 'closed': '⚫️'}
            for t in tickets:
                emoji = emojis.get(t.status, '⚪️')
                msg += f"{emoji} `{t.id.__str__()[-6:]}` | {t.status}\nDesc: {t.description[:20]}...\n\n"
            
            await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_main_keyboard_markup())
            
    except Exception as e:
        logger.error(f"Error fetching tickets: {e}")
        await update.message.reply_text("Error al obtener tickets.")
        
    return MENU_PRINCIPAL

async def solicitar_agente(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    user_name = update.effective_user.first_name
    
    client = get_client_by_telegram_id(user_id)
    client_name = client.name if client else user_name
    
    # Crear ticket de alta prioridad
    ticket_id = crear_ticket(
        cliente_external_id=user_id, 
        cliente_plataforma='telegram',
        cliente_nombre=client_name, 
        cliente_ip_cpe="N/A",
        tipo_solicitud='Solicitud de Soporte en Vivo', 
        descripcion="Cliente solicita hablar con un agente humano ahora."
    )

    if ticket_id:
        await update.message.reply_text(
            "🙋 Solicitud enviada. Un agente se pondrá en contacto pronto.\n"
            "Puedes escribir aquí y el agente lo verá.", 
            reply_markup=get_main_keyboard_markup()
        )
    else:
        await update.message.reply_text("❌ Error al solicitar agente.", reply_markup=get_main_keyboard_markup())
    
    return MENU_PRINCIPAL

async def handle_chat_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Checks if the user has an active chat session (open ticket with specific subject).
    If so, routes message to ticket.
    If not, falls back to showing menu.
    """
    user_id = str(update.effective_user.id)
    message_text = update.message.text
    
    logger.info(f"📩 DEBUG: Chat handler triggered for user {user_id}. Text: {message_text}")
    
    # Check for active "Live Support" ticket
    # We need a way to check this efficiently. 
    # For now, we fetch recent open tickets for this client and check subject.
    
    client = get_client_by_telegram_id(user_id)
    if not client:
        logger.info(f"🤔 DEBUG: Client not found for Telegram ID {user_id}")
        await show_menu_if_client(update, context)
        return
    else:
        logger.info(f"👤 DEBUG: Client found: {client.name} (ID: {client.id})")

    # TODO: Optimize this query to get ONLY open tickets for this client
    # Current helper obtener_tickets is too generic.
    # We will use a direct session here for specific logic.
    try:
        from app.models.ticket import Ticket
        with Session(engine) as session:
            # Check for ANY open ticket that implies "Chat Mode"? 
            # Or strictly "Solicitud de Soporte en Vivo"?
            # Match only tickets that are truly active (not closed or resolved)
            # and pick the most recently updated one to avoid stale routing
            statement = select(Ticket).where(
                Ticket.client_id == client.id,
                Ticket.subject == "Solicitud de Soporte en Vivo",
                Ticket.status.in_(["open", "pending"]) 
            ).order_by(Ticket.updated_at.desc())
            
            active_ticket = session.exec(statement).first()
            
            if active_ticket:
                logger.info(f"🎫 DEBUG: Active ticket found: {active_ticket.id} - Status: {active_ticket.status}")
                # Route message
                success = agregar_respuesta_a_ticket(
                    ticket_id=active_ticket.id,
                    mensaje=message_text,
                    autor_tipo='client',
                    autor_id=user_id # using telegram id as author id for client
                )
                if success:
                    logger.info("✅ DEBUG: Message added to ticket successfully.")
                    # Optional: Ack? No, chat should be seamless. 
                    # Maybe double check tick?
                    pass
                else:
                    logger.error("❌ DEBUG: Failed to add message to ticket.")
                    await update.message.reply_text("⚠️ Error al enviar mensaje.")
            else:
                logger.info("🚫 DEBUG: No active 'Solicitud de Soporte en Vivo' ticket found.")
                # No active chat session, show menu
                await show_menu_if_client(update, context)
                
    except Exception as e:
        logger.error(f"Error in chat handler: {e}")
        await show_menu_if_client(update, context)

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Cancelado.", reply_markup=get_main_keyboard_markup())
    return MENU_PRINCIPAL

async def show_menu_if_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Menú:", reply_markup=get_main_keyboard_markup())

main_menu_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start_command)],
    states={
        MENU_PRINCIPAL: [
            CommandHandler("start", start_command),
            MessageHandler(filters.Regex(f"^{BTN_REPORTAR}"), reportar_falla),
            MessageHandler(filters.Regex(f"^{BTN_VER_ESTADO}"), ver_estado),
            MessageHandler(filters.Regex(f"^{BTN_SOLICITAR_AGENTE}"), solicitar_agente),
            # Allow chat processing even while in menu state
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_chat_messages),
        ],
        AWAITING_FALLA: [MessageHandler(filters.TEXT & ~filters.COMMAND, guardar_solicitud)],
    },
    fallbacks=[CommandHandler("cancelar", cancelar)],
)

unknown_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, show_menu_if_client)
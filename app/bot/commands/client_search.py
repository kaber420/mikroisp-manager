# commands/client_search.py
"""
Módulo de comandos para que los técnicos busquen información de clientes.
Comando /cliente: Permite buscar por nombre, teléfono o ID.
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters
)
from sqlmodel import select, Session, or_, col
from app.db.engine_sync import sync_engine as engine
from app.models.client import Client
from app.models.service import ClientService
from app.models.plan import Plan
from app.bot.core.auth import check_authorization
from app.bot.core.middleware import rate_limit

logger = logging.getLogger(__name__)

# --- Estados para la conversación ---
AWAITING_SEARCH, SELECT_CLIENT = range(2)

CALLBACK_PREFIX = "clientsearch"


def _escape_markdown(text: str) -> str:
    """Escape special characters for Telegram Markdown."""
    if not text:
        return "N/A"
    # Escape backticks, asterisks, underscores
    for char in ['`', '*', '_', '[', ']']:
        text = text.replace(char, f'\\{char}')
    return text


def _build_client_detail_message(client: Client, service: ClientService = None, plan: Plan = None) -> str:
    """Build formatted message with client and service details."""
    status_emoji = "✅" if client.service_status == "active" else "⏸️"
    
    msg = (
        f"👤 *Detalles del Cliente*\n\n"
        f"*Nombre:* {_escape_markdown(client.name)}\n"
        f"*Teléfono:* {_escape_markdown(client.phone_number)}\n"
        f"*WhatsApp:* {_escape_markdown(client.whatsapp_number)}\n"
        f"*Dirección:* {_escape_markdown(client.address)}\n"
        f"*Email:* {_escape_markdown(client.email)}\n"
        f"*Estado:* {status_emoji} `{client.service_status}`\n"
        f"*Día de Cobro:* `{client.billing_day or 'N/A'}`\n"
    )
    
    if client.notes:
        msg += f"*Notas:* {_escape_markdown(client.notes)}\n"
    
    msg += "\n"
    
    if service:
        service_status_emoji = "✅" if service.status == "active" else "⏸️"
        plan_name = plan.name if plan else (service.profile_name or "N/A")
        
        msg += (
            f"🌐 *Servicio*\n"
            f"*Tipo:* `{service.service_type}`\n"
            f"*Plan:* `{plan_name}`\n"
            f"*IP:* `{service.ip_address or 'Dinámica'}`\n"
            f"*Usuario PPPoE:* `{service.pppoe_username or 'N/A'}`\n"
            f"*Router:* `{service.router_host}`\n"
            f"*Estado:* {service_status_emoji} `{service.status}`\n"
        )
    else:
        msg += "🌐 *Servicio*\n_Sin servicio asignado._\n"
    
    if client.coordinates:
        # Create Google Maps link from coordinates
        coords_clean = client.coordinates.replace(" ", "")
        maps_url = f"https://www.google.com/maps?q={coords_clean}"
        msg += f"\n📍 [Ver Ubicación en Mapa]({maps_url})"
    
    return msg


def _build_client_list_keyboard(clients: list) -> InlineKeyboardMarkup:
    """Build keyboard with list of matching clients."""
    keyboard = []
    for client in clients[:10]:  # Max 10 results
        # Truncate name if too long
        label = client.name[:25] + "..." if len(client.name) > 25 else client.name
        callback_data = f"{CALLBACK_PREFIX}:select:{client.id}"
        keyboard.append([InlineKeyboardButton(f"👤 {label}", callback_data=callback_data)])
    
    keyboard.append([InlineKeyboardButton("❌ Cerrar", callback_data=f"{CALLBACK_PREFIX}:cancel")])
    return InlineKeyboardMarkup(keyboard)


def _build_detail_keyboard(client_id: str) -> InlineKeyboardMarkup:
    """Build keyboard for client detail view."""
    keyboard = [
        [InlineKeyboardButton("🔍 Nueva Búsqueda", callback_data=f"{CALLBACK_PREFIX}:new_search")],
        [InlineKeyboardButton("❌ Cerrar", callback_data=f"{CALLBACK_PREFIX}:cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)


def _search_clients(search_term: str) -> list:
    """Search clients by name, phone, or telegram ID."""
    with Session(engine) as session:
        search_pattern = f"%{search_term}%"
        statement = select(Client).where(
            or_(
                col(Client.name).ilike(search_pattern),
                col(Client.phone_number).ilike(search_pattern),
                col(Client.whatsapp_number).ilike(search_pattern),
                col(Client.telegram_contact).ilike(search_pattern),
                col(Client.address).ilike(search_pattern)
            )
        ).limit(15)
        results = session.exec(statement).all()
        # Expunge to detach from session
        return [client for client in results]


def _get_client_with_service(client_id: str):
    """Get client with their service and plan info."""
    from uuid import UUID
    with Session(engine) as session:
        client_uuid = UUID(client_id) if isinstance(client_id, str) else client_id
        client = session.get(Client, client_uuid)
        if not client:
            return None, None, None
        
        # Get service
        service_stmt = select(ClientService).where(ClientService.client_id == client_uuid)
        service = session.exec(service_stmt).first()
        
        plan = None
        if service and service.plan_id:
            plan = session.get(Plan, service.plan_id)
        
        return client, service, plan


@rate_limit(limit=5, window=10)
async def cliente_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for /cliente command."""
    if not await check_authorization(update, context):
        await update.message.reply_text("❌ Acceso denegado.")
        return ConversationHandler.END
    
    await update.message.reply_text(
        "🔍 *Buscar Cliente*\n\n"
        "Por favor, ingresa el nombre, teléfono, dirección o ID del cliente:",
        parse_mode="Markdown"
    )
    return AWAITING_SEARCH


async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle search term input."""
    search_term = update.message.text.strip()
    
    if len(search_term) < 2:
        await update.message.reply_text("⚠️ Ingresa al menos 2 caracteres para buscar.")
        return AWAITING_SEARCH
    
    try:
        clients = _search_clients(search_term)
        
        if not clients:
            await update.message.reply_text(
                f"❌ No se encontraron clientes con: `{_escape_markdown(search_term)}`\n\n"
                "Intenta con otro término o usa /cancel para salir.",
                parse_mode="Markdown"
            )
            return AWAITING_SEARCH
        
        if len(clients) == 1:
            # Single result - show details directly
            client, service, plan = _get_client_with_service(str(clients[0].id))
            if client:
                await update.message.reply_text(
                    _build_client_detail_message(client, service, plan),
                    reply_markup=_build_detail_keyboard(str(client.id)),
                    parse_mode="Markdown"
                )
                return SELECT_CLIENT
            else:
                await update.message.reply_text("❌ Error al obtener datos del cliente.")
                return AWAITING_SEARCH
        
        # Multiple results - show selection keyboard
        await update.message.reply_text(
            f"📋 *Resultados* ({len(clients)} encontrados)\n\n"
            "Selecciona un cliente:",
            reply_markup=_build_client_list_keyboard(clients),
            parse_mode="Markdown"
        )
        return SELECT_CLIENT
        
    except Exception as e:
        logger.error(f"Error searching clients: {e}", exc_info=True)
        await update.message.reply_text("❌ Error en la búsqueda. Intenta de nuevo.")
        return AWAITING_SEARCH


async def selection_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle client selection from keyboard."""
    query = update.callback_query
    await query.answer()
    
    if not await check_authorization(update, context):
        await query.edit_message_text("❌ Acceso denegado.")
        return ConversationHandler.END
    
    parts = query.data.split(":")
    action = parts[1] if len(parts) > 1 else ""
    
    try:
        if action == "cancel":
            await query.edit_message_text("👋 Búsqueda cerrada.")
            return ConversationHandler.END
        
        elif action == "new_search":
            await query.edit_message_text(
                "🔍 *Buscar Cliente*\n\n"
                "Por favor, ingresa el nombre, teléfono, dirección o ID del cliente:",
                parse_mode="Markdown"
            )
            return AWAITING_SEARCH
        
        elif action == "select":
            client_id = parts[2]
            client, service, plan = _get_client_with_service(client_id)
            
            if client:
                await query.edit_message_text(
                    _build_client_detail_message(client, service, plan),
                    reply_markup=_build_detail_keyboard(client_id),
                    parse_mode="Markdown"
                )
            else:
                await query.edit_message_text("❌ Cliente no encontrado.")
                return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error in selection handler: {e}", exc_info=True)
        await query.edit_message_text("❌ Error inesperado.")
        return ConversationHandler.END
    
    return SELECT_CLIENT


async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /cancel command."""
    await update.message.reply_text("👋 Búsqueda cancelada.")
    return ConversationHandler.END


# --- Conversation Handler Export ---
client_search_conversation_handler = ConversationHandler(
    entry_points=[CommandHandler("cliente", cliente_command)],
    states={
        AWAITING_SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_handler)],
        SELECT_CLIENT: [
            CallbackQueryHandler(selection_handler, pattern=rf"^{CALLBACK_PREFIX}:.*$"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, search_handler)  # Allow new search from detail
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel_handler)],
    per_user=True
)

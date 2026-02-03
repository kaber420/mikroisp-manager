# commands/ticket_manager.py
"""
Módulo de comandos y handlers para que los técnicos gestionen tickets.
Interfaz de usuario para Telegram: comandos, botones, paginación.
Utiliza core/ticket_manager.py para la lógica de negocio y acceso a datos.
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
from app.bot.core.auth import check_authorization
from app.bot.core.middleware import rate_limit
from app.bot.core.ticket_manager import (
    obtener_tickets,
    obtener_ticket_por_id,
    actualizar_estado_ticket,
    auto_asignar_ticket_a_tecnico,
    agregar_respuesta_a_ticket
)

logger = logging.getLogger(__name__)

# --- Estados para la conversación ---
MENU, AWAITING_RESPONSE = range(2)

# --- Constantes del módulo ---
TICKETS_PER_PAGE = 5
ESTADOS_PERMITIDOS = ['open', 'pending', 'resolved', 'closed'] # Updated to match models/ticket.py defaults? or map? 
# Model says default="open".
ESTADOS_ESP = {'open': 'Abierto', 'pending': 'Pendiente', 'resolved': 'Resuelto', 'closed': 'Cerrado'}
ESTADOS_PARA_FILTRAR = ['todos'] + list(ESTADOS_ESP.keys())
CALLBACK_PREFIX = "ticketmgr"

def _build_error_keyboard() -> InlineKeyboardMarkup:
    """Keyboard shown on errors to allow navigation back."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Volver a Lista", callback_data=f"{CALLBACK_PREFIX}:back_to_list")],
        [InlineKeyboardButton("❌ Cerrar", callback_data=f"{CALLBACK_PREFIX}:cancel")]
    ])

def _build_filter_keyboard(current_filters: dict) -> InlineKeyboardMarkup:
    estado_actual = current_filters.get('estado', 'todos')
    dias_actual = current_filters.get('dias', 'todos')
    filter_row = [
        InlineKeyboardButton(f"Estado: {estado_actual}", callback_data=f"{CALLBACK_PREFIX}:filter:estado_menu"),
        InlineKeyboardButton(f"Días: {dias_actual}", callback_data=f"{CALLBACK_PREFIX}:filter:dias")
    ]
    return InlineKeyboardMarkup([filter_row])

def _build_state_filter_keyboard() -> InlineKeyboardMarkup:
    keyboard = []
    row = []
    for i, estado in enumerate(ESTADOS_PARA_FILTRAR):
        label = ESTADOS_ESP.get(estado, estado).capitalize() if estado != 'todos' else 'Todos'
        row.append(InlineKeyboardButton(label, callback_data=f"{CALLBACK_PREFIX}:set_filter_state:{estado}"))
        if (i + 1) % 3 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data=f"{CALLBACK_PREFIX}:apply_filters")])
    return InlineKeyboardMarkup(keyboard)

def _build_pagination_keyboard(page: int, total_pages: int, filters: dict) -> InlineKeyboardMarkup:
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"{CALLBACK_PREFIX}:page:{page-1}")) # Simplified data to save space
    
    button_text = f"Pág {page}/{total_pages} ❌"
    nav_buttons.append(InlineKeyboardButton(button_text, callback_data=f"{CALLBACK_PREFIX}:cancel"))
    
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"{CALLBACK_PREFIX}:page:{page+1}")) # Simplified
    
    return InlineKeyboardMarkup([nav_buttons])

def _build_ticket_list_keyboard(tickets: list, filters: dict) -> InlineKeyboardMarkup:
    keyboard = []
    emojis = {'open': '🟢', 'pending': '🟡', 'resolved': '🔵', 'closed': '⚫️'}
    for ticket in tickets:
        estado_emoji = emojis.get(ticket['estado'], '⚪️')
        # Use short ID logic if possible, but we rely on UUID. Truncate visual ID?
        visual_id = ticket['id'][:8]
        button_text = f"{estado_emoji} {visual_id} | {ticket.get('cliente_nombre', 'N/A')[:10]}"
        # Ensure callback data is short enough. UUID=36. Prefix=16. Total 52. Safe.
        callback_data = f"{CALLBACK_PREFIX}:detail:{ticket['id']}" 
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    return InlineKeyboardMarkup(keyboard)

def _build_ticket_list_message(page: int, total_pages: int, total_count: int, filters: dict) -> str:
    if total_count == 0:
        return f"ℹ️ *No se encontraron tickets*\n*Filtros:* Estado=`{filters.get('estado', 'todos')}`"
    mensaje = f"📋 *Lista de Tickets* ({total_count})\n"
    mensaje += f"*Filtros:* Estado=`{filters.get('estado', 'todos')}`\n"
    return mensaje

def _build_ticket_detail_message(ticket: dict) -> str:
    return (
        f"🎫 *Ticket* `{ticket['id']}`\n\n"
        f"👤 *Cliente:* {ticket.get('cliente_nombre')}\n"
        f"🛠️ *Asunto:* `{ticket.get('tipo_solicitud')}`\n"
        f"📊 *Estado:* `{ticket.get('estado')}`\n"
        f"🧑‍🔧 *Técnico:* `{ticket.get('tecnico_asignado') or 'Nadie'}`\n"
        f"📅 *Creado:* `{ticket.get('fecha_creacion')}`\n\n"
        f"📝 *Descripción:*\n`{ticket.get('descripcion')}`\n"
    )

def _build_ticket_detail_keyboard(ticket_id: str, filters: dict) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("📌 Tomar", callback_data=f"{CALLBACK_PREFIX}:take:{ticket_id}"),
            InlineKeyboardButton("🔄 Estado", callback_data=f"{CALLBACK_PREFIX}:change_state:{ticket_id}")
        ],
        [InlineKeyboardButton("💬 Responder", callback_data=f"{CALLBACK_PREFIX}:respond:{ticket_id}")],
        [InlineKeyboardButton("⬅️ Volver", callback_data=f"{CALLBACK_PREFIX}:back_to_list")] # Removing filters from callback to save space
    ]
    return InlineKeyboardMarkup(keyboard)

def _build_change_state_keyboard(ticket_id: str) -> InlineKeyboardMarkup:
    """Build keyboard for state changes. Uses short state names to fit 64-byte limit."""
    keyboard = []; row = []
    for i, estado in enumerate(ESTADOS_PERMITIDOS):
        # Use short callback data: prefix + action + state only
        # ticket_id is stored in context.user_data['current_ticket_id']
        row.append(InlineKeyboardButton(ESTADOS_ESP.get(estado, estado), callback_data=f"{CALLBACK_PREFIX}:ss:{estado}"))
        if (i + 1) % 2 == 0: keyboard.append(row); row = []
    if row: keyboard.append(row)
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data=f"{CALLBACK_PREFIX}:back_detail")])
    return InlineKeyboardMarkup(keyboard)

@rate_limit(limit=5, window=10)
async def ver_tickets_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await check_authorization(update, context):
        await update.message.reply_text("❌ Acceso denegado."); return ConversationHandler.END
    
    initial_filters = {'estado': 'open', 'dias': 'todos'}
    context.user_data['current_ticket_filters'] = initial_filters
    await _show_ticket_list(update, context, page=1, filters=initial_filters)
    return MENU

async def _show_ticket_list(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int, filters: dict):
    try:
        estado_filtro = filters.get('estado') if filters.get('estado') != 'todos' else None
        dias_filtro = None # Simplified for now
        
        tickets, total_count = obtener_tickets(estado=estado_filtro, dias=dias_filtro, limit=TICKETS_PER_PAGE, offset=(page - 1) * TICKETS_PER_PAGE)
        total_pages = max(1, (total_count + TICKETS_PER_PAGE - 1) // TICKETS_PER_PAGE)
        
        mensaje = _build_ticket_list_message(page, total_pages, total_count, filters)
        all_button_rows = []
        all_button_rows.extend(_build_ticket_list_keyboard(tickets, filters).inline_keyboard)
        all_button_rows.extend(_build_filter_keyboard(filters).inline_keyboard)
        
        pagination_keyboard = _build_pagination_keyboard(page, total_pages, filters)
        if pagination_keyboard.inline_keyboard: all_button_rows.extend(pagination_keyboard.inline_keyboard)
        
        reply_markup = InlineKeyboardMarkup(all_button_rows)
        if update.callback_query: await update.callback_query.edit_message_text(mensaje, reply_markup=reply_markup, parse_mode="Markdown")
        else: await update.message.reply_text(mensaje, reply_markup=reply_markup, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error list ticket: {e}", exc_info=True)
        msg = "❌ Error al listar tickets."
        if update.callback_query: await update.callback_query.edit_message_text(msg)
        else: await update.message.reply_text(msg)

async def ticket_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query; await query.answer()
    if not await check_authorization(update, context):
        await query.edit_message_text("❌ Acceso denegado."); return ConversationHandler.END
        
    tecnico_id_telegram = str(update.effective_user.id)
    parts = query.data.split(":")
    action = parts[1] if len(parts) > 1 else ""
    
    # Retrieve filters from context instead of callback data (to save space)
    filters = context.user_data.get('current_ticket_filters', {'estado': 'open'})
    
    try:
        if action == "cancel":
            await query.edit_message_text("👋 Gestor de tickets cerrado.")
            return ConversationHandler.END
            
        elif action == "page":
            page = int(parts[2])
            await _show_ticket_list(update, context, page=page, filters=filters)
            
        elif action == "filter":
            filter_type = parts[2]
            if filter_type == "estado_menu":
                await query.edit_message_text("Filtrar por estado:", reply_markup=_build_state_filter_keyboard())
                
        elif action == "set_filter_state":
            filters['estado'] = parts[2]
            context.user_data['current_ticket_filters'] = filters
            await _show_ticket_list(update, context, page=1, filters=filters)
            
        elif action == "apply_filters" or action == "back_to_list":
             await _show_ticket_list(update, context, page=1, filters=filters)
             
        elif action == "detail":
            ticket_id = parts[2]
            ticket = obtener_ticket_por_id(ticket_id)
            if ticket:
                await query.edit_message_text(
                    _build_ticket_detail_message(ticket), 
                    reply_markup=_build_ticket_detail_keyboard(ticket_id, filters), 
                    parse_mode="Markdown"
                )
            else:
                 await query.edit_message_text("❌ Ticket no encontrado.", reply_markup=_build_error_keyboard())

        elif action == "take":
            ticket_id = parts[2]
            if auto_asignar_ticket_a_tecnico(ticket_id, tecnico_id_telegram):
                await query.answer("✅ Ticket asignado.", show_alert=True)
                # Refresh view
                ticket = obtener_ticket_por_id(ticket_id)
                await query.edit_message_text(_build_ticket_detail_message(ticket), reply_markup=_build_ticket_detail_keyboard(ticket_id, filters), parse_mode="Markdown")
            else:
                await query.answer("❌ Error al asignar.", show_alert=True)
                
        elif action == "change_state":
            ticket_id = parts[2]
            context.user_data['current_ticket_id'] = ticket_id  # Store for later
            await query.edit_message_reply_markup(reply_markup=_build_change_state_keyboard(ticket_id))
            
        elif action == "ss":  # short for set_state
            ticket_id = context.user_data.get('current_ticket_id')
            if not ticket_id:
                await query.answer("Error: ticket no encontrado.", show_alert=True)
                return MENU
            nuevo_estado = parts[2]
            if actualizar_estado_ticket(ticket_id, nuevo_estado, tecnico_id_telegram):
                await query.answer(f"✅ Estado: {ESTADOS_ESP.get(nuevo_estado, nuevo_estado)}", show_alert=True)
                ticket = obtener_ticket_por_id(ticket_id)
                await query.edit_message_text(_build_ticket_detail_message(ticket), reply_markup=_build_ticket_detail_keyboard(ticket_id, filters), parse_mode="Markdown")
            else:
                await query.answer("Error al actualizar estado.", show_alert=True)
        
        elif action == "back_detail":
            ticket_id = context.user_data.get('current_ticket_id')
            if ticket_id:
                ticket = obtener_ticket_por_id(ticket_id)
                if ticket:
                    await query.edit_message_text(_build_ticket_detail_message(ticket), reply_markup=_build_ticket_detail_keyboard(ticket_id, filters), parse_mode="Markdown")
                    return MENU
            await _show_ticket_list(update, context, page=1, filters=filters)
                
        elif action == "respond":
            context.user_data['ticket_id_response'] = parts[2]
            await query.edit_message_text("📝 Escribe tu respuesta:")
            return AWAITING_RESPONSE
            
    except Exception as e:
        logger.error(f"Error handler: {e}", exc_info=True)
        try:
            await query.edit_message_text("❌ Error inesperado.", reply_markup=_build_error_keyboard())
        except Exception:
            pass  # Message might already be deleted or unchanged
        
    return MENU

async def save_response_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ticket_id = context.user_data.get('ticket_id_response')
    if not ticket_id:
        return MENU
        
    resp = update.message.text
    tech_id = str(update.effective_user.id) # Use telegram ID, core converts if needed or stores string
    
    if agregar_respuesta_a_ticket(ticket_id, resp, 'tech', tech_id):
        await update.message.reply_text("✅ Respuesta guardada. 📤 Enviado al cliente.")
        # Return to menu?
        # Ideally show ticket detail again.
        ticket = obtener_ticket_por_id(ticket_id)
        if ticket:
             filters = context.user_data.get('current_ticket_filters', {})
             await update.message.reply_text(
                _build_ticket_detail_message(ticket), 
                reply_markup=_build_ticket_detail_keyboard(ticket_id, filters), 
                parse_mode="Markdown"
            )
    else:
        await update.message.reply_text("❌ Error.")
        
    return MENU

async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Operación cancelada.")
    return ConversationHandler.END

ticket_manager_conversation_handler = ConversationHandler(
    entry_points=[CommandHandler("tickets", ver_tickets_command), CommandHandler("ver_tickets", ver_tickets_command)],
    states={
        MENU: [CallbackQueryHandler(ticket_menu_handler, pattern=rf"^{CALLBACK_PREFIX}:.*$")],
        AWAITING_RESPONSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_response_handler)],
    },
    fallbacks=[CommandHandler("cancel", cancel_handler)],
    per_user=True
)
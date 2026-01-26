# app/bot/commands/location_cmd.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from sqlmodel import select, Session, col
from app.db.engine_sync import sync_engine as engine
from app.models.client import Client

# Estados de la conversación
LOCATION, SEARCH_CLIENT, CONFIRM = range(3)

async def start_here(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia el flujo de actualización de ubicación."""
    await update.message.reply_text("📍 Por favor, envía tu ubicación actual (adjunto 'Location' 📎).")
    return LOCATION

async def receive_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe la ubicación y pide buscar el cliente."""
    user_location = update.message.location
    context.user_data['lat'] = user_location.latitude
    context.user_data['lon'] = user_location.longitude
    
    await update.message.reply_text(
        f"✅ Coordenadas recibidas: `{user_location.latitude}, {user_location.longitude}`\n"
        "🔍 Ahora, **escribe el nombre** (o parte del nombre) del cliente para buscarlo:",
        parse_mode="Markdown"
    )
    return SEARCH_CLIENT

async def search_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Busca clientes por nombre en la BD."""
    query_text = update.message.text
    
    try:
        with Session(engine) as session:
            # Búsqueda insensible a mayúsculas/minúsculas
            statement = select(Client).where(col(Client.name).ilike(f"%{query_text}%")).limit(5)
            clients = session.exec(statement).all()
            
        if not clients:
            await update.message.reply_text("❌ No encontré clientes con ese nombre. Intenta de nuevo o escribe /cancel:")
            return SEARCH_CLIENT
            
        keyboard = []
        for client in clients:
            # Usar ID UUID, esperamos que quepa en callback_data (64 bytes limit standard, UUID string is 36 chars so it fits)
            keyboard.append([InlineKeyboardButton(f"{client.name}", callback_data=f"loc_client_{client.id}")])
            
        keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="loc_cancel")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text("🔽 Selecciona el cliente:", reply_markup=reply_markup)
        return CONFIRM
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error al buscar: {str(e)}")
        return ConversationHandler.END

async def confirm_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Actualiza las coordenadas del cliente seleccionado."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data == "loc_cancel":
        await query.edit_message_text("❌ Operación cancelada.")
        return ConversationHandler.END
        
    import uuid
    client_id_str = data.replace("loc_client_", "")
    lat = context.user_data.get('lat')
    lon = context.user_data.get('lon')
    
    try:
        with Session(engine) as session:
            # Fix: Cast string ID to UUID object for SQLModel/SQLAlchemy
            client_id = uuid.UUID(client_id_str)
            client = session.get(Client, client_id)
            if client:
                client.coordinates = f"{lat},{lon}"
                session.add(client)
                session.commit()
                await query.edit_message_text(f"✅ ¡Ubicación actualizada para **{client.name}**!\n📍 `{lat}, {lon}`", parse_mode="Markdown")
            else:
                await query.edit_message_text("❌ Error: Cliente no encontrado (tal vez fue borrado).")
    except Exception as e:
         await query.edit_message_text(f"❌ Error al guardar: {str(e)}")
            
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operación cancelada.")
    return ConversationHandler.END

# El Handler principal a exportar
location_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("here", start_here)],
    states={
        LOCATION: [MessageHandler(filters.LOCATION, receive_location)],
        SEARCH_CLIENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_client)],
        CONFIRM: [CallbackQueryHandler(confirm_client, pattern="^loc_")]
    },
    fallbacks=[CommandHandler("cancel", cancel)]
)

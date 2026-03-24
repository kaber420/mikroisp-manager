import os
from livekit import api
from app.core.config import settings

def create_room_token(room_name: str, participant_identity: str, participant_name: str, is_tech: bool) -> str:
    """
    Genera un Token JWT para que un usuario se conecte a una sala de LiveKit.
    - room_name: El nombre o ID de la sala (puede ser el ID del Ticket).
    - participant_identity: Un UUID o identificador único para el usuario.
    - participant_name: El nombre a mostrar en la interfaz.
    - is_tech: Si es True, da permisos de administrador en la sala.
    """
    if not settings.LIVEKIT_API_KEY or not settings.LIVEKIT_API_SECRET:
        raise ValueError("Las credenciales de LiveKit no están configuradas en las variables de entorno.")
        
    token = api.AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
    token.with_identity(str(participant_identity))
    token.with_name(participant_name)
    
    # Otorgar permisos
    grant = api.VideoGrant(
        room_join=True,
        room=room_name,
        can_publish=True,
        can_publish_data=True,
        can_subscribe=True,
        room_admin=is_tech,      # El técnico puede expulsar, silenciar, etc.
    )
    token.with_grants(grant)
    
    return token.to_jwt()

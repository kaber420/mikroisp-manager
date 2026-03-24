from fastapi import WebSocket, status
import logging
from typing import Optional

from app.core.config import settings
from app.core.users import get_jwt_strategy

logger = logging.getLogger("app.websocket.auth")

async def verify_ws_origin_and_token(
    websocket: WebSocket,
    access_token: Optional[str],
    allowed_roles: list[str] = ["admin"]
) -> bool:
    """
    Valida el Origen y el Token JWT para conexiones WebSocket.
    Retorna True si es válido, False (y cierra la conexión) si es inválido.
    """
    # 1. Validar Origen (Seguridad CSWSH)
    origin = websocket.headers.get("origin")
    allowed_origins = settings.get_allowed_origins()
    
    if origin:
        origin_normalized = origin.rstrip("/")
        is_trusted = any(origin_normalized == a for a in allowed_origins)
        if not is_trusted:
            logger.warning(f"🛡️ WebSocket BLOQUEADO: origen {origin} no permitido")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return False

    # Si estamos en entorno en donde CORS debería estar presente pero no lo está.
    # Como los navegadores SIEMPRE envían origin para WebSockets iniciados por JS 
    # desde otra web, la ausencia puede que venga de un cliente non-browser (script python, etc).
    # Como la seguridad por cookie se usa por browser, la falta de origin puede ser ok
    # o sospechosa, pero CORS usualmente asume que si hay Origin, hay que chequearlo.

    # 2. Validar Autenticación (Auth JWT Cookie/Header)
    is_authorized = False
    authenticated_user = None
    
    if access_token:
        try:
            strategy = get_jwt_strategy()
            import jwt
            try:
                # FastAPI-Users typical audience is ["fastapi-users:auth"]
                data = jwt.decode(
                    access_token, 
                    strategy.secret, 
                    audience=["fastapi-users:auth"], 
                    algorithms=[strategy.algorithm]
                )
            except jwt.PyJWTError as e:
                logger.debug(f"Invalid JWT: {e}")
                data = None
                
            if data and "sub" in data:
                user_id = data["sub"]
                from app.db.engine import async_session_maker
                from sqlalchemy import select
                from app.models.user import User
                async with async_session_maker() as session:
                    result = await session.execute(select(User).where(User.id == user_id))
                    authenticated_user = result.scalars().first()
                    
            if authenticated_user and authenticated_user.is_active and authenticated_user.role in allowed_roles:
                is_authorized = True
        except Exception as e:
            logger.debug(f"Error validando token WS: {e}")

    if not is_authorized:
        logger.warning(f"🛡️ WebSocket RECHAZADO: Falla de autenticación o rol insuficiente. Roles requeridos: {allowed_roles}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return False

    # Adjuntar usuario al scope del WebSocket para uso posterior
    websocket.scope["user"] = authenticated_user

    return True

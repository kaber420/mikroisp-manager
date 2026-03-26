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
    
    # Intentar obtener token de la cabecera si no vino por cookie (útil en dev/proxies)
    if not access_token:
        auth_header = websocket.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            access_token = auth_header.split(" ")[1]
            print("DEBUG: WS Auth - Token obtained from Authorization header")

    print(f"DEBUG: WS Auth - access_token exists: {access_token is not None}")
    if not access_token:
        print(f"DEBUG: WS Auth - Headers: {dict(websocket.headers)}")

    if access_token:
        try:
            strategy = get_jwt_strategy()
            import jwt
            try:
                # FastAPI-Users typical audience is ["fastapi-users:auth"], but current strategy doesn't set it.
                # We disable audience verification to stay compatible with the global JWTStrategy.
                data = jwt.decode(
                    access_token, 
                    strategy.secret, 
                    options={"verify_aud": False}, 
                    algorithms=[strategy.algorithm]
                )
            except jwt.PyJWTError as e:
                logger.debug(f"Invalid JWT: {e}")
                data = None
                
            if data and "sub" in data:
                import uuid
                try:
                    user_id_str = data["sub"]
                    user_id = uuid.UUID(user_id_str)
                    from app.db.engine import async_session_maker
                    from sqlalchemy import select
                    from app.models.user import User
                    async with async_session_maker() as session:
                        result = await session.execute(select(User).where(User.id == user_id))
                        authenticated_user = result.scalars().first()
                    
                    if authenticated_user:
                        print(f"DEBUG: WS Auth - User Found: {authenticated_user.username}, Role: {authenticated_user.role}")
                    else:
                        print(f"DEBUG: WS Auth - User NOT Found in DB for ID: {user_id}")
                except Exception as e:
                    print(f"DEBUG: WS Auth - Error identifying user from sub '{data.get('sub')}': {e}")
                
            if authenticated_user and authenticated_user.is_active and authenticated_user.role in allowed_roles:
                is_authorized = True
            else:
                reason = "No user found" if not authenticated_user else f"Inactive or wrong role ({authenticated_user.role})"
                print(f"DEBUG: WS Auth - Authorization failed: {reason}. Allowed: {allowed_roles}")
        except Exception as e:
            print(f"DEBUG: WS Auth - Global Exception: {e}")
            logger.error(f"Error fatal validando token WS: {e}", exc_info=True)

    if not is_authorized:
        logger.warning(f"🛡️ WebSocket RECHAZADO: Falla de autenticación o rol insuficiente. Roles requeridos: {allowed_roles}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return False

    # Adjuntar usuario al scope del WebSocket para uso posterior
    websocket.scope["user"] = authenticated_user

    return True

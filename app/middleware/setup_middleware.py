import logging
import os
from fastapi import Request, status
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

logger = logging.getLogger("app.middleware.setup")

# Cache global para no consultar la BD en cada petición una vez que sabemos que hay usuarios
_SYSTEM_HAS_USERS_CACHE = False

class SetupMiddleware(BaseHTTPMiddleware):
    """
    Verifica si el sistema tiene al menos un usuario administrador.
    Si no lo tiene, redirige todas las peticiones (que no sean estáticas o de setup) a /setup.
    """
    
    # Rutas que no deben ser redirigidas
    EXEMPT_PATHS = {
        "/setup",       # Página SPA del setup (GET)
        "/api/setup",   # Endpoint real del backend (POST)
        "/uploads",
        "/docs",
        "/openapi.json",
        "/favicon.png"
    }

    STATIC_EXTENSIONS = (
        ".js", ".css", ".png", ".jpg", ".jpeg", ".svg", ".woff", ".woff2", ".ttf", ".ico", ".json"
    )

    def _is_exempt(self, path: str) -> bool:
        if path in self.EXEMPT_PATHS:
            return True
        if path.startswith("/_app/") or path.startswith("/assets/"):
            return True
        if path.startswith("/ws"):
            return True
        if any(path.endswith(ext) for ext in self.STATIC_EXTENSIONS):
            return True
        return False

    async def dispatch(self, request: Request, call_next):
        global _SYSTEM_HAS_USERS_CACHE
        
        path = request.url.path
        
        if self._is_exempt(path):
            return await call_next(request)

        # Si ya sabemos que hay usuarios, pasamos directo
        if _SYSTEM_HAS_USERS_CACHE:
            if path == "/setup":
                return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
            return await call_next(request)

        has_users = False
        try:
            from app.db.engine import engine
            from app.models.user import User
            
            async with AsyncSession(engine) as session:
                result = await session.execute(select(User).limit(1))
                has_users = result.first() is not None
                if has_users:
                    _SYSTEM_HAS_USERS_CACHE = True
                    
        except Exception as e:
            logger.error(f"Error comprobando estado de DB en middleware: {e}")
            return await call_next(request)

        if not has_users:
            logger.info(f"Redirigiendo acceso a '{path}' hacia /setup porque no hay usuarios.")
            return RedirectResponse(url="/setup", status_code=status.HTTP_307_TEMPORARY_REDIRECT)

        if path == "/setup":
            logger.warning("Intento de acceso a /setup, pero el sistema ya configurado. Redirigiendo a /dashboard.")
            return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)

        return await call_next(request)

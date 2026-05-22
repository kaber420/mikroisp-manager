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
        "/api/infra",   # Permitir configuración de infraestructura sin usuarios
        "/api/settings/system", # Permitir configuración de servicios sin usuarios
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
        # Soporte para subrutas
        if any(path.startswith(p + "/") for p in self.EXEMPT_PATHS):
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
        
        # 1. Comprobar proactivamente si el sistema ya tiene usuarios si no está cacheado
        if not _SYSTEM_HAS_USERS_CACHE:
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
                # En caso de fallo crítico en base de datos, dejamos que la petición continúe
                pass

        # 2. Si ya hay usuarios, desactivar por completo los endpoints de setup con 404
        if _SYSTEM_HAS_USERS_CACHE:
            if path == "/setup" or path == "/api/setup" or path.startswith("/api/setup/"):
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={"detail": "Not Found"}
                )
            
            # Cualquier otra petición de la app pasa normalmente (incluye exenciones como /uploads, /docs, etc.)
            if self._is_exempt(path):
                return await call_next(request)
            return await call_next(request)

        # 3. Si NO hay usuarios (Modo Bootstrap / Instalación inicial)
        # Permitimos el acceso a las rutas exentas (que incluyen /setup y /api/setup)
        if self._is_exempt(path):
            return await call_next(request)
            
        # Si intenta acceder a cualquier otra ruta sin haber usuarios, redirigir a /setup
        logger.info(f"Redirigiendo acceso a '{path}' hacia /setup porque no hay usuarios.")
        return RedirectResponse(url="/setup", status_code=status.HTTP_307_TEMPORARY_REDIRECT)

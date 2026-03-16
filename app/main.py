# app/main.py
import os

from dotenv import load_dotenv
from app.core.config import settings

# Cargar variables de entorno desde .env ANTES de cualquier otra cosa
load_dotenv()

# --- PERFORMANCE: Instalar uvloop en Linux/macOS ---
import sys
if sys.platform != "win32":
    try:
        import asyncio
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        print("✅ uvloop instalado como event loop")
    except ImportError:
        pass  # uvloop no instalado, usamos el loop por defecto

import asyncio
from typing import Optional, List, Any

from fastapi import Cookie, FastAPI, Request, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

# SlowAPI (Rate Limiting)
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.exceptions import HTTPException as StarletteHTTPException

from .api.aps import main as aps_main_api
from .api.aps import spectral as aps_spectral_api
from .api.clients import main as clients_main_api
from .api.cpes import main as cpes_main_api
from .api.plans import main as plans_main_api
from .api.routers import main as routers_main_api
from .api.security import main as security_main_api
from .api.settings import main as settings_main_api
from .api.stats import main as stats_main_api
from .api.switches import main as switches_main_api
from .api.users import main as users_main_api
from .api.zonas import infra as zonas_infra_api
from .api.zonas import main as zonas_main_api
from .api.tickets import main as tickets_main_api
from .api.broadcast import main as broadcast_main_api
from .api.health import router as health_router
from .api.setup import main as setup_api
from .api.portal import main as portal_api
from .api.broadcast import announcements as broadcast_announcements_api
from .api.waiting_room import endpoints as waiting_room_api

# Shared Core Modules

# FastAPI Users imports
from .core.users import (
    ACCESS_TOKEN_COOKIE_NAME,
    auth_backend_cookie,
    auth_backend_jwt,
    fastapi_users,
)
from .core.websockets import manager

# CSP Middleware with Nonces
from .csp_middleware import CSPMiddleware

from .schemas.user import UserCreate, UserRead, UserUpdate

# Importaciones de API Routers

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables and background services on application startup, and cleanup on shutdown"""
    from .core.bootstrap import bootstrap_system
    bootstrap_system()
    print("✅ System bootstrapped (DB & Admin)")

    # --- Redict Cache: Conectar si está habilitado ---
    if settings.CACHE_BACKEND == "redict":
        from .utils.cache.redict_store import redict_manager

        redict_url = settings.REDICT_URL
        connected = await redict_manager.connect(redict_url)
        if connected:
            print("✅ Redict cache conectado")
            # Iniciar listener Pub/Sub para notificaciones en tiempo real
            asyncio.create_task(manager.start_redict_listener())
            print("✅ Redict Pub/Sub listener iniciado")
        else:
            print("⚠️ Redict no disponible, usando cache en memoria")

    # --- Cache V2: Iniciar MonitorScheduler ---
    # Este scheduler consulta routers suscritos y llena el cache
    # Los WebSockets leen del cache en lugar de conectar directamente
    from .services.monitoring.monitor_scheduler import monitor_scheduler

    asyncio.create_task(monitor_scheduler.run())
    print("✅ MonitorScheduler iniciado (Cache V2)")

    # --- Cache V2: Iniciar APMonitorScheduler ---
    # Mismo patrón para APs
    from .services.monitoring.ap_monitor_scheduler import ap_monitor_scheduler

    asyncio.create_task(ap_monitor_scheduler.run())
    print("✅ APMonitorScheduler iniciado (Cache V2)")


    # --- Cache V2: Iniciar SwitchMonitorScheduler ---
    # Mismo patrón para Switches
    from .services.monitoring.switch_monitor_scheduler import switch_monitor_scheduler

    asyncio.create_task(switch_monitor_scheduler.run())
    print("✅ SwitchMonitorScheduler iniciado (Cache V2)")

    # --- BOT MANAGER (Hybrid Architecture) ---
    from .services.core.bot_manager import bot_manager
    asyncio.create_task(bot_manager.start())
    
    # --- STATUS REPORTER (File-Based for TUI) ---
    from .services.monitoring.status_reporter import status_reporter_loop
    asyncio.create_task(status_reporter_loop())
    
    yield # Aquí es donde la aplicación corre y sirve las peticiones HTTP
    
    # --- SHUTDOWN ---
    # Desconectar Redict si estaba conectado
    if settings.CACHE_BACKEND == "redict":
        from .utils.cache.redict_store import redict_manager

        if redict_manager.is_connected:
            await redict_manager.disconnect()
            print("✅ Redict desconectado")

    # Detener Bots
    from .services.core.bot_manager import bot_manager
    await bot_manager.stop()

app = FastAPI(title="µMonitor Pro", version="0.5.0", lifespan=lifespan)


# --- Configuración de SlowAPI ---
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter


from starlette.responses import Response


def custom_rate_limit_handler(request: Request, exc: Exception) -> Response:
    detail = getattr(exc, "detail", str(exc))
    return JSONResponse(content={"error": f"Rate limit exceeded: {detail}"}, status_code=429)


app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)

APP_ENV = settings.APP_ENV


# --- SEGURIDAD: CONFIGURACIÓN CORS ESTRICTA ---
origins = settings.get_allowed_origins()

# Auto-detectar hosts permitidos
allowed_hosts_env = settings.ALLOWED_HOSTS.split(",")
allowed_hosts = set(allowed_hosts_env)
allowed_hosts.update(["localhost", "127.0.0.1"])

# Auto-detectar IP local para entornos LAN (Out-of-the-Box)
import socket
try:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        allowed_hosts.add(local_ip)
        app_port = settings.UVICORN_PORT
        allowed_hosts.add(f"{local_ip}:{app_port}")
except Exception:
    pass

app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(allowed_hosts))

# --- SEGURIDAD: CSP con Nonces ---
app.add_middleware(CSPMiddleware)

# --- OPTIMIZACIÓN: Compresión Gzip ---
app.add_middleware(GZipMiddleware, minimum_size=1000)


# --- SEGURIDAD: ORIGIN SHIELD (Protección CSRF por verificación de origen)
from urllib.parse import urlparse

from starlette.middleware.base import BaseHTTPMiddleware


class TrustedOriginMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces origin checking for state-changing HTTP methods.
    Blocks POST, PUT, DELETE, PATCH requests that don't originate from trusted origins.
    This provides CSRF protection without requiring tokens in the frontend.
    """

    UNSAFE_METHODS = {"POST", "PUT", "DELETE", "PATCH"}
    SAFE_PATHS = {
        "/api/internal/",
        "/auth/jwt/login",
        "/api/webhooks/",  # Webhooks are server-to-server (no Origin header)
    }  # Internal endpoints & Login don't need Origin check

    async def dispatch(self, request: Request, call_next):
        if request.method in self.UNSAFE_METHODS:
            # Skip origin check for internal/safe paths
            if any(request.url.path.startswith(path) for path in self.SAFE_PATHS):
                return await call_next(request)

            origin = request.headers.get("origin")
            referer = request.headers.get("referer")

            # Determine the source of the request
            request_origin = None
            if origin:
                request_origin = origin
            elif referer:
                parsed = urlparse(referer)
                request_origin = f"{parsed.scheme}://{parsed.netloc}"

            # SECURITY: Block requests without Origin/Referer from browsers.
            # Exception: Allow if it's likely a non-browser client (API tools).
            # Browser requests for POST/PUT/DELETE ALWAYS include Origin or Referer.
            if not request_origin:
                # Check if this looks like an API client (has Authorization header)
                # or internal tool vs a browser without origin headers (suspicious)
                has_auth = request.headers.get("authorization") is not None
                if not has_auth:
                    print(
                        f"🛡️ [Origin Shield] BLOCKED: Missing Origin/Referer for {request.method} {request.url.path}"
                    )
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={"detail": "Forbidden: Missing origin information"},
                    )
                # Allow API clients with explicit auth
                return await call_next(request)

            # Normalize both sides for comparison
            is_trusted = False
            request_origin_normalized = request_origin.rstrip("/")

            for allowed in origins:
                allowed_normalized = allowed.rstrip("/")
                # Support both http and https for the same host in development
                if request_origin_normalized == allowed_normalized:
                    is_trusted = True
                    break
                # Also check if only the scheme differs (http vs https)
                if request_origin_normalized.replace(
                    "https://", "http://"
                ) == allowed_normalized.replace("https://", "http://"):
                    is_trusted = True
                    break

            if not is_trusted:
                # [NEW] Allow requests with Authorization header (Mobile Apps/API Clients)
                # Mobile apps often have different origins (e.g. capacitor://) but send valid auth tokens.
                # Only browser-based CSRF relies on cookies without custom headers.
                if request.headers.get("authorization"):
                    return await call_next(request)

                print(f"🛡️ [Origin Shield] BLOCKED request from untrusted origin: {request_origin}")
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Forbidden: Invalid origin"},
                )

        return await call_next(request)


app.add_middleware(TrustedOriginMiddleware)

# --- SETUP MIDDLEWARE ---
from app.middleware.setup_middleware import SetupMiddleware
app.add_middleware(SetupMiddleware)



# --- SEGURIDAD: CABECERAS DE SEGURIDAD HTTP ---
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)

    # Prevenir que el sitio sea embebido en iframes (Clickjacking)
    # DENY es más seguro: si necesitas modales de impresión, usa CSP frame-ancestors 'self'
    response.headers["X-Frame-Options"] = "DENY"

    # Prevenir que el navegador intente adivinar el tipo de contenido (MIME Sniffing)
    response.headers["X-Content-Type-Options"] = "nosniff"

    # Filtro XSS legacy para navegadores antiguos
    response.headers["X-XSS-Protection"] = "1; mode=block"

    # Controlar cuánta información se envía en el Referer
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # HSTS: Forzar HTTPS (solo si APP_ENV es producción)
    if settings.APP_ENV == "production":
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )

    # Permissions Policy: Restringir acceso a hardware y APIs sensibles si no se usan
    # Ajusta según las necesidades de tu app (cámara, micro, gps, etc.)
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=(), interest-cohort=()"
    )

    # NOTA: Content-Security-Policy ahora es manejado por CSPMiddleware con nonces

    return response


# --- SEGURIDAD: RATE LIMITING MIDDLEWARE ---
# Simple in-memory rate limiter for authentication endpoints
from collections import defaultdict
from time import time

_rate_limit_store: dict[str, list[float]] = defaultdict(list)
_RATE_LIMITS = {
    "/auth/cookie/login": (5, 60),  # 5 attempts per 60 seconds
    "/auth/register": (3, 60),  # 3 attempts per 60 seconds
    "/auth/jwt/login": (10, 60),  # 10 attempts per 60 seconds (API)
}


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting for sensitive authentication endpoints"""
    path = request.url.path

    # Check if this path needs rate limiting
    if path in _RATE_LIMITS and request.method == "POST":
        max_requests, window_seconds = _RATE_LIMITS[path]
        client_ip = request.client.host if request.client else "unknown"
        key = f"{client_ip}:{path}"

        now = time()
        # Clean old entries outside the time window
        _rate_limit_store[key] = [
            timestamp for timestamp in _rate_limit_store[key] if now - timestamp < window_seconds
        ]

        # Check if rate limit exceeded
        if len(_rate_limit_store[key]) >= max_requests:
            return JSONResponse(
                content={"error": "Rate limit exceeded. Please try again later."},
                status_code=429,
            )

        # Record this request
        _rate_limit_store[key].append(now)

    return await call_next(request)


# --- Configuración de Directorios ---
current_dir = os.path.dirname(__file__)
uploads_dir = os.path.join(current_dir, "..", "data", "uploads")

os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")


# --- GLOBAL EXCEPTION HANDLER ---

# Handler for Starlette HTTP Exceptions
@app.exception_handler(StarletteHTTPException)
async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
    return await _handle_http_exception(request, exc.status_code, exc.detail)


# Handler for FastAPI HTTP Exceptions (raised by dependencies like RoleChecker)
from fastapi import HTTPException as FastAPIHTTPException


@app.exception_handler(FastAPIHTTPException)
async def fastapi_http_exception_handler(request: Request, exc: FastAPIHTTPException):
    return await _handle_http_exception(request, exc.status_code, exc.detail)


# Handler for domain exceptions (AppError hierarchy)
from .core.exceptions import AppError


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    """
    Maneja todas las excepciones de dominio automáticamente.
    Cada subclase de AppError define su propio status_code.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


# Handler de seguridad: captura IntegrityError no manejados por servicios
from sqlalchemy.exc import IntegrityError


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    """Red de seguridad: captura cualquier IntegrityError que se escape de los servicios."""
    import logging
    logging.getLogger("app.errors").error(f"IntegrityError no capturado por servicio: {exc}")
    return JSONResponse(
        status_code=409,
        content={"detail": "El recurso ya existe o viola una restricción de unicidad"},
    )



async def _handle_http_exception(request: Request, status_code: int, detail: str):
    """Common handler for both Starlette and FastAPI HTTP exceptions."""
    return JSONResponse(status_code=status_code, content={"detail": detail})


# --- ENDPOINTS WEBSOCKET Y NOTIFICACIÓN INTERNA ---
@app.websocket("/ws/dashboard")
async def websocket_dashboard(
    websocket: WebSocket, umonitorpro_access_token_v2: str = Cookie(None)
):
    import logging
    logger = logging.getLogger("app.websocket")
    logger.info(f"🔌 WebSocket connection attempt from {websocket.client}")
    
    # --- SECURITY: Validate authentication cookie ---
    if umonitorpro_access_token_v2 is None:
        logger.warning(f"⚠️ [WebSocket] Rechazado: No cookie '{ACCESS_TOKEN_COOKIE_NAME}'.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # --- SECURITY: Validate Origin header to prevent CSWSH ---
    origin = websocket.headers.get("origin")
    logger.info(f"🔌 WebSocket origin: {origin}, checking against allowed: {origins}")
    
    if origin:
        origin_normalized = origin.rstrip("/")
        is_trusted_origin = False
        for allowed in origins:
            allowed_normalized = allowed.rstrip("/")
            if origin_normalized == allowed_normalized:
                is_trusted_origin = True
                break
            # Also check http vs https variance
            if origin_normalized.replace("https://", "http://") == allowed_normalized.replace(
                "https://", "http://"
            ):
                is_trusted_origin = True
                break

        if not is_trusted_origin:
            logger.warning(f"🛡️ [WebSocket] BLOCKED: Untrusted origin {origin}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    # --- Accept connection ---
    await manager.connect(websocket)
    logger.info(f"✅ WebSocket connected! Total clients: {len(manager.active_connections)}")
    try:
        while True:
            data = await websocket.receive_text()
            # Handle ping/pong for keep-alive
            if data == 'ping':
                await websocket.send_text('pong')
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info(f"🔌 WebSocket disconnected. Remaining clients: {len(manager.active_connections)}")


@app.post("/api/internal/notify-monitor-update", include_in_schema=False)
async def notify_monitor_update(
    message: Optional[str] = None, 
    level: str = "info", 
    ticket_id: Optional[str] = None,
    request: Request = None
):
    """
    Endpoint interno llamado por monitor.py o bots.
    Ahora soporta tanto query params como JSON body.
    """
    import logging
    logger = logging.getLogger("app.notifications")
    
    # Try to get data from JSON and merge with existing parameters
    if request:
        try:
            # Only try to read JSON if there's a content-type header suggesting JSON
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                body = await request.json()
                if body:
                    message = message or body.get("message")
                    level = body.get("level") or level
                    ticket_id = ticket_id or body.get("ticket_id")
                    logger.info(f"Received notification merge: query_msg={message}, json={body}")
        except Exception as e:
            logger.error(f"Error parsing JSON in notify-monitor-update: {e}")
            pass

    logger.info(f"Notify broadcast: msg={message}, level={level}, ticket={ticket_id}")
    
    payload = {"type": "db_updated"}
    if message:
        payload["notification"] = message
        payload["level"] = level
    if ticket_id:
        payload["ticket_id"] = ticket_id
        
    await manager.broadcast_event("db_updated", payload)
    return {"status": "broadcast_sent", "payload": payload}


# --- ROUTERS INCLUSION ---

# 0. Setup Wizard (only active on first run)
app.include_router(setup_api.router, prefix="/api")

# 1. Main Views (Pages & Legacy Auth)

# 2. FastAPI Users Routers (Behavior largely replaces old manual auth)
# Rate limiting is handled by rate_limit_middleware for auth endpoints
app.include_router(
    fastapi_users.get_auth_router(auth_backend_jwt),
    prefix="/api/auth/jwt",
    tags=["FastAPI Users - JWT Auth"],
)
app.include_router(
    fastapi_users.get_auth_router(auth_backend_cookie),
    prefix="/api/auth/cookie",
    tags=["FastAPI Users - Cookie Auth"],
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/api/auth",
    tags=["FastAPI Users - Registration"],
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/api/users",
    tags=["FastAPI Users - Users Management"],
)

# 3. Domain API Routers
app.include_router(routers_main_api.router, prefix="/api", tags=["Routers"])
app.include_router(aps_main_api.router, prefix="/api", tags=["APs"])
app.include_router(aps_spectral_api.router, prefix="/api", tags=["APs - Spectral"])
app.include_router(cpes_main_api.router, prefix="/api", tags=["CPEs"])
app.include_router(clients_main_api.router, prefix="/api", tags=["Clients"])
app.include_router(zonas_main_api.router, prefix="/api", tags=["Zonas"])
app.include_router(zonas_infra_api.router, prefix="/api", tags=["Zonas Infrastructure"])
app.include_router(users_main_api.router, prefix="/api", tags=["Users"])
app.include_router(settings_main_api.router, prefix="/api", tags=["Settings"])
app.include_router(stats_main_api.router, prefix="/api", tags=["Stats"])
app.include_router(plans_main_api.router, prefix="/api", tags=["Plans"])
app.include_router(switches_main_api.router, prefix="/api", tags=["Switches"])
app.include_router(security_main_api.router, prefix="/api", tags=["Security"])
app.include_router(tickets_main_api.router, prefix="/api", tags=["Tickets"])
app.include_router(portal_api.router, prefix="/api", tags=["Portal de Clientes"])
app.include_router(broadcast_main_api.router, prefix="/api/broadcast", tags=["Broadcast"])
app.include_router(broadcast_announcements_api.router, prefix="/api/broadcast", tags=["Broadcast - CMS"])
app.include_router(waiting_room_api.router, prefix="/api/waiting-room", tags=["Waiting Room"])
app.include_router(health_router, prefix="/api", tags=["Health"])

# --- WEBHOOKS PARA BOTS ---
@app.post("/api/webhooks/{bot_type}/{token}", include_in_schema=False)
async def bot_webhook(bot_type: str, token: str, request: Request):
    """
    Endpoint único para recibir updates de Telegram.
    bot_type: 'client' o 'tech'
    """
    from .services.core.bot_manager import bot_manager
    
    try:
        data = await request.json()
        await bot_manager.process_update(bot_type, token, data)
        return {"status": "ok"}
    except Exception as e:
        print(f"⚠️ Webhook Error: {e}")
        return {"status": "error", "detail": str(e)}

# --- FRONTEND SPA FALLBACK ---
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend(full_path: str, request: Request):
    """Sirve la Single Page Application (SvelteKit) y sus archivos estáticos."""
    import os
    
    # Primero buscamos en la ruta de producción (build en la raíz)
    prod_frontend_dir = os.path.join(current_dir, "..", "build")
    # Luego la ruta de desarrollo
    dev_frontend_dir = os.path.join(current_dir, "..", "frontend-v2-daisy", "build")
    
    frontend_dir = prod_frontend_dir if os.path.isdir(prod_frontend_dir) else dev_frontend_dir
    file_path = os.path.join(frontend_dir, full_path)
    
    # Determinar MIME type explícito para evitar problemas con SvelteKit
    media_type = None
    if file_path.endswith(".js"):
        media_type = "application/javascript"
    elif file_path.endswith(".css"):
        media_type = "text/css"
    elif file_path.endswith(".html"):
        media_type = "text/html"
    elif file_path.endswith(".json"):
        media_type = "application/json"
    elif file_path.endswith(".png"):
        media_type = "image/png"
    elif file_path.endswith(".ico"):
        media_type = "image/x-icon"
    elif file_path.endswith(".svg"):
        media_type = "image/svg+xml"

    # Si es un archivo estático real (js, css, png)
    if os.path.isfile(file_path):
        return FileResponse(file_path, media_type=media_type)
        
    # Fallback a index.html para rutas de la SPA (ej: /setup, /dashboard)
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.isfile(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Inyectar el nonce de CSP generado en el Middleware
        if hasattr(request, "state") and hasattr(request.state, "csp_nonce"):
            nonce = request.state.csp_nonce
            content = content.replace("<script", f'<script nonce="{nonce}"')
            
        return HTMLResponse(content)
        
    # Si no existe el build
    return JSONResponse(
        status_code=404, 
        content={"detail": "Frontend no construido o no disponible. Ejecuta npm run build en frontend-v2-daisy."}
    )

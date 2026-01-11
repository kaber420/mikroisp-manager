# app/main.py
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env ANTES de cualquier otra cosa
load_dotenv()

import asyncio
from fastapi import (
    FastAPI,
    Request,
    WebSocket,
    WebSocketDisconnect,
    Cookie,
    status,
    Depends
)
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic_settings import BaseSettings

# SlowAPI (Rate Limiting)
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# FastAPI Users imports
from .core.users import (
    fastapi_users,
    auth_backend_jwt,
    auth_backend_cookie,
    ACCESS_TOKEN_COOKIE_NAME,
)
from .schemas.user import UserRead, UserCreate, UserUpdate
from .db.engine import create_db_and_tables

# Shared Core Modules
from .core.templates import templates
from .core.websockets import manager

# Importaciones de API Routers
from .views import router as views_router
from .api.routers import main as routers_main_api
from .api.clients import main as clients_main_api
from .api.cpes import main as cpes_main_api
from .api.zonas import main as zonas_main_api
from .api.zonas import infra as zonas_infra_api
from .api.users import main as users_main_api
from .api.settings import main as settings_main_api
from .api.aps import main as aps_main_api
from .api.aps import spectral as aps_spectral_api
from .api.stats import main as stats_main_api
from .api.plans import main as plans_main_api
from .api.switches import main as switches_main_api
from .api.security import main as security_main_api


app = FastAPI(title="µMonitor Pro", version="0.5.0")


# --- Database Initialization ---
@app.on_event("startup")
async def on_startup():
    """Initialize database tables and background services on application startup"""
    await create_db_and_tables()
    print("✅ Database tables initialized")
    
    # --- Cache V2: Iniciar MonitorScheduler ---
    # Este scheduler consulta routers suscritos y llena el cache
    # Los WebSockets leen del cache en lugar de conectar directamente
    from .services.monitor_scheduler import monitor_scheduler
    import asyncio
    asyncio.create_task(monitor_scheduler.run())
    print("✅ MonitorScheduler iniciado (Cache V2)")
    
    # --- Cache V2: Iniciar APMonitorScheduler ---
    # Mismo patrón para APs
    from .services.ap_monitor_scheduler import ap_monitor_scheduler
    asyncio.create_task(ap_monitor_scheduler.run())
    print("✅ APMonitorScheduler iniciado (Cache V2)")
    
    # --- Cache V2: Iniciar SwitchMonitorScheduler ---
    # Mismo patrón para Switches
    from .services.switch_monitor_scheduler import switch_monitor_scheduler
    asyncio.create_task(switch_monitor_scheduler.run())
    print("✅ SwitchMonitorScheduler iniciado (Cache V2)")


# --- Configuración de SlowAPI ---
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter


async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    if request.url.path == "/auth/cookie/login":
        # Note: This handler relies on templates. login.html is used here.
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error_message": "⚠️ Demasiados intentos fallidos. Por favor, espera 1 minuto.",
            },
            status_code=429,
        )
    return JSONResponse(
        content={"error": f"Rate limit exceeded: {exc.detail}"}, status_code=429
    )


app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)

APP_ENV = os.getenv("APP_ENV", "development")


# --- SEGURIDAD: CONFIGURACIÓN CORS ESTRICTA ---
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000")
origins = allowed_origins_env.split(",")

# Flutter Mobile App Development Support
# Set FLUTTER_DEV=true in .env to allow Flutter web dev server (port 33000)
if os.getenv("FLUTTER_DEV", "false").lower() == "true":
    origins.append("http://localhost:33000")
    print("🦋 Flutter development mode enabled (port 33000)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- SEGURIDAD: TRUSTED HOSTS ---
allowed_hosts = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)


# --- SEGURIDAD: ORIGIN SHIELD (Protección CSRF por verificación de origen)
from starlette.middleware.base import BaseHTTPMiddleware
from urllib.parse import urlparse


class TrustedOriginMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces origin checking for state-changing HTTP methods.
    Blocks POST, PUT, DELETE, PATCH requests that don't originate from trusted origins.
    This provides CSRF protection without requiring tokens in the frontend.
    """

    UNSAFE_METHODS = {"POST", "PUT", "DELETE", "PATCH"}
    SAFE_PATHS = {"/api/internal/", "/auth/jwt/login"}  # Internal endpoints & Login don't need Origin check

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
                    print(f"🛡️ [Origin Shield] BLOCKED: Missing Origin/Referer for {request.method} {request.url.path}")
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={"detail": "Forbidden: Missing origin information"}
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
                if request_origin_normalized.replace("https://", "http://") == allowed_normalized.replace("https://", "http://"):
                    is_trusted = True
                    break

            if not is_trusted:
                print(f"🛡️ [Origin Shield] BLOCKED request from untrusted origin: {request_origin}")
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Forbidden: Invalid origin"}
                )

        return await call_next(request)


app.add_middleware(TrustedOriginMiddleware)


# --- SEGURIDAD: CABECERAS DE SEGURIDAD HTTP ---
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    
    # Prevenir que el sitio sea embebido en iframes (Clickjacking)
    response.headers["X-Frame-Options"] = "DENY"
    
    # Prevenir que el navegador intente adivinar el tipo de contenido (MIME Sniffing)
    response.headers["X-Content-Type-Options"] = "nosniff"
    
    # Filtro XSS legacy para navegadores antiguos
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    # Controlar cuánta información se envía en el Referer
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    # HSTS: Forzar HTTPS (solo si APP_ENV es producción)
    if os.getenv("APP_ENV", "development") == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    
    # Permissions Policy: Restringir acceso a hardware y APIs sensibles si no se usan
    # Ajusta según las necesidades de tu app (cámara, micro, gps, etc.)
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), interest-cohort=()"
    
    return response


# --- SEGURIDAD: RATE LIMITING MIDDLEWARE ---
# Simple in-memory rate limiter for authentication endpoints
from collections import defaultdict
from time import time

_rate_limit_store = defaultdict(list)
_RATE_LIMITS = {
    "/auth/cookie/login": (5, 60),      # 5 attempts per 60 seconds
    "/auth/register": (3, 60),           # 3 attempts per 60 seconds  
    "/auth/jwt/login": (10, 60),         # 10 attempts per 60 seconds (API)
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
            timestamp for timestamp in _rate_limit_store[key]
            if now - timestamp < window_seconds
        ]
        
        # Check if rate limit exceeded
        if len(_rate_limit_store[key]) >= max_requests:
            if path == "/auth/cookie/login":
                # Return HTML error for web login
                return templates.TemplateResponse(
                    "login.html",
                    {
                        "request": request,
                        "error_message": "⚠️ Demasiados intentos fallidos. Por favor, espera 1 minuto.",
                    },
                    status_code=429,
                )
            else:
                # Return JSON error for API endpoints
                return JSONResponse(
                    content={"error": "Rate limit exceeded. Please try again later."},
                    status_code=429
                )
        
        # Record this request
        _rate_limit_store[key].append(now)
    
    return await call_next(request)


# --- Configuración de Directorios ---
current_dir = os.path.dirname(__file__)
static_dir = os.path.join(current_dir, "..", "static")
uploads_dir = os.path.join(current_dir, "..", "data", "uploads")

os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Note: templates are now handled in .core.templates, imported above.


# --- GLOBAL EXCEPTION HANDLER ---
def _is_web_request(request: Request) -> bool:
    """
    Determine if the request is a browser/web request vs an API call.
    Web requests typically Accept HTML and don't start with /api/.
    """
    if request.url.path.startswith("/api/"):
        return False
    accept_header = request.headers.get("accept", "")
    # Browser requests typically include text/html in Accept header
    return "text/html" in accept_header or "*/*" in accept_header


# Handler for Starlette HTTP Exceptions
@app.exception_handler(StarletteHTTPException)
async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
    return await _handle_http_exception(request, exc.status_code, exc.detail)


# Handler for FastAPI HTTP Exceptions (raised by dependencies like RoleChecker)
from fastapi import HTTPException as FastAPIHTTPException

@app.exception_handler(FastAPIHTTPException)
async def fastapi_http_exception_handler(request: Request, exc: FastAPIHTTPException):
    return await _handle_http_exception(request, exc.status_code, exc.detail)


async def _handle_http_exception(request: Request, status_code: int, detail: str):
    """Common handler for both Starlette and FastAPI HTTP exceptions."""
    is_web = _is_web_request(request)

    # Redirect to login for 401 on web pages
    if status_code == 401 and is_web:
        response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
        response.delete_cookie(ACCESS_TOKEN_COOKIE_NAME)
        return response

    # Show friendly 403 page for web requests
    if status_code == 403 and is_web:
        return templates.TemplateResponse(
            "403.html",
            {"request": request},
            status_code=403,
        )

    return JSONResponse(status_code=status_code, content={"detail": detail})


# --- ENDPOINTS WEBSOCKET Y NOTIFICACIÓN INTERNA ---
@app.websocket("/ws/dashboard")
async def websocket_dashboard(
    websocket: WebSocket, umonitorpro_access_token_v2: str = Cookie(None)
):
    # --- SECURITY: Validate authentication cookie ---
    if umonitorpro_access_token_v2 is None:
        print(
            f"⚠️ [WebSocket] Rechazado: No se encontró la cookie '{ACCESS_TOKEN_COOKIE_NAME}'."
        )
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    # --- SECURITY: Validate Origin header to prevent CSWSH ---
    # (Cross-Site WebSocket Hijacking)
    origin = websocket.headers.get("origin")
    if origin:
        origin_normalized = origin.rstrip("/")
        is_trusted_origin = False
        for allowed in origins:
            allowed_normalized = allowed.rstrip("/")
            if origin_normalized == allowed_normalized:
                is_trusted_origin = True
                break
            # Also check http vs https variance
            if origin_normalized.replace("https://", "http://") == allowed_normalized.replace("https://", "http://"):
                is_trusted_origin = True
                break
        
        if not is_trusted_origin:
            print(f"🛡️ [WebSocket] BLOCKED: Untrusted origin {origin}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    # --- Accept connection ---
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.post("/api/internal/notify-monitor-update", include_in_schema=False)
async def notify_monitor_update():
    """
    Endpoint interno llamado por monitor.py cuando termina un ciclo de escaneo.
    """
    await manager.broadcast_event("db_updated")
    return {"status": "broadcast_sent"}


# --- ROUTERS INCLUSION ---

# 1. Main Views (Pages & Legacy Auth)
app.include_router(views_router)

# 2. FastAPI Users Routers (Behavior largely replaces old manual auth)
# Rate limiting is handled by rate_limit_middleware for auth endpoints
app.include_router(
    fastapi_users.get_auth_router(auth_backend_jwt),
    prefix="/auth/jwt",
    tags=["FastAPI Users - JWT Auth"],
)
app.include_router(
    fastapi_users.get_auth_router(auth_backend_cookie),
    prefix="/auth/cookie",
    tags=["FastAPI Users - Cookie Auth"],
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["FastAPI Users - Registration"],
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
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


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
from .api.stats import main as stats_main_api
from .api.plans import main as plans_main_api


app = FastAPI(title="µMonitor Pro", version="0.5.0")


# --- Database Initialization ---
@app.on_event("startup")
async def on_startup():
    """Initialize database tables on application startup"""
    await create_db_and_tables()
    print("✅ Database tables initialized")


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


# ============================================================================
# --- SEGURIDAD: CONFIGURACIÓN CORS ESTRICTA ---
# ============================================================================
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000")
origins = allowed_origins_env.split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# --- SEGURIDAD: TRUSTED HOSTS ---
# ============================================================================
allowed_hosts = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)


# ============================================================================
# --- SEGURIDAD: ORIGIN SHIELD (Protección CSRF por verificación de origen)
# ============================================================================
from starlette.middleware.base import BaseHTTPMiddleware
from urllib.parse import urlparse


class TrustedOriginMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces origin checking for state-changing HTTP methods.
    Blocks POST, PUT, DELETE, PATCH requests that don't originate from trusted origins.
    This provides CSRF protection without requiring tokens in the frontend.
    """

    UNSAFE_METHODS = {"POST", "PUT", "DELETE", "PATCH"}

    async def dispatch(self, request: Request, call_next):
        if request.method in self.UNSAFE_METHODS:
            origin = request.headers.get("origin")
            referer = request.headers.get("referer")

            # Determine the source of the request
            request_origin = None
            if origin:
                request_origin = origin
            elif referer:
                parsed = urlparse(referer)
                request_origin = f"{parsed.scheme}://{parsed.netloc}"

            # If no origin info at all (e.g., direct curl without headers), allow.
            # This is for internal/API tools. Browser attacks ALWAYS send Origin/Referer.
            if request_origin:
                # Normalize and check against allowed origins
                is_trusted = False
                for allowed in origins:  # 'origins' from CORS config
                    if request_origin == allowed or request_origin.rstrip("/") == allowed.rstrip("/"):
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


# ============================================================================
# --- SEGURIDAD: CABECERAS DE SEGURIDAD HTTP ---
# ============================================================================
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# --- Configuración de Directorios ---
current_dir = os.path.dirname(__file__)
static_dir = os.path.join(current_dir, "..", "static")

os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Note: templates are now handled in .core.templates, imported above.


# ============================================================================
# --- GLOBAL EXCEPTION HANDLER ---
# ============================================================================
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    # Redirect to login for 401 on pages (not API)
    if exc.status_code == 401 and not request.url.path.startswith("/api/"):
        response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
        response.delete_cookie(ACCESS_TOKEN_COOKIE_NAME)
        return response
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


# ============================================================================
# --- ENDPOINTS WEBSOCKET Y NOTIFICACIÓN INTERNA ---
# ============================================================================
@app.websocket("/ws/dashboard")
async def websocket_dashboard(
    websocket: WebSocket, umonitorpro_access_token: str = Cookie(None)
):
    # --- DEBUG: Imprimir qué está pasando ---
    if umonitorpro_access_token is None:
        print(
            f"⚠️ [WebSocket] Rechazado: No se encontró la cookie '{ACCESS_TOKEN_COOKIE_NAME}' (var name mismatched?)."
        )
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # ----------------------------------------
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


# ============================================================================
# --- ROUTERS INCLUSION ---
# ============================================================================

# 1. Main Views (Pages & Legacy Auth)
app.include_router(views_router)

# 2. FastAPI Users Routers (Behavior largely replaces old manual auth)
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
app.include_router(cpes_main_api.router, prefix="/api", tags=["CPEs"])
app.include_router(clients_main_api.router, prefix="/api", tags=["Clients"])
app.include_router(zonas_main_api.router, prefix="/api", tags=["Zonas"])
app.include_router(zonas_infra_api.router, prefix="/api", tags=["Zonas Infrastructure"])
app.include_router(users_main_api.router, prefix="/api", tags=["Users"])
app.include_router(settings_main_api.router, prefix="/api", tags=["Settings"])
app.include_router(stats_main_api.router, prefix="/api", tags=["Stats"])
app.include_router(plans_main_api.router, prefix="/api", tags=["Plans"])

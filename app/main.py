# app/main.py
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env ANTES de cualquier otra cosa
load_dotenv()

import asyncio
from fastapi import (
    FastAPI,
    HTTPException,
    status,
    Depends,
    Request,
    WebSocket,
    WebSocketDisconnect,
    Cookie,
)
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from datetime import timedelta
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from typing import List

# SlowAPI (Rate Limiting)
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# FastAPI Users imports (replaces manual auth.py)
from .core.users import (
    fastapi_users,
    auth_backend_jwt,
    auth_backend_cookie,
    current_active_user,
    ACCESS_TOKEN_COOKIE_NAME,
)
from .schemas.user import UserRead, UserCreate, UserUpdate
from .models.user import User
from .models.payment import Payment
from .models.client import Client
from .db.engine import create_db_and_tables, get_session  # Async para FastAPI Users
from .db.engine_sync import get_sync_session  # Sync para el resto de la app
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Session, select as sync_select

# Legacy auth imports (for backward compatibility with old /token endpoint)
from .auth import verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

# Importaciones de API
from .services.settings_service import SettingsService
from datetime import datetime
from dateutil.relativedelta import relativedelta


from .api.routers import main as routers_main_api
from .api.clients import main as clients_main_api
from .api.cpes import main as cpes_main_api
from .api.zonas import main as zonas_main_api
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
    if request.url.path == "/token":
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
# Leemos los orígenes permitidos desde el archivo .env
# Si no está definido, por defecto solo permitimos localhost para desarrollo.
# Formato en .env: ALLOWED_ORIGINS="http://localhost:8000,http://127.0.0.1:8000"

allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000")
origins = allowed_origins_env.split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # <--- Aquí está la clave: Solo IPs de la lista
    allow_credentials=True,  # Necesario para que funcionen las cookies y WebSockets
    allow_methods=["*"],  # Permitir todos los métodos (GET, POST, PUT, DELETE)
    allow_headers=["*"],  # Permitir todos los headers
)

# ============================================================================
# --- SEGURIDAD: TRUSTED HOSTS (Evitar ataques de Host Header) ---
# ============================================================================
# Un atacante podría falsificar el encabezado Host en una petición HTTP para
# engañar a tu aplicación y hacer que genere enlaces de restablecimiento de
# contraseña apuntando a un dominio malicioso.
# Este middleware valida el header "Host" para bloquear hosts no autorizados.

# Leer hosts permitidos desde .env
# Formato: ALLOWED_HOSTS="localhost,127.0.0.1,192.168.1.50,miwisp.com"
allowed_hosts = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

# ============================================================================
# --- SEGURIDAD: CABECERAS DE SEGURIDAD HTTP (Security Headers) ---
# ============================================================================
# Los navegadores son muy permisivos por defecto. Enviamos cabeceras especiales
# que le indican al navegador que sea más estricto para evitar ataques como
# Clickjacking (poner tu web en un iframe invisible) o MIME sniffing.


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    # 1. Evita que tu web sea puesta en un iframe (Clickjacking)
    response.headers["X-Frame-Options"] = "DENY"
    # 2. Evita que el navegador "adivine" tipos de archivo (MIME Sniffing)
    response.headers["X-Content-Type-Options"] = "nosniff"
    # 3. Activa el filtro XSS del navegador (capa extra)
    response.headers["X-XSS-Protection"] = "1; mode=block"
    # 4. Política de Referrer estricta (Privacidad)
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# --- Configuración de Directorios ---
current_dir = os.path.dirname(__file__)
static_dir = os.path.join(current_dir, "..", "static")
templates_dir = os.path.join(current_dir, "..", "templates")

os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)

# ACCESS_TOKEN_COOKIE_NAME now imported from core.users


# ============================================================================
# --- GESTOR DE WEBSOCKETS (REFACTORIZADO & GENÉRICO) ---
# ============================================================================
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_event(self, event_type: str, data: dict = None):
        """
        Envía una señal JSON genérica a todos los clientes conectados.
        """
        payload = {"type": event_type}
        if data:
            payload.update(data)

        # Iteramos sobre una copia [:] para evitar errores si la lista cambia durante el envío
        for connection in self.active_connections[:]:
            try:
                await connection.send_json(payload)
            except Exception:
                self.disconnect(connection)


manager = ConnectionManager()

# --- Funciones de Utilidad y Auth ---


async def get_current_user_or_redirect(
    user: User = Depends(current_active_user),
) -> User:
    return user


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 401 and not request.url.path.startswith("/api/"):
        response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
        response.delete_cookie(ACCESS_TOKEN_COOKIE_NAME)
        return response
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


# ============================================================================
# --- ENDPOINTS WEBSOCKET Y NOTIFICACIÓN INTERNA ---
# ============================================================================


@app.websocket("/ws/dashboard")  # <--- Asegúrate que esta ruta coincida con tu JS
async def websocket_dashboard(
    websocket: WebSocket, umonitorpro_access_token: str = Cookie(None)
):
    # --- DEBUG: Imprimir qué está pasando ---
    if umonitorpro_access_token is None:
        print(
            f"⚠️ [WebSocket] Rechazado: No se encontró la cookie 'umonitorpro_access_token'."
        )
        # Por ahora, cerramos con Policy Violation
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    print(f"✅ [WebSocket] Cookie encontrada. Aceptando conexión...")
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
    Envía la señal 'db_updated' a todos los clientes conectados.
    """
    await manager.broadcast_event("db_updated")
    return {"status": "broadcast_sent"}


# ============================================================================
# --- ENDPOINTS DE PÁGINAS (HTML) ---
# ============================================================================


@app.get("/login", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


# ⚠️  LEGACY ENDPOINT - Bridges old auth with new FastAPI Users system
# Uses SYNC database for login, then creates FastAPI Users compatible token
@app.post("/token", tags=["Auth & Pages"], include_in_schema=False)
@limiter.limit("5/minute")
async def login_for_web_ui(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_sync_session),  # Usar sesión SYNC
):
    """
    Legacy login endpoint for Web UI.
    Uses SYNC session to query users, then creates async-compatible token.
    """
    from fastapi_users.password import PasswordHelper

    password_helper = PasswordHelper()

    # Buscar usuario por username en la tabla nueva (SYNC)
    statement = sync_select(User).where(User.username == form_data.username)
    user = session.exec(statement).first()

    # Validar credenciales
    if not user:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error_message": "Usuario o contraseña incorrectos"},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    # Verificar contraseña
    verified, updated_hash = password_helper.verify_and_update(
        form_data.password, user.hashed_password
    )

    if not verified:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error_message": "Usuario o contraseña incorrectos"},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    # Actualizar hash si es necesario
    if updated_hash:
        user.hashed_password = updated_hash
        session.add(user)
        session.commit()

    # Verificar que el usuario esté activo
    if not user.is_active:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error_message": "Usuario inactivo"},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    # Generar token usando la estrategia de FastAPI Users
    from fastapi_users.authentication import Strategy

    strategy: Strategy = auth_backend_cookie.get_strategy()
    token = await strategy.write_token(user)

    # Crear respuesta de redirección
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    # Establecer cookie
    is_secure_cookie = APP_ENV == "production"
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=1800,
        samesite="lax",
        secure=is_secure_cookie,
    )

    print(f"🔐 User logged in: {user.username} (ID: {user.id})")

    return response


@app.get("/logout", tags=["Auth & Pages"], include_in_schema=False)
async def logout_and_redirect():
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(ACCESS_TOKEN_COOKIE_NAME)
    return response


@app.get("/", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_dashboard(
    request: Request, current_user: User = Depends(get_current_user_or_redirect)
):
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "active_page": "dashboard", "user": current_user},
    )


@app.get("/aps", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_aps_page(
    request: Request, current_user: User = Depends(get_current_user_or_redirect)
):
    return templates.TemplateResponse(
        "aps.html", {"request": request, "active_page": "aps", "user": current_user}
    )


@app.get("/ap/{host}", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_ap_details_page(
    request: Request,
    host: str,
    current_user: User = Depends(get_current_user_or_redirect),
):
    return templates.TemplateResponse(
        "ap_details.html",
        {
            "request": request,
            "active_page": "ap_details",
            "host": host,
            "user": current_user,
        },
    )


@app.get("/zonas", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_zones_page(
    request: Request, current_user: User = Depends(current_active_user)
):
    return templates.TemplateResponse(
        "zonas.html", {"request": request, "active_page": "zonas", "user": current_user}
    )


@app.get("/zona/{zona_id}", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_zona_details_page(
    request: Request,
    zona_id: int,
    current_user: User = Depends(get_current_user_or_redirect),
):
    return templates.TemplateResponse(
        "zona_details.html",
        {
            "request": request,
            "active_page": "zonas",
            "zona_id": zona_id,
            "user": current_user,
        },
    )


@app.get("/settings", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_settings_page(
    request: Request, current_user: User = Depends(get_current_user_or_redirect)
):
    return templates.TemplateResponse(
        "settings.html",
        {"request": request, "active_page": "settings", "user": current_user},
    )


@app.get("/users", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_users_page(
    request: Request, current_user: User = Depends(get_current_user_or_redirect)
):
    return templates.TemplateResponse(
        "users.html", {"request": request, "active_page": "users", "user": current_user}
    )


@app.get("/cpes", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_cpes_page(
    request: Request, current_user: User = Depends(current_active_user)
):
    return templates.TemplateResponse(
        "cpes.html", {"request": request, "active_page": "cpes", "user": current_user}
    )


@app.get("/clients", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_clients_page(
    request: Request, current_user: User = Depends(get_current_user_or_redirect)
):
    return templates.TemplateResponse(
        "clients.html",
        {"request": request, "active_page": "clients", "user": current_user},
    )


@app.get("/client/{client_id}", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_client_details_page(
    request: Request,
    client_id: int,
    current_user: User = Depends(get_current_user_or_redirect),
):
    return templates.TemplateResponse(
        "client_details.html",
        {
            "request": request,
            "active_page": "clients",
            "client_id": client_id,
            "user": current_user,
        },
    )


@app.get("/payment/{payment_id}/receipt", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_payment_receipt(
    request: Request,
    payment_id: int,
    session: Session = Depends(get_sync_session),
    current_user: User = Depends(get_current_user_or_redirect),
):
    payment = session.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Pago no encontrado")

    client = session.get(Client, payment.client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado para este pago")

    settings_service = SettingsService(session)
    settings = settings_service.get_all_settings()

    # Calcular el ciclo de servicio
    try:
        billing_day = client.billing_day or 1
        payment_month_date = datetime.strptime(payment.mes_correspondiente, "%Y-%m")
        
        start_date = payment_month_date.replace(day=billing_day)
        end_date = start_date + relativedelta(months=1)
    except (ValueError, TypeError):
        start_date = None
        end_date = None

    context = {
        "request": request,
        "payment": payment,
        "client": client,
        "isp_name": settings.get("company_name"),
        "isp_address": settings.get("billing_address"),  # Ahora toma el campo largo
        "isp_phone": settings.get("billing_phone") or settings.get("notification_email"),
        "isp_logo": settings.get("company_logo_url"),  # Nuevo campo
        "ticket_message": settings.get("ticket_footer_message"),  # Nuevo campo
        "start_date": start_date.strftime("%d de %B de %Y") if start_date else "N/A",
        "end_date": end_date.strftime("%d de %B de %Y") if end_date else "N/A",
    }
    return templates.TemplateResponse("ticket.html", context)


@app.get("/routers", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_routers_page(
    request: Request, current_user: User = Depends(get_current_user_or_redirect)
):
    return templates.TemplateResponse(
        "routers.html",
        {"request": request, "active_page": "routers", "user": current_user},
    )


@app.get("/router/{host}", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_router_details_page(
    request: Request,
    host: str,
    current_user: User = Depends(get_current_user_or_redirect),
):
    return templates.TemplateResponse(
        "router_details.html",
        {
            "request": request,
            "active_page": "router_details",
            "host": host,
            "user": current_user,
        },
    )


from .services.user_service import UserService


# ...
# ⚠️  DEPRECATED: Old API login endpoint - kept for backward compatibility
# Recommendation: Use /auth/jwt/login instead
@app.post("/api/login/access-token", response_model=dict, tags=["API Auth"])
@limiter.limit("5/minute")
async def login_for_api_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_sync_session),
):
    user_service = UserService(session)
    user = user_service.get_user_by_username(form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


# --- FastAPI Users Routers (Automatic Auth Endpoints) ---
# These replace manual auth endpoints and provide standardized user management

# JWT Auth Router (for API Bearer token access)
app.include_router(
    fastapi_users.get_auth_router(auth_backend_jwt),
    prefix="/auth/jwt",
    tags=["FastAPI Users - JWT Auth"],
)

# Cookie Auth Router (for Web UI session-based auth)
app.include_router(
    fastapi_users.get_auth_router(auth_backend_cookie),
    prefix="/auth/cookie",
    tags=["FastAPI Users - Cookie Auth"],
)

# User Registration Router
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["FastAPI Users - Registration"],
)

# User Management Router (CRUD operations)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["FastAPI Users - Users Management"],
)

# --- Inclusión de Routers API ---
app.include_router(routers_main_api.router, prefix="/api", tags=["Routers"])
app.include_router(aps_main_api.router, prefix="/api", tags=["APs"])
app.include_router(cpes_main_api.router, prefix="/api", tags=["CPEs"])
app.include_router(clients_main_api.router, prefix="/api", tags=["Clients"])
app.include_router(zonas_main_api.router, prefix="/api", tags=["Zonas"])
app.include_router(users_main_api.router, prefix="/api", tags=["Users"])
app.include_router(settings_main_api.router, prefix="/api", tags=["Settings"])
app.include_router(stats_main_api.router, prefix="/api", tags=["Stats"])
app.include_router(plans_main_api.router, prefix="/api", tags=["Plans"])

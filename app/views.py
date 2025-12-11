
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Request, Depends, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_csrf_protect import CsrfProtect
from sqlmodel import Session, select as sync_select

from .core.users import current_active_user, ACCESS_TOKEN_COOKIE_NAME, auth_backend_cookie
from .core.templates import templates
from .db.engine_sync import get_sync_session
from .models.user import User
from .models.payment import Payment
from .models.client import Client
from .services.settings_service import SettingsService

router = APIRouter()

APP_ENV = os.getenv("APP_ENV", "development")

# --- Dependency ---
async def get_current_user_or_redirect(
    user: User = Depends(current_active_user),
) -> User:
    return user

# --- Auth Routes (Web UI) ---

@router.get("/login", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_login_form(request: Request, csrf_protect: CsrfProtect = Depends()):
    """Login page with CSRF token generation"""
    csrf_token, signed_token = csrf_protect.generate_csrf_tokens()
    response = templates.TemplateResponse(
        "login.html", 
        {"request": request, "csrf_token": csrf_token}
    )
    csrf_protect.set_csrf_cookie(signed_token, response)
    return response

# ⚠️  LEGACY ENDPOINT - Bridges old auth with new FastAPI Users system
# Uses SYNC database for login, then creates FastAPI Users compatible token
@router.post("/token", tags=["Auth & Pages"], include_in_schema=False)
async def login_for_web_ui(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_sync_session),
    csrf_protect: CsrfProtect = Depends(),
):
    """
    Legacy login endpoint for Web UI with CSRF protection.
    Uses SYNC session to query users, then creates async-compatible token.
    """
    # Validate CSRF token
    await csrf_protect.validate_csrf(request)
    
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

@router.get("/logout", tags=["Auth & Pages"], include_in_schema=False)
async def logout_and_redirect():
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(ACCESS_TOKEN_COOKIE_NAME)
    return response

# --- Page Routes ---

@router.get("/", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_dashboard(
    request: Request, current_user: User = Depends(get_current_user_or_redirect)
):
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "active_page": "dashboard", "user": current_user},
    )

@router.get("/aps", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_aps_page(
    request: Request, current_user: User = Depends(get_current_user_or_redirect)
):
    return templates.TemplateResponse(
        "aps.html", {"request": request, "active_page": "aps", "user": current_user}
    )

@router.get("/ap/{host}", response_class=HTMLResponse, tags=["Auth & Pages"])
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

@router.get("/zonas", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_zones_page(
    request: Request, current_user: User = Depends(current_active_user)
):
    return templates.TemplateResponse(
        "zonas.html", {"request": request, "active_page": "zonas", "user": current_user}
    )

@router.get("/zona/{zona_id}", response_class=HTMLResponse, tags=["Auth & Pages"])
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

@router.get("/settings", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_settings_page(
    request: Request, current_user: User = Depends(get_current_user_or_redirect)
):
    return templates.TemplateResponse(
        "settings.html",
        {"request": request, "active_page": "settings", "user": current_user},
    )

@router.get("/users", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_users_page(
    request: Request, current_user: User = Depends(get_current_user_or_redirect)
):
    return templates.TemplateResponse(
        "users.html", {"request": request, "active_page": "users", "user": current_user}
    )

@router.get("/cpes", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_cpes_page(
    request: Request, current_user: User = Depends(current_active_user)
):
    return templates.TemplateResponse(
        "cpes.html", {"request": request, "active_page": "cpes", "user": current_user}
    )

@router.get("/clients", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_clients_page(
    request: Request, current_user: User = Depends(get_current_user_or_redirect)
):
    return templates.TemplateResponse(
        "clients.html",
        {"request": request, "active_page": "clients", "user": current_user},
    )

@router.get("/client/{client_id}", response_class=HTMLResponse, tags=["Auth & Pages"])
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

@router.get("/payment/{payment_id}/receipt", response_class=HTMLResponse, tags=["Auth & Pages"])
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
        "isp_address": settings.get("billing_address"),
        "isp_phone": settings.get("billing_phone") or settings.get("notification_email"),
        "isp_logo": settings.get("company_logo_url"),
        "ticket_message": settings.get("ticket_footer_message"),
        "start_date": start_date.strftime("%d de %B de %Y") if start_date else "N/A",
        "end_date": end_date.strftime("%d de %B de %Y") if end_date else "N/A",
    }
    return templates.TemplateResponse("ticket.html", context)

@router.get("/routers", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_routers_page(
    request: Request, current_user: User = Depends(get_current_user_or_redirect)
):
    return templates.TemplateResponse(
        "routers.html",
        {"request": request, "active_page": "routers", "user": current_user},
    )

@router.get("/router/{host}", response_class=HTMLResponse, tags=["Auth & Pages"])
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

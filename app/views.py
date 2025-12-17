
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Request, Depends, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlmodel import Session

from .core.users import current_active_user, ACCESS_TOKEN_COOKIE_NAME, require_technician, require_admin
from .core.templates import templates
from .db.engine_sync import get_sync_session
from .models.user import User
from .models.payment import Payment
from .models.client import Client
from .services.settings_service import SettingsService

router = APIRouter()



# --- Dependency ---
async def get_current_user_or_redirect(
    user: User = Depends(current_active_user),
) -> User:
    return user

# --- Auth Routes (Web UI) ---

@router.get("/login", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_login_form(request: Request):
    """Login page"""
    return templates.TemplateResponse("login.html", {"request": request})

@router.get("/403", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_forbidden_page(request: Request):
    """403 Forbidden error page"""
    return templates.TemplateResponse("403.html", {"request": request}, status_code=403)

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
    request: Request, current_user: User = Depends(require_technician)
):
    return templates.TemplateResponse(
        "aps.html", {"request": request, "active_page": "aps", "user": current_user}
    )

@router.get("/ap/{host}", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_ap_details_page(
    request: Request,
    host: str,
    session: Session = Depends(get_sync_session),
    current_user: User = Depends(require_technician),
):
    from .models.ap import AP
    ap = session.get(AP, host)
    if not ap:
        raise HTTPException(status_code=404, detail="AP not found")
    return templates.TemplateResponse(
        "ap_details.html",
        {
            "request": request,
            "active_page": "ap_details",
            "host": host,
            "user": current_user,
            "ap": ap,
        },
    )


@router.get("/zonas", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_zones_page(
    request: Request, current_user: User = Depends(require_technician)
):
    return templates.TemplateResponse(
        "zonas.html", {"request": request, "active_page": "zonas", "user": current_user}
    )

@router.get("/zona/{zona_id}", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_zona_details_page(
    request: Request,
    zona_id: int,
    current_user: User = Depends(require_technician),
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
    request: Request, current_user: User = Depends(require_admin)
):
    return templates.TemplateResponse(
        "settings.html",
        {"request": request, "active_page": "settings", "user": current_user},
    )

@router.get("/users", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_users_page(
    request: Request, current_user: User = Depends(require_admin)
):
    return templates.TemplateResponse(
        "users.html", {"request": request, "active_page": "users", "user": current_user}
    )

@router.get("/cpes", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_cpes_page(
    request: Request, current_user: User = Depends(require_technician)
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
    request: Request, current_user: User = Depends(require_technician)
):
    return templates.TemplateResponse(
        "routers.html",
        {"request": request, "active_page": "routers", "user": current_user},
    )

@router.get("/router/{host}", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_router_details_page(
    request: Request,
    host: str,
    current_user: User = Depends(require_technician),
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

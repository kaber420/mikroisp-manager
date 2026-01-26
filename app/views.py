from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session

from .core.templates import templates
from .core.users import (
    ACCESS_TOKEN_COOKIE_NAME,
    current_active_user,
    require_admin,
    require_technician,
)
from .db.engine_sync import get_sync_session
from .models.user import User

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
    # Rate limit is applied to POST /auth/cookie/login in main.py
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
async def read_aps_page(request: Request, current_user: User = Depends(require_technician)):
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
async def read_zones_page(request: Request, current_user: User = Depends(require_technician)):
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
async def read_settings_page(request: Request, current_user: User = Depends(require_admin)):
    return templates.TemplateResponse(
        "settings.html",
        {"request": request, "active_page": "settings", "user": current_user},
    )


@router.get("/users", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_users_page(request: Request, current_user: User = Depends(require_admin)):
    return templates.TemplateResponse(
        "users.html", {"request": request, "active_page": "users", "user": current_user}
    )


@router.get("/cpes", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_cpes_page(request: Request, current_user: User = Depends(require_technician)):
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
    client_id: str,
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
    from .services.billing_service import BillingService

    billing_service = BillingService(session)
    
    try:
        context = billing_service.get_payment_receipt_context(payment_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    # Add request to context for template
    context["request"] = request
    
    return templates.TemplateResponse("payment_receipt.html", context)


@router.get("/routers", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_routers_page(request: Request, current_user: User = Depends(require_technician)):
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


@router.get("/switches", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_switches_page(request: Request, current_user: User = Depends(require_technician)):
    return templates.TemplateResponse(
        "switches.html",
        {"request": request, "active_page": "switches", "user": current_user},
    )


@router.get("/switch/{host}", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_switch_details_page(
    request: Request,
    host: str,
    current_user: User = Depends(require_technician),
):
    return templates.TemplateResponse(
        "switch_details.html",
        {
            "request": request,
            "active_page": "switch_details",
            "host": host,
            "user": current_user,
        },
    )


@router.get("/tickets", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_tickets_page(request: Request, current_user: User = Depends(require_technician)):
    return templates.TemplateResponse(
        "tickets.html", {"request": request, "active_page": "tickets", "user": current_user}
    )


@router.get("/guia", response_class=HTMLResponse, tags=["Auth & Pages"])
async def read_guide_page(request: Request, current_user: User = Depends(get_current_user_or_redirect)):
    """Documentation guide page"""
    return templates.TemplateResponse(
        "guide.html",
        {"request": request, "active_page": "guia", "user": current_user},
    )


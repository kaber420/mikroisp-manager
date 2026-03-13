import logging
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session

logger = logging.getLogger(__name__)

from ...core.users import require_billing
from ...db.engine_sync import get_sync_session
from ...middleware.degraded_mode import verify_not_degraded
from ...models.user import User


# Import service classes
from ...services.business.billing_service import BillingService
from ...services.business.client_service import ClientService as ClientManagerService
from ...services.business.payment_service import PaymentService
from ...services.business.user_service import UserService
from ...schemas.user import UserCreate, UserRead
from .models import (
    AssignedCPE,
    ClientCreate,
    ClientPagination,
    ClientRead,
    ClientService,
    ClientServiceCreate,
    ClientUpdate,
    Payment,
    PaymentCreate,
)

router = APIRouter()


# --- Dependency Injectors ---
def get_client_service(session: Session = Depends(get_sync_session)) -> ClientManagerService:
    return ClientManagerService(session)


def get_payment_service(session: Session = Depends(get_sync_session)) -> PaymentService:
    return PaymentService(session)


def get_billing_service(session: Session = Depends(get_sync_session)) -> BillingService:
    return BillingService(session)


def get_user_service(session: Session = Depends(get_sync_session)) -> UserService:
    return UserService(session)


# --- Client Endpoints ---


@router.get("/clients", response_model=ClientPagination)
def api_get_all_clients(
    page: int = 1,
    page_size: int = 10,
    search: Optional[str] = None,
    status: Optional[str] = None,
    service: ClientManagerService = Depends(get_client_service),
    current_user: User = Depends(require_billing),
) -> ClientPagination:
    return service.get_clients_paginated(page, page_size, search, status)


@router.get("/clients/{client_id}", response_model=ClientRead)
def api_get_client(
    client_id: uuid.UUID,
    service: ClientManagerService = Depends(get_client_service),
    current_user: User = Depends(require_billing),
):
    return service.get_client_by_id(client_id)


@router.post("/clients", response_model=ClientRead, status_code=status.HTTP_201_CREATED)
def api_create_client(
    client: ClientCreate,
    service: ClientManagerService = Depends(get_client_service),
    current_user: User = Depends(require_billing),
    _: bool = Depends(verify_not_degraded),
):
    new_client = service.create_client(client.model_dump())
    return new_client


@router.put("/clients/{client_id}", response_model=ClientRead)
def api_update_client(
    client_id: uuid.UUID,
    client_update: ClientUpdate,
    service: ClientManagerService = Depends(get_client_service),
    current_user: User = Depends(require_billing),
    _: bool = Depends(verify_not_degraded),
):
    update_fields = client_update.model_dump(exclude_unset=True)
    updated_client = service.update_client(client_id, update_fields)
    return updated_client


@router.delete("/clients/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def api_delete_client(
    client_id: uuid.UUID,
    request: Request,
    service: ClientManagerService = Depends(get_client_service),
    current_user: User = Depends(require_billing),
    _: bool = Depends(verify_not_degraded),
):
    from ...core.audit import log_action

    service.delete_client(client_id)
    log_action("DELETE", "client", str(client_id), user=current_user, request=request)
    return


@router.get("/clients/{client_id}/cpes", response_model=list[AssignedCPE])
def api_get_cpes_for_client(
    client_id: uuid.UUID,
    service: ClientManagerService = Depends(get_client_service),
    current_user: User = Depends(require_billing),
):
    return service.get_cpes_for_client(client_id)


@router.post("/clients/{client_id}/generate-access", response_model=UserRead)
def api_generate_client_access(
    client_id: uuid.UUID,
    user_data: UserCreate,
    client_service: ClientManagerService = Depends(get_client_service),
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(require_billing),
):
    """
    Genera credenciales de acceso vinculadas a un cliente específico.
    """
    # Verificar que el cliente existe
    client = client_service.get_client_by_id(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    # Asegurar que el client_id en user_data coincide con el de la URL
    user_data.client_id = client_id
    user_data.role = "client"

    try:
        new_user = user_service.create_user(user_data)
        return new_user
    except Exception as e:
        logger.error(f"Error generando acceso para cliente {client_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# --- Service Endpoints ---


@router.post(
    "/clients/{client_id}/services",
    response_model=ClientService,
    status_code=status.HTTP_201_CREATED,
)
def api_create_client_service(
    client_id: uuid.UUID,
    service_data: ClientServiceCreate,
    service: ClientManagerService = Depends(get_client_service),
    current_user: User = Depends(require_billing),
):
    new_service = service.create_client_service(client_id, service_data.model_dump())
    return new_service


@router.get("/clients/{client_id}/services", response_model=list[ClientService])
def api_get_client_services(
    client_id: uuid.UUID,
    service: ClientManagerService = Depends(get_client_service),
    current_user: User = Depends(require_billing),
):
    return service.get_client_services(client_id)


@router.put("/services/{service_id}/plan")
def api_change_service_plan(
    service_id: int,
    new_plan_id: int,
    service: ClientManagerService = Depends(get_client_service),
    current_user: User = Depends(require_billing),
):
    """
    Change the plan for an existing client service.

    This endpoint:
    - Updates the plan_id in the database
    - For PPPoE: Updates the profile on the router
    - For Simple Queue: Updates the queue limit on the router
    - Kills active PPPoE connection to force re-auth with new settings
    """
    result = service.change_client_service_plan(service_id, new_plan_id)
    return result


@router.put("/services/{service_id}", response_model=ClientService)
def api_update_client_service(
    service_id: int,
    service_update: ClientServiceCreate,
    service: ClientManagerService = Depends(get_client_service),
    current_user: User = Depends(require_billing),
):
    """Update an existing client service."""
    return service.update_client_service(
        service_id, service_update.model_dump(exclude_unset=True)
    )


@router.delete("/services/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def api_delete_client_service(
    service_id: int,
    service: ClientManagerService = Depends(get_client_service),
    current_user: User = Depends(require_billing),
):
    """Delete a client service."""
    service.delete_client_service(service_id)
    return


@router.put("/services/{service_id}/pppoe-profile")
def api_change_pppoe_profile(
    service_id: int,
    new_profile: str,
    service: ClientManagerService = Depends(get_client_service),
    current_user: User = Depends(require_billing),
):
    """
    Change the PPPoE profile for a service.

    This endpoint is used for PPPoE services where the profile is selected
    from the router's available profiles rather than from the local plans database.
    """
    result = service.change_pppoe_service_profile(service_id, new_profile)
    return result


@router.post("/services/{service_id}/sync")
def api_sync_service_to_router(
    service_id: int,
    service: ClientManagerService = Depends(get_client_service),
    current_user: User = Depends(require_billing),
):
    """
    Synchronize a service configuration to the router.
    
    This endpoint re-applies the service configuration to the router,
    useful when the original provisioning failed or was incomplete.
    Creates/updates Simple Queue or PPPoE secret as needed.
    """
    result = service.sync_client_service_to_router(service_id)
    return result


# --- Payment Endpoints ---


@router.post(
    "/clients/{client_id}/payments",
    response_model=Payment,
    status_code=status.HTTP_201_CREATED,
)
def api_register_payment_and_reactivate(
    client_id: uuid.UUID,
    payment: PaymentCreate,
    billing_service: BillingService = Depends(get_billing_service),
    payment_service: PaymentService = Depends(get_payment_service),
    current_user: User = Depends(require_billing),
    _: bool = Depends(verify_not_degraded),
):
    """
    Register a payment and execute reactivation logic (if applicable).
    """
    # 1. Check for duplicate payments
    # 1. Check for duplicate payments (raises DuplicateError if found)
    payment_service.check_payment_exists(client_id, payment.mes_correspondiente)

    try:
        # Register payment and reactivate service
        new_payment = billing_service.reactivate_client_services(
            client_id=client_id, payment_data=payment.model_dump()
        )
        return new_payment
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error crítico en pagos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno procesando el pago")


@router.get("/clients/{client_id}/payments", response_model=list[Payment])
def api_get_payment_history(
    client_id: uuid.UUID,
    service: ClientManagerService = Depends(get_client_service),
    current_user: User = Depends(require_billing),
):
    return service.get_payment_history(client_id)


@router.get("/clients/payments/{payment_id}/receipt")
def api_get_payment_receipt(
    payment_id: int,
    billing_service: BillingService = Depends(get_billing_service),
    current_user: User = Depends(require_billing),
):
    """
    Get all context data needed to render a payment receipt.
    Adapts Pydantic/SQLModel instances to dictionaries.
    """
    context = billing_service.get_payment_receipt_context(payment_id)
    if "payment" in context and hasattr(context["payment"], "model_dump"):
        context["payment"] = context["payment"].model_dump()
    if "client" in context and hasattr(context["client"], "model_dump"):
        context["client"] = context["client"].model_dump()
        
    return context

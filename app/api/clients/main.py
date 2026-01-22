import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session

from ...core.users import require_billing
from ...db.engine_sync import get_sync_session
from ...models.user import User

# Import service classes
from ...services.billing_service import BillingService
from ...services.client_service import ClientService as ClientManagerService
from ...services.payment_service import PaymentService
from .models import (
    AssignedCPE,
    Client,
    ClientCreate,
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


# --- Client Endpoints ---


@router.get("/clients", response_model=list[Client])
def api_get_all_clients(
    service: ClientManagerService = Depends(get_client_service),
    current_user: User = Depends(require_billing),
):
    return service.get_all_clients()


@router.get("/clients/{client_id}", response_model=Client)
def api_get_client(
    client_id: uuid.UUID,
    service: ClientManagerService = Depends(get_client_service),
    current_user: User = Depends(require_billing),
):
    try:
        return service.get_client_by_id(client_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/clients", response_model=Client, status_code=status.HTTP_201_CREATED)
def api_create_client(
    client: ClientCreate,
    service: ClientManagerService = Depends(get_client_service),
    current_user: User = Depends(require_billing),
):
    try:
        new_client = service.create_client(client.model_dump())
        return new_client
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/clients/{client_id}", response_model=Client)
def api_update_client(
    client_id: uuid.UUID,
    client_update: ClientUpdate,
    service: ClientManagerService = Depends(get_client_service),
    current_user: User = Depends(require_billing),
):
    update_fields = client_update.model_dump(exclude_unset=True)
    try:
        updated_client = service.update_client(client_id, update_fields)
        return updated_client
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/clients/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def api_delete_client(
    client_id: uuid.UUID,
    request: Request,
    service: ClientManagerService = Depends(get_client_service),
    current_user: User = Depends(require_billing),
):
    from ...core.audit import log_action

    try:
        service.delete_client(client_id)
        log_action("DELETE", "client", str(client_id), user=current_user, request=request)
        return
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/clients/{client_id}/cpes", response_model=list[AssignedCPE])
def api_get_cpes_for_client(
    client_id: uuid.UUID,
    service: ClientManagerService = Depends(get_client_service),
    current_user: User = Depends(require_billing),
):
    return service.get_cpes_for_client(client_id)


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
    try:
        new_service = service.create_client_service(client_id, service_data.model_dump())
        return new_service
    except ValueError as e:
        if "ya existe" in str(e):
            raise HTTPException(status_code=409, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))


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
    try:
        result = service.change_client_service_plan(service_id, new_plan_id)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error changing plan: {e}")
        raise HTTPException(status_code=500, detail=f"Error changing plan: {e}")


@router.put("/services/{service_id}", response_model=ClientService)
def api_update_client_service(
    service_id: int,
    service_update: ClientServiceCreate,
    service: ClientManagerService = Depends(get_client_service),
    current_user: User = Depends(require_billing),
):
    """Update an existing client service."""
    try:
        return service.update_client_service(
            service_id, service_update.model_dump(exclude_unset=True)
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/services/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def api_delete_client_service(
    service_id: int,
    service: ClientManagerService = Depends(get_client_service),
    current_user: User = Depends(require_billing),
):
    """Delete a client service."""
    try:
        service.delete_client_service(service_id)
        return
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


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
    try:
        result = service.change_pppoe_service_profile(service_id, new_profile)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error changing PPPoE profile: {e}")
        raise HTTPException(status_code=500, detail=f"Error changing profile: {e}")


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
    try:
        result = service.sync_client_service_to_router(service_id)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error syncing service to router: {e}")
        raise HTTPException(status_code=500, detail=f"Error syncing service: {e}")


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
):
    """
    Register a payment and execute reactivation logic (if applicable).
    """
    # 1. Check for duplicate payments
    if payment_service.check_payment_exists(client_id, payment.mes_correspondiente):
        raise HTTPException(
            status_code=409,  # Conflict
            detail=f"El pago para el mes {payment.mes_correspondiente} ya está registrado.",
        )

    try:
        # Register payment and reactivate service
        new_payment = billing_service.reactivate_client_services(
            client_id=client_id, payment_data=payment.model_dump()
        )
        return new_payment
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Log the real error to server console
        print(f"Error crítico en pagos: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {e}")


@router.get("/clients/{client_id}/payments", response_model=list[Payment])
def api_get_payment_history(
    client_id: uuid.UUID,
    service: ClientManagerService = Depends(get_client_service),
    current_user: User = Depends(require_billing),
):
    return service.get_payment_history(client_id)

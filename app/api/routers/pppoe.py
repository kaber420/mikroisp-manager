# app/api/routers/pppoe.py
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ...core.users import current_active_user as get_current_active_user
from ...models.user import User

# --- CORRECCIÓN DE IMPORTS ---
from ...services.router_service import (
    RouterCommandError,
    RouterService,
    get_router_service,
)  # <-- LÍNEA CAMBIADA

# --- FIN DE CORRECCIÓN ---
from .models import PppoeSecretCreate, PppoeSecretDisable, PppoeSecretUpdate

router = APIRouter()


@router.get("/pppoe/secrets", response_model=list[dict[str, Any]])
def api_get_pppoe_secrets(
    name: str | None = Query(None),
    service: RouterService = Depends(get_router_service),
    user: User = Depends(get_current_active_user),
):
    try:
        return service.get_pppoe_secrets(username=name)
    except RouterCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pppoe/active", response_model=list[dict[str, Any]])
def api_get_pppoe_active_connections(
    name: str | None = Query(None),
    service: RouterService = Depends(get_router_service),
    user: User = Depends(get_current_active_user),
):
    try:
        return service.get_pppoe_active_connections(name=name)
    except RouterCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pppoe/secrets", response_model=dict[str, Any])
def api_create_pppoe_secret(
    secret: PppoeSecretCreate,
    service: RouterService = Depends(get_router_service),
    user: User = Depends(get_current_active_user),
):
    try:
        return service.create_pppoe_secret(**secret.model_dump())
    except (RouterCommandError, ValueError) as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.put("/pppoe/secrets/{secret_id:path}", response_model=dict[str, Any])
def api_update_pppoe_secret(
    secret_id: str,
    secret_update: PppoeSecretUpdate,
    service: RouterService = Depends(get_router_service),
    user: User = Depends(get_current_active_user),
):
    updates = secret_update.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar.")
    try:
        return service.update_pppoe_secret(secret_id, **updates)
    except RouterCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/pppoe/secrets/{secret_id:path}/status", response_model=dict[str, Any])
def api_disable_pppoe_secret(
    secret_id: str,
    status_update: PppoeSecretDisable,
    service: RouterService = Depends(get_router_service),
    user: User = Depends(get_current_active_user),
):
    try:
        return service.set_pppoe_secret_status(secret_id, disable=status_update.disable)
    except RouterCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/pppoe/secrets/{secret_id:path}", status_code=status.HTTP_204_NO_CONTENT)
def api_remove_pppoe_secret(
    secret_id: str,
    service: RouterService = Depends(get_router_service),
    user: User = Depends(get_current_active_user),
):
    try:
        service.remove_pppoe_secret(secret_id)
        return
    except RouterCommandError as e:
        raise HTTPException(status_code=404, detail=f"No se pudo eliminar el 'secret': {e}")


@router.get("/pppoe/profiles", response_model=list[dict[str, Any]])
def api_get_pppoe_profiles(
    service: RouterService = Depends(get_router_service),
    user: User = Depends(get_current_active_user),
):
    """
    Obtiene la lista de perfiles PPPoE (Planes) del router.
    Usado por el frontend para poblar el select de planes.
    """
    try:
        return service.get_ppp_profiles()
    except RouterCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- NEW: Service Suspension & Connection Management Endpoints ---

from .models import (
    AddressListActionRequest,
    ChangePlanRequest,
    KillConnectionRequest,
    RestoreServiceRequest,
    SuspendServiceRequest,
)


@router.post("/pppoe/suspend-service", response_model=dict[str, Any])
def api_suspend_service(
    data: SuspendServiceRequest,
    service: RouterService = Depends(get_router_service),
    user: User = Depends(get_current_active_user),
):
    """
    Suspends a client's service by managing address lists.
    Supports both blacklist (add to block) and whitelist (remove to block) strategies.
    Optionally kills active PPPoE connection.
    """
    try:
        result = service.suspend_service(
            address=data.address,
            list_name=data.list_name,
            strategy=data.strategy,
            pppoe_username=data.pppoe_username,
            comment=data.comment,
        )
        return {"status": "success", "data": result}
    except RouterCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pppoe/restore-service", response_model=dict[str, Any])
def api_restore_service(
    data: RestoreServiceRequest,
    service: RouterService = Depends(get_router_service),
    user: User = Depends(get_current_active_user),
):
    """
    Restores a suspended service.
    Blacklist: removes from block list. Whitelist: adds back to allow list.
    """
    try:
        result = service.restore_service(
            address=data.address,
            list_name=data.list_name,
            strategy=data.strategy,
            comment=data.comment,
        )
        return {"status": "success", "data": result}
    except RouterCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pppoe/change-plan", response_model=dict[str, Any])
def api_change_plan(
    data: ChangePlanRequest,
    service: RouterService = Depends(get_router_service),
    user: User = Depends(get_current_active_user),
):
    """
    Changes a PPPoE user's plan by updating their profile.
    Optionally kills the active connection to force re-authentication with new limits.
    """
    try:
        result = service.change_plan(
            pppoe_username=data.pppoe_username,
            new_profile=data.new_profile,
            kill_connection=data.kill_connection,
        )
        return {"status": "success", "data": result}
    except RouterCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pppoe/kill-connection", response_model=dict[str, Any])
def api_kill_connection(
    data: KillConnectionRequest,
    service: RouterService = Depends(get_router_service),
    user: User = Depends(get_current_active_user),
):
    """
    Terminates an active PPPoE connection for a specific user.
    Useful for forcing re-authentication or immediate disconnection.
    """
    try:
        result = service.kill_pppoe_connection(data.username)
        return result
    except RouterCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/firewall/address-list", response_model=list[dict[str, Any]])
def api_get_address_list(
    list_name: str | None = Query(None),
    service: RouterService = Depends(get_router_service),
    user: User = Depends(get_current_active_user),
):
    """
    Gets address list entries, optionally filtered by list name.
    """
    try:
        return service.get_address_list(list_name=list_name)
    except RouterCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/firewall/address-list", response_model=dict[str, Any])
def api_update_address_list(
    data: AddressListActionRequest,
    service: RouterService = Depends(get_router_service),
    user: User = Depends(get_current_active_user),
):
    """
    Directly manipulates address list entries.
    Actions: 'add', 'remove', 'disable'.
    """
    try:
        result = service.update_address_list(
            list_name=data.list_name,
            address=data.address,
            action=data.action,
            comment=data.comment,
        )
        return result
    except RouterCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))

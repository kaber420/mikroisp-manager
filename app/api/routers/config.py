# app/api/routers/config.py
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from ...core.users import current_active_user as get_current_active_user
from ...models.user import User
from ...services.router_service import (
    RouterCommandError,
    RouterService,
    get_router_service,
)
from .models import (
    AddIpRequest,
    AddNatRequest,
    AddPppoeServerRequest,
    AddSimpleQueueRequest,
    CreatePlanRequest,
    RouterFullDetails,
)

router = APIRouter()


@router.get("/full-details", response_model=RouterFullDetails)
def get_router_full_details(
    service: RouterService = Depends(get_router_service),
    user: User = Depends(get_current_active_user),
):
    try:
        return service.get_full_details()
    except RouterCommandError as e:
        raise HTTPException(status_code=500, detail=f"Error reading bulk data from router: {e}")


# --- Endpoints de Escritura (ADD) ---


@router.post("/write/create-plan", response_model=dict[str, Any])
def write_create_service_plan(
    data: CreatePlanRequest,
    service: RouterService = Depends(get_router_service),
    user: User = Depends(get_current_active_user),
):
    try:
        result = service.create_service_plan(**data.model_dump())
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])
        return result
    except (RouterCommandError, ValueError) as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/write/add-simple-queue", response_model=dict[str, Any])
def write_add_simple_queue(
    data: AddSimpleQueueRequest,
    service: RouterService = Depends(get_router_service),
    user: User = Depends(get_current_active_user),
):
    try:
        return service.add_simple_queue(**data.model_dump())
    except (RouterCommandError, ValueError) as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/write/add-ip", response_model=dict[str, Any])
def write_add_ip_address(
    data: AddIpRequest,
    service: RouterService = Depends(get_router_service),
    user: User = Depends(get_current_active_user),
):
    try:
        api_response = service.add_ip_address(
            address=data.address, interface=data.interface, comment=data.comment
        )
        return {
            "status": "success",
            "message": "IP address added.",
            "data": api_response,
        }
    except RouterCommandError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/write/add-nat", response_model=dict[str, Any])
def write_add_nat_rule(
    data: AddNatRequest,
    service: RouterService = Depends(get_router_service),
    user: User = Depends(get_current_active_user),
):
    try:
        api_response = service.add_nat_masquerade(
            out_interface=data.out_interface, comment=data.comment
        )
        if isinstance(api_response, dict) and api_response.get("status") == "warning":
            return api_response
        return {"status": "success", "message": "NAT rule added.", "data": api_response}
    except RouterCommandError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/write/add-pppoe-server", response_model=dict[str, Any])
def write_add_pppoe_server(
    data: AddPppoeServerRequest,
    service: RouterService = Depends(get_router_service),
    user: User = Depends(get_current_active_user),
):
    try:
        api_response = service.add_pppoe_server(**data.model_dump())
        if isinstance(api_response, dict) and api_response.get("status") == "warning":
            return api_response
        return {
            "status": "success",
            "message": "PPPoE server added.",
            "data": api_response,
        }
    except RouterCommandError as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- Endpoints de Escritura (DELETE) ---


@router.delete("/write/delete-ip", status_code=status.HTTP_204_NO_CONTENT)
def write_delete_ip_address(
    address: str = Query(...),
    host: str = "",
    request: Request = None,
    service: RouterService = Depends(get_router_service),
    user: User = Depends(get_current_active_user),
):
    from ...core.audit import log_action

    try:
        if not service.remove_ip_address(address):
            raise HTTPException(status_code=404, detail="IP address not found on router.")
        log_action("DELETE", "ip_address", address, user=user, request=request)
    except RouterCommandError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/write/delete-nat", status_code=status.HTTP_204_NO_CONTENT)
def write_delete_nat_rule(
    comment: str = Query(...),
    host: str = "",
    request: Request = None,
    service: RouterService = Depends(get_router_service),
    user: User = Depends(get_current_active_user),
):
    from ...core.audit import log_action

    try:
        if not service.remove_nat_rule(comment):
            raise HTTPException(status_code=404, detail="NAT rule with that comment not found.")
        log_action("DELETE", "nat_rule", comment, user=user, request=request)
    except RouterCommandError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/write/delete-pppoe-server", status_code=status.HTTP_204_NO_CONTENT)
def write_delete_pppoe_server(
    service_name: str = Query(...),
    host: str = "",
    request: Request = None,
    service: RouterService = Depends(get_router_service),
    user: User = Depends(get_current_active_user),
):
    from ...core.audit import log_action

    try:
        if not service.remove_pppoe_server(service_name):
            raise HTTPException(
                status_code=404, detail="PPPoE server with that service name not found."
            )
        log_action("DELETE", "pppoe_server", service_name, user=user, request=request)
    except RouterCommandError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/write/delete-plan", response_model=dict[str, bool])
def write_delete_service_plan(
    plan_name: str = Query(...),
    host: str = "",
    request: Request = None,
    service: RouterService = Depends(get_router_service),
    user: User = Depends(get_current_active_user),
):
    from ...core.audit import log_action

    try:
        results = service.remove_service_plan(plan_name)
        if not results:
            raise HTTPException(status_code=404, detail="No components found for that plan name.")
        log_action("DELETE", "service_plan", plan_name, user=user, request=request)
        return results
    except RouterCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/write/delete-simple-queue/{queue_id:path}", status_code=status.HTTP_204_NO_CONTENT)
def write_delete_simple_queue(
    queue_id: str,
    host: str = "",
    request: Request = None,
    service: RouterService = Depends(get_router_service),
    user: User = Depends(get_current_active_user),
):
    from ...core.audit import log_action

    try:
        service.remove_simple_queue(queue_id)
        log_action("DELETE", "simple_queue", queue_id, user=user, request=request)
        return
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except RouterCommandError as e:
        raise HTTPException(
            status_code=404,
            detail=f"No se pudo eliminar la cola con ID {queue_id}. Causa: {e}",
        )

# app/api/zonas/infra.py
"""
Infrastructure visualization API endpoints.
Provides live router interface data for SVG diagram rendering.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ...core.users import require_technician
from ...db import switches_db
from ...db.engine_sync import get_sync_session
from ...models.router import Router
from ...models.user import User
from ...services import switch_service
from ...services.router_service import (
    RouterConnectionError,
    RouterNotProvisionedError,
    RouterService,
)
from ...utils.security import decrypt_data

router = APIRouter(tags=["Zone Infrastructure"])


@router.get("/zonas/{zona_id}/infra/routers")
def get_zone_routers(
    zona_id: int,
    session: Session = Depends(get_sync_session),
    current_user: User = Depends(require_technician),
) -> list[dict[str, Any]]:
    """
    Get all routers linked to a specific zone.
    Returns basic info for each router (host, hostname, model, status).
    """
    statement = select(Router).where(Router.zona_id == zona_id)
    routers = session.exec(statement).all()

    return [
        {
            "host": r.host,
            "hostname": r.hostname,
            "model": r.model,
            "firmware": r.firmware,
            "last_status": r.last_status,
            "is_enabled": r.is_enabled,
        }
        for r in routers
    ]


@router.get("/zonas/infra/router/{host}/ports")
def get_router_ports(
    host: str,
    session: Session = Depends(get_sync_session),
    current_user: User = Depends(require_technician),
) -> dict[str, Any]:
    """
    Fetch live interface data from a router for SVG rendering.
    Returns structured data: physical ports, VLANs, bridges, and their relationships.
    """
    # Get router credentials
    router_creds = session.get(Router, host)
    if not router_creds:
        raise HTTPException(status_code=404, detail=f"Router {host} not found")

    if not router_creds.is_enabled:
        raise HTTPException(status_code=400, detail=f"Router {host} is disabled")

    # Check if router is provisioned
    if router_creds.api_port != router_creds.api_ssl_port:
        raise HTTPException(
            status_code=400, detail=f"Router {host} is not provisioned for API access"
        )

    try:
        # Decrypt password and create service
        decrypted_password = decrypt_data(router_creds.password)
        service = RouterService(host, router_creds, decrypted_password)

        try:
            # Get API client exposed by service
            api = service.get_api_client()

            # Use shared infrastructure service to get data
            from ...services.infrastructure_service import get_device_infrastructure_data

            return get_device_infrastructure_data(
                api=api, host=host, hostname=router_creds.hostname, model=router_creds.model
            )

        finally:
            service.disconnect()

    except (RouterConnectionError, RouterNotProvisionedError) as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching router data: {str(e)}")


@router.get("/zonas/{zona_id}/infra/switches")
async def get_zone_switches(
    zona_id: int,
    current_user: User = Depends(require_technician),
) -> list[dict[str, Any]]:
    """
    Get all switches linked to a specific zone.
    Returns basic info for each switch (host, hostname, model, status).
    """
    from ...db import switches_db
    from ...db.engine import async_session_maker

    # Get all switches and filter by zona_id
    async with async_session_maker() as session:
        all_switches = await switches_db.get_all_switches(session)
        zone_switches = [s for s in all_switches if s.zona_id == zona_id]

    return [
        {
            "host": s.host,
            "hostname": s.hostname,
            "model": s.model,
            "firmware": s.firmware,
            "last_status": s.last_status,
            "is_enabled": s.is_enabled if hasattr(s, 'is_enabled') else True,
            "device_type": "switch",
        }
        for s in zone_switches
    ]


@router.get("/zonas/infra/switch/{host}/ports")
async def get_switch_ports(
    host: str,
    current_user: User = Depends(require_technician),
) -> dict[str, Any]:
    """
    Fetch live interface data from a switch for SVG rendering.
    Returns structured data: physical ports, VLANs, bridges, and their relationships.
    """
    from ...db.engine import async_session_maker

    async with async_session_maker() as session:
        switch_data = await switches_db.get_switch_by_host(session, host)

    if not switch_data:
        raise HTTPException(status_code=404, detail=f"Switch {host} not found")

    if not getattr(switch_data, 'is_enabled', True):
        raise HTTPException(status_code=400, detail=f"Switch {host} is disabled")

    try:
        service = switch_service.get_switch_service(host)
        try:
            # Get API client exposed by service
            api = service.get_api_client()

            # Use shared infrastructure service to get data
            from ...services.infrastructure_service import get_device_infrastructure_data

            hostname = switch_data.hostname or host
            model = switch_data.model or "Unknown Switch"

            return get_device_infrastructure_data(
                api=api, host=host, hostname=hostname, model=model
            )

        finally:
            service.disconnect()

    except switch_service.SwitchConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching switch data: {str(e)}")

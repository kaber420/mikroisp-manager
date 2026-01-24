# app/api/switches/main.py
"""
FastAPI Router for Switches domain.
Provides CRUD endpoints and real-time status via WebSocket.
"""

import asyncio
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.constants import DeviceStatus
from ...core.users import require_admin, require_technician
from ...db.engine import get_session
from ...models.user import User
from ...services import switch_service

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Pydantic Models ---


class SwitchBase(BaseModel):
    """Base model for switch data."""

    host: str = Field(..., description="IP address of the switch")
    username: str = Field(..., description="API username")
    zona_id: int | None = Field(None, description="Zone ID")
    api_port: int = Field(8728, description="API port")
    is_enabled: bool = Field(True, description="Whether the switch is enabled for monitoring")
    location: str | None = Field(None, description="Physical location")
    notes: str | None = Field(None, description="Additional notes")


class SwitchCreate(SwitchBase):
    """Model for creating a new switch."""

    password: str = Field(..., description="API password")


class SwitchUpdate(BaseModel):
    """Model for updating a switch."""

    username: str | None = None
    password: str | None = None
    zona_id: int | None = None
    api_port: int | None = None
    is_enabled: bool | None = None
    location: str | None = None
    notes: str | None = None


class SwitchResponse(BaseModel):
    """Response model for switch data."""

    host: str
    username: str
    zona_id: int | None = None
    api_port: int | None = None
    api_ssl_port: int | None = None
    is_enabled: bool | None = None
    hostname: str | None = None
    model: str | None = None
    firmware: str | None = None
    mac_address: str | None = None
    location: str | None = None
    notes: str | None = None
    last_status: str | None = None

    class Config:
        from_attributes = True


# --- WebSocket Stream for Live Data ---


@router.websocket("/ws/switch/{host}")
async def switch_resources_stream(websocket: WebSocket, host: str):
    """
    WebSocket endpoint for streaming live switch metrics.
    Uses SwitchMonitorScheduler + Cache for efficient connection pooling.
    """
    await websocket.accept()

    # Get switch data using a new session
    from ...db.engine import async_session_maker

    async with async_session_maker() as session:
        switch_data = await switch_service.get_switch_by_host(session, host)

    if not switch_data:
        await websocket.send_json({"error": f"Switch {host} not found"})
        await websocket.close()
        return

    from ...services.switch_monitor_scheduler import switch_monitor_scheduler
    from ...utils.cache import cache_manager

    # Prepare credentials
    password = switch_data.get("password", "")
    port = switch_data.get("api_ssl_port") or switch_data.get("api_port", 8728)

    creds = {"username": switch_data.get("username", ""), "password": password, "port": port}

    try:
        # Subscribe triggers immediate poll
        await switch_monitor_scheduler.subscribe(host, creds)

        stats_cache = cache_manager.get_store("switch_stats")

        while True:
            data = stats_cache.get(host)

            if data:
                if "error" in data:
                    await websocket.send_json(
                        {"type": "error", "host": host, "message": data["error"]}
                    )
                else:
                    total_mem = data.get("total_memory", 0)
                    free_mem = data.get("free_memory", 0)
                    used_mem = 0
                    mem_percent = 0

                    try:
                        t = int(total_mem) if total_mem else 0
                        f = int(free_mem) if free_mem else 0
                        if t > 0:
                            used_mem = t - f
                            mem_percent = round((used_mem / t) * 100, 1)
                    except (ValueError, TypeError):
                        pass

                    payload = {
                        "type": "switch_status",
                        "host": host,
                        "timestamp": datetime.utcnow().isoformat(),
                        "data": {
                            "cpu_load": data.get("cpu_load"),
                            "memory_used": used_mem,
                            "memory_total": total_mem,
                            "memory_free": free_mem,
                            "memory_percent": mem_percent,
                            "uptime": data.get("uptime"),
                            "version": data.get("version"),
                            "board_name": data.get("board_name"),
                            "identity": data.get("name"),
                        },
                    }

                    await websocket.send_json(payload)
            else:
                await websocket.send_json({"type": "loading", "data": {}})

            await asyncio.sleep(2)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for switch {host}")
    except Exception as e:
        logger.error(f"WebSocket error for switch {host}: {e}")
    finally:
        await switch_monitor_scheduler.unsubscribe(host)


# --- CRUD Endpoints ---


@router.post("/switches", response_model=SwitchResponse, status_code=status.HTTP_201_CREATED)
async def create_switch(
    switch: SwitchCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_technician),
):
    """
    Register a new Switch in the system.
    """
    try:
        switch_data = switch.model_dump()
        new_switch = await switch_service.create_switch(session, switch_data)
        return SwitchResponse(**new_switch)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating switch: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/switches", response_model=list[SwitchResponse])
async def get_all_switches(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_technician),
):
    """
    Get all registered switches.
    """
    try:
        switches = await switch_service.get_all_switches(session)
        return [SwitchResponse(**s) for s in switches]
    except Exception as e:
        logger.error(f"Error getting switches: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/switches/{host}", response_model=SwitchResponse)
async def get_switch(
    host: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_technician),
):
    """
    Get details of a specific switch by its host/IP.
    """
    switch_data = await switch_service.get_switch_by_host(session, host)
    if not switch_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Switch {host} not found"
        )
    return SwitchResponse(**switch_data)


@router.put("/switches/{host}", response_model=SwitchResponse)
async def update_switch(
    host: str,
    switch_update: SwitchUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_technician),
):
    """
    Update an existing switch configuration.
    """
    # Check if switch exists
    existing = await switch_service.get_switch_by_host(session, host)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Switch {host} not found"
        )

    # Filter out None values
    update_data = {k: v for k, v in switch_update.model_dump().items() if v is not None}

    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No data to update")

    rows_affected = await switch_service.update_switch(session, host, update_data)
    if rows_affected == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update switch"
        )

    # Return updated data
    updated_switch = await switch_service.get_switch_by_host(session, host)
    return SwitchResponse(**updated_switch)


@router.delete("/switches/{host}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_switch(
    host: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_technician),
):
    """
    Delete a switch from the system.
    """
    existing = await switch_service.get_switch_by_host(session, host)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Switch {host} not found"
        )

    rows_deleted = await switch_service.delete_switch(session, host)
    if rows_deleted == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete switch"
        )

    return None


@router.get("/switches/{host}/status")
async def get_switch_live_status(
    host: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_technician),
):
    """
    Get live status of a switch (CPU, RAM, etc).
    Connects directly to the device.
    """
    switch_data = await switch_service.get_switch_by_host(session, host)
    if not switch_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Switch {host} not found"
        )

    try:
        service = await switch_service.get_switch_service(session, host)
        status_data = service.get_status()
        service.disconnect()
        return status_data
    except switch_service.SwitchConnectionError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting live status for switch {host}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/switches/validate")
async def validate_switch_connection(switch_data: SwitchCreate):
    """
    Test connection to a switch without saving to database.
    """
    try:
        from ...utils.device_clients.adapters.mikrotik_switch import MikrotikSwitchAdapter

        adapter = MikrotikSwitchAdapter(
            host=switch_data.host,
            username=switch_data.username,
            password=switch_data.password,
            port=switch_data.api_port,
        )

        success = adapter.test_connection()

        if success:
            # Try to get system info
            resources = adapter.get_system_resources()
            adapter.disconnect()
            return {
                "success": True,
                "message": "Connection successful",
                "device_info": {
                    "hostname": resources.get("name"),
                    "model": resources.get("board-name"),
                    "version": resources.get("version"),
                },
            }
        else:
            adapter.disconnect()
            return {"success": False, "message": "Could not establish connection"}

    except Exception as e:
        logger.error(f"Error validating switch connection: {e}")
        return {"success": False, "message": str(e)}


@router.post("/switches/{host}/check", status_code=status.HTTP_200_OK)
async def check_switch_status(
    host: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_technician),
):
    """
    Connect to switch, get system info, and update database with hostname, model, firmware.
    This is called after adding a switch to populate device details without waiting for monitor.
    """
    switch_data = await switch_service.get_switch_by_host(session, host)
    if not switch_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Switch {host} not found"
        )

    if not switch_data.get("is_enabled", True):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Switch is disabled")

    try:
        from ...utils.device_clients.adapters.mikrotik_switch import MikrotikSwitchAdapter

        # Create adapter and connect
        adapter = MikrotikSwitchAdapter(
            host=host,
            username=switch_data.get("username", ""),
            password=switch_data.get("password", ""),
            port=switch_data.get("api_port", 8728),
        )

        # Get system resources
        resources = adapter.get_system_resources()
        adapter.disconnect()

        if resources:
            # Update database with device info
            update_data = {
                "hostname": resources.get("name"),
                "model": resources.get("board-name"),
                "firmware": resources.get("version"),
                "last_status": DeviceStatus.ONLINE,
            }
            await switch_service.update_switch(session, host, update_data)

            return {
                "status": "success",
                "message": "Switch checked and database updated",
                "device_info": {
                    "hostname": resources.get("name"),
                    "model": resources.get("board-name"),
                    "firmware": resources.get("version"),
                    "uptime": resources.get("uptime"),
                    "cpu_load": resources.get("cpu-load"),
                },
            }
        else:
            # Update status to offline
            await switch_service.update_switch(session, host, {"last_status": DeviceStatus.OFFLINE})
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not retrieve system info from switch",
            )

    except HTTPException:
        raise
    except Exception as e:
        # Update status to offline on error
        await switch_service.update_switch(session, host, {"last_status": DeviceStatus.OFFLINE})
        logger.error(f"Error checking switch {host}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Connection failed: {str(e)}"
        )


# --- Additional Endpoints for Switch Details Page ---


@router.get("/switches/{host}/interfaces")
async def get_switch_interfaces(
    host: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_technician),
):
    """
    Get all interfaces from a switch.
    """
    switch_data = await switch_service.get_switch_by_host(session, host)
    if not switch_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Switch {host} not found"
        )

    try:
        service = await switch_service.get_switch_service(session, host)
        interfaces = service.get_interfaces()
        service.disconnect()
        return interfaces
    except switch_service.SwitchConnectionError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting interfaces for switch {host}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/switches/{host}/bridges")
async def get_switch_bridges(
    host: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_technician),
):
    """
    Get all bridges configured on a switch.
    """
    switch_data = await switch_service.get_switch_by_host(session, host)
    if not switch_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Switch {host} not found"
        )

    try:
        service = await switch_service.get_switch_service(session, host)
        bridges = service.get_bridges()
        service.disconnect()
        return bridges
    except switch_service.SwitchConnectionError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting bridges for switch {host}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/switches/{host}/vlans")
async def get_switch_vlans(
    host: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_technician),
):
    """
    Get all VLANs configured on a switch.
    """
    switch_data = await switch_service.get_switch_by_host(session, host)
    if not switch_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Switch {host} not found"
        )

    try:
        service = await switch_service.get_switch_service(session, host)
        vlans = service.get_vlans()
        service.disconnect()
        return vlans
    except switch_service.SwitchConnectionError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting VLANs for switch {host}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/switches/{host}/backups")
async def get_switch_backups(
    host: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_technician),
):
    """
    Get list of backup files on a switch.
    """
    switch_data = await switch_service.get_switch_by_host(session, host)
    if not switch_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Switch {host} not found"
        )

    try:
        service = await switch_service.get_switch_service(session, host)
        backups = service.get_backup_files()
        service.disconnect()
        return backups
    except switch_service.SwitchConnectionError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting backups for switch {host}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/switches/{host}/port-stats")
async def get_switch_port_stats(
    host: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_technician),
):
    """
    Get port statistics (ethernet interfaces) from a switch.
    """
    switch_data = await switch_service.get_switch_by_host(session, host)
    if not switch_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Switch {host} not found"
        )

    try:
        service = await switch_service.get_switch_service(session, host)
        port_stats = service.get_port_stats()
        service.disconnect()
        return port_stats
    except switch_service.SwitchConnectionError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting port stats for switch {host}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/switches/{host}/ssl/status")
async def get_switch_ssl_status(
    host: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_technician),
):
    """
    Obtiene el estado SSL/TLS de un Switch MikroTik.
    Retorna si SSL está habilitado, si el certificado es confiable, etc.

    MikrotikSwitchAdapter hereda de MikrotikRouterAdapter y tiene acceso a get_ssl_status().
    """
    switch_data = await switch_service.get_switch_by_host(session, host)
    if not switch_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Switch {host} not found"
        )

    try:
        service = await switch_service.get_switch_service(session, host)

        # MikrotikSwitchAdapter inherits get_ssl_status from MikrotikRouterAdapter
        status_data = service.get_ssl_status()
        service.disconnect()

        return status_data

    except switch_service.SwitchConnectionError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting SSL status for switch {host}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


class SwitchRepairRequest(BaseModel):
    """Request body for switch repair endpoint."""
    action: str = "renew"  # 'renew' or 'unprovision'


@router.post("/switches/{host}/ssl/repair")
async def repair_switch_ssl(
    host: str,
    body: SwitchRepairRequest | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """
    Repairs SSL configuration on a switch.

    Actions:
    - `renew`: Reinstalls SSL certificates (default).
    - `unprovision`: Marks as not provisioned (DB only).
    """
    switch_data = await switch_service.get_switch_by_host(session, host)
    if not switch_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Switch {host} not found"
        )

    action = body.action if body else "renew"

    if action == "unprovision":
        # Mark switch as needing re-provisioning
        await switch_service.update_switch(session, host, {"is_provisioned": False})
        return {
            "status": "success",
            "message": "Switch desvinculado. Listo para re-aprovisionar.",
            "action": "unprovision",
        }

    elif action == "renew":
        # Use MikrotikProvisioningService.renew_ssl for consistency
        from ...services.provisioning import MikrotikProvisioningService

        result = await MikrotikProvisioningService.renew_ssl(
            host=host,
            username=switch_data.get("username", ""),
            password=switch_data.get("password", ""),
            ssl_port=switch_data.get("api_ssl_port") or 8729,
        )

        if result.get("status") == "error":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("message", "SSL renewal failed"),
            )

        return {
            "status": "success",
            "message": "Certificados SSL renovados exitosamente.",
            "action": "renew",
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Acción desconocida: {action}"
        )


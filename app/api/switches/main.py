# app/api/switches/main.py
"""
FastAPI Router for Switches domain.
Provides CRUD endpoints and real-time status via WebSocket.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, WebSocket, WebSocketDisconnect
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio
import logging

from pydantic import BaseModel, Field

from ...core.users import require_technician
from ...models.user import User
from ...services import switch_service
from ...db import switches_db

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Pydantic Models ---

class SwitchBase(BaseModel):
    """Base model for switch data."""
    host: str = Field(..., description="IP address of the switch")
    username: str = Field(..., description="API username")
    zona_id: Optional[int] = Field(None, description="Zone ID")
    api_port: int = Field(8728, description="API port")
    is_enabled: bool = Field(True, description="Whether the switch is enabled for monitoring")
    location: Optional[str] = Field(None, description="Physical location")
    notes: Optional[str] = Field(None, description="Additional notes")


class SwitchCreate(SwitchBase):
    """Model for creating a new switch."""
    password: str = Field(..., description="API password")


class SwitchUpdate(BaseModel):
    """Model for updating a switch."""
    username: Optional[str] = None
    password: Optional[str] = None
    zona_id: Optional[int] = None
    api_port: Optional[int] = None
    is_enabled: Optional[bool] = None
    location: Optional[str] = None
    notes: Optional[str] = None


class SwitchResponse(BaseModel):
    """Response model for switch data."""
    host: str
    username: str
    zona_id: Optional[int] = None
    api_port: Optional[int] = None
    api_ssl_port: Optional[int] = None
    is_enabled: Optional[bool] = None
    hostname: Optional[str] = None
    model: Optional[str] = None
    firmware: Optional[str] = None
    mac_address: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    last_status: Optional[str] = None

    class Config:
        from_attributes = True


# --- WebSocket Stream for Live Data ---

@router.websocket("/ws/switch/{host}")
async def switch_resources_stream(websocket: WebSocket, host: str):
    """
    WebSocket endpoint for streaming live switch metrics.
    Sends CPU, RAM, ports status in real-time.
    """
    await websocket.accept()
    service = None
    
    try:
        # Get switch data and create service
        switch_data = switches_db.get_switch_by_host(host)
        if not switch_data:
            await websocket.send_json({"error": f"Switch {host} not found"})
            await websocket.close()
            return
        
        service = switch_service.SwitchService(host, switch_data)
        
        while True:
            try:
                # Get system resources
                resources = service.get_system_resources()
                
                # Build payload
                payload = {
                    "type": "switch_status",
                    "host": host,
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {
                        "cpu_load": resources.get("cpu-load"),
                        "memory_used": None,
                        "memory_total": resources.get("total-memory"),
                        "memory_free": resources.get("free-memory"),
                        "uptime": resources.get("uptime"),
                        "version": resources.get("version"),
                        "board_name": resources.get("board-name"),
                        "identity": resources.get("name"),
                    }
                }
                
                # Calculate memory percentage
                total_mem = resources.get("total-memory", 0)
                free_mem = resources.get("free-memory", 0)
                if total_mem and free_mem:
                    used_mem = int(total_mem) - int(free_mem)
                    payload["data"]["memory_used"] = used_mem
                    payload["data"]["memory_percent"] = round((used_mem / int(total_mem)) * 100, 1)
                
                await websocket.send_json(payload)
                
            except Exception as e:
                logger.error(f"Error getting switch resources for {host}: {e}")
                await websocket.send_json({
                    "type": "error",
                    "host": host,
                    "message": str(e)
                })
            
            # Wait before next update
            await asyncio.sleep(5)
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for switch {host}")
    except Exception as e:
        logger.error(f"WebSocket error for switch {host}: {e}")
    finally:
        if service:
            service.disconnect()


# --- CRUD Endpoints ---

@router.post("/switches", response_model=SwitchResponse, status_code=status.HTTP_201_CREATED)
async def create_switch(
    switch: SwitchCreate,
    current_user: User = Depends(require_technician),
):
    """
    Register a new Switch in the system.
    """
    try:
        switch_data = switch.model_dump()
        new_switch = switch_service.create_switch(switch_data)
        return SwitchResponse(**new_switch)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating switch: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/switches", response_model=List[SwitchResponse])
async def get_all_switches(
    current_user: User = Depends(require_technician),
):
    """
    Get all registered switches.
    """
    try:
        switches = switch_service.get_all_switches()
        return [SwitchResponse(**s) for s in switches]
    except Exception as e:
        logger.error(f"Error getting switches: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/switches/{host}", response_model=SwitchResponse)
async def get_switch(
    host: str,
    current_user: User = Depends(require_technician),
):
    """
    Get details of a specific switch by its host/IP.
    """
    switch_data = switch_service.get_switch_by_host(host)
    if not switch_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Switch {host} not found")
    return SwitchResponse(**switch_data)


@router.put("/switches/{host}", response_model=SwitchResponse)
async def update_switch(
    host: str,
    switch_update: SwitchUpdate,
    current_user: User = Depends(require_technician),
):
    """
    Update an existing switch configuration.
    """
    # Check if switch exists
    existing = switch_service.get_switch_by_host(host)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Switch {host} not found")
    
    # Filter out None values
    update_data = {k: v for k, v in switch_update.model_dump().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No data to update")
    
    rows_affected = switch_service.update_switch(host, update_data)
    if rows_affected == 0:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update switch")
    
    # Return updated data
    updated_switch = switch_service.get_switch_by_host(host)
    return SwitchResponse(**updated_switch)


@router.delete("/switches/{host}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_switch(
    host: str,
    current_user: User = Depends(require_technician),
):
    """
    Delete a switch from the system.
    """
    existing = switch_service.get_switch_by_host(host)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Switch {host} not found")
    
    rows_deleted = switch_service.delete_switch(host)
    if rows_deleted == 0:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete switch")
    
    return None


@router.get("/switches/{host}/status")
async def get_switch_live_status(
    host: str,
    current_user: User = Depends(require_technician),
):
    """
    Get live status of a switch (CPU, RAM, etc).
    Connects directly to the device.
    """
    switch_data = switch_service.get_switch_by_host(host)
    if not switch_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Switch {host} not found")
    
    try:
        service = switch_service.get_switch_service(host)
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
            port=switch_data.api_port
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
                }
            }
        else:
            adapter.disconnect()
            return {
                "success": False,
                "message": "Could not establish connection"
            }
            
    except Exception as e:
        logger.error(f"Error validating switch connection: {e}")
        return {
            "success": False,
            "message": str(e)
        }


@router.post("/switches/{host}/check", status_code=status.HTTP_200_OK)
async def check_switch_status(
    host: str,
    current_user: User = Depends(require_technician),
):
    """
    Connect to switch, get system info, and update database with hostname, model, firmware.
    This is called after adding a switch to populate device details without waiting for monitor.
    """
    switch_data = switch_service.get_switch_by_host(host)
    if not switch_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Switch {host} not found")
    
    if not switch_data.get("is_enabled", True):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Switch is disabled")
    
    try:
        from ...utils.device_clients.adapters.mikrotik_switch import MikrotikSwitchAdapter
        
        # Create adapter and connect
        adapter = MikrotikSwitchAdapter(
            host=host,
            username=switch_data.get("username", ""),
            password=switch_data.get("password", ""),
            port=switch_data.get("api_port", 8728)
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
                "last_status": "online",
            }
            switches_db.update_switch_in_db(host, update_data)
            
            return {
                "status": "success",
                "message": "Switch checked and database updated",
                "device_info": {
                    "hostname": resources.get("name"),
                    "model": resources.get("board-name"),
                    "firmware": resources.get("version"),
                    "uptime": resources.get("uptime"),
                    "cpu_load": resources.get("cpu-load"),
                }
            }
        else:
            # Update status to offline
            switches_db.update_switch_in_db(host, {"last_status": "offline"})
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
                detail="Could not retrieve system info from switch"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        # Update status to offline on error
        switches_db.update_switch_in_db(host, {"last_status": "offline"})
        logger.error(f"Error checking switch {host}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Connection failed: {str(e)}"
        )



# --- Additional Endpoints for Switch Details Page ---

@router.get("/switches/{host}/interfaces")
async def get_switch_interfaces(
    host: str,
    current_user: User = Depends(require_technician),
):
    """
    Get all interfaces from a switch.
    """
    switch_data = switch_service.get_switch_by_host(host)
    if not switch_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Switch {host} not found")
    
    try:
        service = switch_service.get_switch_service(host)
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
    current_user: User = Depends(require_technician),
):
    """
    Get all bridges configured on a switch.
    """
    switch_data = switch_service.get_switch_by_host(host)
    if not switch_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Switch {host} not found")
    
    try:
        service = switch_service.get_switch_service(host)
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
    current_user: User = Depends(require_technician),
):
    """
    Get all VLANs configured on a switch.
    """
    switch_data = switch_service.get_switch_by_host(host)
    if not switch_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Switch {host} not found")
    
    try:
        service = switch_service.get_switch_service(host)
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
    current_user: User = Depends(require_technician),
):
    """
    Get list of backup files on a switch.
    """
    switch_data = switch_service.get_switch_by_host(host)
    if not switch_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Switch {host} not found")
    
    try:
        service = switch_service.get_switch_service(host)
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
    current_user: User = Depends(require_technician),
):
    """
    Get port statistics (ethernet interfaces) from a switch.
    """
    switch_data = switch_service.get_switch_by_host(host)
    if not switch_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Switch {host} not found")
    
    try:
        service = switch_service.get_switch_service(host)
        port_stats = service.get_port_stats()
        service.disconnect()
        return port_stats
    except switch_service.SwitchConnectionError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting port stats for switch {host}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

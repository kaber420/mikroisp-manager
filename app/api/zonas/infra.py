# app/api/zonas/infra.py
"""
Infrastructure visualization API endpoints.
Provides live router interface data for SVG diagram rendering.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from sqlmodel import Session, select

from ...core.users import require_technician
from ...models.user import User
from ...models.router import Router
from ...services.router_service import RouterService, RouterConnectionError, RouterNotProvisionedError
from ...db.engine_sync import get_sync_session
from ...utils.security import decrypt_data

router = APIRouter(tags=["Zone Infrastructure"])


@router.get("/zonas/{zona_id}/infra/routers")
def get_zone_routers(
    zona_id: int,
    session: Session = Depends(get_sync_session),
    current_user: User = Depends(require_technician),
) -> List[Dict[str, Any]]:
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
) -> Dict[str, Any]:
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
            status_code=400, 
            detail=f"Router {host} is not provisioned for API access"
        )
    
    try:
        # Decrypt password and create service
        decrypted_password = decrypt_data(router_creds.password)
        service = RouterService(host, router_creds, decrypted_password)
        
        try:
            # Get interface data from the router
            api = service.pool.get_api()
            
            # Get all interfaces
            interfaces = api.get_resource("/interface").get()
            
            # Get VLANs
            vlans = api.get_resource("/interface/vlan").get()
            
            # Get bridges
            bridges = api.get_resource("/interface/bridge").get()
            
            # Get bridge ports
            bridge_ports = api.get_resource("/interface/bridge/port").get()
            
            # Get ethernet details (includes speed and PoE settings)
            ethernet_details = {}
            try:
                ethernet_list = api.get_resource("/interface/ethernet").get()
                for eth in ethernet_list:
                    name = eth.get("name", "")
                    ethernet_details[name] = {
                        "speed": eth.get("speed"),  # Configured speed
                        "poe_out": eth.get("poe-out"),  # PoE config: auto-on, off, forced-on
                    }
            except Exception:
                pass  # Not all routers support this
            
            # Get real link speed using ethernet monitor
            # This gives us the actual negotiated speed, not just the configured one
            link_speeds = {}
            try:
                ethernet_resource = api.get_resource("/interface/ethernet")
                # Monitor each ethernet interface that is running
                for iface in interfaces:
                    iface_name = iface.get("name", "")
                    if iface_name.startswith("ether") and iface.get("running") == "true":
                        try:
                            # Use call to run monitor command with once=true
                            monitor_result = ethernet_resource.call(
                                "monitor",
                                {"numbers": iface_name, "once": ""}
                            )
                            if monitor_result and len(monitor_result) > 0:
                                mon = monitor_result[0]
                                link_speeds[iface_name] = {
                                    "rate": mon.get("rate"),  # e.g., "100Mbps", "1Gbps"
                                    "status": mon.get("status"),  # e.g., "link-ok"
                                    "full_duplex": mon.get("full-duplex"),
                                    "auto_negotiation": mon.get("auto-negotiation"),
                                }
                        except Exception:
                            pass  # Individual interface monitoring failed
            except Exception as e:
                logger.debug(f"Could not monitor ethernet interfaces: {e}")
            
            # Get PoE status (for devices with PoE)
            poe_status = {}
            try:
                poe_list = api.get_resource("/interface/ethernet/poe").get()
                for poe in poe_list:
                    name = poe.get("name", "")
                    poe_status[name] = {
                        "poe_out_status": poe.get("poe-out-status"),  # powered-on, waiting-for-load, short-circuit, overload, off
                        "poe_out_voltage": poe.get("poe-out-voltage"),
                        "poe_out_current": poe.get("poe-out-current"),
                        "poe_out_power": poe.get("poe-out-power"),
                    }
            except Exception:
                pass  # Not all routers have PoE
            
            # Process interfaces for visualization
            physical_ports = []
            for iface in interfaces:
                iface_type = iface.get("type", "")
                iface_name = iface.get("name", "")
                
                # Filter for physical ethernet interfaces
                if iface_type == "ether" or iface_name.startswith("ether") or iface_name.startswith("sfp"):
                    # Find VLAN assignments for this port
                    port_vlans = [
                        {"id": v.get("vlan-id"), "name": v.get("name")}
                        for v in vlans
                        if v.get("interface") == iface_name
                    ]
                    
                    # Find bridge membership
                    bridge_membership = None
                    for bp in bridge_ports:
                        if bp.get("interface") == iface_name:
                            bridge_membership = bp.get("bridge")
                            break
                    
                    # Get Ethernet details for this interface
                    eth_info = ethernet_details.get(iface_name, {})
                    poe_info = poe_status.get(iface_name, {})
                    link_info = link_speeds.get(iface_name, {})
                    
                    # Determine PoE status - prioritize poe-out-status from PoE resource
                    poe_out_val = poe_info.get("poe_out_status") or eth_info.get("poe_out") or iface.get("poe-out")
                    
                    # Determine speed - prioritize monitor rate (actual), then interface rate, then config
                    speed_val = link_info.get("rate") or iface.get("rate") or eth_info.get("speed")
                    
                    physical_ports.append({
                        "id": iface.get(".id"),
                        "name": iface_name,
                        "type": iface_type,
                        "running": iface.get("running") == "true",
                        "disabled": iface.get("disabled") == "true",
                        "mac_address": iface.get("mac-address"),
                        "rate": speed_val,  # e.g., "1Gbps", "100Mbps"
                        "speed": speed_val,  # Same for compatibility
                        "poe": poe_out_val,  # PoE status: "powered-on", "off", "waiting-for-load", etc.
                        "poe_voltage": poe_info.get("poe_out_voltage"),
                        "poe_current": poe_info.get("poe_out_current"),
                        "poe_power": poe_info.get("poe_out_power"),
                        "vlans": port_vlans,
                        "bridge": bridge_membership,
                    })
            
            # Sort ports naturally (ether1, ether2, ... ether10, sfp1, etc.)
            def sort_key(port):
                name = port["name"]
                # Extract prefix and number
                import re
                match = re.match(r"([a-zA-Z]+)(\d+)", name)
                if match:
                    return (match.group(1), int(match.group(2)))
                return (name, 0)
            
            physical_ports.sort(key=sort_key)
            
            # Process bridges
            processed_bridges = []
            for bridge in bridges:
                bridge_name = bridge.get("name")
                members = [
                    bp.get("interface") 
                    for bp in bridge_ports 
                    if bp.get("bridge") == bridge_name
                ]
                processed_bridges.append({
                    "id": bridge.get(".id"),
                    "name": bridge_name,
                    "members": members,
                    "running": bridge.get("running") == "true",
                })
            
            return {
                "host": host,
                "hostname": router_creds.hostname,
                "model": router_creds.model,
                "ports": physical_ports,
                "bridges": processed_bridges,
                "vlans": [
                    {
                        "id": v.get(".id"),
                        "vlan_id": v.get("vlan-id"),
                        "name": v.get("name"),
                        "interface": v.get("interface"),
                    }
                    for v in vlans
                ],
            }
            
        finally:
            service.disconnect()
            
    except (RouterConnectionError, RouterNotProvisionedError) as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error fetching router data: {str(e)}"
        )

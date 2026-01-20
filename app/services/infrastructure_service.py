# app/services/infrastructure_service.py
from typing import Any


def get_device_infrastructure_data(api, host: str, hostname: str, model: str) -> dict[str, Any]:
    """
    Fetch live interface data from a device (Router or Switch) for SVG rendering.
    Returns structured data: physical ports, VLANs, bridges, and their relationships.
    """
    # Get all interfaces
    interfaces = api.get_resource("/interface").get()

    # Get VLANs
    vlans = api.get_resource("/interface/vlan").get()

    # Get bridges
    bridges = api.get_resource("/interface/bridge").get()

    # Get bridge ports
    bridge_ports = api.get_resource("/interface/bridge/port").get()

    # Get detailed ethernet status using reusable function
    from ..utils.device_clients.mikrotik.interfaces import MikrotikInterfaceManager

    interface_manager = MikrotikInterfaceManager(api)
    ethernet_status = interface_manager.get_ethernet_detailed_status()

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

            # Get detailed status from our reusable function
            eth_status = ethernet_status.get(iface_name, {})

            # Determine PoE status - prioritize poe_status, fallback to poe_config
            poe_out_val = eth_status.get("poe_status") or eth_status.get("poe_config")

            # Determine speed - prioritize rate (actual), fallback to speed_config
            speed_val = eth_status.get("rate") or eth_status.get("speed_config")

            physical_ports.append(
                {
                    "id": iface.get(".id"),
                    "name": iface_name,
                    "type": iface_type,
                    "running": iface.get("running") == "true",
                    "disabled": iface.get("disabled") == "true",
                    "mac_address": iface.get("mac-address"),
                    "rate": speed_val,
                    "speed": speed_val,
                    "poe": poe_out_val,
                    "poe_voltage": eth_status.get("poe_voltage"),
                    "poe_current": eth_status.get("poe_current"),
                    "poe_power": eth_status.get("poe_power"),
                    "vlans": port_vlans,
                    "bridge": bridge_membership,
                }
            )

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
        members = [bp.get("interface") for bp in bridge_ports if bp.get("bridge") == bridge_name]
        processed_bridges.append(
            {
                "id": bridge.get(".id"),
                "name": bridge_name,
                "members": members,
                "running": bridge.get("running") == "true",
            }
        )

    return {
        "host": host,
        "hostname": hostname,
        "model": model,
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

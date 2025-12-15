from routeros_api.api import RouterOsApi
from typing import List, Dict, Any
from .base import get_id


class MikrotikInterfaceManager:
    def __init__(self, api: RouterOsApi):
        self.api = api

    def add_vlan(
        self, name: str, vlan_id: str, interface: str, comment: str
    ) -> Dict[str, Any]:
        vlan_resource = self.api.get_resource("/interface/vlan")
        vlan_resource.add(
            name=name, vlan_id=vlan_id, interface=interface, comment=comment
        )
        return vlan_resource.get(name=name)[0]

    def update_vlan(
        self, vlan_id: str, name: str, new_vlan_id: str, interface: str
    ) -> Dict[str, Any]:
        vlan_resource = self.api.get_resource("/interface/vlan")
        vlan_resource.set(
            id=vlan_id, name=name, vlan_id=new_vlan_id, interface=interface
        )
        return vlan_resource.get(id=vlan_id)[0]

    def add_bridge(self, name: str, comment: str) -> Dict[str, Any]:
        bridge_resource = self.api.get_resource("/interface/bridge")
        bridge_resource.add(name=name, comment=comment)
        return bridge_resource.get(name=name)[0]

    def update_bridge(self, bridge_id: str, new_name: str = None) -> Dict[str, Any]:
        """
        Update a bridge. We return the bridge so the caller can use its name for port updates.
        If new_name matches existing name, no rename is done (just return the bridge).
        """
        bridge_resource = self.api.get_resource("/interface/bridge")
        
        # First try to find by name (new_name) since that's what we usually have
        bridges_by_name = bridge_resource.get(name=new_name) if new_name else []
        
        if bridges_by_name:
            # Bridge already exists with this name - no rename needed
            return bridges_by_name[0]
        
        # If not found by name, search all bridges to find by ID
        all_bridges = bridge_resource.get()
        current = None
        for b in all_bridges:
            bid = b.get(".id") or b.get("id")
            if bid == bridge_id:
                current = b
                break
        
        if not current:
            raise ValueError(f"Bridge {bridge_id} not found")
        
        current_name = current.get("name")
        
        # If new_name is different and not already taken, rename
        if new_name and new_name != current_name:
            actual_id = current.get(".id") or current.get("id")
            bridge_resource.set(id=actual_id, name=new_name)
            return bridge_resource.get(name=new_name)[0]
        
        return current

    def set_bridge_ports(self, bridge_name: str, ports: List[str]):
        """
        Update bridge ports using a diff approach:
        - Remove only ports that are no longer in the desired list
        - Add only ports that are new in the desired list
        This prevents accidentally removing ports not shown in the UI.
        """
        bridge_port_resource = self.api.get_resource("/interface/bridge/port")
        
        # Get current ports for this bridge
        current_ports = bridge_port_resource.get(bridge=bridge_name)
        current_port_names = {p.get("interface") for p in current_ports}
        desired_port_names = set(ports)
        
        # Calculate differences
        ports_to_remove = current_port_names - desired_port_names
        ports_to_add = desired_port_names - current_port_names
        
        # Remove only the ports that need to be removed
        for port in current_ports:
            if port.get("interface") in ports_to_remove:
                port_id = get_id(port)
                bridge_port_resource.remove(id=port_id)
        
        # Add only the new ports
        for port_name in ports_to_add:
            bridge_port_resource.add(bridge=bridge_name, interface=port_name)

    def get_bridge_ports(self) -> List[Dict[str, Any]]:
        return self.api.get_resource("/interface/bridge/port").get()

    def remove_interface(self, interface_id: str, interface_type: str):
        """Elimina una interfaz basada en su tipo."""
        resource_path = self._get_resource_path(interface_type)
        resource = self.api.get_resource(resource_path)
        resource.remove(id=interface_id)

    def set_interface_status(
        self, interface_id: str, disable: bool, interface_type: str
    ):
        """Habilita o deshabilita una interfaz."""
        resource_path = self._get_resource_path(interface_type)
        resource = self.api.get_resource(resource_path)
        resource.set(id=interface_id, disabled=disable)

    def _get_resource_path(self, interface_type: str) -> str:
        """Determina el path del recurso según el tipo de interfaz."""
        if interface_type == "vlan":
            return "/interface/vlan"
        elif interface_type == "bridge":
            return "/interface/bridge"
        elif interface_type == "ether":
            return "/interface/ethernet"
        else:
            # Fallback genérico, aunque podría fallar si el tipo no es exacto
            return f"/interface/{interface_type}"

    def get_ethernet_detailed_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Consolida estado de puertos ethernet desde configuración, monitor de tráfico y PoE.
        
        Returns:
            Dict[interface_name, {
                "poe_config": str,      # auto-on, off, etc
                "rate": str,            # 100Mbps, 1Gbps
                "status": str,          # link-ok, no-link
                "poe_status": str,      # powered-on, short-circuit
                "poe_voltage": str,     # Voltaje en V
                "poe_power": str        # Potencia en W
            }]
        """
    
        
        result = {}
        
        # Get all interfaces first to know which are running
        try:
            interfaces = self.api.get_resource("/interface").get()
            running_ethers = {
                iface.get("name"): iface.get("running") == "true"
                for iface in interfaces
                if iface.get("name", "").startswith("ether")
            }
        except Exception:
            running_ethers = {}
        
        # Get ethernet configuration (poe-out setting)
        try:
            ethernet_list = self.api.get_resource("/interface/ethernet").get()
            for eth in ethernet_list:
                name = eth.get("name", "")
                if name:
                    result[name] = {
                        "poe_config": eth.get("poe-out"),
                        "speed_config": eth.get("speed"),
                    }
        except Exception:
            pass
        
        # Get real link speed using ethernet monitor 
        try:
            ethernet_resource = self.api.get_resource("/interface/ethernet")
            for iface_name, is_running in running_ethers.items():
                if is_running:
                    try:
                        monitor_result = ethernet_resource.call(
                            "monitor",
                            {"numbers": iface_name, "once": ""}
                        )
                        if monitor_result and len(monitor_result) > 0:
                            mon = monitor_result[0]
                            if iface_name not in result:
                                result[iface_name] = {}
                            result[iface_name].update({
                                "rate": mon.get("rate"),
                                "status": mon.get("status"),
                                "full_duplex": mon.get("full-duplex"),
                                "auto_negotiation": mon.get("auto-negotiation"),
                            })
                    except Exception:
                        pass
        except Exception:
            pass
        
        # Get PoE status
        try:
            poe_list = self.api.get_resource("/interface/ethernet/poe").get()
            for poe in poe_list:
                name = poe.get("name", "")
                if name:
                    if name not in result:
                        result[name] = {}
                    result[name].update({
                        "poe_status": poe.get("poe-out-status"),
                        "poe_voltage": poe.get("poe-out-voltage"),
                        "poe_current": poe.get("poe-out-current"),
                        "poe_power": poe.get("poe-out-power"),
                    })
        except Exception:
            pass
        
        return result

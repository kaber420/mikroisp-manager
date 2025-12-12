from routeros_api.api import RouterOsApi
from typing import List, Dict, Any


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

    def update_bridge(self, bridge_id: str, name: str) -> Dict[str, Any]:
        bridge_resource = self.api.get_resource("/interface/bridge")
        bridge_resource.set(id=bridge_id, name=name)
        return bridge_resource.get(id=bridge_id)[0]

    def set_bridge_ports(self, bridge_name: str, ports: List[str]):
        bridge_port_resource = self.api.get_resource("/interface/bridge/port")

        # Remove existing ports
        for port in bridge_port_resource.get(bridge=bridge_name):
            bridge_port_resource.remove(id=port[".id"])

        # Add new ports
        for port_name in ports:
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

# app/utils/device_clients/adapters/mikrotik_router.py
import logging
from typing import Dict, Any, List, Optional
from routeros_api.api import RouterOsApi
from .base import BaseDeviceAdapter, DeviceStatus, ConnectedClient
from ..mikrotik import system, ip, firewall, queues, ppp, ssl
from ..mikrotik import connection as mikrotik_connection
from ..mikrotik.interfaces import MikrotikInterfaceManager

logger = logging.getLogger(__name__)

class MikrotikRouterAdapter(BaseDeviceAdapter):
    """
    Adapter for MikroTik Routers.
    Implements all standard RouterOS functionality (IP, Queues, Firewall, PPP, etc.)
    using the shared low-level modules.
    
    This adapter can be used by RouterService OR extended by MikrotikWirelessAdapter.
    """
    
    def __init__(self, host: str, username: str, password: str, port: int = 8729, api: Optional[RouterOsApi] = None):
        super().__init__(host, username, password, port)
        self._external_api = api
        self._pool_ref = None
        self._internal_api = None # Cache for local connection reuse

    @property
    def vendor(self) -> str:
        return "mikrotik"

    def _get_api(self) -> RouterOsApi:
        """
        Get an API connection.
        """
        if self._external_api:
            return self._external_api
            
        if self._internal_api:
            return self._internal_api

        # Use centralized connection manager but FORCE fresh connection (managed by this adapter)
        # to ensure proper isolation and cleanup
        self._pool_ref = mikrotik_connection.get_pool(self.host, self.username, self.password, self.port, force_new=True)
        self._internal_api = self._pool_ref.get_api()
        return self._internal_api

    def _exec_with_retry(self, callback):
        """
        Executes a callback that takes 'api' as argument.
        If a connection error occurs, clears local cache and retries once.
        """
        try:
            api = self._get_api()
            return callback(api)
        except Exception as e:
            # Basic detection of connection/SSL errors
            err_str = str(e).lower()
            retryable = any(x in err_str for x in ['connection', 'closed', 'file descriptor', 'ssl', 'broken pipe'])
            
            if retryable:
                logger.warning(f"Connection error in adapter ({e}). Retrying with fresh connection...")
                # 1. Clear local cache
                self._internal_api = None
                # 2. Get fresh API (this triggers pool logic if needed)
                api = self._get_api()
                # 3. Retry action
                return callback(api)
            raise e

    # --- BaseDeviceAdapter Implementation ---

    def get_status(self) -> DeviceStatus:
        """
        Get basic status for a Router (no wireless info).
        """
        try:
            api = self._get_api()
            sys_res = system.get_system_resources(api)
            
            # Simple status for a router
            return DeviceStatus(
                host=self.host,
                vendor=self.vendor,
                role="router",
                hostname=sys_res.get("name"),
                model=sys_res.get("model") or sys_res.get("board-name"),
                firmware=sys_res.get("version"),
                is_online=True,
                extra={
                    "cpu_load": sys_res.get("cpu-load"),
                    "free_memory": sys_res.get("free-memory"),
                    "total_memory": sys_res.get("total-memory"),
                    "platform": sys_res.get("platform")
                }
            )
        except Exception as e:
            logger.error(f"Error getting router status: {e}")
            return DeviceStatus(host=self.host, vendor=self.vendor, role="router", is_online=False, last_error=str(e))

    def get_connected_clients(self) -> List[ConnectedClient]:
        # Routers don't have "connected clients" in the AP sense (wireless registration).
        # Could return ARP table or similar if desired in future.
        return []

    def test_connection(self) -> bool:
        try:
            api = self._get_api()
            return bool(system.get_system_resources(api))
        except Exception:
            return False

    def disconnect(self):
        if self._external_api:
            self._external_api = None
            return
            
        # CRITICAL FIX: Do NOT destroy the shared pool on standard disconnect.
        # But DO close our local cached connection instance to prevent leaks.
        if self._pool_ref:
             try:
                 self._pool_ref.disconnect()
             except Exception:  # nosec B110 - Pool disconnect cleanup
                 pass
             self._pool_ref = None
             self._internal_api = None

    # --- Router Specific Methods (Migrated from RouterService) ---

    def get_full_details(self) -> Dict[str, Any]:
        """Obtains a complete view of the router configuration."""
        def fetch_all(api):
            interface_manager = MikrotikInterfaceManager(api)
            return {
                "interfaces": api.get_resource("/interface").get(),
                "ip_addresses": ip.get_ip_addresses(api),
                "nat_rules": firewall.get_nat_rules(api),
                "pppoe_servers": ppp.get_pppoe_servers(api),
                "ppp_profiles": ppp.get_ppp_profiles(api),
                "simple_queues": queues.get_simple_queues(api),
                "ip_pools": ip.get_ip_pools(api),
                "bridge_ports": interface_manager.get_bridge_ports(),
                "pppoe_secrets": ppp.get_pppoe_secrets(api),
                "pppoe_active": ppp.get_pppoe_active_connections(api),
                "users": system.get_router_users(api),
                "files": system.get_backup_files(api),
                "static_resources": system.get_system_resources(api),
            }
        
        try:
            return self._exec_with_retry(fetch_all)
        except Exception as e:
            logger.error(f"Error getting full details: {e}")
            raise e

    # --- Interfaces ---
    
    def add_vlan(self, name: str, vlan_id: str, interface: str, comment: str):
        api = self._get_api()
        manager = MikrotikInterfaceManager(api)
        return manager.add_vlan(name, vlan_id, interface, comment)

    def update_vlan(self, vlan_id: str, name: str, new_vlan_id: str, interface: str):
        api = self._get_api()
        manager = MikrotikInterfaceManager(api)
        return manager.update_vlan(vlan_id, name, new_vlan_id, interface)

    def add_bridge(self, name: str, ports: List[str], comment: str):
        api = self._get_api()
        manager = MikrotikInterfaceManager(api)
        bridge = manager.add_bridge(name, comment)
        manager.set_bridge_ports(name, ports)
        return bridge

    def update_bridge(self, bridge_id: str, name: str, ports: List[str]):
        api = self._get_api()
        manager = MikrotikInterfaceManager(api)
        bridge = manager.update_bridge(bridge_id, new_name=name)
        actual_name = bridge.get("name", name)
        manager.set_bridge_ports(actual_name, ports)
        return bridge

    def remove_interface(self, interface_id: str, interface_type: str):
        api = self._get_api()
        manager = MikrotikInterfaceManager(api)
        manager.remove_interface(interface_id, interface_type)

    def set_interface_status(self, interface_id: str, disable: bool, interface_type: str):
        api = self._get_api()
        manager = MikrotikInterfaceManager(api)
        manager.set_interface_status(interface_id, disable, interface_type)

    # --- PPP ---

    def set_pppoe_secret_status(self, secret_id: str, disable: bool):
        api = self._get_api()
        return ppp.enable_disable_pppoe_secret(api, secret_id=secret_id, disable=disable)

    def get_pppoe_secrets(self, username: str = None) -> List[Dict[str, Any]]:
        api = self._get_api()
        return ppp.get_pppoe_secrets(api, username=username)

    def get_ppp_profiles(self) -> List[Dict[str, Any]]:
        api = self._get_api()
        return ppp.get_ppp_profiles(api)
        
    def get_pppoe_active_connections(self, name: str = None) -> List[Dict[str, Any]]:
        api = self._get_api()
        return ppp.get_pppoe_active_connections(api, name=name)

    def create_pppoe_secret(self, **kwargs) -> Dict[str, Any]:
        api = self._get_api()
        return ppp.create_pppoe_secret(api, **kwargs)

    def update_pppoe_secret(self, secret_id: str, **kwargs) -> Dict[str, Any]:
        api = self._get_api()
        return ppp.update_pppoe_secret(api, secret_id, **kwargs)

    def remove_pppoe_secret(self, secret_id: str) -> None:
        api = self._get_api()
        return ppp.remove_pppoe_secret(api, secret_id)
        
    def add_pppoe_server(self, **kwargs):
        api = self._get_api()
        return ppp.add_pppoe_server(api, **kwargs)

    def remove_pppoe_server(self, service_name: str):
        api = self._get_api()
        return ppp.remove_pppoe_server(api, service_name=service_name)
        
    def create_service_plan(self, **kwargs):
        api = self._get_api()
        return ppp.create_service_plan(api, **kwargs)

    def remove_service_plan(self, plan_name: str):
        api = self._get_api()
        return ppp.remove_service_plan(api, plan_name=plan_name)
        
    def kill_pppoe_connection(self, username: str) -> Dict[str, Any]:
        api = self._get_api()
        return ppp.kill_active_pppoe_connection(api, username=username)

    def update_pppoe_profile(self, username: str, new_profile: str) -> Dict[str, Any]:
        api = self._get_api()
        return ppp.update_pppoe_secret_profile(api, username=username, new_profile=new_profile)

    # --- System ---
    
    def get_system_resources(self) -> Dict[str, Any]:
        return self._exec_with_retry(lambda api: system.get_system_resources(api))
        
    def get_backup_files(self):
        api = self._get_api()
        return system.get_backup_files(api)

    def create_backup(self, backup_name: str):
        api = self._get_api()
        return system.create_backup(api, backup_name=backup_name)

    def create_export_script(self, script_name: str):
        api = self._get_api()
        return system.create_export_script(api, script_name=script_name)

    def remove_file(self, file_id: str):
        api = self._get_api()
        return system.remove_file(api, file_id=file_id)

    def get_router_users(self):
        api = self._get_api()
        return system.get_router_users(api)

    def add_router_user(self, **kwargs):
        api = self._get_api()
        return system.add_router_user(api, **kwargs)

    def remove_router_user(self, user_id: str):
        api = self._get_api()
        return system.remove_router_user(api, user_id=user_id)
        
    def cleanup_connections(self, username: str) -> int:
        api = self._get_api()
        return system.kill_zombie_sessions(api, username=username)

    # --- IP & Firewall ---
    
    def add_ip_address(self, address: str, interface: str, comment: str):
        api = self._get_api()
        return ip.add_ip_address(api, address=address, interface=interface, comment=comment)

    def remove_ip_address(self, address: str):
        api = self._get_api()
        return ip.remove_ip_address(api, address=address)

    def add_nat_masquerade(self, **kwargs):
        api = self._get_api()
        return firewall.add_nat_masquerade(api, **kwargs)

    def remove_nat_rule(self, comment: str):
        api = self._get_api()
        return firewall.remove_nat_rule(api, comment=comment)
        
    def update_address_list(self, list_name: str, address: str, action: str, comment: str = "") -> Dict[str, Any]:
        api = self._get_api()
        return firewall.update_address_list_entry(api, list_name=list_name, address=address, action=action, comment=comment)

    def get_address_list(self, list_name: str = None) -> List[Dict[str, Any]]:
        api = self._get_api()
        return firewall.get_address_list_entries(api, list_name=list_name)

    # --- Queues ---
    
    def add_simple_queue(self, **kwargs):
        api = self._get_api()
        return queues.add_simple_queue(api, **kwargs)

    def remove_simple_queue(self, queue_id: str):
        api = self._get_api()
        return queues.remove_simple_queue(api, queue_id=queue_id)

    def get_simple_queue_stats(self, target: str) -> Optional[Dict[str, Any]]:
        api = self._get_api()
        all_queues = queues.get_simple_queues(api)
        target_variations = [target, f"{target}/32"]
        for queue in all_queues:
            if queue.get("target", "") in target_variations:
                return queue
        return None
        
    def update_queue_limit(self, target: str, max_limit: str) -> Dict[str, Any]:
        api = self._get_api()
        return queues.set_simple_queue_limit(api, target=target, max_limit=max_limit)

    # --- SSL/Certificate Management (Delegates to ssl module) ---
    
    def generate_csr(self, common_name: str, organization: str = "uManager") -> str:
        """Generate a CSR on the router (Router-Side generation)."""
        api = self._get_api()
        return ssl.generate_csr(api, self.host, self.username, self.password, common_name, organization)
    
    def import_certificate(self, cert_pem: str, key_pem: str = None, cert_name: str = "umanager_ssl") -> Dict[str, Any]:
        """Import a signed certificate."""
        api = self._get_api()
        return ssl.import_certificate(api, self.host, self.port, self.username, self.password, cert_pem, key_pem, cert_name)
    
    def install_ca_certificate(self, ca_pem: str, ca_name: str = "umanager_ca") -> Dict[str, Any]:
        """Install the Root CA certificate so the router trusts the server."""
        api = self._get_api()
        return ssl.install_ca_certificate(api, self.host, self.username, self.password, ca_pem, ca_name)
    
    def get_ssl_status(self) -> Dict[str, Any]:
        """Check the SSL/TLS status of the router."""
        return self._exec_with_retry(ssl.get_ssl_status)


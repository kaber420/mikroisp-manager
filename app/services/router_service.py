# app/services/router_service.py
import ssl
import logging
from typing import Dict, Any, List, Optional
from routeros_api import RouterOsApiPool
from fastapi import HTTPException, status

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from ..models.router import Router
from ..utils.security import encrypt_data, decrypt_data
from ..utils.device_clients.mikrotik import system, ip, firewall, queues, ppp
from ..utils.device_clients.mikrotik.interfaces import MikrotikInterfaceManager

logger = logging.getLogger(__name__)


class RouterConnectionError(Exception):
    pass


class RouterCommandError(Exception):
    pass


class RouterNotProvisionedError(Exception):
    pass


class RouterService:
    """
    Servicio para interactuar con un router específico.
    """

    def __init__(self, host: str, creds: Router, decrypted_password: str = None):
        self.host = host
        self.creds = creds

        if not self.creds:
            raise RouterConnectionError(f"Router {host} no encontrado.")

        if self.creds.api_port != self.creds.api_ssl_port:
            raise RouterNotProvisionedError(
                f"Router {host} no está aprovisionado. El servicio no puede conectar."
            )

        self.decrypted_password = decrypted_password
        self.pool = self._create_pool()

    def _create_pool(self) -> RouterOsApiPool:
        """Crea y devuelve un pool de conexiones SSL."""
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        # Decrypt password if not provided
        password = self.decrypted_password if self.decrypted_password else decrypt_data(self.creds.password)
        
        return RouterOsApiPool(
            self.host,
            username=self.creds.username,
            password=password,
            port=self.creds.api_ssl_port,
            use_ssl=True,
            ssl_context=ssl_context,
            plaintext_login=True,
        )

    def disconnect(self):
        """Cierra el pool de conexiones."""
        if self.pool:
            self.pool.disconnect()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def _execute_command(self, func, *args, **kwargs) -> Any:
        """Wrapper para ejecutar un comando de los módulos mikrotik manejando la conexión."""
        api = None
        try:
            api = self.pool.get_api()
            return func(api, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error de comando en {self.host} ({func.__name__}): {e}")
            raise RouterCommandError(f"Error en {self.host}: {e}")

    # --- MÉTODOS DELEGADOS A LOS NUEVOS MÓDULOS ---

    def add_vlan(self, name: str, vlan_id: str, interface: str, comment: str):
        api = self.pool.get_api()
        manager = MikrotikInterfaceManager(api)
        return manager.add_vlan(name, vlan_id, interface, comment)

    def update_vlan(self, vlan_id: str, name: str, new_vlan_id: str, interface: str):
        api = self.pool.get_api()
        manager = MikrotikInterfaceManager(api)
        return manager.update_vlan(vlan_id, name, new_vlan_id, interface)

    def add_bridge(self, name: str, ports: List[str], comment: str):
        api = self.pool.get_api()
        manager = MikrotikInterfaceManager(api)
        bridge = manager.add_bridge(name, comment)
        manager.set_bridge_ports(name, ports)
        return bridge

    def update_bridge(self, bridge_id: str, name: str, ports: List[str]):
        api = self.pool.get_api()
        manager = MikrotikInterfaceManager(api)
        bridge = manager.update_bridge(bridge_id, name)
        manager.set_bridge_ports(name, ports)
        return bridge

    def remove_interface(self, interface_id: str, interface_type: str):
        api = self.pool.get_api()
        manager = MikrotikInterfaceManager(api)
        manager.remove_interface(interface_id, interface_type)

    def set_interface_status(
        self, interface_id: str, disable: bool, interface_type: str
    ):
        api = self.pool.get_api()
        manager = MikrotikInterfaceManager(api)
        manager.set_interface_status(interface_id, disable, interface_type)

    def set_pppoe_secret_status(self, secret_id: str, disable: bool):
        return self._execute_command(
            ppp.enable_disable_pppoe_secret, secret_id=secret_id, disable=disable
        )

    def get_pppoe_secrets(self, username: str = None) -> List[Dict[str, Any]]:
        return self._execute_command(ppp.get_pppoe_secrets, username=username)

    def get_ppp_profiles(self) -> List[Dict[str, Any]]:
        """Obtiene solo la lista de perfiles PPP."""
        return self._execute_command(ppp.get_ppp_profiles)

    def get_pppoe_active_connections(self, name: str = None) -> List[Dict[str, Any]]:
        return self._execute_command(ppp.get_pppoe_active_connections, name=name)

    def create_pppoe_secret(self, **kwargs) -> Dict[str, Any]:
        return self._execute_command(ppp.create_pppoe_secret, **kwargs)

    def update_pppoe_secret(self, secret_id: str, **kwargs) -> Dict[str, Any]:
        return self._execute_command(ppp.update_pppoe_secret, secret_id, **kwargs)

    def remove_pppoe_secret(self, secret_id: str) -> None:
        return self._execute_command(ppp.remove_pppoe_secret, secret_id)

    def get_system_resources(self) -> Dict[str, Any]:
        return self._execute_command(system.get_system_resources)

    def create_service_plan(self, **kwargs):
        return self._execute_command(ppp.create_service_plan, **kwargs)

    def add_simple_queue(self, **kwargs):
        return self._execute_command(queues.add_simple_queue, **kwargs)

    def add_ip_address(self, address: str, interface: str, comment: str):
        return self._execute_command(
            ip.add_ip_address, address=address, interface=interface, comment=comment
        )

    def add_nat_masquerade(self, **kwargs):
        return self._execute_command(firewall.add_nat_masquerade, **kwargs)

    def add_pppoe_server(self, **kwargs):
        return self._execute_command(ppp.add_pppoe_server, **kwargs)

    def remove_ip_address(self, address: str):
        return self._execute_command(ip.remove_ip_address, address=address)

    def remove_nat_rule(self, comment: str):
        return self._execute_command(firewall.remove_nat_rule, comment=comment)

    def remove_pppoe_server(self, service_name: str):
        return self._execute_command(ppp.remove_pppoe_server, service_name=service_name)

    def remove_service_plan(self, plan_name: str):
        return self._execute_command(ppp.remove_service_plan, plan_name=plan_name)

    def remove_simple_queue(self, queue_id: str):
        return self._execute_command(queues.remove_simple_queue, queue_id=queue_id)

    # --- NEW: Service Suspension & Connection Management Methods ---

    def update_address_list(
        self, list_name: str, address: str, action: str, comment: str = ""
    ) -> Dict[str, Any]:
        """
        Updates an address list entry. 
        action: 'add', 'remove', or 'disable'
        """
        return self._execute_command(
            firewall.update_address_list_entry,
            list_name=list_name,
            address=address,
            action=action,
            comment=comment,
        )

    def get_address_list(self, list_name: str = None) -> List[Dict[str, Any]]:
        """Gets address list entries, optionally filtered by list name."""
        return self._execute_command(
            firewall.get_address_list_entries, list_name=list_name
        )

    def kill_pppoe_connection(self, username: str) -> Dict[str, Any]:
        """Terminates an active PPPoE connection for a specific user."""
        return self._execute_command(ppp.kill_active_pppoe_connection, username=username)

    def update_pppoe_profile(self, username: str, new_profile: str) -> Dict[str, Any]:
        """Updates the profile for a PPPoE secret by username (for plan changes)."""
        return self._execute_command(
            ppp.update_pppoe_secret_profile, username=username, new_profile=new_profile
        )

    def suspend_service(
        self, 
        address: str, 
        list_name: str, 
        strategy: str = "blacklist",
        pppoe_username: str = None,
        comment: str = "Suspended by UManager"
    ) -> Dict[str, Any]:
        """
        Suspends a service based on the configured strategy.
        
        Args:
            address: IP address of the client
            list_name: Name of the address list to use
            strategy: 'blacklist' (add to list = block) or 'whitelist' (remove from list = block)
            pppoe_username: If provided, also kills active PPPoE connection
            comment: Comment for the address list entry
        
        Returns:
            dict with status and details of actions taken
        """
        results = {"address_list": None, "pppoe_kill": None}
        
        # Address list action based on strategy
        if strategy == "blacklist":
            # Blacklist: Add to list to block
            results["address_list"] = self.update_address_list(
                list_name=list_name, address=address, action="add", comment=comment
            )
        elif strategy == "whitelist":
            # Whitelist: Remove from list to block (no longer allowed)
            results["address_list"] = self.update_address_list(
                list_name=list_name, address=address, action="remove"
            )
        
        # Kill PPPoE connection if username provided
        if pppoe_username:
            results["pppoe_kill"] = self.kill_pppoe_connection(pppoe_username)
        
        return results

    def restore_service(
        self,
        address: str,
        list_name: str,
        strategy: str = "blacklist",
        comment: str = "Restored by UManager"
    ) -> Dict[str, Any]:
        """
        Restores a suspended service based on the configured strategy.
        
        Args:
            address: IP address of the client
            list_name: Name of the address list to use
            strategy: 'blacklist' (remove from list = unblock) or 'whitelist' (add to list = allow)
            comment: Comment for the address list entry
        
        Returns:
            dict with status of the action
        """
        if strategy == "blacklist":
            # Blacklist: Remove from list to unblock
            return self.update_address_list(
                list_name=list_name, address=address, action="remove"
            )
        elif strategy == "whitelist":
            # Whitelist: Add back to list to allow
            return self.update_address_list(
                list_name=list_name, address=address, action="add", comment=comment
            )
        return {"status": "error", "message": f"Unknown strategy: {strategy}"}

    def change_plan(
        self,
        pppoe_username: str,
        new_profile: str,
        kill_connection: bool = True
    ) -> Dict[str, Any]:
        """
        Changes a user's plan by updating their PPPoE profile.
        Optionally kills the active connection to force re-authentication.
        
        Args:
            pppoe_username: The PPPoE username to update
            new_profile: Name of the new PPP profile
            kill_connection: If True, terminates active connection after update
        
        Returns:
            dict with status and details of actions taken
        """
        results = {"profile_update": None, "connection_kill": None}
        
        # Update the secret's profile
        results["profile_update"] = self.update_pppoe_profile(pppoe_username, new_profile)
        
        # Kill connection to force re-auth with new profile
        if kill_connection and results["profile_update"].get("status") == "success":
            results["connection_kill"] = self.kill_pppoe_connection(pppoe_username)
        
        return results

    def get_backup_files(self):
        return self._execute_command(system.get_backup_files)

    def create_backup(self, backup_name: str):
        return self._execute_command(system.create_backup, backup_name=backup_name)

    def create_export_script(self, script_name: str):
        return self._execute_command(
            system.create_export_script, script_name=script_name
        )

    def remove_file(self, file_id: str):
        return self._execute_command(system.remove_file, file_id=file_id)

    def get_router_users(self):
        return self._execute_command(system.get_router_users)

    def add_router_user(self, **kwargs):
        return self._execute_command(system.add_router_user, **kwargs)

    def remove_router_user(self, user_id: str):
        return self._execute_command(system.remove_router_user, user_id=user_id)

    # --- Legacy-compatible Suspension Methods (used by billing_service) ---
    
    def _get_prefixed_list_name(self, base_name: str, strategy: str) -> str:
        """Returns the address list name with BL_/WL_ prefix based on strategy."""
        prefix = "BL_" if strategy == "blacklist" else "WL_"
        return f"{prefix}{base_name}"

    def suspend_user_address_list(
        self, 
        ip: str, 
        list_name: str = None, 
        strategy: str = None
    ) -> Dict[str, Any]:
        """
        Suspends a user by managing their IP in the address list.
        Uses the provided strategy/name or falls back to router defaults.
        """
        # Fallback logic: Argument -> Creds -> Default
        strategy = strategy or getattr(self.creds, 'address_list_strategy', 'blacklist') or 'blacklist'
        base_name = list_name or getattr(self.creds, 'address_list_name', 'morosos') or 'morosos'
        
        full_list_name = self._get_prefixed_list_name(base_name, strategy)
        
        logger.info(f"🔴 Suspending {ip} via address list '{full_list_name}' (strategy: {strategy})")
        return self.suspend_service(
            address=ip,
            list_name=full_list_name,
            strategy=strategy,
            comment=f"Suspended by UManager - {ip}"
        )

    def activate_user_address_list(
        self, 
        ip: str, 
        list_name: str = None, 
        strategy: str = None
    ) -> Dict[str, Any]:
        """
        Restores a user by managing their IP in the address list.
        Uses the provided strategy/name or falls back to router defaults.
        """
        # Fallback logic: Argument -> Creds -> Default
        strategy = strategy or getattr(self.creds, 'address_list_strategy', 'blacklist') or 'blacklist'
        base_name = list_name or getattr(self.creds, 'address_list_name', 'morosos') or 'morosos'
        
        full_list_name = self._get_prefixed_list_name(base_name, strategy)
        
        logger.info(f"🟢 Restoring {ip} via address list '{full_list_name}' (strategy: {strategy})")
        return self.restore_service(
            address=ip,
            list_name=full_list_name,
            strategy=strategy,
            comment=f"Restored by UManager - {ip}"
        )

    def suspend_user_limit(self, ip: str, min_limit: str = "1k/1k") -> Dict[str, Any]:
        """
        Suspends a user by setting their queue limit to the minimum.
        """
        logger.info(f"🔴 Suspending {ip} via queue limit (setting to {min_limit})")
        return self._execute_command(
            queues.set_simple_queue_limit, target=ip, max_limit=min_limit
        )

    def activate_user_limit(self, ip: str, max_limit: str) -> Dict[str, Any]:
        """
        Restores a user's queue limit to their plan speed.
        """
        logger.info(f"🟢 Restoring {ip} queue limit to {max_limit}")
        return self._execute_command(
            queues.set_simple_queue_limit, target=ip, max_limit=max_limit
        )

    def update_queue_limit(self, target: str, max_limit: str) -> Dict[str, Any]:
        """
        Updates a simple queue's max-limit (used for plan changes).
        """
        logger.info(f"📊 Updating queue limit for {target} to {max_limit}")
        return self._execute_command(
            queues.set_simple_queue_limit, target=target, max_limit=max_limit
        )


    def get_full_details(self) -> Dict[str, Any]:
        """
        Obtiene una vista completa de la configuración del router en una sola sesión.
        """
        api = None
        try:
            # Obtener una única conexión para todas las operaciones
            api = self.pool.get_api()
            interface_manager = MikrotikInterfaceManager(api)

            # Ejecutar todos los comandos con la misma conexión
            details = {
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
            return details
        except Exception as e:
            logger.error(f"Error obteniendo detalles completos de {self.host}: {e}")
            raise RouterCommandError(f"Error en {self.host}: {e}")

    def cleanup_connections(self) -> int:
        """
        Auto-saneamiento: Elimina sesiones zombies en el router.
        """
        try:
            # Usamos nuestro usuario actual para buscar sus duplicados
            return self._execute_command(
                system.kill_zombie_sessions, username=self.creds.username
            )
        except Exception:
            # Es normal que falle al final si nos auto-eliminamos.
            # Lo importante es que intentamos limpiar.
            return 0


# --- CRUD Functions (Sync for background tasks) ---

def get_enabled_routers_sync(session) -> List[Router]:
    """Synchronous version of get_enabled_routers."""
    statement = select(Router).where(Router.is_enabled == True).where(Router.api_port == Router.api_ssl_port)
    return session.exec(statement).all()


# --- CRUD Functions (Async) ---

async def get_all_routers(session: AsyncSession) -> List[Dict[str, Any]]:
    from ..models.zona import Zona
    
    # Fetch routers with zona_nombre via LEFT JOIN
    statement = (
        select(Router, Zona.nombre.label("zona_nombre"))
        .outerjoin(Zona, Router.zona_id == Zona.id)
    )
    result = await session.execute(statement)
    rows = result.all()
    
    # Convert to dict and add zona_nombre
    routers_list = []
    for router, zona_nombre in rows:
        router_dict = router.model_dump()
        router_dict["zona_nombre"] = zona_nombre
        routers_list.append(router_dict)
    
    return routers_list

async def get_router_by_host(session: AsyncSession, host: str) -> Optional[Router]:
    router = await session.get(Router, host)
    return router

async def create_router(session: AsyncSession, router_data: dict) -> Router:
    # Encrypt password
    if "password" in router_data:
        router_data["password"] = encrypt_data(router_data["password"])
    
    router = Router(**router_data)
    session.add(router)
    await session.commit()
    await session.refresh(router)
    return router

async def update_router(session: AsyncSession, host: str, router_data: dict) -> Optional[Router]:
    router = await session.get(Router, host)
    if not router:
        return None
    
    if "password" in router_data and router_data["password"]:
        router_data["password"] = encrypt_data(router_data["password"])
        
    for key, value in router_data.items():
        setattr(router, key, value)
        
    session.add(router)
    await session.commit()
    await session.refresh(router)
    return router

async def delete_router(session: AsyncSession, host: str) -> bool:
    router = await session.get(Router, host)
    if not router:
        return False
    await session.delete(router)
    await session.commit()
    return True

async def get_enabled_routers(session: AsyncSession) -> List[Router]:
    statement = select(Router).where(Router.is_enabled == True).where(Router.api_port == Router.api_ssl_port)
    result = await session.exec(statement)
    return result.all()


# --- Dependency Injection ---
from fastapi import Depends
from ..db.engine import get_session

async def get_router_service(host: str, session: AsyncSession = Depends(get_session)):
    """
    Obtiene una instancia de RouterService y asegura que la conexión se cierre correctamente.
    """
    service = None
    try:
        # Obtener credenciales del router desde la BD
        router = await get_router_by_host(session, host)
        if not router:
            raise RouterConnectionError(f"Router {host} no encontrado en la DB.")
        
        # Crear el servicio (esto abre la conexión al router)
        service = RouterService(host, router)
        
        # Entregar el servicio al endpoint que lo solicitó
        yield service
        
    except (RouterConnectionError, RouterNotProvisionedError) as e:
        # Manejo de errores si no se pudo conectar al inicio
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error en get_router_service para {host}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
    finally:
        # CRÍTICO: Cerrar la conexión SIEMPRE después de que el endpoint termine
        if service:
            try:
                service.disconnect()
                logger.debug(f"✅ Conexión con {host} cerrada correctamente.")
            except Exception as e:
                logger.error(f"❌ Error cerrando conexión con {host}: {e}")

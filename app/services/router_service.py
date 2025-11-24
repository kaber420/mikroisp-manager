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
    service = None
    try:
        # --- FASE 1: PREPARACIÓN (Setup) ---
        router = await get_router_by_host(session, host)
        if not router:
             raise RouterConnectionError(f"Router {host} no encontrado en la DB.")
        
        # Initialize service with router model (contains encrypted password)
        service = RouterService(host, router)

        # --- PAUSA Y ENTREGA ---
        yield service

    except (RouterConnectionError, RouterNotProvisionedError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )

    finally:
        # --- FASE 2: LIMPIEZA (Teardown) ---
        if service:
            try:
                service.disconnect()
                # print(f"Conexión con {host} cerrada correctamente.")
            except Exception as e:
                print(f"Error cerrando conexión: {e}")

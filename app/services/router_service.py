
import logging
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..db.router_db import get_router_by_host
from ..models.router import Router
from ..utils.security import decrypt_data, encrypt_data

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
        self.decrypted_password = decrypted_password
        self.adapter = None

        if not self.creds:
            raise RouterConnectionError(f"Router {host} no encontrado.")

        # Use is_provisioned flag to determine if router is ready for secure connection
        if not self.creds.is_provisioned:
            raise RouterNotProvisionedError(
                f"Router {host} no está aprovisionado. El servicio no puede conectar."
            )

        # Initialize the adapter
        # Handle password: it might be already decrypted if creds came from router_db.get_router_by_host
        password = self.decrypted_password
        if not password:
            try:
                # Attempt to decrypt
                password = decrypt_data(self.creds.password)
            except Exception:
                # If decrypt fails, assume it's already plain text (refactored db returns decrypted)
                password = self.creds.password

        from ..utils.device_clients.adapters.mikrotik_router import MikrotikRouterAdapter

        self.adapter = MikrotikRouterAdapter(
            host=self.host,
            username=self.creds.username,
            password=password,
            port=self.creds.api_ssl_port,
        )

    def disconnect(self):
        """
        Cierra la conexión del adaptador.
        """
        if self.adapter:
            try:
                self.adapter.disconnect()
            except Exception:
                pass
            self.adapter = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def get_api_client(self):
        """
        Devuelve el cliente API subyacente (RouterOsApi).
        Útil para servicios compartidos que necesitan acceso directo.
        """
        if not self.adapter:
            raise RouterConnectionError("Adapter is not initialized")
        return self.adapter._get_api()

    # --- MÉTODOS DELEGADOS A LOS NUEVOS MÓDULOS ---
    # Ahora estos métodos simplemente delegan en el adaptador

    def add_vlan(self, name: str, vlan_id: str, interface: str, comment: str):
        return self.adapter.add_vlan(name, vlan_id, interface, comment)

    def update_vlan(self, vlan_id: str, name: str, new_vlan_id: str, interface: str):
        return self.adapter.update_vlan(vlan_id, name, new_vlan_id, interface)

    def add_bridge(self, name: str, ports: list[str], comment: str):
        return self.adapter.add_bridge(name, ports, comment)

    def update_bridge(self, bridge_id: str, name: str, ports: list[str]):
        return self.adapter.update_bridge(bridge_id, name, ports)

    def remove_interface(self, interface_id: str, interface_type: str):
        return self.adapter.remove_interface(interface_id, interface_type)

    def set_interface_status(self, interface_id: str, disable: bool, interface_type: str):
        return self.adapter.set_interface_status(interface_id, disable, interface_type)

    def set_pppoe_secret_status(self, secret_id: str, disable: bool):
        return self.adapter.set_pppoe_secret_status(secret_id, disable)

    def get_pppoe_secrets(self, username: str = None) -> list[dict[str, Any]]:
        return self.adapter.get_pppoe_secrets(username)

    def get_ppp_profiles(self) -> list[dict[str, Any]]:
        return self.adapter.get_ppp_profiles()

    def get_pppoe_active_connections(self, name: str = None) -> list[dict[str, Any]]:
        return self.adapter.get_pppoe_active_connections(name)

    def create_pppoe_secret(self, **kwargs) -> dict[str, Any]:
        return self.adapter.create_pppoe_secret(**kwargs)

    def update_pppoe_secret(self, secret_id: str, **kwargs) -> dict[str, Any]:
        return self.adapter.update_pppoe_secret(secret_id, **kwargs)

    def remove_pppoe_secret(self, secret_id: str) -> None:
        return self.adapter.remove_pppoe_secret(secret_id)

    def get_system_resources(self) -> dict[str, Any]:
        return self.adapter.get_system_resources()

    def create_service_plan(self, **kwargs):
        return self.adapter.create_service_plan(**kwargs)

    def add_simple_queue(self, **kwargs):
        return self.adapter.add_simple_queue(**kwargs)

    def add_ip_address(self, address: str, interface: str, comment: str):
        return self.adapter.add_ip_address(address, interface, comment)

    def add_nat_masquerade(self, **kwargs):
        return self.adapter.add_nat_masquerade(**kwargs)

    def add_pppoe_server(self, **kwargs):
        return self.adapter.add_pppoe_server(**kwargs)

    def remove_ip_address(self, address: str):
        return self.adapter.remove_ip_address(address)

    def remove_nat_rule(self, comment: str):
        return self.adapter.remove_nat_rule(comment)

    def remove_pppoe_server(self, service_name: str):
        return self.adapter.remove_pppoe_server(service_name)

    def remove_service_plan(self, plan_name: str):
        return self.adapter.remove_service_plan(plan_name)

    def remove_simple_queue(self, queue_id: str):
        return self.adapter.remove_simple_queue(queue_id)

    def get_simple_queue_stats(self, target: str) -> dict[str, Any] | None:
        return self.adapter.get_simple_queue_stats(target)

    # --- NEW: Service Suspension & Connection Management Methods ---

    def update_address_list(
        self, list_name: str, address: str, action: str, comment: str = ""
    ) -> dict[str, Any]:
        return self.adapter.update_address_list(list_name, address, action, comment)

    def get_address_list(self, list_name: str = None) -> list[dict[str, Any]]:
        return self.adapter.get_address_list(list_name)

    def kill_pppoe_connection(self, username: str) -> dict[str, Any]:
        return self.adapter.kill_pppoe_connection(username)

    def update_pppoe_profile(self, username: str, new_profile: str) -> dict[str, Any]:
        return self.adapter.update_pppoe_profile(username, new_profile)

    def suspend_service(
        self,
        address: str,
        list_name: str,
        strategy: str = "blacklist",
        pppoe_username: str = None,
        comment: str = "Suspended by UManager",
    ) -> dict[str, Any]:
        return self.adapter.suspend_service(address, list_name, strategy, pppoe_username, comment)

    def restore_service(
        self,
        address: str,
        list_name: str,
        strategy: str = "blacklist",
        comment: str = "Restored by UManager",
    ) -> dict[str, Any]:
        return self.adapter.restore_service(address, list_name, strategy, comment)

    def change_plan(
        self, pppoe_username: str, new_profile: str, kill_connection: bool = True
    ) -> dict[str, Any]:
        return self.adapter.change_plan(pppoe_username, new_profile, kill_connection)

    def get_backup_files(self):
        return self.adapter.get_backup_files()

    def create_backup(self, backup_name: str):
        return self.adapter.create_backup(backup_name)

    def create_export_script(self, script_name: str):
        return self.adapter.create_export_script(script_name)

    def remove_file(self, file_id: str):
        return self.adapter.remove_file(file_id)

    def get_router_users(self):
        return self.adapter.get_router_users()

    def add_router_user(self, **kwargs):
        return self.adapter.add_router_user(**kwargs)

    def remove_router_user(self, user_id: str):
        return self.adapter.remove_router_user(user_id)

    # --- Legacy-compatible Suspension Methods (used by billing_service) ---

    def _get_prefixed_list_name(self, base_name: str, strategy: str) -> str:
        """Returns the address list name with BL_/WL_ prefix based on strategy."""
        prefix = "BL_" if strategy == "blacklist" else "WL_"
        return f"{prefix}{base_name}"

    def suspend_user_address_list(
        self, ip: str, list_name: str = None, strategy: str = None
    ) -> dict[str, Any]:
        strategy = (
            strategy or getattr(self.creds, "address_list_strategy", "blacklist") or "blacklist"
        )
        base_name = list_name or getattr(self.creds, "address_list_name", "morosos") or "morosos"
        full_list_name = self._get_prefixed_list_name(base_name, strategy)

        logger.info(
            f"🔴 Suspending {ip} via address list '{full_list_name}' (strategy: {strategy})"
        )
        return self.suspend_service(
            address=ip,
            list_name=full_list_name,
            strategy=strategy,
            comment=f"Suspended by UManager - {ip}",
        )

    def activate_user_address_list(
        self, ip: str, list_name: str = None, strategy: str = None
    ) -> dict[str, Any]:
        strategy = (
            strategy or getattr(self.creds, "address_list_strategy", "blacklist") or "blacklist"
        )
        base_name = list_name or getattr(self.creds, "address_list_name", "morosos") or "morosos"
        full_list_name = self._get_prefixed_list_name(base_name, strategy)

        logger.info(f"🟢 Restoring {ip} via address list '{full_list_name}' (strategy: {strategy})")
        return self.restore_service(
            address=ip,
            list_name=full_list_name,
            strategy=strategy,
            comment=f"Restored by UManager - {ip}",
        )

    def suspend_user_limit(self, ip: str, min_limit: str = "1k/1k") -> dict[str, Any]:
        logger.info(f"🔴 Suspending {ip} via queue limit (setting to {min_limit})")
        return self.adapter.update_queue_limit(target=ip, max_limit=min_limit)

    def activate_user_limit(self, ip: str, max_limit: str) -> dict[str, Any]:
        logger.info(f"🟢 Restoring {ip} queue limit to {max_limit}")
        return self.adapter.update_queue_limit(target=ip, max_limit=max_limit)

    def update_queue_limit(self, target: str, max_limit: str) -> dict[str, Any]:
        logger.info(f"📊 Updating queue limit for {target} to {max_limit}")
        return self.adapter.update_queue_limit(target=target, max_limit=max_limit)

    def get_full_details(self) -> dict[str, Any]:
        return self.adapter.get_full_details()

    def cleanup_connections(self) -> int:
        return self.adapter.cleanup_connections(self.creds.username)

    def ensure_ssl_provisioned(self) -> bool:
        """
        Checks if the router has a valid/trusted SSL certificate.
        If not, automatically provisions one using PKIService.
        Returns True if provisioned (or already valid), False if failed.
        """
        try:
            # 1. Check current Status
            status = self.adapter.get_ssl_status()  # Use adapter directly

            # If already secure, we are good.
            # We check both is_trusted AND that it is enabled (ssl_enabled=True)
            if (
                status.get("ssl_enabled")
                and status.get("is_trusted")
                and status.get("status") == "secure"
            ):
                logger.info(f"Router {self.host} SSL is ALREADY SECURE (Zero Trust Compliant).")
                return True

            logger.warning(
                f"Router {self.host} SSL is INSECURE ({status.get('status')}). Auto-provisioning for Zero Trust..."
            )

            # 2. Generate Certs
            from .pki_service import PKIService

            pki = PKIService()
            success, key_pem, cert_pem = pki.generate_full_cert_pair(self.host)

            if not success:
                logger.error(f"Failed to generate certificates for {self.host}")
                return False

            # 3. Import & Apply (Atomic SSH Restart logic inside adapter)
            result = self.adapter.import_certificate(cert_pem, key_pem)

            if result.get("status") == "success":
                logger.info(f"✅ Auto-provisioning successful for {self.host}. Connection secured.")
                return True
            else:
                logger.error(
                    f"❌ Auto-provisioning failed for {self.host}: {result.get('message')}"
                )
                return False

        except Exception as e:
            logger.error(f"Error in ensure_ssl_provisioned for {self.host}: {e}")
            import traceback

            traceback.print_exc()
            return False



# --- CRUD Functions (Sync for background tasks) ---

def get_enabled_routers_sync(session) -> list[Router]:
    """Synchronous version of get_enabled_routers."""
    # We need to import select here or use existing
    # select is already imported from sqlmodel at top level
    statement = select(Router).where(Router.is_enabled == True).where(Router.is_provisioned == True)
    # Check if we need to decrypt passwords? 
    # original get_enabled_routers_from_db did decrypt.
    # The consumers of this function (like billing_job) expect Router objects.
    # RouterService.__init__ handles decryption if we pass encrypted.
    # But wait, RouterService.__init__ checks:
    # password = self.decrypted_password
    # if not password: try decrypt(self.creds.password)
    # So if we return the object from DB directly (encrypted), RouterService will handle it.
    # Correct.
    return session.exec(statement).all()


# --- Dependency Injection ---
from fastapi import Depends

from ..db.engine import get_session


async def get_router_service(host: str, session: AsyncSession = Depends(get_session)):
    """
    Obtiene una instancia de RouterService y asegura que la conexión se cierre correctamente.
    REQUIERE que el router esté aprovisionado (is_provisioned=True).
    """
    service = None
    try:
        # Obtener credenciales del router desde la BD usando el módulo refactorizado
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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    finally:
        # CRÍTICO: Cerrar la conexión SIEMPRE después de que el endpoint termine
        if service:
            try:
                service.disconnect()
                logger.debug(f"✅ Conexión con {host} cerrada correctamente.")
            except Exception as e:
                logger.error(f"❌ Error cerrando conexión con {host}: {e}")


async def get_router_service_for_provisioning(
    host: str, session: AsyncSession = Depends(get_session)
):
    """
    Obtiene un adapter de conexión para routers que NO están aprovisionados.

    Usado por endpoints de SSL/provisioning que necesitan conectar a routers
    antes de que tengan is_provisioned=True.

    NOTA: Este NO es un RouterService completo, es solo el adapter directo.
    """
    adapter = None
    try:
        # Obtener credenciales del router desde la BD
        router = await get_router_by_host(session, host)
        if not router:
            raise RouterConnectionError(f"Router {host} no encontrado en la DB.")

        # Handle password decryption safely
        password = router.password
        try:
            password = decrypt_data(router.password)
        except Exception:
            pass
            
        # Create adapter directly (bypassing is_provisioned check)
        from ..utils.device_clients.adapters.mikrotik_router import MikrotikRouterAdapter

        adapter = MikrotikRouterAdapter(
            host=host,
            username=router.username,
            password=password,
            port=router.api_ssl_port,  # Intentar SSL primero
        )

        # Return a simple object with the adapter and host
        class ProvisioningContext:
            def __init__(self, host, adapter, creds):
                self.host = host
                self.adapter = adapter
                self.creds = creds

        yield ProvisioningContext(host, adapter, router)

    except RouterConnectionError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error en get_router_service_for_provisioning para {host}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    finally:
        # Cerrar la conexión
        if adapter:
            try:
                adapter.disconnect()
            except Exception:
                pass

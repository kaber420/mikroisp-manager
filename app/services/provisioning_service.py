"""
DEPRECATED: Use app.services.provisioning.MikrotikProvisioningService instead.

This module is kept for backwards compatibility only.
New code should import from app.services.provisioning directly.
"""

import logging
import warnings
from typing import Any

from fastapi import HTTPException

from ..models.router import Router
from ..services.router_service import update_router as update_router_service
from ..utils.security import decrypt_data

# Import the new unified service
from .provisioning import MikrotikProvisioningService

logger = logging.getLogger(__name__)


class ProvisioningService:
    """
    Legacy Provisioning Service - DEPRECATED.

    Delegates to MikrotikProvisioningService for all operations.
    Will be removed in a future version.

    Use MikrotikProvisioningService.provision_device() directly instead.
    """

    @staticmethod
    async def auto_provision_ssl(session, router: Router) -> bool:
        """
        Attempts to auto-provision SSL for a newly created router (Zero Trust).
        This runs as a background/side-effect task during creation.

        DEPRECATED: This method is kept for backwards compatibility.
        """
        warnings.warn(
            "ProvisioningService.auto_provision_ssl is deprecated.",
            DeprecationWarning,
            stacklevel=2,
        )

        try:
            from ..services.router_service import RouterService

            password = decrypt_data(router.password)
            service = RouterService(router.host, router, decrypted_password=password)

            try:
                is_secure = service.ensure_ssl_provisioned()
                if is_secure:
                    if router.api_port != router.api_ssl_port:
                        await update_router_service(
                            session, router.host, {"api_port": router.api_ssl_port}
                        )
                        return True
            finally:
                service.disconnect()
        except Exception as e:
            logger.error(f"Failed to auto-provision SSL for {router.host}: {e}")
            return False
        return False

    @staticmethod
    def _run_provisioning_sync(
        creds, password, new_user, new_password, new_group="api_full_access"
    ):
        """
        DEPRECATED: Use MikrotikProvisioningService._run_api_provisioning() instead.
        """
        warnings.warn(
            "ProvisioningService._run_provisioning_sync is deprecated. "
            "Use MikrotikProvisioningService._run_api_provisioning() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return MikrotikProvisioningService._run_api_provisioning(
            host=creds.host,
            username=creds.username,
            password=password,
            new_user=new_user,
            new_password=new_password,
            ssl_port=creds.api_ssl_port,
            api_port=creds.api_port,
            new_group=new_group,
        )

    @staticmethod
    def _run_provisioning_ssh_pure(
        host: str,
        ssh_username: str,
        ssh_password: str,
        new_user: str,
        new_password: str,
        ssl_port: int = 8729,
        new_group: str = "api_full_access",
    ) -> dict[str, Any]:
        """
        DEPRECATED: Use MikrotikProvisioningService._run_ssh_provisioning() instead.
        """
        warnings.warn(
            "ProvisioningService._run_provisioning_ssh_pure is deprecated. "
            "Use MikrotikProvisioningService._run_ssh_provisioning() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return MikrotikProvisioningService._run_ssh_provisioning(
            host=host,
            ssh_username=ssh_username,
            ssh_password=ssh_password,
            new_user=new_user,
            new_password=new_password,
            ssl_port=ssl_port,
            new_group=new_group,
        )

    @staticmethod
    async def provision_router(session, host: str, creds, data) -> dict[str, Any]:
        """
        DEPRECATED: Use MikrotikProvisioningService.provision_device() instead.

        This wrapper delegates to the new unified service and handles
        DB updates for backwards compatibility.
        """
        warnings.warn(
            "ProvisioningService.provision_router is deprecated. "
            "Use MikrotikProvisioningService.provision_device() instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        password = decrypt_data(creds.password)
        method = getattr(data, "method", "api")

        try:
            # Delegate to new unified service
            result = await MikrotikProvisioningService.provision_device(
                host=host,
                current_username=creds.username,
                current_password=password,
                new_user=data.new_api_user,
                new_password=data.new_api_password,
                ssl_port=creds.api_ssl_port,
                method=method,
                device_type="router",
                current_api_port=creds.api_port,
            )

            if result.get("status") == "error":
                raise HTTPException(status_code=500, detail=result["message"])

            # Update DB: new user, password, SSL port, and mark as provisioned
            update_data = {
                "username": data.new_api_user,
                "password": data.new_api_password,
                "api_port": creds.api_ssl_port,
                "is_provisioned": True,
            }
            await update_router_service(session, host, update_data)

            # Subscribe to monitor and refresh immediately
            import asyncio

            from .monitor_scheduler import monitor_scheduler

            new_creds = {
                "username": data.new_api_user,
                "password": data.new_api_password,
                "port": creds.api_ssl_port,
            }

            try:
                await asyncio.sleep(2)
                await monitor_scheduler.subscribe(host, new_creds)
                await monitor_scheduler.refresh_host(host)
            except Exception as e:
                logger.warning(f"Could not refresh status immediately for {host}: {e}")

            return result

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Provisioning failed for {host}: {e}")
            import traceback

            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))

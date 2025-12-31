import logging
import asyncio
from typing import Dict, Any, Optional

from fastapi import HTTPException
from routeros_api import RouterOsApiPool

from ..models.router import Router
from ..services.router_service import RouterService, update_router as update_router_service
from ..services.pki_service import PKIService
from ..utils.security import decrypt_data
from ..utils.device_clients.mikrotik import ssl as ssl_module
from ..utils.device_clients.mikrotik.base import get_id
from ..utils.device_clients.adapters.mikrotik_router import MikrotikRouterAdapter

logger = logging.getLogger(__name__)

class ProvisioningService:
    
    @staticmethod
    async def auto_provision_ssl(session, router: Router) -> bool:
        """
        Attempts to auto-provision SSL for a newly created router (Zero Trust).
        This runs as a background/side-effect task during creation.
        """
        try:
            # Decrypt password for connection
            password = decrypt_data(router.password)
            
            # Init service (connects automatically)
            # We use a synchronous context or manual checking here as per original logic
            # but wrapping in try/finally to ensure disconnect
            service = RouterService(router.host, router, decrypted_password=password)
            try:
                # Trigger auto-provisioning
                is_secure = service.ensure_ssl_provisioned()
                if is_secure:
                    # Update DB to reflect SSL port if it was different
                    if router.api_port != router.api_ssl_port:
                        await update_router_service(session, router.host, {"api_port": router.api_ssl_port})
                        return True
            finally:
                service.disconnect()
        except Exception as e:
            # Log error but don't fail router creation (Zero Trust allows eventual consistency)
            logger.error(f"Failed to auto-provision SSL for {router.host}: {e}")
            return False
        return False

    @staticmethod
    def _run_provisioning_sync(creds, password, new_user, new_password, new_group="api_full_access"):
        """
        Synchronous logic for provisioning:
        1. Connect via insecure API (initial setup).
        2. Create dedicated API user.
        3. Setup SSL via PKI Service.
        """
        pool = RouterOsApiPool(
            creds.host,
            username=creds.username,
            password=password,
            port=creds.api_port,
            use_ssl=False,
            plaintext_login=True,
        )
        api = pool.get_api()
        
        try:
            # 1. Create dedicated API user with correct group
            group_resource = api.get_resource("/user/group")
            group_list = group_resource.get(name=new_group)
            current_policy = "local,ssh,read,write,policy,test,password,sniff,sensitive,api,romon,ftp,!telnet,!reboot,!winbox,!web,!rest-api"
            
            if not group_list:
                group_resource.add(name=new_group, policy=current_policy)
            else:
                group_resource.set(id=get_id(group_list[0]), policy=current_policy)
            
            user_resource = api.get_resource("/user")
            existing_user = user_resource.get(name=new_user)
            if existing_user:
                user_resource.set(id=get_id(existing_user[0]), password=new_password, group=new_group)
            else:
                user_resource.add(name=new_user, password=new_password, group=new_group)
            
            # 2. Setup SSL via PKI Service (secure SSH method preferred, fallback to API)
            pki = PKIService()
            if not pki.verify_mkcert_available():
                return {"status": "error", "message": "mkcert no está disponible. Instálalo para habilitar SSL."}
            
            # Install CA on router
            ca_pem = pki.get_ca_pem()
            if ca_pem:
                # Note: We are using the synchronous API we just opened to install the CA
                ssl_module.install_ca_certificate(api, creds.host, creds.username, password, ca_pem, "umanager_ca")
                
                # Generate and install router certificate
                success, key_pem, cert_pem = pki.generate_full_cert_pair(creds.host)
                if success:
                    # Import certificate using the API helper
                    ssl_module.import_certificate(api, creds.host, creds.api_ssl_port, new_user, new_password, cert_pem, key_pem, "umanager_ssl")
                else:
                    return {"status": "error", "message": f"Error generando certificado: {cert_pem}"}
            
            return {"status": "success", "message": "Router aprovisionado con API-SSL seguro."}
        finally:
            pool.disconnect()

    @staticmethod
    async def provision_router(session, host: str, creds, data) -> Dict[str, Any]:
        """
        Unified Provisioning:
        Creates a dedicated API user and installs a trusted SSL certificate.
        """
        password = decrypt_data(creds.password)

        try:
            # Run the synchronous provisioning logic in a thread
            result = await asyncio.to_thread(
                ProvisioningService._run_provisioning_sync,
                creds,
                password,
                data.new_api_user,
                data.new_api_password
            )

            if result["status"] == "error":
                raise HTTPException(status_code=500, detail=result["message"])

            # Update DB: new user, password, SSL port, and mark as provisioned
            update_data = {
                "username": data.new_api_user,
                "password": data.new_api_password,
                "api_port": creds.api_ssl_port,
                "is_provisioned": True,
            }
            await update_router_service(session, host, update_data)
            return result

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Provisioning failed for {host}: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))

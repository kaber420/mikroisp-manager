import logging
import asyncio
import time
from typing import Dict, Any, Optional

from fastapi import HTTPException
from routeros_api import RouterOsApiPool

from ..models.router import Router
from ..services.router_service import RouterService, update_router as update_router_service
from ..services.pki_service import PKIService
from ..utils.security import decrypt_data
from ..utils.device_clients.mikrotik import ssl as ssl_module
from ..utils.device_clients.mikrotik.base import get_id
from ..utils.device_clients.mikrotik.ssh_client import MikrotikSSHClient
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
    def _run_provisioning_ssh_pure(
        host: str,
        ssh_username: str,
        ssh_password: str,
        new_user: str,
        new_password: str,
        ssl_port: int = 8729,
        new_group: str = "api_full_access"
    ) -> Dict[str, Any]:
        """
        Pure SSH Provisioning:
        Performs all provisioning steps via SSH without enabling the insecure API port.
        
        Steps:
        1. Connect via SSH.
        2. Create dedicated API user with proper permissions.
        3. Upload and import CA certificate.
        4. Generate, upload and import router certificate.
        5. Configure and enable api-ssl service.
        """
        ssh_client = MikrotikSSHClient(
            host=host,
            username=ssh_username,
            password=ssh_password
        )
        
        try:
            # 1. Connect via SSH
            if not ssh_client.connect():
                return {"status": "error", "message": f"No se pudo conectar via SSH a {host}"}
            
            logger.info(f"[SSH Provisioning] Conectado a {host}")
            
            # 2. Create API user group and user
            policy = "local,ssh,read,write,policy,test,password,sniff,sensitive,api,romon,ftp,!telnet,!reboot,!winbox,!web,!rest-api"
            
            # Create group (ignore error if exists)
            group_cmd = f':do {{ /user group add name={new_group} policy="{policy}" }} on-error={{}}'
            ssh_client.exec_command(group_cmd)
            time.sleep(0.5)
            
            # Create or update user
            # First try to find if user exists
            check_user_cmd = f'/user print where name="{new_user}"'
            _, stdout, _ = ssh_client.exec_command(check_user_cmd)
            user_output = stdout.read().decode()
            
            if new_user in user_output:
                # User exists, update password and group
                user_cmd = f'/user set [find name="{new_user}"] password="{new_password}" group={new_group}'
            else:
                # Create new user
                user_cmd = f'/user add name="{new_user}" password="{new_password}" group={new_group}'
            
            ssh_client.exec_command(user_cmd)
            time.sleep(0.5)
            logger.info(f"[SSH Provisioning] Usuario '{new_user}' configurado")
            
            # 3. Setup SSL certificates via PKI Service
            pki = PKIService()
            if not pki.verify_mkcert_available():
                return {"status": "error", "message": "mkcert no está disponible. Instálalo para habilitar SSL."}
            
            # 3a. Upload and import CA certificate
            ca_pem = pki.get_ca_pem()
            if not ca_pem:
                return {"status": "error", "message": "Certificado CA no encontrado"}
            
            sftp = ssh_client.open_sftp()
            
            ca_filename = "umanager_ca.pem"
            with sftp.file(ca_filename, "w") as f:
                f.write(ca_pem.encode("utf-8"))
            
            time.sleep(0.5)
            
            # Import CA
            import_ca_cmd = f'/certificate import file-name={ca_filename} passphrase=""'
            ssh_client.exec_command(import_ca_cmd)
            time.sleep(1)
            logger.info(f"[SSH Provisioning] CA importado")
            
            # 3b. Generate and upload router certificate
            success, key_pem, cert_pem = pki.generate_full_cert_pair(host)
            if not success:
                return {"status": "error", "message": f"Error generando certificado: {cert_pem}"}
            
            timestamp = int(time.time())
            cert_filename = f"umanager_ssl_{timestamp}.crt"
            key_filename = f"umanager_ssl_{timestamp}.key"
            
            with sftp.file(cert_filename, "w") as f:
                f.write(cert_pem.encode("utf-8"))
            
            with sftp.file(key_filename, "w") as f:
                f.write(key_pem.encode("utf-8"))
            
            time.sleep(0.5)
            
            # Import cert and key
            import_cert_cmd = f'/certificate import file-name={cert_filename} passphrase=""'
            ssh_client.exec_command(import_cert_cmd)
            time.sleep(1)
            
            import_key_cmd = f'/certificate import file-name={key_filename} passphrase=""'
            ssh_client.exec_command(import_key_cmd)
            time.sleep(1)
            logger.info(f"[SSH Provisioning] Certificado del router importado")
            
            # 4. Find the cert name by common-name (host IP)
            # RouterOS names certs based on imported file, we need to find it
            find_cert_cmd = f'/certificate print where common-name="{host}"'
            _, stdout, _ = ssh_client.exec_command(find_cert_cmd)
            cert_output = stdout.read().decode()
            
            # Parse the certificate name from output
            # Output format typically includes "name=..." or first column is name
            cert_name = None
            for line in cert_output.split('\n'):
                if 'name=' in line.lower():
                    # Try to extract name=value
                    for part in line.split():
                        if part.lower().startswith('name='):
                            cert_name = part.split('=')[1].strip('"')
                            break
                elif host in line and 'K' in line:
                    # Fallback: look for line with host and K (has private key)
                    parts = line.split()
                    if len(parts) >= 2:
                        # First non-flag column is usually the name
                        for p in parts:
                            if not p.startswith(('K', 'L', 'A', 'T', 'R', 'C', 'E')) and not p.isdigit():
                                cert_name = p
                                break
            
            if not cert_name:
                # Fallback: use the base name of imported file
                cert_name = cert_filename.replace('.crt', '').replace('.pem', '')
                logger.warning(f"[SSH Provisioning] No se encontró nombre de cert, usando fallback: {cert_name}")
            
            logger.info(f"[SSH Provisioning] Usando certificado: {cert_name}")
            
            # 5. Configure and enable api-ssl service
            # First disable, set cert, then enable (atomic restart)
            service_cmd = (
                f'/ip service set [find name=api-ssl dynamic=no] '
                f'certificate="{cert_name}" disabled=no port={ssl_port}'
            )
            ssh_client.exec_command(service_cmd)
            time.sleep(1)
            
            logger.info(f"[SSH Provisioning] api-ssl habilitado en puerto {ssl_port}")
            
            # Cleanup temp files (best effort)
            try:
                cleanup_cmd = f'/file remove [find name~"umanager"]'
                ssh_client.exec_command(cleanup_cmd)
            except Exception:
                pass
            
            return {"status": "success", "message": "Router aprovisionado via SSH con API-SSL seguro."}
            
        except Exception as e:
            logger.error(f"[SSH Provisioning] Error: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": str(e)}
        finally:
            try:
                ssh_client.disconnect()
            except Exception:
                pass

    @staticmethod
    async def provision_router(session, host: str, creds, data) -> Dict[str, Any]:
        """
        Unified Provisioning:
        Creates a dedicated API user and installs a trusted SSL certificate.
        
        Supports two methods:
        - 'api': Uses the RouterOS API (requires API port accessible)
        - 'ssh': Uses pure SSH (works even if API is disabled)
        """
        password = decrypt_data(creds.password)
        
        # Get method from request (default to 'api' for backwards compatibility)
        method = getattr(data, 'method', 'api')

        try:
            if method == "ssh":
                # Pure SSH Provisioning
                logger.info(f"[Provisioning] Using SSH method for {host}")
                result = await asyncio.to_thread(
                    ProvisioningService._run_provisioning_ssh_pure,
                    host,
                    creds.username,
                    password,
                    data.new_api_user,
                    data.new_api_password,
                    creds.api_ssl_port
                )
            else:
                # Legacy API Provisioning
                logger.info(f"[Provisioning] Using API method for {host}")
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
            
            # Subscribe to monitor and refresh immediately to show "Online" in list
            # Note: API-SSL may need a moment to restart after provisioning
            from .monitor_scheduler import monitor_scheduler
            new_creds = {
                "username": data.new_api_user,
                "password": data.new_api_password,
                "port": creds.api_ssl_port
            }
            
            try:
                # Wait for API-SSL to restart
                await asyncio.sleep(2)
                await monitor_scheduler.subscribe(host, new_creds)
                await monitor_scheduler.refresh_host(host)
            except Exception as e:
                # Don't fail provisioning - scheduler will pick it up on next poll
                logger.warning(f"Could not refresh status immediately for {host}: {e}")
            
            return result

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Provisioning failed for {host}: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))

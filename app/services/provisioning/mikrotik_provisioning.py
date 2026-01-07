"""
Unified MikroTik Provisioning Service.

Provides provisioning for Routers, APs, and Switches running RouterOS.
All MikroTik devices share the same user/certificate management system.
"""
import asyncio
import logging
import time
from typing import Dict, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DeviceCredentials:
    """Generic device credentials for provisioning."""
    
    host: str
    username: str
    password: str  # Already decrypted
    ssl_port: int = 8729
    ssh_port: int = 22


class MikrotikProvisioningService:
    """
    Unified MikroTik Provisioning Service.
    
    Works for Routers, APs, and Switches running RouterOS.
    Supports two provisioning methods:
    - SSH (recommended): More secure, works even if API is disabled
    - API: Uses RouterOS API, requires API port accessible
    """
    
    # Configuration constants
    DEFAULT_SSL_PORT = 8729
    DEFAULT_SSH_PORT = 22
    API_RESTART_WAIT_SECONDS = 3
    MAX_RETRY_ATTEMPTS = 3
    
    @staticmethod
    async def provision_device(
        host: str,
        current_username: str,
        current_password: str,
        new_user: str,
        new_password: str,
        ssl_port: int = 8729,
        method: str = "ssh",
        device_type: str = "router",
        current_api_port: int = 8728
    ) -> Dict[str, Any]:
        """
        Unified provisioning for any MikroTik device.
        
        Args:
            host: Device IP/hostname
            current_username: Existing SSH/API username
            current_password: Existing password (decrypted)
            new_user: New API user to create
            new_password: Password for new user
            ssl_port: Target API-SSL port (default 8729)
            method: "ssh" (recommended) or "api"
            device_type: For logging context ("router", "ap", "switch")
            current_api_port: Current API port for API method (default 8728)
            
        Returns:
            Dict with status, message, method_used, and optional warnings
        """
        logger.info(
            f"[Provisioning] Starting {method.upper()} provisioning "
            f"for {device_type} {host}"
        )
        
        try:
            if method == "ssh":
                result = await asyncio.to_thread(
                    MikrotikProvisioningService._run_ssh_provisioning,
                    host, current_username, current_password,
                    new_user, new_password, ssl_port
                )
            else:
                result = await asyncio.to_thread(
                    MikrotikProvisioningService._run_api_provisioning,
                    host, current_username, current_password,
                    new_user, new_password, ssl_port, current_api_port
                )
            
            result["method_used"] = method
            
            # Log the result
            if result["status"] == "success":
                logger.info(
                    f"[Provisioning] Successfully provisioned {device_type} {host} "
                    f"via {method.upper()}"
                )
            else:
                logger.error(
                    f"[Provisioning] Failed to provision {device_type} {host}: "
                    f"{result.get('message', 'Unknown error')}"
                )
            
            return result
            
        except Exception as e:
            logger.error(f"[Provisioning] Unexpected error for {host}: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "message": str(e),
                "method_used": method
            }
    
    @staticmethod
    def _run_ssh_provisioning(
        host: str,
        ssh_username: str,
        ssh_password: str,
        new_user: str,
        new_password: str,
        ssl_port: int = 8729,
        new_group: str = "api_full_access"
    ) -> Dict[str, Any]:
        """
        Pure SSH Provisioning.
        
        Performs all provisioning steps via SSH without enabling the insecure API port.
        
        Steps:
        1. Connect via SSH.
        2. Create dedicated API user with proper permissions.
        3. Upload and import CA certificate.
        4. Generate, upload and import router certificate.
        5. Configure and enable api-ssl service.
        """
        # Import here to avoid circular imports
        from ..pki_service import PKIService
        from ...utils.device_clients.mikrotik.ssh_client import MikrotikSSHClient
        
        ssh_client = MikrotikSSHClient(
            host=host,
            username=ssh_username,
            password=ssh_password
        )
        
        try:
            # 1. Connect via SSH
            if not ssh_client.connect():
                return {
                    "status": "error",
                    "message": f"No se pudo conectar via SSH a {host}"
                }
            
            logger.info(f"[SSH Provisioning] Conectado a {host}")
            
            # 2. Create API user group and user
            policy = (
                "local,ssh,read,write,policy,test,password,sniff,sensitive,"
                "api,romon,ftp,!telnet,!reboot,!winbox,!web,!rest-api"
            )
            
            # Create group (ignore error if exists)
            group_cmd = (
                f':do {{ /user group add name={new_group} policy="{policy}" }} '
                f'on-error={{}}'
            )
            ssh_client.exec_command(group_cmd)
            time.sleep(0.5)
            
            # Create or update user
            # First try to find if user exists
            check_user_cmd = f'/user print where name="{new_user}"'
            _, stdout, _ = ssh_client.exec_command(check_user_cmd)
            user_output = stdout.read().decode()
            
            if new_user in user_output:
                # User exists, update password and group
                user_cmd = (
                    f'/user set [find name="{new_user}"] '
                    f'password="{new_password}" group={new_group}'
                )
            else:
                # Create new user
                user_cmd = (
                    f'/user add name="{new_user}" '
                    f'password="{new_password}" group={new_group}'
                )
            
            ssh_client.exec_command(user_cmd)
            time.sleep(0.5)
            logger.info(f"[SSH Provisioning] Usuario '{new_user}' configurado")
            
            # 3. Setup SSL certificates via PKI Service
            pki = PKIService()
            if not pki.verify_mkcert_available():
                return {
                    "status": "error",
                    "message": "mkcert no está disponible. Instálalo para habilitar SSL."
                }
            
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
                return {
                    "status": "error",
                    "message": f"Error generando certificado: {cert_pem}"
                }
            
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
            find_cert_cmd = f'/certificate print where common-name="{host}"'
            _, stdout, _ = ssh_client.exec_command(find_cert_cmd)
            cert_output = stdout.read().decode()
            
            # Parse the certificate name from output
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
                        for p in parts:
                            if (not p.startswith(('K', 'L', 'A', 'T', 'R', 'C', 'E')) 
                                    and not p.isdigit()):
                                cert_name = p
                                break
            
            if not cert_name:
                # Fallback: use the base name of imported file
                cert_name = cert_filename.replace('.crt', '').replace('.pem', '')
                logger.warning(
                    f"[SSH Provisioning] No se encontró nombre de cert, "
                    f"usando fallback: {cert_name}"
                )
            
            logger.info(f"[SSH Provisioning] Usando certificado: {cert_name}")
            
            # 5. Configure and enable api-ssl service
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
            
            return {
                "status": "success",
                "message": "Dispositivo aprovisionado via SSH con API-SSL seguro."
            }
            
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
    def _run_api_provisioning(
        host: str,
        username: str,
        password: str,
        new_user: str,
        new_password: str,
        ssl_port: int = 8729,
        api_port: int = 8728,
        new_group: str = "api_full_access"
    ) -> Dict[str, Any]:
        """
        API-based Provisioning.
        
        Uses the RouterOS API (requires API port accessible).
        
        Steps:
        1. Connect via insecure API (initial setup).
        2. Create dedicated API user.
        3. Setup SSL via PKI Service.
        """
        # Import here to avoid circular imports
        from ..pki_service import PKIService
        from ...utils.device_clients.mikrotik.base import get_id
        from ...utils.device_clients.mikrotik import ssl as ssl_module
        from routeros_api import RouterOsApiPool
        
        pool = RouterOsApiPool(
            host,
            username=username,
            password=password,
            port=api_port,
            use_ssl=False,
            plaintext_login=True,
        )
        
        try:
            api = pool.get_api()
            
            # 1. Create dedicated API user with correct group
            group_resource = api.get_resource("/user/group")
            group_list = group_resource.get(name=new_group)
            current_policy = (
                "local,ssh,read,write,policy,test,password,sniff,sensitive,"
                "api,romon,ftp,!telnet,!reboot,!winbox,!web,!rest-api"
            )
            
            if not group_list:
                group_resource.add(name=new_group, policy=current_policy)
            else:
                group_resource.set(id=get_id(group_list[0]), policy=current_policy)
            
            user_resource = api.get_resource("/user")
            existing_user = user_resource.get(name=new_user)
            if existing_user:
                user_resource.set(
                    id=get_id(existing_user[0]),
                    password=new_password,
                    group=new_group
                )
            else:
                user_resource.add(
                    name=new_user,
                    password=new_password,
                    group=new_group
                )
            
            logger.info(f"[API Provisioning] Usuario '{new_user}' configurado")
            
            # 2. Setup SSL via PKI Service
            pki = PKIService()
            if not pki.verify_mkcert_available():
                return {
                    "status": "error",
                    "message": "mkcert no está disponible. Instálalo para habilitar SSL."
                }
            
            # Install CA on router
            ca_pem = pki.get_ca_pem()
            if ca_pem:
                ssl_module.install_ca_certificate(
                    api, host, username, password, ca_pem, "umanager_ca"
                )
                
                # Generate and install router certificate
                success, key_pem, cert_pem = pki.generate_full_cert_pair(host)
                if success:
                    ssl_module.import_certificate(
                        api, host, ssl_port, new_user, new_password,
                        cert_pem, key_pem, "umanager_ssl"
                    )
                    logger.info(f"[API Provisioning] Certificados instalados")
                else:
                    return {
                        "status": "error",
                        "message": f"Error generando certificado: {cert_pem}"
                    }
            
            return {
                "status": "success",
                "message": "Dispositivo aprovisionado con API-SSL seguro."
            }
            
        except Exception as e:
            logger.error(f"[API Provisioning] Error: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": str(e)}
        finally:
            pool.disconnect()
    
    @staticmethod
    async def verify_provisioning(
        host: str,
        username: str,
        password: str,
        ssl_port: int = 8729,
        max_attempts: int = 3,
        wait_seconds: int = 2
    ) -> Tuple[bool, str]:
        """
        Verify that provisioning was successful by attempting API-SSL connection.
        
        Uses exponential backoff to wait for the API-SSL service to restart.
        
        Args:
            host: Device IP/hostname
            username: New API username
            password: New API password (decrypted)
            ssl_port: API-SSL port
            max_attempts: Maximum verification attempts
            wait_seconds: Base wait time between attempts
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        from ...utils.device_clients.mikrotik.base import MikrotikApiClient
        
        for attempt in range(max_attempts):
            try:
                # Exponential backoff
                await asyncio.sleep(wait_seconds * (attempt + 1))
                
                client = MikrotikApiClient(
                    host=host,
                    username=username,
                    password=password,
                    port=ssl_port,
                    use_ssl=True
                )
                
                if client.connect():
                    client.disconnect()
                    return True, "API-SSL connection verified successfully"
                    
            except Exception as e:
                logger.warning(
                    f"[Provisioning] Verification attempt {attempt + 1} failed: {e}"
                )
                continue
        
        return False, f"Could not verify API-SSL after {max_attempts} attempts"

"""
Unified MikroTik Provisioning Service.

Provides provisioning for Routers, APs, and Switches running RouterOS.
All MikroTik devices share the same user/certificate management system.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

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
        current_api_port: int = 8728,
    ) -> dict[str, Any]:
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
            f"[Provisioning] Starting {method.upper()} provisioning for {device_type} {host}"
        )

        try:
            if method == "ssh":
                result = await asyncio.to_thread(
                    MikrotikProvisioningService._run_ssh_provisioning,
                    host,
                    current_username,
                    current_password,
                    new_user,
                    new_password,
                    ssl_port,
                )
            else:
                result = await asyncio.to_thread(
                    MikrotikProvisioningService._run_api_provisioning,
                    host,
                    current_username,
                    current_password,
                    new_user,
                    new_password,
                    ssl_port,
                    current_api_port,
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
            return {"status": "error", "message": str(e), "method_used": method}

    @staticmethod
    def _run_ssh_provisioning(
        host: str,
        ssh_username: str,
        ssh_password: str,
        new_user: str,
        new_password: str,
        ssl_port: int = 8729,
        new_group: str = "api_full_access",
    ) -> dict[str, Any]:
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
        from ...utils.device_clients.mikrotik.ssh_client import MikrotikSSHClient
        from ..pki_service import PKIService

        ssh_client = MikrotikSSHClient(host=host, username=ssh_username, password=ssh_password)

        try:
            # 1. Connect via SSH
            if not ssh_client.connect():
                return {"status": "error", "message": f"No se pudo conectar via SSH a {host}"}

            logger.info(f"[SSH Provisioning] Conectado a {host}")

            # Detect RouterOS Version
            _, stdout, _ = ssh_client.exec_command("/system resource print")
            resource_output = stdout.read().decode()
            logger.debug(f"[SSH Provisioning] Resource output: {resource_output[:500]}")
            router_os_version = "6"  # Default fallback

            # Try multiple patterns to find version
            for line in resource_output.split("\n"):
                line_lower = line.lower().strip()
                # Pattern 1: "version: 7.12.1"
                if "version" in line_lower and ":" in line:
                    ver_str = line.split(":")[-1].strip().split()[0]
                    logger.info(f"[SSH Provisioning] Found version string: '{ver_str}'")
                    if ver_str.startswith("7"):
                        router_os_version = "7"
                    break
                # Pattern 2: "version=7.12.1" (value-list format)
                elif "version=" in line_lower:
                    ver_str = line.split("=")[-1].strip().split()[0]
                    logger.info(f"[SSH Provisioning] Found version string: '{ver_str}'")
                    if ver_str.startswith("7"):
                        router_os_version = "7"
                    break

            # 2. Create API user group and user
            # Adjust policy based on version
            base_policy = "local,ssh,read,write,policy,test,password,sniff,sensitive,api,romon,ftp,!telnet,!reboot,!winbox,!web"
            if router_os_version == "7":
                policy = f"{base_policy},!rest-api"
            else:
                # v6 does not have rest-api policy
                policy = base_policy

            logger.info(f"[SSH Provisioning] Gestionando grupo '{new_group}'...")

            # Simple, robust group creation
            # Try to add, catch error if exists
            group_add_cmd = f'/user group add name={new_group} policy="{policy}"'
            _, stdout, stderr = ssh_client.exec_command(group_add_cmd)
            g_out = stdout.read().decode()
            g_err = stderr.read().decode()

            if g_err and "already exists" not in g_err.lower():
                logger.error(f"[SSH Provisioning] Error creando grupo: {g_err}")
                # Don't return error yet, try to proceed in case it's a transient issue
            elif "already exists" in g_err.lower():
                logger.info(
                    f"[SSH Provisioning] Grupo '{new_group}' ya existe. Asegurando permisos..."
                )
                # Update permissions just in case
                group_set_cmd = f'/user group set [find name={new_group}] policy="{policy}"'
                ssh_client.exec_command(group_set_cmd)

            time.sleep(0.5)

            # Create or update user
            logger.info(f"[SSH Provisioning] Gestionando usuario '{new_user}'...")

            # Check existence first
            check_cmd = f'/user print count-only where name="{new_user}"'
            _, stdout, _ = ssh_client.exec_command(check_cmd)
            count_str = stdout.read().decode().strip()

            if count_str and count_str.isdigit() and int(count_str) > 0:
                logger.info("[SSH Provisioning] Usuario existe. Actualizando contraseña y grupo...")
                user_cmd = (
                    f'/user set [find name="{new_user}"] '
                    f'password="{new_password}" group={new_group}'
                )
            else:
                logger.info("[SSH Provisioning] Creando nuevo usuario...")
                user_cmd = (
                    f'/user add name="{new_user}" password="{new_password}" group={new_group}'
                )

            _, stdout, stderr = ssh_client.exec_command(user_cmd)
            u_out = stdout.read().decode()
            u_err = stderr.read().decode()

            if u_err and "already exists" not in u_err.lower():
                logger.warning(f"[SSH Provisioning] Error gestionando usuario: {u_err}")

            time.sleep(1)

            # FINAL VERIFICATION of user checking
            verify_user_cmd = f'/user print count-only where name="{new_user}"'
            _, stdout, _ = ssh_client.exec_command(verify_user_cmd)
            final_count = stdout.read().decode().strip()

            if not final_count or not final_count.isdigit() or int(final_count) == 0:
                logger.error(
                    f"[SSH Provisioning] FALLO CRÍTICO: El usuario '{new_user}' no se encuentra después de intentar crearlo."
                )
                return {
                    "status": "error",
                    "message": f"No se pudo crear el usuario API '{new_user}'. Error: {u_err}",
                }

            logger.info(f"[SSH Provisioning] Usuario '{new_user}' verificado correctamente.")

            # 3. Setup SSL certificates via PKI Service
            pki = PKIService()
            if not pki.verify_mkcert_available():
                return {
                    "status": "error",
                    "message": "mkcert no está disponible. Instálalo para habilitar SSL.",
                }

            # 3a. Upload and import CA certificate
            ca_pem = pki.get_ca_pem()
            if not ca_pem:
                return {"status": "error", "message": "Certificado CA no encontrado"}

            sftp = ssh_client.open_sftp()

            ca_filename = "umanager_ca.pem"

            # CRITICAL: Ensure we upload to root directory where /certificate import looks
            try:
                sftp.chdir("/")
            except Exception:
                pass  # Some SFTP servers don't support chdir but default to /

            # Log current directory
            try:
                cwd = sftp.getcwd()
                logger.info(f"[SSH Provisioning] SFTP working directory: {cwd}")
            except Exception:
                pass

            with sftp.file(ca_filename, "w") as f:
                f.write(ca_pem.encode("utf-8"))

            time.sleep(0.5)

            # Verify file exists on router
            _, stdout, _ = ssh_client.exec_command(f'/file print where name="{ca_filename}"')
            file_check = stdout.read().decode()
            logger.info(f"[SSH Provisioning] Archivo CA en router: {file_check}")

            # Import CA
            import_ca_cmd = f'/certificate import file-name={ca_filename} passphrase=""'
            ssh_client.exec_command(import_ca_cmd)
            time.sleep(1)
            logger.info("[SSH Provisioning] CA importado")

            # 3b. Generate certificate on SERVER and upload (Restored)
            success, key_pem, cert_pem = pki.generate_full_cert_pair(host)
            if not success:
                sftp.close()
                return {"status": "error", "message": f"Error generando certificado: {cert_pem}"}

            timestamp = int(time.time())
            cert_filename = f"umanager_ssl_{timestamp}.crt"
            key_filename = f"umanager_ssl_{timestamp}.key"

            with sftp.file(cert_filename, "w") as f:
                f.write(cert_pem.encode("utf-8"))

            with sftp.file(key_filename, "w") as f:
                f.write(key_pem.encode("utf-8"))

            time.sleep(2)  # Allow checking filesystem sync
            sftp.close()

            # Verify files were uploaded (Diagnostic only)
            # using terse for reliable parsing
            verify_files_cmd = '/file print terse where name~"umanager"'
            _, stdout, _ = ssh_client.exec_command(verify_files_cmd)
            files_output = stdout.read().decode()
            logger.info(f"[SSH Provisioning] Verificación de archivos (RAW): {files_output}")

            if cert_filename not in files_output:
                logger.warning(
                    f"[SSH Provisioning] ADVERTENCIA: {cert_filename} no aparece en '/file print' todavía. Intentando importar de todas formas..."
                )
            else:
                logger.info("[SSH Provisioning] Archivos verificados en disco.")

            logger.info("[SSH Provisioning] Iniciando importación...")

            # Import cert and key with robust error checking
            # Try standard 'file-name' first, fallback to 'file' if needed
            for file_type, fname in [("CERT", cert_filename), ("KEY", key_filename)]:
                logger.info(f"[SSH Provisioning] Importando {file_type}: {fname}")

                # Command 1: Standard
                cmd = f'/certificate import file-name={fname} passphrase=""'
                _, stdout, stderr = ssh_client.exec_command(cmd)
                out = stdout.read().decode()
                err = stderr.read().decode()

                # Check for common successes
                if (
                    "imported" in out.lower() or "passphrase" in out.lower()
                ):  # sometimes it asks for passphrase even if provided
                    logger.info(f"[SSH Provisioning] {file_type} importado (Std Output): {out}")
                elif err and "no such item" in err.lower():  # v6 sometimes prefers 'file'
                    logger.warning(
                        f"[SSH Provisioning] Standard import failed, trying legacy syntax for {fname}"
                    )
                    legacy_cmd = f'/certificate import file={fname} passphrase=""'
                    ssh_client.exec_command(legacy_cmd)
                else:
                    logger.info(f"[SSH Provisioning] {file_type} Output: {out} | Err: {err}")

                time.sleep(2)  # Increased wait for slow devices

            logger.info("[SSH Provisioning] Proceso de importación finalizado")

            # 4. Find the cert name by common-name (host IP)
            # Use 'terse' for easier parsing across versions
            find_cert_cmd = f'/certificate print terse where common-name="{host}"'
            _, stdout, _ = ssh_client.exec_command(find_cert_cmd)
            cert_output = stdout.read().decode()
            logger.info(f"[SSH Provisioning] Certificados encontrados (RAW): {cert_output}")

            # Smart parsing for v6/v7 compatibility
            cert_name = None
            has_private_key = False

            for line in cert_output.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                # Parse flags (always at the start in terse mode, e.g., "0 K T name=...")
                # v7: 0 K T name=...
                # v6: 0 K name=...

                # Check for Private Key flag 'K'
                # In terse output, flags are usually space-separated before properties
                # But to be safe, we check if 'K' appears in the flags section (before first key=value)

                parts = line.split()
                flags_part = ""
                properties_start_idx = 0

                # Find where properties start (k=v)
                for i, part in enumerate(parts):
                    if "=" in part:
                        properties_start_idx = i
                        break
                    if not part.isdigit():  # skip index number
                        flags_part += part

                current_k = "K" in flags_part

                # Extract name
                current_name = None
                for part in parts[properties_start_idx:]:
                    if part.startswith("name="):
                        current_name = part.split("=", 1)[1].strip('"')
                        break

                if current_name:
                    cert_name = current_name
                    if current_k:
                        has_private_key = True
                        break  # Found a perfect match

            if not cert_name:
                # Fallback: use the base name of imported file
                cert_name = cert_filename.replace(".crt", "").replace(".pem", "")
                logger.warning(
                    f"[SSH Provisioning] No se encontró certificado en print output, "
                    f"usando fallback: {cert_name}"
                )

            logger.info(
                f"[SSH Provisioning] Usando certificado: {cert_name} (Tiene llave privada: {has_private_key})"
            )

            if not has_private_key and cert_name:
                logger.warning(
                    f"[SSH Provisioning] ALERTA: El certificado {cert_name} no parece tener llave privada (K). Intentando re-importar llave..."
                )
                # Last ditch effort: Try to import key again specifically
                import_key_retry = f'/certificate import file-name={key_filename} passphrase=""'
                ssh_client.exec_command(import_key_retry)
                time.sleep(2)

            # 5. Configure and enable api-ssl service
            # Split commands for better stability on v6
            logger.info(
                f"[SSH Provisioning] Configurando servicio api-ssl con certificado '{cert_name}'..."
            )

            # Step 1: Set certificate (keep disabled for a moment)
            # using 'numbers' selector combined with 'find' is the most robust method across versions
            set_cert_cmd = f'/ip service set [find name=api-ssl] certificate="{cert_name}"'
            ssh_client.exec_command(set_cert_cmd)
            time.sleep(1)

            # Verify if certificate took
            check_cert_cmd = "/ip service print detail where name=api-ssl"
            _, stdout, _ = ssh_client.exec_command(check_cert_cmd)
            check_output = stdout.read().decode()

            if cert_name not in check_output and f'certificate="{cert_name}"' not in check_output:
                logger.warning(
                    "[SSH Provisioning] La asignación directa falló. Intentando método alternativo (legacy numeric)..."
                )
                # Fallback: legacy method trying to enable port + cert in one go, but using numeric ID 0-10 scan
                # Just try to set on the item found by print
                scan_cmd = (
                    f'/ip service set [find name=api-ssl] certificate="{cert_name}" port={ssl_port}'
                )
                ssh_client.exec_command(scan_cmd)
                time.sleep(1)

            # Step 2: Enable service and set port
            enable_cmd = f"/ip service set [find name=api-ssl] disabled=no port={ssl_port}"
            ssh_client.exec_command(enable_cmd)
            time.sleep(2)  # Give RouterOS time to restart service

            logger.info("[SSH Provisioning] Comandos de servicio ejecutados")

            # Verify service configuration with detail output
            check_service_cmd = "/ip service print detail where name=api-ssl"
            _, stdout, _ = ssh_client.exec_command(check_service_cmd)
            service_output = stdout.read().decode()
            logger.info(f"[SSH Provisioning] Estado final api-ssl: {service_output}")

            # Check if certificate is actually assigned
            # Look for certificate= followed by our cert name (not "none" or empty)
            cert_assigned = False
            if cert_name in service_output:
                cert_assigned = True
            elif "certificate=" in service_output:
                # Extract certificate value and check it's not empty/none
                for line in service_output.split("\n"):
                    if "certificate=" in line:
                        cert_value = line.split("certificate=")[1].split()[0].strip().strip('"')
                        if cert_value and cert_value.lower() not in ["none", '""', "''", ""]:
                            cert_assigned = True
                            logger.info(
                                f"[SSH Provisioning] Certificado asignado detectado: {cert_value}"
                            )
                        break

            if not cert_assigned:
                logger.error(
                    f"[SSH Provisioning] api-ssl no tiene certificado asignado. Output: {service_output}"
                )
                return {
                    "status": "error",
                    "message": f"No se pudo asignar certificado '{cert_name}' a api-ssl. Verifica que el certificado tenga private key (flag K).",
                }

            logger.info(f"[SSH Provisioning] api-ssl habilitado en puerto {ssl_port}")

            # Cleanup temp files (best effort)
            try:
                cleanup_cmd = '/file remove [find name~"umanager"]'
                ssh_client.exec_command(cleanup_cmd)
            except Exception:
                pass

            return {
                "status": "success",
                "message": "Dispositivo aprovisionado via SSH con API-SSL seguro.",
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
        new_group: str = "api_full_access",
    ) -> dict[str, Any]:
        """
        API-based Provisioning.

        Uses the RouterOS API (requires API port accessible).

        Steps:
        1. Connect via insecure API (initial setup).
        2. Create dedicated API user.
        3. Setup SSL via PKI Service.
        """
        # Import here to avoid circular imports
        from routeros_api import RouterOsApiPool

        from ...utils.device_clients.mikrotik import ssl as ssl_module
        from ...utils.device_clients.mikrotik.base import get_id
        from ..pki_service import PKIService

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
                    id=get_id(existing_user[0]), password=new_password, group=new_group
                )
            else:
                user_resource.add(name=new_user, password=new_password, group=new_group)

            logger.info(f"[API Provisioning] Usuario '{new_user}' configurado")

            # 2. Setup SSL via PKI Service
            pki = PKIService()
            if not pki.verify_mkcert_available():
                return {
                    "status": "error",
                    "message": "mkcert no está disponible. Instálalo para habilitar SSL.",
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
                        api,
                        host,
                        ssl_port,
                        new_user,
                        new_password,
                        cert_pem,
                        key_pem,
                        "umanager_ssl",
                    )
                    logger.info("[API Provisioning] Certificados instalados")
                else:
                    return {
                        "status": "error",
                        "message": f"Error generando certificado: {cert_pem}",
                    }

            return {"status": "success", "message": "Dispositivo aprovisionado con API-SSL seguro."}

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
        wait_seconds: int = 2,
    ) -> tuple[bool, str]:
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
                    host=host, username=username, password=password, port=ssl_port, use_ssl=True
                )

                if client.connect():
                    client.disconnect()
                    return True, "API-SSL connection verified successfully"

            except Exception as e:
                logger.warning(f"[Provisioning] Verification attempt {attempt + 1} failed: {e}")
                continue

        return False, f"Could not verify API-SSL after {max_attempts} attempts"

# app/utils/device_clients/mikrotik/ssl.py
"""
SSL/TLS Certificate management functions for MikroTik routers.
Extracted from MikrotikRouterAdapter for better modularity.
"""

import logging
import time
from typing import Any

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from routeros_api.api import RouterOsApi

from . import connection as mikrotik_connection
from .ssh_client import MikrotikSSHClient

logger = logging.getLogger(__name__)


def generate_certificate_ssh(
    ssh_client: MikrotikSSHClient, host: str, cert_name: str = None, router_os_version: str = "6"
) -> dict[str, Any]:
    """
    Generate SSL certificate directly on the router via SSH commands.

    Compatible with RouterOS v6 and v7.

    Args:
        ssh_client: Connected MikrotikSSHClient instance
        host: Router IP (used as common-name)
        cert_name: Optional certificate name (generated if not provided)
        router_os_version: Major version string ("6" or "7")

    Returns:
        Dict with status, cert_name on success, or error message
    """
    import time as t

    if not cert_name:
        timestamp = int(t.time())
        cert_name = f"umanager_ssl_{timestamp}"

    try:
        logger.info(f"[SSL] Creating certificate '{cert_name}' (v{router_os_version}) on router...")

        # Determine commands based on version
        if router_os_version.startswith("7"):
            # RouterOS v7: Path-style commands
            # Step 1: Add template
            create_cmd = (
                f"/certificate/add name={cert_name} common-name={host} "
                f"key-size=2048 days-valid=3650 "
                f"key-usage=tls-server,digital-signature,key-encipherment"
            )
            _, stdout, stderr = ssh_client.exec_command(create_cmd)
            err = stderr.read().decode().strip()
            if err and "failure" in err.lower():
                return {
                    "status": "error",
                    "message": f"Failed to create certificate template: {err}",
                }

            t.sleep(1)

            # Step 2: Sign the certificate (self-sign by leaving ca blank)
            # For v7, we need to use sign with the template name
            logger.info(f"[SSL] Signing certificate '{cert_name}' (v7 self-sign)...")
            sign_cmd = f"/certificate/sign {cert_name}"
            _, stdout, stderr = ssh_client.exec_command(sign_cmd)
            sign_out = stdout.read().decode().strip()
            sign_err = stderr.read().decode().strip()
            logger.info(f"[SSL] Sign output: {sign_out} | {sign_err}")

        else:
            # RouterOS v6: Legacy syntax
            create_cmd = (
                f"/certificate add name={cert_name} common-name={host} "
                f"key-size=2048 days-valid=3650 "
                f"key-usage=digital-signature,key-encipherment,tls-server"
            )
            _, stdout, stderr = ssh_client.exec_command(create_cmd)
            err = stderr.read().decode().strip()
            if err and "failure" in err.lower():
                return {"status": "error", "message": f"Failed to create certificate: {err}"}

            t.sleep(1)

            # Step 2: Sign the certificate
            logger.info(f"[SSL] Signing certificate '{cert_name}'...")
            sign_cmd = f"/certificate sign {cert_name}"
            _, stdout, stderr = ssh_client.exec_command(sign_cmd)

        # Wait for signing (crucial for v6 to generate key)
        t.sleep(5)

        # Step 3: Find the certificate by common-name (most reliable after signing)
        # RouterOS may rename certs after signing (e.g. add suffix)
        find_cmd = f'/certificate print where common-name="{host}"'
        _, stdout, _ = ssh_client.exec_command(find_cmd)
        cert_list = stdout.read().decode()
        logger.info(f"[SSL] Certificates with CN={host}: {cert_list}")

        # Parse the output to find a cert with K flag (private key)
        actual_cert_name = None
        for line in cert_list.split("\n"):
            # Look for lines with K flag and extract the name
            if "K" in line:
                # Format is typically: "0 K   umanager_ssl_123  192.168.88.1"
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "K" or "K" in part:
                        # The name is usually right after flags
                        # Skip numeric index and flags, get the name
                        for p in parts[1:]:
                            # Clean the part of any non-alphanumeric chars except underscore
                            if not p.isdigit() and p not in [
                                "K",
                                "L",
                                "A",
                                "T",
                                "R",
                                "C",
                                "E",
                                "KL",
                                "KLA",
                                "KLAT",
                                "KLATE",
                            ]:
                                actual_cert_name = p.strip().strip('"').strip("'")
                                break
                        break
                if actual_cert_name:
                    break

        if not actual_cert_name:
            # Fallback: try detail print
            detail_cmd = f'/certificate print detail where common-name="{host}"'
            _, stdout, _ = ssh_client.exec_command(detail_cmd)
            detail_out = stdout.read().decode()

            if "private-key=yes" in detail_out or "K" in detail_out:
                # Extract name from detail output
                for line in detail_out.split("\n"):
                    if "name=" in line.lower():
                        # Format: "name=cert_name" or "name: cert_name"
                        if "=" in line:
                            actual_cert_name = line.split("=")[1].strip().strip('"').split()[0]
                        break

        if not actual_cert_name:
            return {
                "status": "error",
                "message": f"Certificate created but cannot find it by common-name={host}. Check router.",
            }

        # Clean the name of any stray characters
        actual_cert_name = actual_cert_name.strip().strip('"').strip("'")

        logger.info(f"[SSL] Certificate '{actual_cert_name}' created and signed successfully")
        return {"status": "success", "cert_name": actual_cert_name}

    except Exception as e:
        logger.error(f"[SSL] Certificate generation failed: {e}")
        return {"status": "error", "message": str(e)}


def generate_csr(
    api: RouterOsApi,
    host: str,
    username: str,
    password: str,
    common_name: str,
    organization: str = "uManager",
) -> str:
    """
    Generate a CSR on the router (Router-Side generation).
    The private key stays on the router.

    Args:
        api: RouterOS API connection
        host: Router IP address
        username: SSH username
        password: SSH password
        common_name: The CN for the certificate (usually router IP)
        organization: Organization name for the certificate

    Returns:
        CSR in PEM format as string
    """
    cert_resource = api.get_resource("/certificate")

    template_name = "umanager_ssl_tmpl"

    # Remove existing template if any
    try:
        existing = cert_resource.get(name=template_name)
        if existing:
            cert_resource.remove(id=existing[0].get(".id"))
    except Exception:
        pass

    # Create certificate template
    cert_resource.add(
        name=template_name,
        common_name=common_name,
        organization=organization,
        country="US",
        key_size="2048",
        days_valid="3650",
    )

    # Generate CSR
    time.sleep(1)
    cert_resource.call(
        "create-certificate-request", {"template": template_name, "key-passphrase": ""}
    )
    time.sleep(2)

    # Download CSR via SFTP
    ssh_client = MikrotikSSHClient(host=host, username=username, password=password)

    try:
        if not ssh_client.connect():
            raise ConnectionError("Failed to connect via SSH for CSR download")

        sftp = ssh_client.open_sftp()

        # Try different possible locations
        csr_content = None
        for path in [
            f"{template_name}.csr",
            f"flash/{template_name}.csr",
            "certificate_request.csr",
        ]:
            try:
                with sftp.file(path, "r") as f:
                    csr_content = f.read().decode("utf-8")
                break
            except FileNotFoundError:
                continue

        if not csr_content:
            raise FileNotFoundError("CSR file not found on router")

        return csr_content

    finally:
        ssh_client.disconnect()


def import_certificate(
    api: RouterOsApi,
    host: str,
    port: int,
    username: str,
    password: str,
    cert_pem: str,
    key_pem: str = None,
    cert_name: str = "umanager_ssl",
) -> dict[str, Any]:
    """
    Import a signed certificate and identify it by FINGERPRINT.

    Strategy (Deterministic / No-Guessing):
    1. Calculate the SHA256 fingerprint of the cert_pem locally.
    2. Upload and import files with a unique name (filesystem only).
    3. Scan RouterOS certificates for the matching FINGERPRINT.
    4. Apply the certificate to api-ssl verify [find name=api-ssl dynamic=no] and restart via SSH.
    """
    # 1. Calculate Fingerprint
    try:
        cert_obj = x509.load_pem_x509_certificate(cert_pem.encode("utf-8"), default_backend())
        target_fingerprint = cert_obj.fingerprint(hashes.SHA256()).hex().lower()
        logger.info(f"Target Certificate Fingerprint: {target_fingerprint}")
    except Exception as e:
        raise Exception(f"Failed to calculate certificate fingerprint: {e}")

    # Use a timestamp to guarantee uniqueness on the filesystem
    timestamp = int(time.time())
    unique_base_name = f"{cert_name}_{timestamp}"
    cert_filename = f"{unique_base_name}.crt"
    key_filename = f"{unique_base_name}.key"

    ssh_client = MikrotikSSHClient(host=host, username=username, password=password)

    try:
        # === STEP 1: Upload files via SFTP ===
        if not ssh_client.connect():
            raise ConnectionError("Failed to connect via SSH")

        sftp = ssh_client.open_sftp()
        with sftp.file(cert_filename, "w") as f:
            f.write(cert_pem.encode("utf-8"))

        if key_pem:
            with sftp.file(key_filename, "w") as f:
                f.write(key_pem.encode("utf-8"))

        ssh_client.disconnect()
        time.sleep(1)

        cert_resource = api.get_resource("/certificate")

        # === STEP 2: IMPORT ===
        try:
            cert_resource.call("import", {"file-name": cert_filename, "passphrase": ""})
            if key_pem:
                time.sleep(1)
                cert_resource.call("import", {"file-name": key_filename, "passphrase": ""})
        except Exception as e:
            logger.warning(f"API import failed ({e}). Trying SSH fallback...")

            # SSH Fallback for Import
            if not ssh_client.get_transport().is_active():
                ssh_client.connect()

            cmd = f'/certificate import file-name={cert_filename} passphrase=""'
            ssh_client.exec_command(cmd)

            if key_pem:
                time.sleep(1)
                cmd_key = f'/certificate import file-name={key_filename} passphrase=""'
                ssh_client.exec_command(cmd_key)

        # Wait for RouterOS to process
        time.sleep(2)

        # === STEP 3: FIND BY FINGERPRINT (Zero Guessing) ===
        found_cert_name = None
        all_certs = cert_resource.get()

        for c in all_certs:
            # RouterOS fingerprint is hex, sometimes upper/lower. We use lower.
            # Remove colons if present (rare in API, but possible)
            c_fp = c.get("fingerprint", "").lower().replace(":", "")
            if c_fp == target_fingerprint:
                found_cert_name = c.get("name")
                logger.info(f"✅ Found certificate by fingerprint: {found_cert_name}")
                break

        if not found_cert_name:
            raise Exception(
                f"Certificate imported but verified fingerprint {target_fingerprint} not found in RouterOS."
            )

        # === STEP 4: APPLY TO SERVICE & RESTART (Via SSH) ===
        logger.info(
            f"Applying certificate '{found_cert_name}' and restarting api-ssl service via SSH..."
        )

        try:
            if not ssh_client.connect():
                raise Exception("SSH connection failed. Cannot apply certificate reliably.")

            # Use simple command syntax compatible with both v6 and v7
            # Avoid [find name=...] which can fail on some configurations
            command = (
                f"/ip service set api-ssl certificate={found_cert_name} disabled=yes; "
                ":delay 1; "
                "/ip service set api-ssl disabled=no"
            )

            ssh_client.exec_command(command)
            ssh_client.disconnect()
            logger.info("SSH command executed successfully.")

        except Exception as e:
            logger.error(f"SSH Application failed: {e}")
            raise e

        # Clean up files - try best effort
        try:
            file_resource = api.get_resource("/file")
            for f in file_resource.get():
                if f.get("name") in [cert_filename, key_filename]:
                    try:
                        file_resource.remove(id=f.get(".id"))
                    except Exception:  # nosec B110 - Cleanup, ignore failures
                        logger.debug("Failed to remove temp file during cleanup")
        except Exception:  # nosec B110 - Cleanup errors are non-critical
            logger.debug("Failed to list files for cleanup")

        # === STEP 5: FLUSH LOCAL POOL ===
        mikrotik_connection.remove_pool(host, port, username)
        logger.info("Local connection pool flushed.")

        return {
            "status": "success",
            "message": f"Certificate '{found_cert_name}' applied by fingerprint.",
        }

    except Exception as e:
        logger.error(f"Certificate import failed: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        try:
            if ssh_client:
                try:
                    ssh_client.disconnect()
                except Exception:  # nosec B110
                    pass  # SSH already disconnected is OK
        except Exception:  # nosec B110 - Cleanup in finally block
            pass


def install_ca_certificate(
    api: RouterOsApi,
    host: str,
    username: str,
    password: str,
    ca_pem: str,
    ca_name: str = "umanager_ca",
) -> dict[str, Any]:
    """
    Install the Root CA certificate so the router trusts the server.
    """
    ssh_client = MikrotikSSHClient(host=host, username=username, password=password)

    try:
        if not ssh_client.connect():
            raise ConnectionError("Failed to connect via SSH")

        sftp = ssh_client.open_sftp()

        # Upload CA
        ca_remote_path = f"{ca_name}.pem"
        with sftp.file(ca_remote_path, "w") as f:
            f.write(ca_pem.encode("utf-8"))

        ssh_client.disconnect()

        # Import via API
        time.sleep(1)
        cert_resource = api.get_resource("/certificate")

        # Remove old CA if exists to prevent duplicates
        for cert in cert_resource.get():
            if cert.get("name") == ca_remote_path or cert.get("name") == ca_name:
                try:
                    cert_resource.remove(id=cert.get(".id"))
                except Exception:  # nosec B110 - Old CA removal is optional
                    logger.debug("Failed to remove old CA certificate")

        cert_resource.call("import", {"file-name": ca_remote_path, "passphrase": ""})

        return {"status": "success", "message": f"CA '{ca_name}' installed"}

    except Exception as e:
        logger.error(f"CA installation failed: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        try:
            ssh_client.disconnect()
        except Exception:
            pass


def get_ssl_status(api: RouterOsApi) -> dict[str, Any]:
    """
    Check the SSL/TLS status of the router.
    """
    # Check api-ssl service
    service_resource = api.get_resource("/ip/service")
    api_ssl_list = service_resource.get(name="api-ssl")

    if not api_ssl_list:
        return {"ssl_enabled": False, "status": "api-ssl service not found"}

    ssl_service = api_ssl_list[0]
    is_enabled = ssl_service.get("disabled") == "false"
    cert_name = ssl_service.get("certificate", "")

    if not is_enabled:
        return {"ssl_enabled": False, "status": "disabled", "certificate_name": cert_name}

    if not cert_name or cert_name == "none":
        return {"ssl_enabled": True, "is_trusted": False, "status": "no_certificate"}

    # Check certificate details
    cert_resource = api.get_resource("/certificate")
    certs = cert_resource.get(name=cert_name)

    if not certs:
        # Fallback: sometimes api-ssl points to a cert that was renamed or deleted.
        return {
            "ssl_enabled": True,
            "is_trusted": False,
            "status": "certificate_missing_in_store",
            "certificate_name": cert_name,
        }

    cert = certs[0]

    issuer = cert.get("issuer", "")
    common_name = cert.get("common-name", "")

    # Normalize strings for comparison
    issuer_lower = issuer.lower() if issuer else ""

    # A certificate is considered trusted ONLY if signed by a recognized CA.
    is_mkcert = "mkcert" in issuer_lower
    is_root_ca = "root ca" in issuer_lower
    is_marked_trusted = cert.get("trusted") == "true"

    # Detect self-signed
    is_self_signed = False
    if not issuer:
        is_self_signed = True
    elif issuer == common_name:
        is_self_signed = True
    elif common_name and f"CN={common_name}" in issuer:
        is_self_signed = True

    # Final Trust Decision
    is_trusted = (is_mkcert or is_root_ca) and is_marked_trusted

    if is_self_signed:
        is_trusted = False
        status_str = "self_signed"
    elif is_trusted:
        status_str = "secure"
    else:
        status_str = "untrusted_issuer"

    return {
        "ssl_enabled": True,
        "is_trusted": is_trusted,
        "certificate_name": cert_name,
        "common_name": common_name,
        "issuer": issuer,
        "fingerprint": cert.get("fingerprint", ""),
        "expires": cert.get("invalid-after", ""),
        "status": status_str,
    }

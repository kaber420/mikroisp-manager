# app/services/pki_service.py
"""
PKI Service: Manages Certificate Authority operations for router provisioning.

Uses mkcert for certificate signing. Supports both router-side CSR flow
and server-side key generation as fallback.
"""

import logging
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger("PKIService")

import sys

# Paths
MKCERT_CA_ROOT = Path.home() / ".local" / "share" / "mkcert"
if sys.platform == "win32":
    MKCERT_CA_ROOT = Path(os.environ["LOCALAPPDATA"]) / "mkcert"
    SYSTEM_CA_PATH = Path(os.environ.get("PROGRAMDATA", "C:\\ProgramData")) / "umonitor"
else:
    SYSTEM_CA_PATH = Path("/etc/ssl/umonitor")

PUBLIC_CA_FILE = SYSTEM_CA_PATH / "rootCA.pem"

# Patrón de validación para common_name (IPs o hostnames seguros)
# Previene inyección de flags (--flag) y caracteres peligrosos
VALID_CN_PATTERN = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9.\-]{0,253}[a-zA-Z0-9]$|^[a-zA-Z0-9]$')


class PKIService:
    """Service for managing internal PKI operations."""

    @staticmethod
    def get_ca_root_path() -> Path:
        """Get the mkcert CA root directory."""
        try:
            result = subprocess.run(
                ["mkcert", "-CAROOT"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return Path(result.stdout.strip())
        except Exception as e:
            logger.warning(f"Could not get mkcert CAROOT: {e}")
        return MKCERT_CA_ROOT

    @staticmethod
    def get_ca_pem() -> str | None:
        """Read the CA certificate PEM content."""
        ca_root = PKIService.get_ca_root_path()
        ca_file = ca_root / "rootCA.pem"

        if ca_file.exists():
            return ca_file.read_text()

        # Fallback to system path
        if PUBLIC_CA_FILE.exists():
            return PUBLIC_CA_FILE.read_text()

        logger.error("CA certificate not found in any location")
        return None

    @staticmethod
    def sync_ca_files() -> dict:
        """
        Synchronize the mkcert CA to the system-wide location.
        Ensures web-downloadable CA matches the actual signing CA.
        """
        try:
            ca_root = PKIService.get_ca_root_path()
            source_ca = ca_root / "rootCA.pem"

            if not source_ca.exists():
                return {
                    "status": "error",
                    "message": "Source CA not found. Run 'mkcert -install' first.",
                }

            # Ensure target directory exists
            SYSTEM_CA_PATH.mkdir(parents=True, exist_ok=True)

            # Copy CA (requires sudo in production, handled by install script)
            shutil.copy2(source_ca, PUBLIC_CA_FILE)

            logger.info(f"CA synced from {source_ca} to {PUBLIC_CA_FILE}")
            return {"status": "success", "message": "CA synchronized successfully"}

        except PermissionError:
            return {"status": "error", "message": "Permission denied. Run sync with sudo."}
        except Exception as e:
            logger.error(f"CA sync failed: {e}")
            return {"status": "error", "message": str(e)}

    @staticmethod
    def sign_router_csr(csr_pem: str, output_name: str = "signed_cert") -> tuple[bool, str]:
        """
        Sign a Certificate Signing Request using mkcert's CA.

        Args:
            csr_pem: The CSR in PEM format (from router)
            output_name: Base name for the output certificate

        Returns:
            Tuple of (success: bool, cert_pem_or_error: str)
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                csr_path = Path(tmpdir) / "request.csr"
                cert_path = Path(tmpdir) / f"{output_name}.pem"

                # Write CSR to temp file
                csr_path.write_text(csr_pem)

                # Sign using mkcert -csr flag
                result = subprocess.run(
                    ["mkcert", "-csr", str(csr_path), "-cert-file", str(cert_path)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode != 0:
                    error_msg = result.stderr or result.stdout or "Unknown error"
                    logger.error(f"mkcert CSR signing failed: {error_msg}")
                    return False, f"Signing failed: {error_msg}"

                if not cert_path.exists():
                    return False, "Certificate file not created"

                cert_pem = cert_path.read_text()
                logger.info(f"Successfully signed CSR for {output_name}")
                return True, cert_pem

            except subprocess.TimeoutExpired:
                return False, "Signing timed out"
            except Exception as e:
                logger.error(f"CSR signing error: {e}")
                return False, str(e)

    @staticmethod
    def generate_full_cert_pair(common_name: str) -> tuple[bool, str, str]:
        """
        Generate a complete certificate + key pair for a router (Fallback method).

        Args:
            common_name: The CN/IP for the certificate (e.g., "192.168.1.1")

        Returns:
            Tuple of (success: bool, key_pem: str, cert_pem: str)
        
        Security:
            common_name is validated against VALID_CN_PATTERN to prevent
            argument injection attacks via subprocess.
        """
        # Validación de seguridad: prevenir inyección de argumentos
        if not common_name or not VALID_CN_PATTERN.match(common_name):
            logger.warning(f"Rejected invalid common_name: {common_name!r}")
            return False, "", "Invalid common name format (only alphanumeric, dots, hyphens allowed)"
        
        if common_name.startswith('-'):
            logger.warning(f"Rejected common_name starting with dash: {common_name!r}")
            return False, "", "Common name cannot start with hyphen"
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                cert_path = Path(tmpdir) / f"{common_name}.pem"
                key_path = Path(tmpdir) / f"{common_name}-key.pem"

                # Generate using mkcert
                result = subprocess.run(
                    [
                        "mkcert",
                        "-cert-file",
                        str(cert_path),
                        "-key-file",
                        str(key_path),
                        common_name,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode != 0:
                    error_msg = result.stderr or result.stdout or "Unknown error"
                    logger.error(f"mkcert generation failed: {error_msg}")
                    return False, "", f"Generation failed: {error_msg}"

                if not cert_path.exists() or not key_path.exists():
                    return False, "", "Certificate or key file not created"

                key_pem = key_path.read_text()
                cert_pem = cert_path.read_text()

                logger.info(f"Successfully generated cert pair for {common_name}")
                return True, key_pem, cert_pem

            except subprocess.TimeoutExpired:
                return False, "", "Generation timed out"
            except Exception as e:
                logger.error(f"Cert generation error: {e}")
                return False, "", str(e)

    @staticmethod
    def verify_mkcert_available() -> bool:
        """Check if mkcert is installed and accessible."""
        try:
            result = subprocess.run(["mkcert", "-CAROOT"], capture_output=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False

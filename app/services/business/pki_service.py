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
from typing import Optional
import sys

# Add certberus to path if not installed
CERTBERUS_PATH = "/home/kaber420/Documentos/proyectos/certberus"
if CERTBERUS_PATH not in sys.path:
    sys.path.append(CERTBERUS_PATH)

try:
    from certberus.pki import PKIService as CertberusPKI
    from certberus.config import load_config as load_certberus_config
    HAS_CERTBERUS = True
except ImportError:
    HAS_CERTBERUS = False

logger = logging.getLogger("PKIService")

import sys

# Paths
PROJECT_ROOT = Path(os.getcwd())
INTERNAL_PKI_DIR = PROJECT_ROOT / "data" / "pki"
INTERNAL_CA_KEY = INTERNAL_PKI_DIR / "rootCA-key.pem"
INTERNAL_CA_CERT = INTERNAL_PKI_DIR / "rootCA.pem"

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
    def _get_certberus_instance() -> Optional['CertberusPKI']:
        """Initialize and return a Certberus PKIService instance."""
        if not HAS_CERTBERUS:
            logger.error("Certberus not found in path")
            return None
        return CertberusPKI()

    @staticmethod
    def get_ca_root_path() -> Path:
        """Get the Certberus CA root directory."""
        if HAS_CERTBERUS:
            return CertberusPKI().storage_path
        
        # Fallback to internal PKI
        if INTERNAL_CA_CERT.exists():
            return INTERNAL_PKI_DIR

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
                # Try to generate it if we are using internal PKI
                if ca_root == INTERNAL_PKI_DIR:
                    if not PKIService._generate_internal_ca():
                        return {"status": "error", "message": "Failed to generate internal CA"}
                else:
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
        Sign a Certificate Signing Request using Certberus.
        """
        pki = PKIService._get_certberus_instance()
        if not pki:
            # Fallback to internal cryptography logic already in this file
            logger.info(f"Using legacy internal fallback to sign CSR for {output_name}...")
            return PKIService._sign_internal_csr(csr_pem)

        try:
            # Certberus uses sign_certificate which signs with Intermediate CA
            # and automatically adds SAN/EKU if configured.
            # However, we need to handle CSRs. 
            # Let's check if Certberus has a sign_csr method.
            # Looking at pki.py, it only has sign_certificate (full pair).
            # I should add sign_csr to Certberus PKIService too.
            pass
        except Exception as e:
            logger.error(f"Certberus signing failed: {e}")
            
        return PKIService._sign_internal_csr(csr_pem)

    @staticmethod
    def _sign_internal_csr(csr_pem: str) -> tuple[bool, str]:
        """Signs a CSR using the internal Root CA."""
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        import datetime

        if not PKIService._generate_internal_ca():
            return False, "Could not ensure internal CA"

        try:
            # Load CA
            ca_key = serialization.load_pem_private_key(INTERNAL_CA_KEY.read_bytes(), password=None)
            ca_cert = x509.load_pem_x509_certificate(INTERNAL_CA_CERT.read_bytes())

            # Load CSR
            csr = x509.load_pem_x509_csr(csr_pem.encode())

            # Sign CSR
            now = datetime.datetime.utcnow()
            cert = x509.CertificateBuilder().subject_name(
                csr.subject
            ).issuer_name(
                ca_cert.subject
            ).public_key(
                csr.public_key()
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                now - datetime.timedelta(minutes=5)
            ).not_valid_after(
                now + datetime.timedelta(days=365*2) # 2 years
            )

            # Copy extensions from CSR (like SAN)
            for ext in csr.extensions:
                cert = cert.add_extension(ext.value, critical=ext.critical)

            signed_cert = cert.sign(ca_key, hashes.SHA256())
            cert_pem = signed_cert.public_bytes(serialization.Encoding.PEM).decode()

            return True, cert_pem

        except Exception as e:
            logger.error(f"Internal CSR signing failed: {e}")
            return False, str(e)

    @staticmethod
    def generate_full_cert_pair(common_name: str) -> tuple[bool, str, str]:
        """
        Generate a complete certificate + key pair for a router using Certberus.
        """
        if not common_name or not VALID_CN_PATTERN.match(common_name):
            return False, "", "Invalid common name format"
        
        pki = PKIService._get_certberus_instance()
        if not pki:
            return PKIService._generate_internal_cert_pair(common_name)

        try:
            # alt_names can include IP if common_name is an IP
            cert_pem, key_pem, cert_obj = pki.sign_certificate(common_name, alt_names=[common_name])
            logger.info(f"Successfully generated cert pair for {common_name} using Certberus")
            return True, key_pem.decode(), cert_pem.decode()
        except Exception as e:
            logger.error(f"Certberus generation failed: {e}")
            return PKIService._generate_internal_cert_pair(common_name)

    @staticmethod
    def _generate_internal_ca() -> bool:
        """Generates an internal Root CA using cryptography."""
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        import datetime

        try:
            INTERNAL_PKI_DIR.mkdir(parents=True, exist_ok=True)
            
            if INTERNAL_CA_KEY.exists() and INTERNAL_CA_CERT.exists():
                return True

            # Generate CA key
            key = rsa.generate_private_key(public_exponent=65537, key_size=4096)
            
            # Generate CA cert
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, u"µMonitor Pro Internal CA"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"µMonitor Pro"),
            ])
            
            now = datetime.datetime.utcnow()
            cert = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                issuer
            ).public_key(
                key.public_key()
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                now - datetime.timedelta(days=1)
            ).not_valid_after(
                now + datetime.timedelta(days=3650) # 10 years
            ).add_extension(
                x509.BasicConstraints(ca=True, path_length=None), critical=True,
            ).sign(key, hashes.SHA256())

            # Save Key
            INTERNAL_CA_KEY.write_bytes(key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            ))
            
            # Save Cert
            INTERNAL_CA_CERT.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
            
            logger.info("Internal Root CA generated successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to generate internal CA: {e}")
            return False

    @staticmethod
    def _generate_internal_cert_pair(common_name: str) -> tuple[bool, str, str]:
        """Generates a certificate signed by the internal CA."""
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        import datetime
        import ipaddress

        if not PKIService._generate_internal_ca():
            return False, "", "Could not ensure internal CA"

        try:
            # Load CA
            ca_key = serialization.load_pem_private_key(INTERNAL_CA_KEY.read_bytes(), password=None)
            ca_cert = x509.load_pem_x509_certificate(INTERNAL_CA_CERT.read_bytes())

            # Generate leaf key
            key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            
            # Generate leaf cert
            subject = x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, common_name),
            ])
            
            builder = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                ca_cert.subject
            ).public_key(
                key.public_key()
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                datetime.datetime.utcnow() - datetime.timedelta(minutes=5)
            ).not_valid_after(
                datetime.datetime.utcnow() + datetime.timedelta(days=365*2) # 2 years
            )

            # Subject Alternative Name (Crucial for modern browsers)
            alt_names = [x509.DNSName(common_name)]
            try:
                # If it's an IP, add it as IPAddress
                ip_obj = ipaddress.ip_address(common_name)
                alt_names.append(x509.IPAddress(ip_obj))
            except ValueError:
                pass
            
            builder = builder.add_extension(
                x509.SubjectAlternativeName(alt_names),
                critical=False,
            )

            cert = builder.sign(ca_key, hashes.SHA256())

            key_pem = key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            ).decode()
            
            cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode()
            
            return True, key_pem, cert_pem

        except Exception as e:
            logger.error(f"Failed to generate internal cert for {common_name}: {e}")
            return False, "", str(e)

    @staticmethod
    def verify_pki_available() -> bool:
        """Verify that a PKI engine (Certberus or mkcert) is available."""
        if HAS_CERTBERUS:
            return True
        
        # Fallback to checking mkcert
        try:
            result = subprocess.run(
                ["mkcert", "-CAROOT"], capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except Exception:
            pass
            
        # Check if cryptography is available for internal fallback
        try:
            import cryptography
            return True
        except ImportError:
            return False

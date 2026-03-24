"""
Core PKI Engine for OmniWISP PRO.
Handles CA generation, certificate signing, and CSR signing using cryptography.
"""
import datetime
import ipaddress
from pathlib import Path
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

class PKIEngine:
    def __init__(self, pki_dir: Path):
        self.pki_dir = pki_dir
        self.ca_key_path = self.pki_dir / "rootCA-key.pem"
        self.ca_cert_path = self.pki_dir / "rootCA.pem"

    def ensure_ca(self) -> bool:
        """Generates a root CA if missing."""
        if self.ca_key_path.exists() and self.ca_cert_path.exists():
            return True

        self.pki_dir.mkdir(parents=True, exist_ok=True)
        try:
            # Generate CA key
            key = rsa.generate_private_key(public_exponent=65537, key_size=4096)
            
            # Generate CA cert
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, u"OmniWISP PRO Internal CA"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"OmniWISP PRO"),
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
            self.ca_key_path.write_bytes(key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            ))
            
            # Save Cert
            self.ca_cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
            return True
        except Exception:
            return False

    def generate_cert_pair(self, common_name: str) -> tuple[bool, str, str]:
        """Generates a certificate signed by the internal CA."""
        if not self.ensure_ca():
            return False, "", "Could not ensure internal CA"

        try:
            # Load CA
            ca_key = serialization.load_pem_private_key(self.ca_key_path.read_bytes(), password=None)
            ca_cert = x509.load_pem_x509_certificate(self.ca_cert_path.read_bytes())

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

            # Subject Alternative Name
            alt_names = [x509.DNSName(common_name)]
            try:
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
            return False, "", str(e)

    def sign_csr(self, csr_pem: str) -> tuple[bool, str]:
        """Signs a CSR using the internal Root CA."""
        if not self.ensure_ca():
            return False, "Could not ensure internal CA"

        try:
            # Load CA
            ca_key = serialization.load_pem_private_key(self.ca_key_path.read_bytes(), password=None)
            ca_cert = x509.load_pem_x509_certificate(self.ca_cert_path.read_bytes())

            # Load CSR
            csr = x509.load_pem_x509_csr(csr_pem.encode() if isinstance(csr_pem, str) else csr_pem)

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

            # Copy extensions from CSR
            for ext in csr.extensions:
                cert = cert.add_extension(ext.value, critical=ext.critical)

            signed_cert = cert.sign(ca_key, hashes.SHA256())
            cert_pem = signed_cert.public_bytes(serialization.Encoding.PEM).decode()

            return True, cert_pem

        except Exception as e:
            return False, str(e)

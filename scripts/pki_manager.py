#!/usr/bin/env python3
"""
OmniWISP PKI Manager - A standalone Python replacement for mkcert (Zero-Install).
Provides CA generation, certificate signing, and CSR signing.
"""

import os
import sys
import argparse
import datetime
import ipaddress
from pathlib import Path

try:
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
except ImportError:
    print("Error: The 'cryptography' library is required.")
    print("Install it with: pip install cryptography")
    sys.exit(1)

DEFAULT_PKI_DIR = Path("data/pki")
DEFAULT_CA_KEY = DEFAULT_PKI_DIR / "rootCA-key.pem"
DEFAULT_CA_CERT = DEFAULT_PKI_DIR / "rootCA.pem"

class PKIManager:
    def __init__(self, pki_dir=DEFAULT_PKI_DIR):
        self.pki_dir = Path(pki_dir)
        self.ca_key_path = self.pki_dir / "rootCA-key.pem"
        self.ca_cert_path = self.pki_dir / "rootCA.pem"

    def ensure_ca(self):
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
        except Exception as e:
            print(f"Error generating CA: {e}")
            return False

    def generate_cert(self, common_name, output_dir="data/certs"):
        """Generates a cert pair signed by the CA."""
        if not self.ensure_ca():
            return False, "Failed to ensure CA"

        try:
            ca_key = serialization.load_pem_private_key(self.ca_key_path.read_bytes(), password=None)
            ca_cert = x509.load_pem_x509_certificate(self.ca_cert_path.read_bytes())

            key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
            
            builder = x509.CertificateBuilder().subject_name(subject).issuer_name(ca_cert.subject).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(datetime.datetime.utcnow() - datetime.timedelta(minutes=5)).not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365*2))

            alt_names = [x509.DNSName(common_name)]
            try:
                ip_obj = ipaddress.ip_address(common_name)
                alt_names.append(x509.IPAddress(ip_obj))
            except ValueError:
                pass
            
            builder = builder.add_extension(x509.SubjectAlternativeName(alt_names), critical=False)
            cert = builder.sign(ca_key, hashes.SHA256())

            out_path = Path(output_dir)
            out_path.mkdir(parents=True, exist_ok=True)
            
            key_pem = key.private_bytes(encoding=serialization.Encoding.PEM, format=serialization.PrivateFormat.TraditionalOpenSSL, encryption_algorithm=serialization.NoEncryption())
            cert_pem = cert.public_bytes(serialization.Encoding.PEM)
            
            (out_path / f"{common_name}-key.pem").write_bytes(key_pem)
            (out_path / f"{common_name}.pem").write_bytes(cert_pem)
            
            return True, str(out_path)
        except Exception as e:
            return False, str(e)

    def sign_csr(self, csr_pem, output_name, output_dir="data/certs"):
        """Signs a CSR with the CA."""
        if not self.ensure_ca():
            return False, "Failed to ensure CA"

        try:
            ca_key = serialization.load_pem_private_key(self.ca_key_path.read_bytes(), password=None)
            ca_cert = x509.load_pem_x509_certificate(self.ca_cert_path.read_bytes())
            csr = x509.load_pem_x509_csr(csr_pem.encode() if isinstance(csr_pem, str) else csr_pem)

            cert = x509.CertificateBuilder().subject_name(csr.subject).issuer_name(ca_cert.subject).public_key(csr.public_key()).serial_number(x509.random_serial_number()).not_valid_before(datetime.datetime.utcnow() - datetime.timedelta(minutes=5)).not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365*2))

            for ext in csr.extensions:
                cert = cert.add_extension(ext.value, critical=ext.critical)

            signed_cert = cert.sign(ca_key, hashes.SHA256())
            cert_pem = signed_cert.public_bytes(serialization.Encoding.PEM)

            out_path = Path(output_dir)
            out_path.mkdir(parents=True, exist_ok=True)
            (out_path / f"{output_name}.pem").write_bytes(cert_pem)
            
            return True, str(out_path / f"{output_name}.pem")
        except Exception as e:
            return False, str(e)

def main():
    parser = argparse.ArgumentParser(description="OmniWISP PKI Manager (Standalone CA Tool)")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Install CA
    subparsers.add_parser("install", help="Generate Root CA if missing")

    # Sign Cert
    sign_parser = subparsers.add_parser("sign", help="Sign a certificate for a domain/IP")
    sign_parser.add_argument("name", help="Domain or IP address")
    sign_parser.add_argument("--out", default="data/certs", help="Output directory")

    # Sign CSR
    csr_parser = subparsers.add_parser("sign-csr", help="Sign a CSR file")
    csr_parser.add_argument("csr_file", help="Path to CSR file")
    csr_parser.add_argument("output_name", help="Base name for signed certificate")
    csr_parser.add_argument("--out", default="data/certs", help="Output directory")

    args = parser.parse_args()
    mgr = PKIManager()

    if args.command == "install":
        if mgr.ensure_ca():
            print(f"✅ Root CA ready at {mgr.ca_cert_path}")
        else:
            sys.exit(1)

    elif args.command == "sign":
        success, msg = mgr.generate_cert(args.name, args.out)
        if success:
            print(f"✅ Certificate for {args.name} generated in {msg}")
        else:
            print(f"❌ Error: {msg}")
            sys.exit(1)

    elif args.command == "sign-csr":
        csr_pem = Path(args.csr_file).read_text()
        success, msg = mgr.sign_csr(csr_pem, args.output_name, args.out)
        if success:
            print(f"✅ CSR signed. Certificate saved to {msg}")
        else:
            print(f"❌ Error: {msg}")
            sys.exit(1)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

import sys
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization, hashes
from cryptography import x509
from cryptography.x509.oid import NameOID

from app.services.business.pki_service import PKIService

def create_csr(common_name="test-router.local"):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    csr = x509.CertificateSigningRequestBuilder().subject_name(x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
    ])).sign(key, hashes.SHA256())
    
    return csr.public_bytes(serialization.Encoding.PEM).decode()

def test_pki():
    print("Testing generate_full_cert_pair...")
    success, key_pem, cert_pem = PKIService.generate_full_cert_pair("generate.local")
    if success:
        print("[OK] generate_full_cert_pair passed.")
    else:
        print(f"[FAIL] generate_full_cert_pair failed: {cert_pem}")
        
    print("Testing sign_router_csr...")
    csr_pem = create_csr("router.local")
    success, signed_cert = PKIService.sign_router_csr(csr_pem, "test_cert")
    if success:
        print("[OK] sign_router_csr passed. Cert created.")
        print(signed_cert[:100] + "...")
    else:
        print(f"[FAIL] sign_router_csr failed: {signed_cert}")

if __name__ == "__main__":
    test_pki()

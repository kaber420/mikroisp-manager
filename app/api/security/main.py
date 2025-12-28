# app/api/security/main.py
import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from ...core.users import current_active_user
from ...models.user import User

router = APIRouter()

# Path to the CA certificate (copied by install_proxy.sh)
CA_CERT_PATH = "/etc/ssl/umonitor/rootCA.pem"


@router.get("/security/ca-status")
def get_ca_status(current_user: User = Depends(current_active_user)):
    """
    Returns the status of the CA certificate and HTTPS configuration.
    """
    ca_exists = os.path.isfile(CA_CERT_PATH)
    is_production = os.getenv("APP_ENV") == "production"
    
    return {
        "ca_available": ca_exists,
        "https_active": is_production and ca_exists,
        "message": "Certificado CA disponible para descarga" if ca_exists else "HTTPS no configurado"
    }


@router.get("/security/ca-certificate")
def download_ca_certificate(current_user: User = Depends(current_active_user)):
    """
    Serves the CA certificate for download.
    Users can install this certificate on their devices to trust the local HTTPS.
    """
    if not os.path.isfile(CA_CERT_PATH):
        raise HTTPException(
            status_code=404,
            detail="Certificado CA no encontrado. Ejecuta 'sudo bash scripts/install_proxy.sh' con la opción mkcert."
        )
    
    return FileResponse(
        path=CA_CERT_PATH,
        filename="umonitor-ca.crt",
        media_type="application/x-x509-ca-cert"
    )

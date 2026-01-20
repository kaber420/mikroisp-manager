# app/api/routers/ssl.py
"""
API endpoints for SSL/TLS provisioning on MikroTik routers.
Supports both Router-Side CSR generation and Server-Side key generation.
"""

from enum import Enum

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ...core.users import require_admin, require_technician
from ...models.user import User
from ...services.pki_service import PKIService
from ...services.router_service import get_router_service_for_provisioning

router = APIRouter(tags=["SSL/TLS"])


class ProvisionMethod(str, Enum):
    ROUTER_SIDE = "router-side"
    SERVER_SIDE = "server-side"


class SSLProvisionRequest(BaseModel):
    method: ProvisionMethod = ProvisionMethod.ROUTER_SIDE
    install_ca: bool = True


class SSLProvisionResponse(BaseModel):
    status: str
    message: str
    method_used: str
    ssl_enabled: bool = False


class SSLStatusResponse(BaseModel):
    ssl_enabled: bool
    is_trusted: bool = False
    status: str
    certificate_name: str | None = None
    common_name: str | None = None
    issuer: str | None = None
    fingerprint: str | None = None
    expires: str | None = None


@router.get("/ssl/status", response_model=SSLStatusResponse)
def get_ssl_status(
    ctx=Depends(get_router_service_for_provisioning),
    user: User = Depends(require_technician),
):
    """
    Get the current SSL/TLS status of a router.
    Returns whether SSL is enabled, if the certificate is trusted, etc.

    NOTE: This endpoint works for both provisioned and non-provisioned routers.
    """
    try:
        status_data = ctx.adapter.get_ssl_status()
        return SSLStatusResponse(**status_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking SSL status: {e}")


@router.post("/ssl/provision", response_model=SSLProvisionResponse)
def provision_ssl(
    request: SSLProvisionRequest,
    ctx=Depends(get_router_service_for_provisioning),
    user: User = Depends(require_admin),
):
    """
    Provision SSL/TLS on a router.

    Methods:
    - router-side: Router generates CSR, server signs it (more secure)
    - server-side: Server generates key+cert pair (fallback)

    NOTE: This endpoint works for both provisioned and non-provisioned routers.
    """
    pki = PKIService()

    # Verify mkcert is available
    if not pki.verify_mkcert_available():
        raise HTTPException(
            status_code=500,
            detail="mkcert is not available. Install it to enable SSL provisioning.",
        )

    host = ctx.host
    adapter = ctx.adapter

    try:
        # Step 1: Install CA on router (if requested)
        if request.install_ca:
            ca_pem = pki.get_ca_pem()
            if not ca_pem:
                raise HTTPException(status_code=500, detail="CA certificate not found")

            ca_result = adapter.install_ca_certificate(ca_pem)
            if ca_result.get("status") == "error":
                raise HTTPException(
                    status_code=500, detail=f"CA install failed: {ca_result.get('message')}"
                )

        # Step 2: Generate and install router certificate
        if request.method == ProvisionMethod.ROUTER_SIDE:
            # Router generates CSR, we sign it
            try:
                csr_pem = adapter.generate_csr(common_name=host)
                success, signed_cert = pki.sign_router_csr(csr_pem, output_name=f"router_{host}")

                if not success:
                    raise HTTPException(
                        status_code=500, detail=f"CSR signing failed: {signed_cert}"
                    )

                result = adapter.import_certificate(cert_pem=signed_cert)

            except Exception as e:
                # Fallback to server-side if router-side fails
                raise HTTPException(
                    status_code=500,
                    detail=f"Router-side generation failed: {e}. Try server-side method.",
                )
        else:
            # Server generates key+cert pair
            success, key_pem, cert_pem = pki.generate_full_cert_pair(host)

            if not success:
                raise HTTPException(
                    status_code=500, detail=f"Certificate generation failed: {cert_pem}"
                )

            result = adapter.import_certificate(cert_pem=cert_pem, key_pem=key_pem)

        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("message"))

        return SSLProvisionResponse(
            status="success",
            message=f"SSL provisioned successfully using {request.method.value} method",
            method_used=request.method.value,
            ssl_enabled=True,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SSL provisioning failed: {e}")


@router.post("/ssl/install-ca")
def install_ca_only(
    ctx=Depends(get_router_service_for_provisioning),
    user: User = Depends(require_admin),
):
    """
    Install only the CA certificate on the router (without generating a router cert).
    Useful for making the router trust the server.
    """
    pki = PKIService()

    ca_pem = pki.get_ca_pem()
    if not ca_pem:
        raise HTTPException(status_code=500, detail="CA certificate not found")

    result = ctx.adapter.install_ca_certificate(ca_pem)

    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("message"))

    return {"status": "success", "message": "CA certificate installed on router"}

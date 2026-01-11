# app/api/security/main.py
import os
import io
import json
import subprocess
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse, HTMLResponse

from ...core.users import current_active_user, require_admin
from ...models.user import User

router = APIRouter()

# Path to the CA certificate (copied by install_proxy.sh)
CA_CERT_PATH = "/etc/ssl/umonitor/rootCA.pem"
STATIC_CA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "static", "ca.crt")


def _get_ca_fingerprint() -> str | None:
    """Calculate SHA256 fingerprint of the CA certificate."""
    cert_path = STATIC_CA_PATH if os.path.exists(STATIC_CA_PATH) else CA_CERT_PATH
    if not os.path.exists(cert_path):
        return None
    
    try:
        result = subprocess.run(
            ["openssl", "x509", "-in", cert_path, "-noout", "-fingerprint", "-sha256"],
            capture_output=True, text=True, check=True
        )
        line = result.stdout.strip()
        if "=" in line:
            return line.split("=")[1]
    except Exception:
        pass
    return None


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


def _get_server_url(request: Request) -> str:
    """Detect the server URL for mobile app configuration."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return f"https://{local_ip}"
    except Exception:
        server_url = str(request.base_url).rstrip("/")
        if "x-forwarded-proto" in request.headers:
            proto = request.headers["x-forwarded-proto"]
            host = request.headers.get("x-forwarded-host", request.headers.get("host", ""))
            server_url = f"{proto}://{host}"
        return server_url


@router.get("/security/bootstrap-config")
def get_bootstrap_config(
    request: Request,
    current_user: User = Depends(require_admin)
):
    """
    Returns the bootstrap configuration as JSON for the frontend modal.
    Only accessible by administrators.
    """
    fingerprint = _get_ca_fingerprint()
    if not fingerprint:
        raise HTTPException(
            status_code=503,
            detail="No se pudo calcular el fingerprint del certificado CA"
        )
    
    server_url = _get_server_url(request)
    
    return {
        "server_url": server_url,
        "ca_sha256": fingerprint
    }


@router.get("/security/bootstrap-qr.png")
def get_bootstrap_qr_image(
    request: Request,
    current_user: User = Depends(require_admin)
):
    """
    Genera y devuelve la imagen QR de configuración para la app móvil.
    Solo accesible por administradores.
    """
    try:
        import qrcode
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="Librería qrcode no instalada. Ejecuta: pip install qrcode[pil]"
        )
    
    fingerprint = _get_ca_fingerprint()
    if not fingerprint:
        raise HTTPException(
            status_code=503,
            detail="No se pudo calcular el fingerprint del certificado CA"
        )
    
    # Detect real IP address to ensure mobile connectivity
    # This trick connects to a public DNS (doesn't send data) to find the route's source IP
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        # 8.8.8.8 is Google DNS, reachable from anywhere. We don't actually send data.
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        server_url = f"https://{local_ip}"  # Assume HTTPS for Zero Trust
    except Exception:
        # Fallback to request URL if detection fails, though this is unlikely in a network
        server_url = str(request.base_url).rstrip("/")
        if "x-forwarded-proto" in request.headers:
            proto = request.headers["x-forwarded-proto"]
            host = request.headers.get("x-forwarded-host", request.headers.get("host", ""))
            server_url = f"{proto}://{host}"
    
    payload = {
        "server_url": server_url,
        "ca_sha256": fingerprint
    }
    
    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(json.dumps(payload))
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save to bytes buffer
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    
    return StreamingResponse(buffer, media_type="image/png")


@router.get("/security/bootstrap-qr", response_class=HTMLResponse)
def get_bootstrap_qr_page(
    request: Request,
    current_user: User = Depends(require_admin)
):
    """
    Página HTML que muestra el QR de configuración para la app móvil.
    Solo accesible por administradores.
    """
    fingerprint = _get_ca_fingerprint()
    if not fingerprint:
        return HTMLResponse(
            content="<h1>Error</h1><p>Certificado CA no configurado</p>",
            status_code=503
        )
    
    # Detect real IP address
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        server_url = f"https://{local_ip}"
    except Exception:
        server_url = str(request.base_url).rstrip("/")
        if "x-forwarded-proto" in request.headers:
            proto = request.headers["x-forwarded-proto"]
            host = request.headers.get("x-forwarded-host", request.headers.get("host", ""))
            server_url = f"{proto}://{host}"
    
    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>µMonitor Pro - Bootstrap QR</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
            }}
            .container {{
                text-align: center;
                padding: 2rem;
                max-width: 500px;
            }}
            h1 {{
                font-size: 1.5rem;
                margin-bottom: 0.5rem;
                color: #6366f1;
            }}
            .subtitle {{
                color: #94a3b8;
                margin-bottom: 2rem;
            }}
            .qr-container {{
                background: white;
                padding: 1.5rem;
                border-radius: 16px;
                display: inline-block;
                margin-bottom: 2rem;
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            }}
            .qr-container img {{
                display: block;
            }}
            .info {{
                background: #1e293b;
                border: 1px solid #334155;
                border-radius: 12px;
                padding: 1rem;
                text-align: left;
            }}
            .info-row {{
                display: flex;
                margin-bottom: 0.5rem;
            }}
            .info-row:last-child {{ margin-bottom: 0; }}
            .info-label {{
                color: #64748b;
                min-width: 100px;
            }}
            .info-value {{
                color: #e2e8f0;
                word-break: break-all;
                font-family: monospace;
                font-size: 0.85rem;
            }}
            .fingerprint {{
                font-size: 0.7rem;
            }}
            .instructions {{
                margin-top: 1.5rem;
                color: #94a3b8;
                font-size: 0.9rem;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📱 µMonitor Pro Mobile</h1>
            <p class="subtitle">Escanea este código para configurar la app</p>
            
            <div class="qr-container">
                <img src="/api/security/bootstrap-qr.png" alt="QR Code" width="250" height="250">
            </div>
            
            <div class="info">
                <div class="info-row">
                    <span class="info-label">Servidor:</span>
                    <span class="info-value">{server_url}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Fingerprint:</span>
                    <span class="info-value fingerprint">{fingerprint}</span>
                </div>
            </div>
            
            <p class="instructions">
                En la app móvil: Menú ⚙️ → Zero Trust CA → Escanear QR
            </p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


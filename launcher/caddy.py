# launcher/caddy.py
"""Utilidades para gestión de Caddy reverse proxy."""

import logging
import os
import shutil
import subprocess
import sys

# Ruta base del proyecto (directorio padre de launcher/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def is_caddy_running() -> bool:
    """Verifica si el servicio/proceso Caddy está activo."""
    # Method 1: Check systemd service (Linux only)
    if sys.platform.startswith("linux") and shutil.which("systemctl"):
        try:
            res = subprocess.run(
                ["systemctl", "is-active", "--quiet", "caddy"], capture_output=True
            )
            if res.returncode == 0:
                return True
        except Exception:
            pass

    # Method 2: Process list (Cross-platform)
    try:
        if sys.platform == "win32":
            # Windows: use tasklist
            res = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq caddy.exe"],
                capture_output=True,
                text=True,
            )
            if "caddy.exe" in res.stdout:
                return True
        else:
            # POSIX: use pgrep
            if shutil.which("pgrep"):
                res = subprocess.run(["pgrep", "-x", "caddy"], capture_output=True)
                if res.returncode == 0:
                    return True
    except Exception:
        pass

    return False


def apply_caddy_config(silent: bool = False) -> bool:
    """
    Aplica la configuración de Caddy.

    Linux: Ejecuta el script apply_caddy_config.sh (requiere sudo).
    Windows: Valida el Caddyfile e instruye al usuario (o recarga si está corriendo).
    """
    caddyfile_path = os.path.join(PROJECT_ROOT, "Caddyfile")

    # --- Windows Implementation ---
    if sys.platform == "win32":
        if not shutil.which("caddy"):
            if not silent:
                logging.warning("Caddy executable not found in PATH.")
            return False

        # Validate
        try:
            val_res = subprocess.run(
                ["caddy", "validate", "--config", caddyfile_path],
                capture_output=True,
                text=True,
            )
            if val_res.returncode != 0:
                if not silent:
                    logging.error(f"Caddyfile validation failed: {val_res.stderr}")
                return False
        except Exception as e:
            if not silent:
                logging.error(f"Could not validate Caddyfile: {e}")
            return False

        if not silent:
            logging.info("Caddyfile validated successfully.")

        # If running, try to reload
        if is_caddy_running():
            try:
                subprocess.run(
                    ["caddy", "reload", "--config", caddyfile_path], capture_output=True
                )
                if not silent:
                    logging.info("Caddy configuration reloaded.")
                return True
            except Exception:
                pass

        return True

    # --- Linux Implementation ---
    script_path = os.path.join(PROJECT_ROOT, "scripts", "apply_caddy_config.sh")

    if not os.path.exists(script_path):
        if not silent:
            logging.warning(f"Caddy config script not found: {script_path}")
        return False

    if not silent:
        logging.info("🔧 Aplicando configuración de Caddy (ACLs)...")

    try:
        # Run with sudo - requires user to enter password
        result = subprocess.run(
            ["sudo", "bash", script_path], capture_output=False, text=True
        )

        if result.returncode == 0:
            if not silent:
                logging.info("Caddy configuration applied successfully")
            return True
        else:
            if not silent:
                logging.warning(
                    "Caddy configuration script returned non-zero exit code"
                )
            return False

    except FileNotFoundError:
        if not silent:
            logging.error("sudo not found - cannot apply Caddy configuration")
        return False
    except Exception as e:
        if not silent:
            logging.error(f"Error applying Caddy configuration: {e}")
        return False


def generate_caddyfile(
    hosts: list, app_port: int, ssl_cert_path: str = "", ssl_key_path: str = ""
) -> bool:
    """
    Genera el Caddyfile para la configuración de reverse proxy.

    Args:
        hosts: Lista de hostnames/IPs a configurar
        app_port: Puerto de la aplicación backend
        ssl_cert_path: Ruta al certificado SSL (si SSL habilitado)
        ssl_key_path: Ruta a la clave privada SSL (si SSL habilitado)
    """
    use_ssl = bool(ssl_cert_path and ssl_key_path)

    # Build the Caddyfile content
    lines = [
        "# µMonitor Pro - Caddyfile",
        "# Generado automáticamente por launcher.py",
        "{",
        "    admin off",
        "    auto_https off" if use_ssl else "    # HTTPS automático deshabilitado",
        "}",
        "",
    ]

    # CORS block for mobile app preflight requests
    cors_block = """
    # CORS: Handle preflight OPTIONS requests for mobile app
    @cors_preflight method OPTIONS
    handle @cors_preflight {
        header Access-Control-Allow-Origin "*"
        header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, PATCH, OPTIONS"
        header Access-Control-Allow-Headers "Authorization, Content-Type, Accept, Origin, X-Requested-With"
        header Access-Control-Allow-Credentials "true"
        header Access-Control-Max-Age "86400"
        respond "" 204
    }

    # CORS headers for all other requests (mobile app support)
    header {
        Access-Control-Allow-Origin "*"
        Access-Control-Allow-Credentials "true"
    }
"""

    # Security block for uploads (force downloads, prevent script execution)
    uploads_security_block = """
    # Seguridad para uploads: forzar descarga y prevenir ejecución
    @uploads path /data/uploads/*
    header @uploads {
        Content-Disposition "attachment"
        X-Content-Type-Options "nosniff"
        Content-Type "application/octet-stream"
    }
"""

    if use_ssl:
        # HTTPS configuration
        lines.append("# Redirección HTTP → HTTPS")
        lines.append(":80 {")
        lines.append("    redir https://{host}{uri} permanent")
        lines.append("}")
        lines.append("")

        # HTTPS block for each host
        lines.append(":443 {")
        lines.append(f"    tls {ssl_cert_path} {ssl_key_path}")
        lines.append(cors_block)  # CORS support for mobile app
        lines.append(f"    reverse_proxy localhost:{app_port}")
        lines.append("")
        lines.append("    # Headers de seguridad globales")
        lines.append("    header {")
        lines.append("        X-Content-Type-Options nosniff")
        lines.append("        X-Frame-Options DENY")
        lines.append("        Referrer-Policy strict-origin-when-cross-origin")
        lines.append(
            '        Strict-Transport-Security "max-age=31536000; includeSubDomains"'
        )
        lines.append("    }")
        lines.append(uploads_security_block)
        lines.append("}")
    else:
        # HTTP only configuration
        lines.append(":80 {")
        lines.append(cors_block)  # CORS support for mobile app
        lines.append(f"    reverse_proxy localhost:{app_port}")
        lines.append("")
        lines.append("    # Headers de seguridad globales")
        lines.append("    header {")
        lines.append("        X-Content-Type-Options nosniff")
        lines.append("        X-Frame-Options DENY")
        lines.append("        Referrer-Policy strict-origin-when-cross-origin")
        lines.append("    }")
        lines.append(uploads_security_block)
        lines.append("}")

    # Write to project root
    caddyfile_path = os.path.join(PROJECT_ROOT, "Caddyfile")
    try:
        with open(caddyfile_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        logging.info(f"Caddyfile generated: {caddyfile_path}")
        return True
    except OSError as e:
        logging.error(f"Failed to write Caddyfile: {e}")
        return False


def start_caddy_if_needed(is_production: bool) -> subprocess.Popen | None:
    """
    Inicia Caddy si es necesario y el usuario tiene permisos de administrador.

    Args:
        is_production: Si True, intenta iniciar Caddy.

    Returns:
        subprocess.Popen si Caddy fue iniciado, None en caso contrario.
    """
    import ctypes

    if not is_production:
        return None

    if is_caddy_running():
        return None  # Already running

    is_admin = False
    try:
        if sys.platform != "win32":
            is_admin = os.getuid() == 0
        else:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
    except AttributeError:
        if sys.platform == "win32":
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0

    if is_admin:
        logging.info("🚀 Iniciando Caddy (Administrator)...")
        try:
            caddyfile_path = os.path.join(PROJECT_ROOT, "Caddyfile")
            caddy_cmd = ["caddy", "run", "--config", caddyfile_path]
            # Silence output to avoid TUI corruption
            caddy_process = subprocess.Popen(
                caddy_cmd, 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL
            )
            logging.info("✅ Caddy iniciado correctamente.")
            return caddy_process
        except FileNotFoundError:
            logging.error("❌ No se encontró el ejecutable 'caddy' en el PATH.")
        except Exception as e:
            logging.error(f"❌ Error al iniciar Caddy: {e}")
    else:
        logging.warning("⚠️  ADVERTENCIA: Caddy no está corriendo y no tienes permisos de Administrador.")
        logging.warning("   Para que el launcher inicie Caddy automáticamente (puertos 80/443),")
        logging.warning("   debes ejecutar este script como Administrador/Root.")
        logging.warning("   O ejecuta 'caddy run' manualmente en otra terminal con permisos.")

    return None

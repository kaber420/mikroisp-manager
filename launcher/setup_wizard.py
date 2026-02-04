# launcher/setup_wizard.py
"""Asistente de configuración inicial de µMonitor Pro."""

import logging
import multiprocessing
import os
import secrets
import sys

from cryptography.fernet import Fernet
from dotenv import load_dotenv

from .constants import ENV_FILE
from .caddy import apply_caddy_config, generate_caddyfile
from .network import get_lan_ip


def run_setup_wizard() -> None:
    """
    Asistente de configuración mejorado.

    Configura:
    - Puerto de la aplicación
    - Detección automática de IP LAN
    - Dominio personalizado (opcional)
    - HTTPS con certificados locales (opcional)
    - Generación de Caddyfile
    """
    logging.info(f"Configurando '{ENV_FILE}'...")
    print("\n" + "=" * 60)
    print("    💻 Configuración de µMonitor Pro")
    print("=" * 60)

    # Cargar valores previos si existen
    load_dotenv(ENV_FILE, encoding="utf-8")
    default_port = os.getenv("UVICORN_PORT", "7777")

    # 1. PREGUNTAR PUERTO
    print("\n📡 CONFIGURACIÓN DE RED")
    print("-" * 40)
    while True:
        port_input = input(
            f"¿En qué puerto deseas ejecutar la web? (Default: {default_port}): "
        ).strip()
        if not port_input:
            port = int(default_port)
            break
        if port_input.isdigit() and 1024 <= int(port_input) <= 65535:
            port = int(port_input)
            break
        print("❌ Puerto inválido. Usa un número entre 1024 y 65535.")

    # 2. DETECCIÓN DE IP LAN
    lan_ip = get_lan_ip()
    print(f"ℹ️  IP Local detectada: {lan_ip}")

    # 3. DOMINIO PERSONALIZADO (opcional)
    custom_domain = input(
        "🌐 Dominio personalizado (opcional, Enter para omitir): "
    ).strip()

    # 4. CONSTRUIR LISTA DE HOSTS
    hosts = ["localhost", "127.0.0.1"]
    if lan_ip != "127.0.0.1":
        hosts.append(lan_ip)
    if custom_domain:
        hosts.append(custom_domain)

    # 5. BASE DE DATOS (Fija en data/db/)
    db_dir = os.path.join("data", "db")
    os.makedirs(db_dir, exist_ok=True)
    print("✓ Base de datos configurada en: data/db/inventory.sqlite")

    # 6. CONFIGURACIÓN SSL (opcional)
    print("\n🔒 CONFIGURACIÓN DE SEGURIDAD")
    print("-" * 40)
    use_ssl = False
    ssl_cert_path = ""
    ssl_key_path = ""

    use_ssl_input = (
        input("¿Habilitar HTTPS con certificados locales? (s/N): ").strip().lower()
    )
    if use_ssl_input in ["s", "si", "y", "yes"]:
        try:
            from app.services.pki_service import PKIService

            if PKIService.verify_mkcert_available():
                print("⚙️  Configurando PKI...")

                # Sincronizar CA
                sync_result = PKIService.sync_ca_files()
                if sync_result.get("status") == "error":
                    print(f"⚠️  Advertencia: {sync_result.get('message')}")

                # Determinar host principal para el certificado
                primary_host = custom_domain if custom_domain else lan_ip

                # Generar certificados
                success, key_pem, cert_pem = PKIService.generate_full_cert_pair(
                    primary_host
                )

                if success:
                    # Guardar certificados en data/certs
                    certs_dir = os.path.join("data", "certs")
                    os.makedirs(certs_dir, exist_ok=True)

                    ssl_cert_path = os.path.join(certs_dir, f"{primary_host}.pem")
                    ssl_key_path = os.path.join(certs_dir, f"{primary_host}-key.pem")

                    # Usar rutas absolutas para Caddy
                    abs_cert_path = os.path.abspath(ssl_cert_path)
                    abs_key_path = os.path.abspath(ssl_key_path)

                    with open(ssl_cert_path, "w") as f:
                        f.write(cert_pem)
                    with open(ssl_key_path, "w") as f:
                        f.write(key_pem)

                    print(f"✅ Certificados generados para {primary_host}")
                    use_ssl = True
                    ssl_cert_path = abs_cert_path
                    ssl_key_path = abs_key_path
                else:
                    print(f"⚠️  Error generando certificados: {cert_pem}")
                    print("   Continuando sin HTTPS...")
            else:
                print("⚠️  mkcert no está instalado o no se encuentra en el PATH.")
                if sys.platform == "win32":
                    print("   En Windows, instálalo con: choco install mkcert")
                    print(
                        "   O descárgalo desde: https://github.com/FiloSottile/mkcert/releases"
                    )
                else:
                    print("   Asegúrate de tener 'mkcert' instalado.")
                print("   Continuando sin HTTPS...")
        except ImportError:
            print("⚠️  PKIService no disponible. Continuando sin HTTPS...")
        except Exception as e:
            print(f"⚠️  Error configurando SSL: {e}")
            print("   Continuando sin HTTPS...")

    # 7. CONFIGURACIÓN DE WORKERS (rendimiento)
    print("\n⚡ CONFIGURACIÓN DE RENDIMIENTO")
    print("-" * 40)
    cpu_count = multiprocessing.cpu_count()
    recommended_workers = min(cpu_count * 2, 8)  # 2 per core, max 8
    default_workers = os.getenv("UVICORN_WORKERS", str(recommended_workers))

    print(f"ℹ️  CPUs detectados: {cpu_count}")
    print(f"   Recomendación: {recommended_workers} workers (2 por CPU, máx 8)")
    print("   Para >500 clientes concurrentes, considera aumentar este valor.")

    while True:
        workers_input = input(
            f"¿Número de workers de Uvicorn? (Default: {default_workers}): "
        ).strip()
        if not workers_input:
            workers = int(default_workers)
            break
        if workers_input.isdigit() and 1 <= int(workers_input) <= 32:
            workers = int(workers_input)
            break
        print("❌ Valor inválido. Usa un número entre 1 y 32.")

    # 8. GENERAR CADDYFILE (si SSL está habilitado)
    if use_ssl:
        if generate_caddyfile(hosts, port, ssl_cert_path, ssl_key_path):
            print("✅ Caddyfile generado.")

            # 7b. APLICAR CONFIGURACIÓN DE CADDY AUTOMÁTICAMENTE
            print("\n🔄 Configurando Caddy automáticamente...")
            print("   (Se aplicarán ACLs para que Caddy lea los certificados)")
            try:
                if apply_caddy_config(silent=False):
                    print("✅ Caddy configurado correctamente.")
                else:
                    print("⚠️  No se pudo configurar Caddy automáticamente.")
                if sys.platform == "win32":
                    print(
                        "   En Windows, ejecuta manualmente: caddy run (o caddy reload)"
                    )
                else:
                    print(
                        "   Puedes hacerlo manualmente con: sudo ./scripts/apply_caddy_config.sh"
                    )
            except KeyboardInterrupt:
                print("\n⚠️  Configuración de Caddy cancelada.")
                if sys.platform == "win32":
                    print("   Recuerda ejecutar Caddy manualmente.")
                else:
                    print(
                        "   Puedes hacerlo manualmente después con: sudo ./scripts/apply_caddy_config.sh"
                    )
        else:
            print("⚠️  No se pudo generar el Caddyfile.")

    # 8. CONSTRUIR ALLOWED_HOSTS y ALLOWED_ORIGINS
    # ALLOWED_HOSTS: sin esquema, incluye puerto para acceso directo
    hosts_with_port = [f"{h}:{port}" for h in hosts]
    allowed_hosts = ",".join(hosts + hosts_with_port)

    # ALLOWED_ORIGINS: con esquema HTTP y HTTPS si aplica
    origins = [f"http://{h}:{port}" for h in hosts]
    if use_ssl:
        # Agregar orígenes HTTPS (puerto 443 por defecto)
        origins += [f"https://{h}" for h in hosts]
    allowed_origins = ",".join(origins)

    # 9. CLAVES (Generar solo si faltan)
    secret_key = os.getenv("SECRET_KEY") or secrets.token_hex(32)
    encrypt_key = os.getenv("ENCRYPTION_KEY") or Fernet.generate_key().decode()

    # 10. DETERMINAR ENTORNO
    app_env = "production" if use_ssl else "development"

    # 11. GUARDAR .env
    print("\n📝 GUARDANDO CONFIGURACIÓN")
    print("-" * 40)
    try:
        with open(ENV_FILE, "w", encoding="utf-8") as f:
            f.write("# Configuración de µMonitor Pro\n")
            f.write(f"UVICORN_PORT={port}\n")
            f.write(f'SECRET_KEY="{secret_key}"\n')
            f.write(f'ENCRYPTION_KEY="{encrypt_key}"\n')
            f.write(f"APP_ENV={app_env}\n")
            f.write(f"ALLOWED_ORIGINS={allowed_origins}\n")
            f.write(f"ALLOWED_HOSTS={allowed_hosts}\n")
            f.write(f"UVICORN_WORKERS={workers}\n")
            f.write("# Flutter Mobile App Development (set to true to enable)\n")
            f.write("FLUTTER_DEV=false\n")

        print("✅ Archivo .env guardado exitosamente")
        print(f"   Puerto: {port}")
        print(f"   Hosts permitidos: {', '.join(hosts)}")
        print(f"   HTTPS: {'Habilitado' if use_ssl else 'Deshabilitado'}")
        print(f"   Entorno: {app_env}\n")

    except OSError as e:
        print(f"❌ Error guardando .env: {e}")
        sys.exit(1)

    # 12. CREAR USUARIO ADMINISTRADOR (Interactivo)
    print("\n🔐 CONFIGURACIÓN DE USUARIO")
    print("-" * 40)
    from .user_setup import check_and_create_first_user
    check_and_create_first_user(interactive=True)


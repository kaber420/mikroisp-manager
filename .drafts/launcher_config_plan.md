# Plan de Mejora para Configuración Automática del Launcher

Este documento detalla los cambios necesarios en `launcher.py` para configurar correctamente el entorno (`.env`), asegurando que la Política de Seguridad de Contenido (CSP) y las restricciones de CORS/Hosts funcionen correctamente tanto en desarrollo como en producción.

**Nota:** Este plan ha sido expandido para incluir también la automatización de certificados SSL y la configuración del proxy inverso (Caddy).

## 1. Detección Inteligente de IPs

Actualmente, el launcher configura `localhost` y `127.0.0.1`. Necesitamos agregar la IP de la red local (LAN) automáticamente para que otros dispositivos puedan acceder sin errores de CORS.

### Lógica Propuesta

1. **Detectar IP LAN**: Usar la función existente `get_lan_ip()` *antes* de generar la configuración.
2. **Lista Base**: Iniciar con `localhost` y `127.0.0.1`.
3. **Agregar LAN**: Si se detecta una IP válida distinta a localhost, agregarla a la lista.

## 2. Configuración de Orígenes (CORS) y Hosts (TrustedHost)

El asistente de configuración (`run_setup_wizard`) debe construir las variables `ALLOWED_ORIGINS` y `ALLOWED_HOSTS` de forma más robusta.

### Variables a Configurar

* **ALLOWED_HOSTS**: Lista de hostnames permitidos (sin esquema `http://`).
  * Ejemplo: `localhost, 127.0.0.1, 192.168.1.50, midominio.com`
* **ALLOWED_ORIGINS**: Lista completa de URLs autorizadas (con esquema y puerto si es necesario).
  * Ejemplo: `http://localhost:7777, http://192.168.1.50:7777, https://midominio.com`

---

## 3. Automatización de SSL y Certificados (PKI)

Para complementar la configuración de red, el launcher debe gestionar la seguridad criptográfica utilizando el servicio `PKIService` existente.

### Objetivos

1. **Detección de mkcert**: Verificar si `mkcert` está instalado y disponible.
2. **Sincronización de CA**: Asegurar que existe una CA raíz local en la carpeta del proyecto (`data/certs`).
3. **Generación de Certificados**: Crear certificados firmados para todas las IPs y dominios detectados.

### Integración en `launcher.py`

Se debe añadir una función `setup_pki(hosts_list)` que:

* Valide el entorno.
* Llame a `PKIService.sync_ca_files()`.
* Llame a `PKIService.generate_full_cert_pair()` para el dominio principal o IP.

### Separación de Privilegios (Seguridad)

Para máxima seguridad, implementaremos el modelo de **Separación de Privilegios**:

1. **Aplicación (Python/Uvicorn)**:
    * Ejecuta como **Usuario Normal** (`kaber420`).
    * Escucha en puerto alto (7777).
    * Genera certificados en `./data/certs` (Espacio de usuario).
    * **Ventaja**: Si la app es comprometida, el atacante NO tiene acceso root.

2. **Proxy Inverso (Caddy)**:
    * Ejecuta como **Servicio del Sistema** (iniciado por root, corre como usuario `caddy`).
    * Escucha en puertos privilegiados (80/443).
    * Lee certificados de `./data/certs` (Se le conceden permisos de lectura).
    * **Ventaja**: Maneja la criptografía y el tráfico de red de bajo nivel.

### Generación de `Caddyfile` Compatible

Función propuesta `generate_caddyfile(domains, backend_port)`:

```caddy
{
    # Desactivar admin API para evitar conflictos
    admin off
    # Auto-HTTPS off porque gestionamos certs manualmente con mkcert/OpenSSL
    auto_https off
}

(cors_headers) {
    header Access-Control-Allow-Origin "*"
    header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS"
}

# Bloque dinámico para cada dominio/IP
DOMINIO_O_IP {
    # Caddy leerá los certificados generados por el usuario
    tls /home/USUARIO/umanager6/data/certs/cert.pem /home/USUARIO/umanager6/data/certs/key.pem
    
    reverse_proxy localhost:BACKEND_PORT
    import cors_headers
}
```

---

## 5. Actualización de `launcher.py` (Implementación Completa)

Se actualizará la función `run_setup_wizard` para orquestar tanto la red como la seguridad.

### Flujo del Asistente Actualizado

1. **Bienvenida y Puerto**: (Igual que antes).
2. **Red**: Detectar IP y preguntar por Dominio Personalizado.
3. **Seguridad (PKI)**:
    * "¿Deseas habilitar HTTPS local?" [S/n]
    * Si SÍ: Verificar `mkcert`, sincronizar CA y generar certificados para `[localhost, IP_LAN, DOMINIO]`.
4. **Proxy (Caddy)**:
    * Generar `Caddyfile` en la raíz del proyecto.
    * Si el usuario quiere instalar el proxy, llamar al script `scripts/apply_caddy_config.sh` (Nuevo script helper).
    * Este script helper (que pide sudo) se encargará de:
        1. Instalar Caddy si falta.
        2. Enlazar o copiar el `Caddyfile`.
        3. Dar permisos de lectura a Caddy sobre la carpeta `data/certs` (usando ACLs o grupo).

### Código Propuesto (Combinado)

```python
def run_setup_wizard():
    # ... Input de Puerto ...

    # 1. Detección de Hosts
    lan_ip = get_lan_ip()
    print(f"ℹ️  IP Local detectada: {lan_ip}")
    custom_domain = input("🌐 Dominio personalizado (opcional): ").strip()
    
    hosts = ["localhost", "127.0.0.1"]
    if lan_ip != "127.0.0.1": hosts.append(lan_ip)
    if custom_domain: hosts.append(custom_domain)

    # 2. Configuración SSL (PKI)
    use_ssl = input("🔒 ¿Habilitar HTTPS con certificados locales? (S/n): ").lower() in ['s', 'sib', 'y', 'yes']
    ssl_cert_path = ""
    ssl_key_path = ""
    
    if use_ssl:
        from app.services.pki_service import PKIService
        print("⚙️  Configurando PKI...")
        PKIService.sync_ca_files()
        # Generar para el primer dominio 'real' (LAN IP o Custom)
        primary_host = custom_domain if custom_domain else lan_ip
        success, key, cert = PKIService.generate_full_cert_pair(primary_host)
        if success:
            print(f"✅ Certificados generados para {primary_host}")
            # Guardar paths para Caddy
            ssl_cert_path = f"data/certs/{primary_host}.pem"
            ssl_key_path = f"data/certs/{primary_host}-key.pem"
        else:
            print("⚠️  Error generando certificados. Se usará HTTP.")
            use_ssl = False

    # 3. Generación de Caddyfile
    if use_ssl:
        generate_caddyfile(hosts, port, ssl_cert_path, ssl_key_path)
        print("✅ Caddyfile generado.")

    # 4. Generación de .env
    allowed_hosts_str = ",".join(hosts)
    # Generar orígenes HTTP y HTTPS si aplica
    origins = [f"http://{h}:{port}" for h in hosts]
    if use_ssl:
        origins += [f"https://{h}" for h in hosts] # Caddy usa puerto 443 default
    
    allowed_origins_str = ",".join(origins)

    # ... Escribir .env ...
```

## 6. Resumen de Acción

1. [ ] **Actualizar `launcher.py`**: Implementar el flujo combinado (Red + PKI + Caddy).
2. [ ] **Helper de Caddy**: Crear función para escribir `Caddyfile`.
3. [ ] **Prueba**: Ejecutar `python launcher.py --config` y verificar que genera `.env` y `Caddyfile` correctamente.

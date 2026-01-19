# Revisión del Plan: Launcher Config

El plan es sólido y mejora significativamente la experiencia de desarrollo (DX) y la configuración inicial. Sin embargo, hay algunos puntos técnicos críticos a considerar para garantizar que no rompa la funcionalidad existente.

## ✅ Puntos Positivos

1. **Detección de IP**: La lógica `get_lan_ip` es correcta y necesaria para evitar problemas de CORS en red local.
2. **Integración PKI**: Aprovechar `PKIService` centraliza la lógica de certificados, lo cual es excelente.
3. **Automatización Caddy**: Generar el `Caddyfile` dinámicamente es mucho más flexible que una plantilla estática.

## ⚠️ Riesgos y Consideraciones

### 1. Permisos de Sistema (Root vs User)

El `launcher.py` generalmente se ejecuta como usuario normal (`kaber420`).

* **Problema**: `PKIService.sync_ca_files()` intenta escribir en `/etc/ssl/umonitor/`, lo cual requiere permisos de `root` (sudo).
* **Impacto**: Si el usuario ejecuta `python launcher.py` sin sudo, esta función fallará y lanzará una excepción o error.
* **Solución Sugerida**:
  * Capturar el error de permisos en `launcher.py` y advertir al usuario.
  * O usar una ruta local para certificados en modo desarrollo (ej: `data/certs/`) y referenciar esa ruta en el `Caddyfile`, evitando escribir en `/etc/ssl` a menos que sea producción/root.

### 2. Puertos Privilegiados (80/443)

El plan menciona usar Caddy en puertos estándar para HTTPS.

* **Problema**: Un proceso instanciado por un usuario normal no puede enlazar puertos por debajo de 1024 (como 80 y 443).
* **Impacto**: Si `launcher.py` intenta ejecutar Caddy directamente (subprocess), fallará al intentar tomar el puerto 443.
* **Solución Sugerida**:
  * Que `launcher.py` solo genere el `Caddyfile`.
  * Para la ejecución, seguir dependiendo del servicio del sistema (`systemctl`) o usar puertos altos (ej: 8443) si se ejecuta en modo usuario/desarrollo.

### 3. Coexistencia con `scripts/install_proxy.sh`

El script bash actual es muy completo (instala dependencias, configura firewall, systemd, etc.).

* **Observación**: El plan mueve la **configuración** a Python, pero la **instalación** de binarios (`apt install caddy`) sigue siendo necesaria.
* **Recomendación**: Mantener `install_proxy.sh` para instalar dependencias, pero modificarlo para que **no** sobrescriba el `Caddyfile` si este ya fue generado por Python, o que Python sea la "fuente de la verdad" para la configuración.

### 4. Dependencia de `.env`

* El plan sobrescribe `ALLOWED_ORIGINS` y `ALLOWED_HOSTS`. Asegurarse de que no elimine otras configuraciones existentes en `.env` (aunque el código propuesto parece regenerar el archivo, vale la pena ser cuidadoso para no borrar claves secretas si ya existen). *Nota: El código actual lee claves existentes antes de reescribir, lo cual es correcto.*

## Conclusión

El plan es viable y se integra bien, **siempre y cuando se maneje el tema de los permisos de escritura de certificados y puertos**.

**Recomendación de implementación**:
Modificar el paso 3 del plan ("Seguridad PKI") para que use rutas relativas (dentro de `./data/certs`) para los certificados cuando no se tiene acceso root, y configurar Caddy para leer de esas rutas. Esto permite que el setup funcione sin sudo.

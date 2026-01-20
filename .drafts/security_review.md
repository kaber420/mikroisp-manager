# Auditoría de Seguridad: µMonitor Pro (umanager6)

Este documento resume la revisión de seguridad realizada a la aplicación y detalla las fortalezas encontradas, así como recomendaciones de mejora.

## 1. Fortalezas de Seguridad Implementadas

### Autenticación y Gestión de Sesiones

- **Framework**: Integración con `fastapi-users` para una gestión estándar y segura de usuarios.
- **Hashing de Contraseñas**: Uso de **Argon2** (vía `passlib`), que es el estándar actual más seguro contra ataques de fuerza bruta y compromisos de base de datos.
- **Cookies Seguras**: Las sesiones web utilizan cookies con atributos `HttpOnly`, `Secure` (en producción) y `SameSite=Strict`, mitigando ataques de XSS y CSRF.
- **JWT**: Soporte para tokens JWT para clientes de API, permitiendo una separación clara entre sesiones de navegador y acceso programático.

### Control de Acceso (RBAC)

- **Roles**: Sistema de roles definido (`admin`, `technician`, `billing`).
- **Middleware de Autorización**: Implementación de `RoleChecker` que asegura que solo usuarios con permisos adecuados accedan a endpoints sensibles.

### Seguridad en la Capa de Datos

- **Inyección SQL**: El uso de **SQLModel/SQLAlchemy** con consultas parametrizadas previene por diseño la inyección SQL.
- **Cifrado en Reposo**: Las credenciales de los dispositivos y las notas sensibles en las zonas se cifran utilizando **Fernet (AES-128-CBC)** antes de guardarse en SQLite.

### Protección en el Navegador (Content Security Policy)

- **CSP con Nonces**: Implementación dinámica de CSP que utiliza un `nonce` único por petición para scripts, bloqueando la ejecución de scripts maliciosos inyectados.
- **Cabeceras Estándar**: Uso de `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff` y `HSTS` para proteger contra Clickjacking, MIME-sniffing y degradación de protocolo.

### Seguridad de Dispositivos (Zero Trust)

- **PKI Interna**: Uso de `mkcert` para generar certificados SSL internos, asegurando que la comunicación entre el servidor y los routers MikroTik viaje por canal **API-SSL (8729)** cifrado.
- **Aprovisionamiento Seguro**: Uso de SSH para la configuración inicial, permitiendo deshabilitar los puertos API inseguros (8728) tras el aprovisionamiento.

### Validación de Entradas y Archivos

- **Validation**: FastAPI valida automáticamente todas las entradas contra esquemas Pydantic.
- **Uploads**: Whitelist estricta de extensiones permitidas para documentos de zona, previniendo la subida de scripts ejecutables (ej. `.php`, `.py`, `.sh`).

---

## 2. Áreas de Mejora y Recomendaciones

### A. Política de CORS más Estricta

- **Hallazgo**: Actualmente se permite cualquier origen mediante regex: `allow_origin_regex=r"https?://.*"`.
- **Riesgo**: Aunque es útil para desarrollo móvil, permite que cualquier sitio web intente realizar peticiones a la API si el usuario está autenticado (mitigado en parte por CSRF, pero sigue siendo un riesgo).
- **Recomendación**: Definir explícitamente los dominios permitidos en la variable de entorno `ALLOWED_ORIGINS`. Para apps móviles, investigar si se pueden usar esquemas específicos (ej. `app://umonitor`) en lugar de permitir todo HTTP/HTTPS.

### B. Uso de `unsafe-eval` en CSP

- **Hallazgo**: La política actual permite `'unsafe-eval'` debido a la dependencia de **Alpine.js**.
- **Riesgo**: Si un atacante logra inyectar código que Alpine procesa, podría ejecutar Javascript arbitrario.
- **Recomendación**: Considerar migrar a la versión "CSP-friendly" de Alpine.js si las funcionalidades utilizadas lo permiten, o asegurar que ninguna entrada de usuario sea procesada directamente por directivas de Alpine (como `x-html`).

### C. Gestión de la Clave de Cifrado (`ENCRYPTION_KEY`)

- **Hallazgo**: El sistema emite un warning si la clave no está presente pero permite continuar.
- **Riesgo**: En producción, si un administrador olvida configurar la clave, las contraseñas se guardarán en texto plano.
- **Recomendación**: Implementar un chequeo en `main.py` que impida el arranque de la aplicación si `APP_ENV=production` y `ENCRYPTION_KEY` es inválida o no está configurada.

### D. Monitoreo y Alertas de Auditoría (sin sentido esta sugerencia,descartada)

- **Hallazgo**: El sistema ya loguea acciones críticas en `audit.log`.
- **Potencial**: No hay un mecanismo de alerta inmediata para acciones fallidas repetidas o accesos no autorizados.
- **Recomendación**: Implementar un sistema de notificaciones (vía Telegram o Email) cuando se detecten fallos críticos en la auditoría o cuando se realicen cambios de configuración en dispositivos de red.

---

## 3. Conclusión

La aplicación presenta un nivel de seguridad **robusto y superior al promedio** para sistemas de gestión de red locales. El enfoque en Zero Trust para los dispositivos MikroTik y el uso de estándares modernos de hashing y CSP demuestran un compromiso serio con la seguridad. Las mejoras sugeridas son refinamientos para alcanzar un nivel de seguridad de grado empresarial.

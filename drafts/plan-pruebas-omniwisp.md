# 🧪 Plan de Pruebas y Validación: Refactorización Dockerizada de OmniWISP Pro

Este plan estratégico establece los **casos de prueba prácticos**, los flujos de ejecución paso a paso y los criterios de aceptación para validar exhaustivamente la nueva infraestructura contenedorizada y la TUI adaptada de OmniWISP Pro.

---

## 🎯 Escenarios Clave de Prueba

El plan se divide en **5 áreas críticas** que cubren desde el aislamiento del backend hasta la visualización en tiempo real del Launcher en el Host:

```
  ┌──────────────────────┐      ┌──────────────────────┐      ┌──────────────────────┐
  │   1. AISLAMIENTO &   │      │   2. RESILIENCIA &   │      │   3. COMPILACIÓN &   │
  │   RED DEL BACKEND    │ ───> │  REINTENTOS DE LA BD │ ───> │    DOCKER COMPOSE    │
  └──────────────────────┘      └──────────────────────┘      └──────────────────────┘
                                                                         │
                                                                         ▼
                                ┌──────────────────────┐      ┌──────────────────────┐
                                │   5. COMPORTAMIENTO  │      │  4. TELEMETRÍA TUI   │
                                │   DEL PORTAL & API   │ <─── │       EN EL HOST     │
                                └──────────────────────┘      └──────────────────────┘
```

---

## 📋 Escenarios Detallados

### Escenario 1: Aislamiento del Demonio Docker en el Backend
*El objetivo es asegurar que el contenedor de backend no requiera `/var/run/docker.sock` y no intente interactuar con el demonio de Docker del host.*

- **Caso de Prueba 1.1:** Ejecución del backend sin socket montado.
  - **Procedimiento:** Verificar que en `docker-compose.yml` el volumen `/var/run/docker.sock` **no** esté mapeado en el servicio `backend`.
  - **Verificación:** Iniciar el stack y consultar la API en `/api/setup/status` o `/api/settings/status`. El backend debe responder con `status: "success"` informando la salud de las conexiones, sin crashear ni arrojar excepciones de `docker.errors.DockerException`.
- **Caso de Prueba 1.2:** Cambio de configuración de infraestructura.
  - **Procedimiento:** Enviar una solicitud POST a `/api/settings/deploy` con variables de base de datos actualizadas.
  - **Verificación:** Confirmar que el backend responde exitosamente con `"status": "success"` indicando que guardó el cambio lógico en `data/services.json`, y constatar que no arrojó errores al omitir la creación física de contenedores.

---

### Escenario 2: Resiliencia del Arranque y Bucle de Reintentos de BD
*El objetivo es validar que el backend soporte retrasos en el arranque de la base de datos (común en entornos orquestados) sin crashearse ni forzar SQLite de inmediato.*

- **Caso de Prueba 2.1:** Retraso en el inicio de PostgreSQL.
  - **Procedimiento:** 
    1. Detener el contenedor de base de datos: `docker compose stop postgres`.
    2. Reiniciar el backend: `docker compose restart backend`.
    3. Leer los logs del backend: `docker compose logs -f backend`.
  - **Resultado Esperado:** El backend debe emitir logs secuenciales del tipo: `🔍 Probing database connection (Attempt 1/10)...`, esperando 5 segundos en cada ciclo sin arrojar un fallo crítico.
    4. Levantar la base de datos a mitad del bucle: `docker compose start postgres`.
  - **Resultado Esperado:** En el siguiente intento, el backend debe conectar exitosamente (`✅ Database connection successful`), crear las tablas de base de datos (`SQLModel.metadata.create_all`) e iniciar el servidor web normalmente sobre PostgreSQL.
- **Caso de Prueba 2.2:** Degradación a SQLite tras agotar reintentos.
  - **Procedimiento:**
    1. Apagar por completo PostgreSQL (`docker compose stop postgres`).
    2. Reiniciar el backend y dejar que transcurran los 10 intentos (50 segundos).
  - **Resultado Esperado:** Al finalizar los 10 intentos fallidos, el backend debe escribir en logs el warning: `⚠️ FALLBACK: Application starting in DEGRADED MODE using SQLite` e iniciar el servidor en puerto 7777 usando `data/db/inventory.sqlite` para asegurar que el WISP no pierda operatividad comercial básica.

---

### Escenario 3: Enrutamiento del Inversa Proxy (Caddy) y Red Privada
*El objetivo es verificar el enrutamiento unificado de Caddy y confirmar que la base de datos y la caché no exponen puertos al host.*

- **Caso de Prueba 3.1:** Aislamiento de Puertos del Host.
  - **Procedimiento:** Intentar conectar a PostgreSQL y Redict directamente desde el host usando las credenciales del `.env` (ej: `psql -h localhost -U umanager -d umanager_db` o `redis-cli`).
  - **Resultado Esperado:** La conexión debe ser rechazada/timeout, debido a que en `docker-compose.yml` los servicios `postgres` y `redict` no exponen puertos al exterior (`ports` removido o acoplado a `127.0.0.1`), protegiendo la base de datos del exterior.
- **Caso de Prueba 3.2:** Enrutamiento de Estáticos y SPA.
  - **Procedimiento:** Navegar en el navegador web del host a `http://localhost/` y recargar páginas SPA de rutas específicas (ej: `http://localhost/setup` o `http://localhost/dashboard`).
  - **Resultado Esperado:** Caddy debe enrutar la primera petición y las subsiguientes de forma transparente a `frontend:3000`, devolviendo `index.html` sin arrojar errores 404 (gracias a `try_files` en el Caddyfile del frontend).
- **Caso de Prueba 3.3:** Enrutamiento de la API y WebSockets.
  - **Procedimiento:** Monitorear el tráfico de red de la consola de desarrollador del navegador al interactuar con el Dashboard en `http://localhost/`.
  - **Resultado Esperado:** Las peticiones XHR a `http://localhost/api/*` y la conexión WebSocket en `ws://localhost/ws/dashboard` deben ser redirigidas de forma instantánea al backend en `backend:7777`, con conexiones WebSocket activas y estables (sin desconexiones por timeout).

---

### Escenario 4: Telemetría e Integración del Launcher TUI en el Host
*El objetivo es certificar que el Launcher interactivo ejecutado en el host puede administrar los contenedores, leer las estadísticas y canalizar el streaming de logs de forma correcta.*

- **Caso de Prueba 4.1:** Inicio guiado y comandos de control.
  - **Procedimiento:** 
    1. Ejecutar el Launcher: `python launcher.py`.
    2. Ir al menú de opciones con la tecla `m` y seleccionar `Restart Web Server`.
  - **Resultado Esperado:** En el host, el Launcher debe ejecutar `docker compose restart backend`. El widget de salud de la terminal debe mostrar temporalmente el estado del backend como `DOWN` o `RESTARTING` y luego cambiar a `ONLINE`.
- **Caso de Prueba 4.2:** Streaming Unificado de Logs.
  - **Procedimiento:** Observar el widget de Logs inferior en la pantalla del Launcher.
  - **Resultado Esperado:** Las líneas de logs de todos los contenedores deben fluir en vivo. La columna de "Origen" (Source) debe identificar claramente de qué contenedor proviene el log (ej. `omniwisp_backend`, `omniwisp_scheduler`, `omniwisp_caddy`) removiendo el pipeline estético ` | ` nativo de compose logs.
- **Caso de Prueba 4.3:** Widget de Monitoreo de Contenedores.
  - **Procedimiento:** Validar la sección de "Database", "Cache", "Api Server" y "Scheduler" en el widget de salud de la terminal.
  - **Resultado Esperado:** El widget debe refrescarse cada 2 segundos. Si apagamos manualmente el planificador en otra terminal (`docker compose stop scheduler`), el widget debe reportar `Scheduler: STOPPED` en color amarillo o rojo de forma reactiva.

---

## 🏅 Criterios de Aceptación del Sistema (CAS)

Se considerará la refactorización como **completada y validada al 100%** si se cumplen las siguientes métricas:

1. **Cero Dependencia de Socket en API:** El backend en ningún escenario requiere acceso a `/var/run/docker.sock` para servir peticiones de API.
2. **Auto-Reinicio Silencioso:** Ante caídas o reinicios del motor de PostgreSQL en el stack, el backend se reconecta de manera autónoma sin requerir el reinicio físico de su contenedor.
3. **Flujo Caddy Unificado:** Todas las peticiones HTTP fluyen por el puerto 80 administradas por Caddy, sin necesidad de exponer puertos internos (3000, 7777).
4. **Compatibilidad TUI Intacta:** El administrador del WISP puede utilizar `launcher.py` en el host para encender, apagar y monitorizar la suite de la misma manera visual en que lo hacía con la infraestructura nativa.

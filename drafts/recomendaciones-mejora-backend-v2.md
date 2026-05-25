# Recomendaciones y Estrategias Avanzadas de Mejora para el Backend (OmniWISP)

Este documento detalla sugerencias y tácticas arquitectónicas concretas surgidas a partir de una auditoría exhaustiva del backend de **OmniWISP** (FastAPI, SQLModel, Uvicorn, background workers y soporte para base de datos híbrida/Redict). 

El objetivo es maximizar la resiliencia en redes locales complejas, optimizar el rendimiento y la escalabilidad, y garantizar una experiencia premium robusta.

---

## 🗺️ Índice de Recomendaciones
1. [⚙️ Unificación de la Capa de Base de Datos (Async vs. Sync)](#1-unificación-de-la-capa-de-base-de-datos-async-vs-sync)
2. [⚡ Envío Asíncrono y Concurrente de Alertas de Telegram](#2-envío-asíncrono-y-concurrente-de-alertas-de-telegram)
3. [🔌 Pool de Conexiones Persistentes para MikroTik RouterOS (Connection Reuse)](#3-pool-de-conexiones-persistentes-para-mikrotik-routeros-connection-reuse)
4. [🗄️ Optimización de Sesiones en Tareas de Monitoreo](#4-optimización-de-sesiones-en-tareas-de-monitoreo)
5. [🛡️ Robustez ante Fallos de Base de Datos en Tareas de Monitoreo](#5-robustez-ante-fallos-de-base-de-datos-en-tareas-de-monitoreo)
6. [🛑 Limitación de Frecuencia (Rate Limiting) Centralizada y Distribuida](#6-limitación-de-frecuencia-rate-limiting-centralizada-y-distribuida)
7. [📈 Backoff Exponencial con Jitter para Resiliencia de Base de Datos](#7-backoff-exponencial-con-jitter-para-resiliencia-de-base-de-datos)
8. [📊 Configuración Centralizada y Estructurada de Logging](#8-configuración-centralizada-y-estructurada-de-logging)

---

## ⚙️ 1. Unificación de la Capa de Base de Datos (Async vs. Sync)

### 📌 Situación Detectada
Actualmente el backend mantiene dos motores de SQLAlchemy y pools independientes en [engine.py](file:///home/kaberromero/Documentos/proyectos/OmniWISP/app/db/engine.py) y [engine_sync.py](file:///home/kaberromero/Documentos/proyectos/OmniWISP/app/db/engine_sync.py).
* `engine` (`aiosqlite` / `asyncpg`) -> Maneja FastAPI Users y endpoints puramente asíncronos.
* `sync_engine` (`sqlite` / `psycopg`) -> Maneja dependencias síncronas en `ClientService`, `ZoneService`, `PaymentService`, etc.

### 💥 Por qué es un problema
1. **Bloqueos en SQLite:** Al utilizar SQLite localmente en desarrollo o modo degradado, tener dos pools escribiendo simultáneamente al mismo archivo incrementa la probabilidad de excepciones `database is locked`, incluso en modo `WAL`.
2. **Consumo de Conexiones en PostgreSQL:** Duplica la cantidad de conexiones persistentes (idle) necesarias contra el servidor PostgreSQL.
3. **Complejidad del Código:** Fuerza a los desarrolladores a elegir entre flujos síncronos y asíncronos de forma ad-hoc.

### 🛠️ Recomendación
Migrar de forma progresiva todos los endpoints y servicios de negocio síncronos a asíncronos utilizando la sesión asíncrona única (`AsyncSession`) provista por `Depends(get_session)`. Esto reduce la complejidad a un único motor asíncrono robusto.

---

## ⚡ 2. Envío Asíncrono y Concurrente de Alertas de Telegram

### 📌 Situación Detectada
En [alerter.py](file:///home/kaberromero/Documentos/proyectos/OmniWISP/app/utils/alerter.py#L65-L74), la función `send_telegram_alert` itera a través de los administradores y realiza peticiones HTTP de forma síncrona y secuencial:

```python
# app/utils/alerter.py (Código Actual)
for chat_id in chat_ids:
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    try:
        response = httpx.post(api_url, json=payload, timeout=10)
        response.raise_for_status()
    ...
```

### 💥 Por qué es un problema
Si hay 10 administradores suscritos y la API de Telegram experimenta lentitud (ej. debido a un timeout de red o rate-limiting), cada mensaje puede tardar hasta 10 segundos. En el peor escenario, **esta llamada bloqueará secuencialmente el hilo durante 100 segundos**. Aunque se ejecute con `asyncio.to_thread` desde los schedulers, esto consumirá hilos valiosos del pool global de Python innecesariamente.

### 🛠️ Recomendación
Refactorizar la función a una versión puramente asíncrona utilizando `httpx.AsyncClient` y concurrencia con `asyncio.gather` para enviar los mensajes a todos los administradores de forma simultánea:

```python
# app/utils/alerter.py (Propuesta Asíncrona)
import asyncio
import httpx

async def send_telegram_alert_async(message: str, alert_type: str = "system"):
    # ... obtener chat_ids de forma asíncrona ...
    if not chat_ids:
        return

    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    async with httpx.AsyncClient() as client:
        # Generar tareas asíncronas concurrentes
        tasks = [
            client.post(
                api_url, 
                json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}, 
                timeout=5
            )
            for chat_id in chat_ids
        ]
        
        # Ejecutar todas las peticiones simultáneamente sin bloquear el hilo
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for chat_id, result in zip(chat_ids, results):
            if isinstance(result, Exception):
                logger.error(f"Error enviando alerta a {chat_id}: {result}")
```

---

## 🔌 3. Pool de Conexiones Persistentes para MikroTik RouterOS (Connection Reuse)

### 📌 Situación Detectada
En [monitor_service.py](file:///home/kaberromero/Documentos/proyectos/OmniWISP/app/services/monitoring/monitor_service.py#L133-L170), cada ciclo de chequeo a routers MikroTik realiza una llamada en segundo plano a `router_connector.fetch_router_stats()`. Este abre una conexión socket TCP/API, realiza la autenticación, hace la consulta y destruye la conexión inmediatamente.

### 💥 Por qué es un problema
Para redes de WISP que tengan decenas de APs o Routers, abrir y cerrar conexiones sockets cada 5 segundos:
1. **Consumo de CPU y Memoria:** Mayor carga de CPU tanto en el backend de OmniWISP como en los propios equipos MikroTik debido a la constante negociación de handshakes y autenticaciones SSL/TCP.
2. **Saturación del Visor de Eventos:** Llena el log de auditoría del RouterOS con miles de registros de login/logout innecesarios cada minuto.

### 🛠️ Recomendación
Implementar una capa de **Registro de Conexiones Activas (Keep-Alive Pool)**. En lugar de conectar ad-hoc, el scheduler solicita una conexión existente al registro por IP de dispositivo. Si la conexión está viva, se reutiliza. Si arroja un error o está desconectada, se descarta, se abre una nueva y se actualiza el registro.

---

## 🗄️ 4. Optimización de Sesiones en Tareas de Monitoreo

### 📌 Situación Detectada
En `MonitorService.get_active_devices_with_session`, se abren y cierran dos bloques de `AsyncSession` de forma consecutiva e innecesaria:

```python
# app/services/monitoring/monitor_service.py (Código Actual)
async def get_active_devices_with_session(self, session_maker):
    async with session_maker() as session:
        aps = await get_enabled_aps_for_monitor(session)

    async with session_maker() as session:
        routers = await get_enabled_routers_from_db(session)
```

### 🛠️ Recomendación
Reutilizar una **única instancia de sesión** para ambos métodos. Esto reduce el overhead de inicialización y negociación de conexiones a la base de datos a la mitad:

```python
# app/services/monitoring/monitor_service.py (Propuesta)
async def get_active_devices_with_session(self, session_maker):
    async with session_maker() as session:
        aps = await get_enabled_aps_for_monitor(session)
        routers = await get_enabled_routers_from_db(session)
        
    return {
        "aps": aps,
        "routers": routers,
    }
```

---

## 🛡️ 5. Robustez ante Fallos de Base de Datos en Tareas de Monitoreo

### 📌 Situación Detectada
Tanto en `check_ap` como en `check_router`, si ocurre un error inesperado al comprobar el dispositivo remoto, el manejador de excepciones ejecuta `_handle_offline_ap` o `update_router_status` para actualizar la base de datos (`update_ap_status`, `add_event_log`):

```python
# app/services/monitoring/monitor_service.py (Manejador actual)
except Exception as e:
    logger.error(f"Error procesando AP {host}: {e}")
    prev_stat = await get_ap_status(session, host) # <-- Puede fallar si falló la conexión a la DB
    await self._handle_offline_ap(session, host, prev_stat) # <-- Escritura DB
```

### 💥 Por qué es un problema
Si la excepción original `e` se produjo por una desconexión o bloqueo temporal de la propia base de datos (e.g. timeout de Postgres o bloqueo de SQLite), intentar hacer nuevas lecturas y escrituras dentro del bloque `except` arrojará un error secundario de base de datos. Esto oculta la excepción de red original en los logs e impide la correcta gestión del flujo.

### 🛠️ Recomendación
1. **Validar Estado de Transacción:** Verificar que la sesión de la base de datos siga activa (`session.is_active`) antes de intentar escrituras secundarias de fallback.
2. **Segundo Bloque de Seguridad:** Encapsular las llamadas del `_handle_offline_ap` en un bloque `try-except` secundario para garantizar que los logs locales de error se impriman de todas formas incluso si la base de datos colapsa por completo.

---

## 🛑 6. Limitación de Frecuencia (Rate Limiting) Centralizada y Distribuida

### 📌 Situación Detectada
El rate-limiting para inicios de sesión en [main.py](file:///home/kaberromero/Documentos/proyectos/OmniWISP/app/main.py#L326-L368) almacena los intentos de peticiones en un diccionario nativo de Python en memoria (`_rate_limit_store`).

### 💥 Por qué es un problema
Si el servidor se despliega en producción con múltiples workers de Uvicorn (`UVICORN_WORKERS` > 1) o en contenedores Docker independientes, la memoria no se comparte. Un atacante podría saltarse el límite distribuyendo sus peticiones entre los distintos workers, ya que cada uno tiene su propio diccionario independiente en memoria.

### 🛠️ Recomendación
Modificar el middleware para que consuma del gestor de caché global de la aplicación (`cache_manager`). Si `settings.CACHE_BACKEND == "redict"`, utilizar el almacén distribuido Redict/Redis para llevar el control de peticiones de manera global y sincronizada entre todos los procesos y servidores, manteniendo el diccionario en memoria únicamente como fallback.

---

## 📈 7. Backoff Exponencial con Jitter para Resiliencia de Base de Datos

### 📌 Situación Detectada
En [resilience.py](file:///home/kaberromero/Documentos/proyectos/OmniWISP/app/db/resilience.py#L27-L45), la función `probe_database_connection` comprueba la salud de la base de datos principal realizando intentos consecutivos con una espera fija de `5` segundos.

### 💥 Por qué es un problema
1. **Thundering Herd:** Si el servidor Postgres está levantándose tras un apagón, realizar conexiones con un intervalo fijo puede estresarlo y retrasar su recuperación.
2. **Arranque Lento:** Si la base de datos se recupera 1 segundo después del primer intento fallido, el sistema de todas formas dormirá 5 segundos inútiles antes de volver a intentar conectar.

### 🛠️ Recomendación
Implementar una estrategia de **Backoff Exponencial con Jitter (Ruido aleatorio)**. El primer reintento ocurre casi inmediatamente (ej. 1s), incrementándose exponencialmente (2s, 4s, 8s...) e introduciendo una pequeña variación aleatoria para distribuir la carga:

```python
# app/db/resilience.py (Ejemplo de Backoff Exponencial)
import random
import time

# En el bucle de intentos:
attempt_sleep = min(15, (2 ** attempt) + random.uniform(0.1, 1.0))
time.sleep(attempt_sleep)
```

---

## 📊 8. Configuración Centralizada y Estructurada de Logging

### 📌 Situación Detectada
La gestión de logs del backend se encuentra dividida entre llamadas a `print()`, capturas de logger locales con `logging.getLogger(__name__)`, y logs formateados de forma directa.

### 🛠️ Recomendación
Centralizar el comportamiento mediante una función `setup_logging()` cargada en el inicio de `main.py` empleando `logging.config.dictConfig`. 
* **Ventajas:** Permite estandarizar los formatos de salida, rotar archivos de logs locales automáticamente, diferenciar niveles (DEBUG, INFO, ERROR) con colores en desarrollo y generar estructuraciones en JSON para producción si se desea integrar con agregadores de logs externos.
* **Correlación de peticiones:** Se aconseja añadir un middleware que genere un UUID (`X-Request-ID`) por petición HTTP/WebSocket y asociarlo al contexto del hilo asíncrono para rastrear de forma exacta la traza de logs de una petición a través de múltiples servicios independientes.

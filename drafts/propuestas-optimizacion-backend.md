# Propuestas de Optimización y Resiliencia del Backend (FastAPI + SQLModel)

Este documento recopila sugerencias y estrategias arquitectónicas avanzadas para mejorar el rendimiento, estabilidad y resiliencia del backend de **OmniWISP**.

---

## 🗺️ Índice de Contenidos
1. [⚠️ El problema del Paralelismo en SQLAlchemy (Concurrencia en `AsyncSession`)](#1-el-problema-del-paralelismo-en-sqlalchemy-concurrencia-en-asyncsession)
2. [⚡ Pre-cálculo y Caché en Redict/Redis para el Dashboard](#2-pre-cálculo-y-caché-en-redictredis-para-el-dashboard)
3. [🛡️ Resiliencia en Monitoreo de Routers MikroTik (Timeouts y Circuit Breakers)](#3-resiliencia-en-monitoreo-de-routers-mikrotik-timeouts-y-circuit-breakers)
4. [🗄️ Carga Eficiente de Relaciones en SQLAlchemy (Evitar N+1)](#4-carga-eficiente-de-relaciones-en-sqlalchemy-evitar-n1)
5. [⚙️ Conmutación por Fallo Automática a Base de Datos de Respaldo (SQLite)](#5-conmutación-por-fallo-automática-a-base-de-datos-de-respaldo-sqlite)

---

## ⚠️ 1. El problema del Paralelismo en SQLAlchemy (Concurrencia en `AsyncSession`)

### 📌 Situación Detectada
En el plan técnico inicial para consolidar las consultas del Dashboard en un único endpoint (`/api/stats/dashboard-summary`), se propuso usar `asyncio.gather` compartiendo una única instancia de `session: AsyncSession` de SQLAlchemy:

```python
# CÓDIGO CON BUG DE CONCURRENCIA
results = await asyncio.gather(
    get_cpe_total_count(session, current_user),
    get_switch_total_count(session, current_user),
    get_ticket_stats(session, current_user),
    # ... otras consultas simultáneas usando la misma sesión
)
```

### 💥 Por qué falla
La sesión asíncrona de SQLAlchemy (`AsyncSession`) **no es segura para el uso concurrente**. Está diseñada para ejecutar una consulta a la vez de forma estrictamente secuencial dentro de una misma corrutina. 

Si múltiples tareas concurrentes en `asyncio.gather` intentan ejecutar queries en la misma sesión al mismo tiempo, el motor lanzará una excepción catastrófica:
> `sqlalchemy.exc.IllegalStateChangeError: Method 'execute()' can't be called when another method is running in this session.`

---

### 🛠️ Soluciones Propuestas

#### Opción A: Ejecución Secuencial (Recomendada)
Para consultas simples de recuento y tops indexados, la ejecución secuencial en una base de datos local o en red es extremadamente rápida (menos de 30ms en total) y es 100% segura para la sesión de DB.

```python
# app/api/stats/main.py
@router.get("/stats/dashboard-summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
):
    try:
        # Consultas de recuento secuenciales (muy veloces)
        cpes = await get_cpe_total_count(session, current_user)
        switches = await get_switch_total_count(session, current_user)
        tickets = await get_ticket_stats(session, current_user)
        routers = await get_router_total_count(session, current_user)
        aps = await get_ap_total_count(session, current_user)

        # Consultas de Tops secuenciales
        top_cpes = await get_top_cpes_by_weak_signal(limit=5, session=session, current_user=current_user)
        top_aps = await get_top_aps_by_airtime(limit=5, session=session, current_user=current_user)
        top_routers = await get_top_routers_by_consumption(limit=5, session=session, current_user=current_user)
        top_offline = await get_top_offline_devices(limit=5, session=session, current_user=current_user)
        routers_list = await get_all_routers_service(session)

        # ... resto del procesamiento de tickets y retorno
```

#### Opción B: Paralelismo Real con Sesiones Independientes
Si de verdad se requiere paralelismo puro (ej. base de datos remota con latencia de red), se debe generar una sesión de base de datos independiente por cada tarea de `asyncio.gather`.

```python
from app.db.engine import get_session # Generador de sesiones

async def run_in_dedicated_session(func, *args, **kwargs):
    """Ejecuta una función de consulta abriendo y cerrando una sesión dedicada."""
    async for session in get_session():
        return await func(session, *args, **kwargs)

# Uso en gather:
results = await asyncio.gather(
    run_in_dedicated_session(get_cpe_total_count, current_user),
    run_in_dedicated_session(get_switch_total_count, current_user),
    run_in_dedicated_session(get_ticket_stats, current_user),
    # ...
)
```
*Nota: Esta opción requiere más conexiones abiertas en el pool de la base de datos simultáneamente.*

---

## ⚡ 2. Pre-cálculo y Caché en Redict/Redis para el Dashboard

### 📌 Situación Actual
El Dashboard es la pantalla principal que los técnicos y administradores del WISP cargan y refrescan con mayor frecuencia. Incluso optimizado de forma secuencial, consultar 10 tablas distintas en base de datos en cada petición HTTP incrementa la latencia y la carga global de la base de datos de manera innecesaria.

### 🛠️ Solución Propuesta: Resumen Pre-calculado (Push-Caching)
Dado que OmniWISP cuenta con tareas en segundo plano programadas (`MonitorScheduler`, `APMonitorScheduler`, etc.), podemos añadir un **Job periódico de pre-cálculo del Dashboard** en segundo plano (ejemplo, cada 30 segundos).

1. **Job en segundo plano (`app/services/monitoring/dashboard_scheduler.py`):**
```python
import asyncio
import logging
from app.db.engine import get_session
from app.utils.cache import cache_manager

logger = logging.getLogger(__name__)

async def update_dashboard_cache_job():
    """Genera de forma periódica el payload estructurado y lo guarda en Redict/Memoria."""
    while True:
        try:
            async for session in get_session():
                # 1. Ejecutar recuentos y tops secuencialmente
                # 2. Construir la estructura completa del JSON
                payload = {
                    "stats": { ... },
                    "tops": { ... },
                    "recent_tickets": [ ... ],
                    "routers_list": [ ... ]
                }
                
                # 3. Guardar en caché con TTL de 60 segundos
                stats_cache = cache_manager.get_store("dashboard_stats")
                stats_cache.set("summary", payload)
                logger.debug("✅ Caché del resumen del Dashboard actualizada")
                break
        except Exception as e:
            logger.error(f"Error actualizando caché del dashboard: {e}")
        
        await asyncio.sleep(30)  # Frecuencia de actualización
```

2. **Endpoint instantáneo (`app/api/stats/main.py`):**
```python
@router.get("/stats/dashboard-summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
):
    # Intentar obtener de la caché primero
    stats_cache = cache_manager.get_store("dashboard_stats")
    cached_summary = stats_cache.get("summary")
    
    if cached_summary:
        return cached_summary
        
    # Fallback en caso de que la caché esté vacía (ej. al arrancar el servidor)
    # Ejecuta el cálculo tradicional desde la DB
    return await compute_dashboard_summary_from_db(session, current_user)
```

**Resultado:** Latencia de red del Dashboard reducida de ~100-300ms a **< 5ms**. Carga en la base de datos de producción reducida a prácticamente cero.

---

## 🛡️ 3. Resiliencia en Monitoreo de Routers MikroTik (Timeouts y Circuit Breakers)

### 📌 Situación Actual
El `MonitorScheduler` usa `asyncio.to_thread` para paralelizar las llamadas síncronas a routers MikroTik utilizando `routeros_api`. Esto es una excelente práctica para no congelar el loop de FastAPI. Sin embargo, no protege al backend si un router remoto experimenta fallos de conectividad severos.

Si un router remoto está desconectado pero su socket no detecta el corte de inmediato, el hilo (`thread`) quedará esperando por 30+ segundos. Si tienes 10 routers en este estado, el pool de hilos de la aplicación se saturará rápidamente con tareas colgadas, enlenteciendo todo el backend.

### 🛠️ Soluciones Recomendadas

1. **Configurar un Timeout Bajo a nivel de Socket:**
   Asegurar que el adaptador de MikroTik use un timeout estricto (ej. 3 segundos) al intentar abrir conexiones y realizar consultas.

2. **Implementar Circuit Breakers (Disyuntores) en Monitoreo:**
   Si un router falla en responder consecutivamente:
   - Marcar el router en estado `offline` en base de datos.
   - Guardar una marca de tiempo `backoff_until` en memoria.
   - En los siguientes ciclos de *polling*, omitir la conexión a ese router y responder directamente desde la caché "Offline" para no desperdiciar recursos ni tiempo de CPU intentando reconexiones fallidas continuamente.

---

## 🗄️ 4. Carga Eficiente de Relaciones en SQLAlchemy (Evitar N+1)

### 📌 Situación Detectada
En `/stats/dashboard-summary`, se obtienen los tickets recientes y luego se cargan los nombres de los clientes y técnicos asignados haciendo consultas por separado en la base de datos:

```python
# Consultas secuenciales adicionales por lotes de IDs (N+1 parcial)
client_ids = {t.client_id for t in tickets}
tech_ids = {t.assigned_tech_id for t in tickets if t.assigned_tech_id}

clients = {}
if client_ids:
    c_res = await session.exec(select(Client).where(Client.id.in_(client_ids)))
    # ...
```

### 🛠️ Solución Recomendada: `joinedload` (Eager Loading)
Utilizar la carga activa (`joinedload` o `selectinload`) de SQLAlchemy. Esto le indica a SQLAlchemy que realice un `JOIN` SQL automático o una subconsulta optimizada en un único viaje a la base de datos:

```python
from sqlalchemy.orm import joinedload, selectinload

# Consulta optimizada en un único viaje
ticket_stmt = (
    select(Ticket)
    .options(
        joinedload(Ticket.client),          # Carga el cliente asociado en el mismo query
        joinedload(Ticket.assigned_tech),   # Carga el técnico asignado en el mismo query
        selectinload(Ticket.messages)       # Carga la colección de mensajes en 1 query óptimo
    )
    .order_by(desc(Ticket.updated_at))
    .limit(10)
)
ticket_result = await session.exec(ticket_stmt)
tickets = ticket_result.all()

# Acceso inmediato sin hacer consultas manuales:
# ticket.client.name ya está precargado en memoria de forma ultra rápida
```

---

## ⚙️ 5. Conmutación por Fallo Automática a Base de Datos de Respaldo (SQLite)

### 📌 Situación
OmniWISP está diseñado para WISPs locales que operan frecuentemente en entornos de redes físicas complejas, servidores locales expuestos a cortes de energía o variaciones de recursos. Si PostgreSQL no arranca o falla por mantenimiento, el panel de administración completo se desploma.

### 🛠️ Solución Propuesta: Resiliencia de Base de Datos Híbrida
Ya que OmniWISP cuenta con la variable global `DEGRADED_MODE` y un sistema de fallback a SQLite en `data/db/inventory.sqlite`, podemos automatizar la conmutación por error en el arranque (`bootstrap_system`):

```python
# app/core/bootstrap.py (Representación conceptual)
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

def bootstrap_system():
    try:
        # 1. Intentar conectar a PostgreSQL si está configurado
        if settings.DATABASE_URL.startswith("postgresql"):
            logger.info("Prueba de conexión con PostgreSQL...")
            test_db_connection() # Función de verificación rápida
            logger.info("✅ Base de datos principal (PostgreSQL) conectada.")
            
    except ConnectionError as e:
        logger.error("🚨 No se pudo conectar a PostgreSQL en el arranque!")
        logger.warning("⚠️ Conmutando automáticamente a base de datos de respaldo SQLite...")
        
        # Activar banderas de emergencia
        settings.DEGRADED_MODE = True
        settings.DATABASE_URL = settings.SQLITE_DATABASE_URL # Conmutar URLs
        settings.DATABASE_URL_SYNC = settings.SQLITE_DATABASE_URL_SYNC
        
        # Notificar en la interfaz de terminal (TUI) y logs
        alert_system_of_degradation(e)
```

**Beneficios:**
- **Operación Continua:** El WISP puede seguir gestionando la red, visualizando históricos guardados localmente y realizando aprovisionamientos básicos en los routers MikroTik aunque falle el servidor PostgreSQL principal.
- **Transparencia:** La interfaz TUI y el bot de Telegram informan automáticamente el estado en que se encuentra el backend.

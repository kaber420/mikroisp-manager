# Reporte de Deuda Técnica y Oportunidades de Mejora

Este documento sirve como bitácora para registrar áreas del código que requieren refactorización, limpieza o estandarización.

## 1. Conectores de Dispositivos (Device Connectors)

**Archivos Afectados:**

- `app/services/router_connector.py`
- `app/services/ap_connector.py`
- `app/services/switch_connector.py`

**Problema Detectado:**
Violación del principio DRY (Don't Repeat Yourself). Los tres archivos implementan lógica casi idéntica para:

1. **Gestión de Credenciales:** Todos mantienen un diccionario `self._credentials` y métodos `subscribe`/`unsubscribe` muy similares.
2. **Manejo de Errores:** Todos tienen bloques `try/except` repetitivos para capturar errores de conexión.
3. **Logging**: Patrones de logs idénticos ("Initialized", "Subscribed to...", "Error fetching...").
4. **Patrón Singleton:** Todos instancia un objeto global al final del archivo.

**Nivel de Complejidad Actual:** Alto (para mantenimiento). Si quieres cambiar cómo se manejan los errores de conexión, tienes que editar 3 archivos.

**Propuesta de Solución (POO):**
Crear una clase base abstracta `BaseDeviceConnector` que maneje la "fontanería" común.

```python
class BaseDeviceConnector:
    def __init__(self):
        self._credentials = {}
        self.logger = logging.getLogger(self.__class__.__name__)

    async def subscribe(self, host, creds):
        self._credentials[host] = creds
        self.logger.info(f"Subscribed to {host}")
        # Hook para lógica específica
        await self._on_subscribe(host, creds)
        
    async def unsubscribe(self, host):
        if host in self._credentials:
           # ... lógica común ...
```

## 2. Estandarización de Respuestas de API

**Observación:**

- `router_connector.py` devuelve `{"cpu_load": ...}`
- `ap_connector.py` devuelve `{"cpu_load": ..., "extra": {...}}`
- `switch_connector.py` devuelve `{"cpu_load": ...}` pero usa una lógica de obtención diferente.

Existe riesgo de que el frontend tenga que adivinar qué formato de datos recibirá. Sería ideal unificar la estructura del diccionario de retorno (o usar `TypedDict` / Pydantic models).

## 3. Manejo de "Magic Strings"

Se observan cadenas repetidas como `"username"`, `"password"`, `"port"`, `"mikrotik"`.
**Acción Sugerida:** Mover estas constantes a un archivo de configuración o enumeraciones (`DeviceType.MIKROTIK`).

---
> *Nota para el Desarrollador: No intentes arreglar todo esto hoy. Este documento es tu mapa para cuando tengas tiempo y energía. Empieza por lo que más te duela.*

## 4. Duplicación en Schedulers de Monitoreo

**Archivos Afectados:**

- `app/services/monitor_scheduler.py` (para Routers)
- `app/services/ap_monitor_scheduler.py` (para APs)
- `app/services/switch_monitor_scheduler.py` (probablemente para Switches)

**Problema Detectado:**
Violación flagrante del principio DRY. Las clases `MonitorScheduler` y `APMonitorScheduler` son casi idénticas en un 90%. Ambas implementan:

- Gestión de suscripciones con `ref_count`.
- Lógica de "Backoff exponencial" en caso de error.
- Tareas de limpieza (`_cleanup_task`) con timeouts configurables.
- Loop principal de `asyncio` (`run`) con lógica de polling.

**Riesgo:**
Cualquier mejora en la robustez del monitoreo (ej. mejor manejo de timeouts, logging estructurado) debe copiarse manualmente en 3 archivos. Es muy fácil introducir bugs sutiles si se actualiza uno y se olvida el otro.

**Propuesta de Solución:**
Crear una clase genérica `DeviceMonitorScheduler` (posiblemente usando Generics de Python) que acepte:

- Un `connector` (interfaz común).
- Un `db_handler` o callback para actualizar estado.
- Configuración de intervalos.

## 5. Lógica de Negocio en Vistas (Views)

**Archivos Afectados:**

- `app/views.py`

**Problema Detectado:**
El archivo de vistas contiene lógica de negocio que debería residir en la capa de servicios.

- *Ejemplo:* En `read_payment_receipt`, hay lógica explícita para calcular fechas de inicio y fin de facturación (`billing_day`, `relativedelta`, etc.) y manejo de excepciones.

**Acción Sugerida:**
Mover esta lógica a `BillingService` o `PaymentService`. Las vistas solo deberían orquestar la llamada al servicio y devolver el template, sin saber cómo se calcula un ciclo de facturación.

## 6. Configuración Dispersa y Hardcoded

**Observación:**
Se detectan llamadas a `os.getenv` dispersas por varios archivos (ej. `monitor_scheduler.py`), a menudo con valores por defecto "mágicos" (`30`, `300`).
No existe un `app/core/config.py` centralizado (o similar) que valide y tipifique la configuración al inicio.

**Acción Sugerida:**
Implementar `pydantic-settings` para centralizar toda la configuración (variables de entorno) en una sola clase singleton `Settings`. Esto facilita el testing y evita errores por typos en nombres de variables de entorno.

estado actual :Estado de Deuda Técnica
Basado en el análisis del código actual vs
technical_debt.md
:

### ✅ Ya Implementado

1. **Refactorización de Connectors (DRY)**
   - **Estado:** Completado. `BaseDeviceConnector` implementado y usado por todos los conectores.

2. **Manejo de "Magic Strings" (Fase 1)**
   - **Estado:** Parcialmente completado.
   - **Detalle:** Se creó `app/core/constants.py` con Enums básicos (`CredentialKeys`, `DeviceVendor`).

### 🚧 Pendiente (Lo que falta)

1. **Manejo de "Magic Strings" (Fase 2)**
   - **Estado:** Pendiente.
   - **Referencia:** `/.scratch/refactor_magic_strings_phase2.md`
   - **Acción:** Implementar uso de Enums `DeviceStatus`, `DeviceRole`, `CPEStatus` en toda la aplicación (Schedulers, Adapters, DB).

2. **Duplicación en Monitor Schedulers**
   - **Estado:** Pendiente.
   - **Acción:** Crear clase genérica `DeviceMonitorScheduler`.

3. **Estandarización de Respuestas de API**
   - **Estado:** Pendiente.
   - **Acción:** Implementar `TypedDict` o Pydantic models.

4. **Lógica de Negocio en Vistas**
   - **Estado:** Pendiente.
   - **Acción:** Mover lógica a Servicios.

5. **Configuración Centralizada**
   - **Estado:** Pendiente.
   - **Acción:** Implementar `pydantic-settings`.

## 7. Refactorización de Arquitectura de Adaptadores (OOP/Managers)

**Archivos Afectados:**

- `app/utils/device_clients/adapters/mikrotik_router.py`
- Nuevos archivos en `app/utils/device_clients/mikrotik/managers/`

**Problema Detectado:**
El adaptador `MikrotikRouterAdapter` actúa como un "God Object", mezclando lógica de colas, firewall, sistema, e interfaces en una sola clase larga. Esto dificulta el mantenimiento y la extensibilidad.

**Propuesta de Solución (Composición):**
Implementar un diseño basado en Managers temáticos (FirewallManager, QueueManager, SystemManager) que sean instanciados dentro del adaptador principal.

- **Referencia:** `/.drafts/plan_refactorizacion_oop.md`
- **Estado:** Pendiente.

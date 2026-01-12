# Plan de Continuación: Eliminación de Magic Strings (Fase 2)

Este documento extiende el trabajo realizado en la Fase 1 (vendors y credenciales) para cubrir el resto de magic strings identificadas.

## Compatibilidad
- ✅ **No rompe funcionalidad**: Los enums heredan de `str`, por lo que son compatibles con comparaciones existentes y datos en DB.
- ✅ **Ortogonal al refactor OOP**: Estos cambios son de valores, no de estructura.

---

## Proposed Changes

### Core
#### [MODIFY] app/core/constants.py
Agregar las siguientes enumeraciones:

```python
@unique
class DeviceStatus(str, Enum):
    """Estados de conexión de dispositivos."""
    ONLINE = "online"
    OFFLINE = "offline"

@unique
class DeviceRole(str, Enum):
    """Roles/tipos de dispositivos."""
    ACCESS_POINT = "access_point"
    ROUTER = "router"
    SWITCH = "switch"

@unique
class CPEStatus(str, Enum):
    """Estados de CPEs."""
    ACTIVE = "active"
    OFFLINE = "offline"
    DISABLED = "disabled"

@unique
class EventType(str, Enum):
    """Tipos de eventos para logs."""
    SUCCESS = "success"
    DANGER = "danger"
    WARNING = "warning"
    INFO = "info"
```

---

### Schedulers (DeviceStatus)
Archivos que usan `"online"` / `"offline"` repetidamente:

#### [MODIFY] app/services/monitor_scheduler.py
#### [MODIFY] app/services/ap_monitor_scheduler.py
#### [MODIFY] app/services/switch_monitor_scheduler.py
#### [MODIFY] app/services/monitor_service.py

Ejemplo de cambio:
```python
# Antes:
await self._update_db_status(host, "online", result)

# Después:
await self._update_db_status(host, DeviceStatus.ONLINE, result)
```

---

### Adaptadores (DeviceRole)
Archivos que usan `"access_point"`, `"router"`, `"switch"`:

#### [MODIFY] app/utils/device_clients/adapters/mikrotik_router.py
#### [MODIFY] app/utils/device_clients/adapters/mikrotik_wireless.py
#### [MODIFY] app/utils/device_clients/adapters/ubiquiti_airmax.py
#### [MODIFY] app/utils/device_clients/adapters/mikrotik_switch.py

Ejemplo de cambio:
```python
# Antes:
return DeviceStatus(host=self.host, vendor=self.vendor, role="router", ...)

# Después:
return DeviceStatus(host=self.host, vendor=self.vendor, role=DeviceRole.ROUTER, ...)
```

---

### Database Layer (DeviceStatus)
Archivos que comparan estados:

#### [MODIFY] app/db/aps_db.py
#### [MODIFY] app/db/router_db.py
#### [MODIFY] app/db/switches_db.py

Ejemplo de cambio:
```python
# Antes:
if status == "online" and data:

# Después:
if status == DeviceStatus.ONLINE and data:
```

---

### CPE Service (CPEStatus)
#### [MODIFY] app/services/cpe_service.py
#### [MODIFY] app/db/stats_db.py

---

### Event Logging (EventType)
#### [MODIFY] app/db/logs_db.py (si tiene tipos hardcoded)
#### [MODIFY] app/services/monitor_service.py

---

## Verification Plan

### Automated
- Verificar que todos los imports funcionan.
- Verificar que la aplicación arranca sin errores.

### Manual
- Probar que un AP se marca como online/offline correctamente.
- Probar que los logs de eventos funcionan.

---

## Prioridad Sugerida
1. **DeviceStatus** (online/offline) - Mayor impacto, ~50 ocurrencias
2. **DeviceRole** - Media prioridad, ~15 ocurrencias
3. **CPEStatus** - Baja prioridad, aislado a CPE service
4. **EventType** - Baja prioridad, aislado a logs

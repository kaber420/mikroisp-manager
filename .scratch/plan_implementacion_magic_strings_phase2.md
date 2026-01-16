# Plan de Implementación: Refactorización Magic Strings (Fase 2)

## Objetivo

Eliminar el uso de cadenas de texto literales ("magic strings") para estados y roles de dispositivos en todo el código, reemplazándolas por Enumeraciones centralizadas (`DeviceStatus`, `DeviceRole`, `CPEStatus`, `EventType`) definidas en `app/core/constants.py`.

## Beneficios

- **Seguridad de Tipos:** Evita errores por typos (ej. "onilne" vs "online").
- **Centralización:** Facilita cambiar valores o añadir nuevos estados en el futuro.
- **Autocompletado:** Mejora la experiencia de desarrollo (IDE support).

## Pasos de Implementación

### 1. Definición de Constantes (Core)

**Archivo:** `app/core/constants.py`

- Agregar las clases Enum:
  - `DeviceStatus`: ONLINE, OFFLINE
  - `DeviceRole`: ROUTER, SWITCH, ACCESS_POINT
  - `CPEStatus`: ACTIVE, OFFLINE, DISABLED
  - `EventType`: SUCCESS, DANGER, WARNING, INFO

### 2. Actualización de Schedulers (Monitoreo)

Reemplazar cadenas "online"/"offline" por `DeviceStatus.ONLINE`/`DeviceStatus.OFFLINE`.

- **Archivos:**
  - `app/services/monitor_scheduler.py`
  - `app/services/ap_monitor_scheduler.py`
  - `app/services/switch_monitor_scheduler.py`
  - `app/services/monitor_service.py`

### 3. Actualización de Adaptadores (Device Clients)

Reemplazar cadenas de roles ("router", "switch", "access_point") y estados.

- **Archivos:**
  - `app/utils/device_clients/adapters/mikrotik_router.py`
  - `app/utils/device_clients/adapters/mikrotik_wireless.py`
  - `app/utils/device_clients/adapters/mikrotik_switch.py`
  - `app/utils/device_clients/adapters/ubiquiti_airmax.py`

### 4. Actualización de Base de Datos (DB Layer)

Asegurar que las comparaciones y actualizaciones en DB usen las constantes.

- **Archivos:**
  - `app/db/router_db.py`
  - `app/db/aps_db.py`
  - `app/db/switches_db.py`
  - `app/db/stats_db.py`

### 5. Actualización de Servicios Adicionales

- **Archivos:**
  - `app/services/cpe_service.py` (Usar `CPEStatus`)

## Verificación

1. **Análisis Estático:** Verificar que no queden referencias hardcoded a las strings antiguas en los archivos modificados.
2. **Ejecución:** Iniciar la aplicación y verificar que el monitoreo sigue reportando el estado de los dispositivos correctamente en la consola/logs.
3. **Tests (si existen):** Ejecutar suites de prueba relacionadas con dispositivos.

## Notas

- Los cambios deben ser puramente de sustitución de valores. No cambiar lógica.
- Los Enums heredarán de `str` (`class DeviceStatus(str, Enum)`) para mantener compatibilidad con la base de datos (que guarda strings) y evitar migraciones de DB en este paso.

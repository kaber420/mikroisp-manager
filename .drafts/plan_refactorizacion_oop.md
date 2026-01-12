# Plan de Refactorización: Arquitectura de Componentes (Managers)

## Descripción del Objetivo
El usuario desea una estructura más modular y orientada a objetos (OOP) para facilitar la adición de múltiples funciones nuevas en el futuro. Actualmente, `MikrotikRouterAdapter` es una clase monolítica que delega a módulos funcionales.

## Propuesta de Cambio
Transformar `MikrotikRouterAdapter` para que use **Composición** en lugar de herencia o delegación directa plana. Agruparemos las funciones en "Managers" temáticos.

### Antes (Arquitectura Actual)
El adaptador tiene todos los métodos mezclados:
```python
router = MikrotikRouterAdapter(...)
router.add_ip_address(...)
router.add_nat_rule(...)      # Firewall
router.add_simple_queue(...)  # Queues
router.create_backup(...)     # System
```
Esto hace que la clase crezca indefinidamente ("God Object").

### Después (Arquitectura Propuesta)
El adaptador expone objetos especializados (Managers):
```python
router = MikrotikRouterAdapter(...)
router.ip.add_address(...)
router.firewall.add_nat_rule(...)
router.queue.add_simple(...)
router.system.create_backup(...)
```

## Cambios Propuestos

### 1. Nueva Clase Base `MikrotikBaseManager`
Una clase padre para todos los managers que maneja la conexión API compartida.

### 2. Creación de Managers Especializados
Convertiremos los módulos funcionales (`app/utils/device_clients/mikrotik/*.py`) o wrappers actuales en Clases:

#### [NEW] `app/utils/device_clients/mikrotik/managers/`
*   `firewall.py` -> `class MikrotikFirewallManager`
*   `system.py` -> `class MikrotikSystemManager`
*   `queue.py` -> `class MikrotikQueueManager`
*   `interface.py` -> `class MikrotikInterfaceManager` (Ya existe parcialmente, se formalizará)

### 3. Refactorización de `MikrotikRouterAdapter`
#### [MODIFY] `app/utils/device_clients/adapters/mikrotik_router.py`
*   Eliminar métodos directos (`add_nat_masquerade`, etc.).
*   Inicializar managers en `__init__`:
    ```python
    self.firewall = MikrotikFirewallManager(self._get_api)
    self.system = MikrotikSystemManager(self._get_api)
    ```
*   Mantener (por ahora) métodos "proxy" marcados como *deprecated* si se necesita retrocompatibilidad, o actualizar las llamadas en el servicio.

## Ventajas
1.  **Organización:** Cada "dominio" (Firewall, IP, System) tiene su propia clase.
2.  **Escalabilidad:** Añadir funciones de firewall solo toca `MikrotikFirewallManager`, no el adaptador principal.
3.  **Intellisense:** Al escribir `router.firewall.`, el IDE sugerirá solo métodos de firewall.

## Plan de Verificación
1.  Crear los Managers.
2.  Actualizar una pequeña parte del código (ej. Firewall) para probar.
3.  Verificar que el aprovisionamiento y monitoreo siguen funcionando.

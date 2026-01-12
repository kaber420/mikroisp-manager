# Plan de Implementación: Eliminación de "Magic Strings"

Este cambio aborda el punto **#3 del Reporte de Deuda Técnica**. El objetivo es reemplazar cadenas de texto repetidas y "mágicas" (hardcoded) por constantes centralizadas y Enumeraciones.

## Compatibilidad con Refactorización OOP (Confirmada)
Basado en el documento `plan_refactorizacion_oop.md`:
1.  **Soporte a Managers**: La refactorización de `MikrotikRouterAdapter` hacia un modelo de Composición con Managers (`MikrotikFirewallManager`, etc.) se beneficiará del uso de constantes compartidas.
2.  **Inyección de Dependencias**: Al crear `MikrotikBaseManager`, en lugar de pasar strings sueltos para tipos de interfaces o acciones de firewall, pasaremos constantes tipadas, reduciendo errores durante la migración estructural masiva.
3.  **No Conflicto**: Este cambio es granular (valores) y el plan OOP es topológico (estructura de clases), por lo que son ortogonales y complementarios.

## User Review Required
> [!NOTE]
> Este cambio no altera la funcionalidad del sistema, solo la organización interna del código.

## Proposed Changes

### Core
#### [NEW] app/core/constants.py
Crear un nuevo archivo para centralizar constantes.
```python
from enum import Enum, unique

@unique
class DeviceVendor(str, Enum):
    MIKROTIK = "mikrotik"
    UBIQUITI = "ubiquiti"
    
@unique
class CredentialKeys(str, Enum):
    USERNAME = "username"
    PASSWORD = "password"
    PORT = "port"

@unique
class InterfaceType(str, Enum):
    ETHERNET = "ether"
    BRIDGE = "bridge"
    VLAN = "vlan"
```

### Aplicación de Constantes (Ejemplos representativos)
Se actualizarán los archivos donde estas cadenas son más frecuentes.

#### [MODIFY] app/services/router_connector.py
- Reemplazar "username", "password" por `CredentialKeys.USERNAME`, etc.
- Reemplazar "mikrotik" por `DeviceVendor.MIKROTIK`.

#### [MODIFY] app/services/ap_connector.py
- Reemplazar claves de diccionarios por las nuevas constantes.

#### [MODIFY] app/services/switch_connector.py
- Estandarización similar a los anteriores.
- Actualizar `vendor` property.

#### [MODIFY] app/utils/device_clients/adapters/mikrotik_router.py
- Actualizar propiedad `vendor`.
- (Opcional) Preparar uso de constantes en métodos que serán migrados a Managers posteriormente.

## Verification Plan

### Automated Tests
- Ejecutar los tests existentes. Dado que solo cambiamos literales por referencias, la lógica debe mantenerse intacta.
- Verificar que la aplicación arranca correctamente.

### Manual Verification
- Revisar que la conexión a los dispositivos siga funcionando (ya que usa estas claves para extraer credenciales).

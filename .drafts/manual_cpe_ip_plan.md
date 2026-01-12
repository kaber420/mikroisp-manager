# Plan de Implementación: Gestión de IPs para CPEs Genéricos

## Problema
Al agregar clientes con CPEs genéricos (no Ubiquiti/AirMax, ej: Mikrotik en modo 802.11 estándar o dispositivos de terceros), el sistema no siempre detecta la dirección IP automáticamente. Esto impide la creación de planes de servicio con IP estática (Simple Queue), ya que el sistema requiere una IP válida y detectada para asociarla.

Actualmente, el backend (`ClientService`) rechaza la creación del servicio (o el frontend no permite enviarlo) si no se proporciona `ip_address`.

## Análisis
1.  **Descubrimiento**: El sistema utiliza `mikrotik/wireless.py` para enriquecer la tabla de registro con ARP.
2.  **Causa Raíz**: Si el dispositivo no está en la tabla ARP (inactivo), la IP es `null`. Los CPEs genéricos a menudo no reportan su IP de gestión de la misma forma que los Ubiquiti (por Discovery/SNMP/API propietaria).
3.  **Bloqueo**: La validación impide asignar una IP que no "venga" del CPE.

## Solución Propuesta

### 1. Habilitar IP Manual en Creación de Cliente (Frontend/Backend)
Permitir introducir manualmente la IP si el sistema no la detectó.

*   **Frontend**: Agregar un campo "IP Manual" en el wizard de creación de servicio. Este campo tendrá prioridad sobre la IP detectada si se rellena.
*   **Backend (`ClientService`)**:
    *   El método `create_client_service` ya acepta `ip_address` en `service_input`.
    *   Verificar que no haya validaciones extra que impidan esto.
    *   Pasar la IP manual al crear la `SimpleQueue`.

### 2. Edición de CPEs Descubiertos (Gestión de Inventario)
Permitir "fijar" una IP conocida a un CPE detectado para usos futuros.

*   **API**: Nuevo endpoint `PUT /api/cpes/{mac}`.
*   **Funcionalidad**: Permitir editar `ip_address`, `hostname`, `model` (si no se detecta bien).
*   **Persistencia**:
    *   Al actualizar los CPEs desde el escaneo periódico, si la IP escaneada es nula pero tenemos una en DB (ingresada manualmente o previa), conservarla.
    *   Esto soluciona el problema de "ya los guarda en la tabla pero no los asigna".

### Tareas Técnicas
- [x] Verificar validación en `app/api/clients/services.py`: **Verificado**. El método `create_client_service` YA acepta `ip_address` manual. No se requieren cambios en ClientService.
- [ ] Implementar `PUT /api/cpes/{mac}` para edición manual.
    - [ ] Agregar método `update_cpe` en `CPEService`.
    - [ ] Implementar persistencia: que `get_all_cpes_globally` combine datos en vivo con datos DB (priorizando IP de DB si la viva es nula).
- [ ] Ajustar UI (Frontend) para permitir input de IP manual.

## Detalles de Implementación Técnica (Validado)

1.  **ClientService (`app/services/client_service.py`)**:
    -   Estado: **Listo**.
    -   El parámetro `service_data` en `create_client_service` acepta `ip_address`.
    -   Se usa directamente para crear la particula de cola simple: `target=service_input.get("ip_address")`.
    -   No hay lógica que rechace la IP si no coincide con un CPE descubierto.

2.  **CPEService (`app/services/cpe_service.py`)**:
    -   Requiere: Nuevo método `update_cpe` para guardar cambios manuales en la tabla `cpes`.
    -   Requiere: Actualizar `get_all_cpes_globally` para hacer un "merge" inteligente. Si la estadística en vivo (RouterOS) no trae IP, usar la almacenada en SQLite.

3.  **API Router**:
    -   Requiere nuevo endpoint `PUT /api/cpes/{mac}` para exponer la edición.

## Estrategia de Implementación

1.  **Fase 1: Edición Manual (Backend)**
    *   Validar flujos en `client_service.py` para asegurar que acepte IPs arbitrarias.
    *   Crear ruta `PUT` para CPEs.

2.  **Fase 2: Interfaz de Usuario**
    *   Actualizar el formulario de "Nuevo Cliente" para permitir input manual de IP cuando se selecciona un CPE.
    *   Actualizar la lista de "CPEs Unassigned" para permitir edición rápida.

3.  **Fase 3: Persistencia Inteligente**
    *   Modificar `CPEService` (o el scheduler de monitoreo) para hacer "merge" de datos nuevos con los existentes, priorizando la IP conocida sobre `null`.

## Preguntas para el Usuario
- ¿Prefieres editar el CPE primero en la lista (asignarle IP) y luego crear el cliente, o hacerlo todo en el momento de crear el cliente (escribir IP al vuelo)? (La propuesta cubre ambos, pero priorizando "al vuelo").

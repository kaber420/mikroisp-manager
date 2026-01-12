# Soporte para Visualización de Múltiples Interfaces (Dual Band) en APs

## Estado Actual
Actualmente, la aplicación solo visualiza la primera interfaz inalámbrica detectada en los puntos de acceso (APs). Entornos con equipos Dual Band (2.4GHz y 5GHz), como es común en equipos MikroTik modernos (ej. hAP ax2, cAP ax), muestran información incompleta, visualizando típicamente solo la banda de 5GHz y ocultando la de 2.4GHz.

## Objetivo
Modificar el sistema para detectar, almacenar y visualizar todas las interfaces inalámbricas presentes en el dispositivo, permitiendo ver el estado (frecuencia, SSID, ruido, etc.) de cada banda individualmente.

## Propuesta Técnica

### Backend (Python)
1.  **Modelo de Datos (`DeviceStatus`)**:
    -   Actualizar la `dataclass` `DeviceStatus` en `app/utils/device_clients/adapters/base.py` para incluir un campo `interfaces: List[Dict]`.
    -   Este campo almacenará una lista de objetos/diccionarios con la info de cada interfaz (nombre, banda, frecuencia, SSID, tx_power, etc.).

2.  **Adaptador MikroTik (`MikrotikWirelessAdapter`)**:
    -   En `app/utils/device_clients/adapters/mikrotik_wireless.py`, metodo `get_status()`:
    -   Utilizar la función ya existente `mikrotik_wireless_lib.get_wireless_interfaces_detailed(api)` que devuelve todas las interfaces.
    -   Iterar sobre esta lista y poblar el nuevo campo `interfaces` del `DeviceStatus`.
    -   Mantener la lógica actual de "interfaz principal" para los campos de resumen del AP (frecuencia, SSID principal), pero añadir el detalle completo en la lista `interfaces`.

3.  **Conector AP (`APConnector`)**:
    -   Asegurar que `fetch_ap_stats` propague esta lista de interfaces en la respuesta JSON entregada al frontend/API.

### Frontend (Vista)
-   Actualizar el componente de detalles del AP para iterar sobre la lista `interfaces`.
-   Mostrar "Tarjetas" o filas separadas para cada interfaz (ej. "Interface 5GHz", "Interface 2.4GHz") con sus respectivas métricas (Ruido, Frecuencia, Canal, SSID).

## Beneficios
-   Visibilidad completa del espectro radioeléctrico del AP.
-   Mejor diagnóstico de problemas (ej. saturación en 2.4GHz vs 5GHz).
-   Inventario de SSIDs más preciso.

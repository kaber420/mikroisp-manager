# Propuesta para Enriquecimiento de CPE con ARP

Este documento detalla la implementación de la mejora solicitada para enriquecer la información de los clientes conectados (CPE) utilizando la tabla ARP del Mikrotik.

## Objetivo
Mejorar la precisión y utilidad de la información de los dispositivos conectados (CPE) mostrando datos adicionales que pueden no estar presentes en la tabla de registro inalámbrico, específicamente `hostname` y `ip_address`.

## Análisis Actual

### `app/utils/device_clients/mikrotik/wireless.py`
Actualmente, `get_connected_clients` obtiene datos de `/interface/wireless/registration-table` (o equivalente en wifiwave2).
Se basa en:
*   `mac-address`: Identificador único.
*   `last-ip`: IP reportada por la interfaz inalámbrica (a veces vacía o desactualizada).
*   `comment`: Comentario manual en la tabla de registro (a menudo vacío).

### `app/utils/device_clients/mikrotik/ip.py`
Actualmente no tiene una función para exponer la tabla ARP.

## Implementación Propuesta

### 1. Modificar `ip.py`
Agregar una función para obtener la tabla ARP.

```python
def get_arp_entries(api: RouterOsApi) -> List[Dict[str, Any]]:
    """
    Retorna toda la tabla ARP.
    Campos típicos de interés: 'mac-address', 'address', 'comment', 'interface', 'status'.
    """
    try:
        return api.get_resource("/ip/arp").get()
    except Exception:
        # Retorno seguro en caso de error
        return []
```

### 2. Modificar `wireless.py`
Actualizar `get_connected_clients` para cruzar datos.

#### Pasos:
1.  Importar el módulo `ip` en `wireless.py`.
2.  Obtener entradas ARP una sola vez al inicio de la función (para reducir llamadas API).
3.  Crear un mapa (diccionario) de ARP indexado por MAC Address.
4.  Al iterar sobre las registraciones inalámbricas, buscar la MAC en el mapa ARP.
5.  Enriquecer:
    *   **IP Address**: Si `last-ip` está ausente, usar la IP del ARP.
    *   **Hostname/Comentario**: Si el comentario de wireless está vacío, intentar usar el comentario del ARP (que a menudo contiene nombres de host si vienen de DHCP estático o dinámico con script).

#### Lógica de Enriquecimiento:

```python
# ... importaciones
from . import ip as mikrotik_ip

def get_connected_clients(api: RouterOsApi) -> List[Dict[str, Any]]:
    # ... código existente ...
    
    # 1. Obtener ARP
    arp_entries = mikrotik_ip.get_arp_entries(api)
    arp_map = {entry.get("mac-address"): entry for entry in arp_entries if entry.get("mac-address")}

    clients = []
    for reg in registrations:
        mac = reg.get("mac-address")
        
        # Datos base
        client_ip = reg.get("last-ip")
        client_comment = reg.get("comment")
        
        # 2. Match con ARP
        arp_info = arp_map.get(mac)
        
        if arp_info:
            # Si no hay IP en wireless, usamos la de ARP
            if not client_ip:
                client_ip = arp_info.get("address")
            
            # Si no hay comentario en wireless, usamos el de ARP (potencialmente hostname)
            if not client_comment:
                client_comment = arp_info.get("comment")
                
                # Bonus: Si en el futuro se quiere "DHCP Leases" para hostname real, sería otro cruce similiar.
                # Por ahora, ARP 'comment' a veces trae info útil.
        
        # Construcción del cliente (actualizado)
        client = {
            "mac": mac,
            "hostname": client_comment, # Ahora puede venir de ARP
            "ip_address": client_ip,    # Ahora puede venir de ARP
            # ... resto de campos ...
        }
        clients.append(client)
        
    return clients
```

## Consideraciones Adicionales (Mejoras al documento original)

1.  **Status ARP**: Las entradas ARP pueden estar `invalid` o `incomplete`.
    *   *Propuesta*: Ignorar entradas ARP que no sean válidas (DC - Dynamic Complete, o S - Static) si es posible, aunque simplemente machear por MAC suele ser seguro.
2.  **Performance**: La tabla ARP puede ser grande en redes muy saturadas (miles de entradas).
    *   *Mitigación*: La conversión a diccionario `arp_map` es O(N) y la búsqueda O(1), lo cual es eficiente en Python. A nivel Mikrotik, `/ip/arp/print` es liviano.
3.  **DHCP Leases**: Si el objetivo real es "hostname" (nombre del dispositivo), la tabla ARP a veces no lo tiene (solo tiene IP/MAC). La tabla `/ip/dhcp-server/lease` es la fuente más fidedigna para `host-name`.
    *   *Análisis*: La solicitud del usuario pide explícitamente **ARP**. Sin embargo, sugeriré en el chat que si el ARP no trae el hostname, DHCP Leases es el siguiente paso lógico. Mantendremos el alcance en ARP por ahora según la solicitud.
4.  **Manejo de Errores**: Si falla la llamada a ARP, el flujo principal de `get_connected_clients` **no debe fallar**. Se debe capturar excepción y proceder sin enriquecimiento (graceful degradation).

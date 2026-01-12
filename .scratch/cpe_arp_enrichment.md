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

### 3. Modificar `wireless.py`
Actualizar `get_connected_clients` para cruzar datos.

#### Pasos:
1.  Importar los módulos `ip` y `ppp` en `wireless.py`.
2.  Obtener **ARP** (`ip.get_arp_entries`) y **PPP Active** (`ppp.get_pppoe_active_connections`) al inicio.
3.  Crear mapas (diccionarios) indexados por MAC Address para ambos.
    *   `arp_map`: MAC -> Entry (para Static/DHCP)
    *   `ppp_map`: Caller ID (MAC) -> Entry (para PPPoE)
4.  Al iterar sobre las registraciones inalámbricas:
    *   Buscar en `arp_map` primero.
    *   Si no hay IP válida, buscar en `ppp_map`.
5.  Enriquecer `ip_address` y `hostname`/`comment` según corresponda.

#### Lógica de Enriquecimiento:

```python
# ... importaciones
from . import ip as mikrotik_ip
from . import ppp as mikrotik_ppp

def get_connected_clients(api: RouterOsApi) -> List[Dict[str, Any]]:
    # ... código existente ...
    
    # 1. Obtener Tablas Auxiliares (ARP y PPP Active)
    arp_entries = mikrotik_ip.get_arp_entries(api)
    arp_map = {entry.get("mac-address"): entry for entry in arp_entries if entry.get("mac-address")}
    
    ppp_active = mikrotik_ppp.get_pppoe_active_connections(api)
    ppp_map = {entry.get("caller-id"): entry for entry in ppp_active if entry.get("caller-id")}

    clients = []
    for reg in registrations:
        mac = reg.get("mac-address")
        
        # Datos base de Wireless
        client_ip = reg.get("last-ip")
        # El comentario en RegistrationTable a menudo está vacío, PERO:
        # En Mikrotik Wireless, 'comment' es un campo editable manualmente.
        # En PPP Active, 'name' es el usuario PPPoE (útil como hostname).
        client_comment = reg.get("comment")
        
        # 2. Match con ARP (Prioridad 1 para IP, Prioridad 2 para nombre)
        arp_info = arp_map.get(mac)
        if arp_info:
            if not client_ip:
                client_ip = arp_info.get("address")
            if not client_comment:
                # ARP comment puede ser útil, pero a veces es autogenerado
                client_comment = arp_info.get("comment")
        
        # 3. Match con PPP (Prioridad para IP si ARP falló, y EXCELENTE para 'hostname' real del cliente)
        #    Si es un cliente PPPoE, su IP real está aquí.
        ppp_info = ppp_map.get(mac)
        if ppp_info:
            # Si aún no tenemos IP (que sea válida) o si preferimos la de la sesión activa:
            # Nota: A veces ARP tiene IP de enlace local, PPP tiene la IP pública/remota real.
            # Preferimos PPP address si existe.
            if ppp_info.get("address"):
                client_ip = ppp_info.get("address")
            
            # PPP 'name' es el usuario (ej: 'cliente_juan'), mucho mejor que un comentario vacío.
            if ppp_info.get("name"):
                 client_comment = ppp_info.get("name")
        
        # Construcción del cliente (actualizado)
        client = {
            "mac": mac,
            "hostname": client_comment,
            "ip_address": client_ip,
            # ... resto de campos ...
        }
        clients.append(client)
        
    return clients
```

## Hallazgos y Estado Actual

### ✅ Implementado
- **IP Address desde ARP**: Funciona correctamente. Si la registration table no tiene `last-ip`, se obtiene de `/ip/arp`.
- **MAC Address**: Siempre disponible desde la registration table.
- **Normalización de MAC**: Se normalizan a mayúsculas para asegurar match entre tablas.

### ❌ Hostname - Limitación Descubierta
El hostname que muestra Winbox en la tabla ARP **no está almacenado** en la tabla ARP. Winbox hace un lookup dinámico (NetBIOS/mDNS) al dispositivo cliente en tiempo real.

### Opciones Futuras para Hostname
1. **NetBIOS Name Query**: Enviar query UDP puerto 137 a cada IP cliente. Requiere acceso de red directo.
2. **mDNS/Bonjour**: Escuchar broadcast mDNS en la red. Requiere presencia en el mismo segmento.
3. **Campo manual**: Permitir al usuario asignar nombres a MACs en la BD local.
4. **PPP Active** (si aplica): Para clientes PPPoE, el `name` del PPP secret es el identificador del cliente.

Por ahora, el enriquecimiento con ARP para IP está activo y funcionando.



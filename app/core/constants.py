"""
Constantes centralizadas para el sistema.
Elimina "magic strings" y provee tipado fuerte para valores comunes.
"""

from enum import Enum, unique


@unique
class DeviceVendor(str, Enum):
    """Fabricantes de dispositivos soportados."""

    MIKROTIK = "mikrotik"
    UBIQUITI = "ubiquiti"


@unique
class CredentialKeys(str, Enum):
    """Claves estándar para diccionarios de credenciales."""

    USERNAME = "username"
    PASSWORD = "password"
    PORT = "port"


@unique
class InterfaceType(str, Enum):
    """Tipos de interfaces de red comunes."""

    ETHERNET = "ether"
    BRIDGE = "bridge"
    VLAN = "vlan"
    WIRELESS = "wireless"
    BONDING = "bonding"


@unique
class DeviceStatus(str, Enum):
    """Estados de conexión de dispositivos."""

    ONLINE = "online"
    OFFLINE = "offline"


@unique
class DeviceRole(str, Enum):
    """Roles/tipos de dispositivos."""

    ROUTER = "router"
    SWITCH = "switch"
    ACCESS_POINT = "access_point"


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

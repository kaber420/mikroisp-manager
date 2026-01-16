from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal


# --- Existing Router Models ---
class RouterResponse(BaseModel):
    id: Optional[int] = None
    host: str
    username: str
    zona_id: Optional[int] = None
    api_port: int
    api_ssl_port: int
    is_enabled: bool
    is_provisioned: bool = False
    hostname: Optional[str] = None
    model: Optional[str] = None
    firmware: Optional[str] = None
    last_status: Optional[str] = None
    zona_nombre: Optional[str] = None
    wan_interface: Optional[str] = None


class RouterCreate(BaseModel):
    host: str
    username: str
    password: str
    zona_id: Optional[int] = None
    api_port: int
    is_enabled: bool = True


class RouterUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    zona_id: Optional[int] = None
    api_port: Optional[int] = None
    is_enabled: Optional[bool] = None
    wan_interface: Optional[str] = None


class ProvisionRequest(BaseModel):
    new_api_user: str
    new_api_password: str
    method: Literal["api", "ssh"] = "api"  # 'api' uses existing API method, 'ssh' uses pure SSH method


class ProvisionResponse(BaseModel):
    status: str
    message: str
    method_used: Optional[str] = None


class GenericActionResponse(BaseModel):
    status: str
    message: str


# --- New VLAN and Bridge Models ---
class VlanCreate(BaseModel):
    name: str
    vlan_id: int
    interface: str
    comment: str


class VlanUpdate(BaseModel):
    name: str
    vlan_id: int
    interface: str


class BridgeCreate(BaseModel):
    name: str
    ports: List[str]
    comment: str


class BridgeUpdate(BaseModel):
    name: str
    ports: List[str]


# --- Models from config.py ---
class RouterFullDetails(BaseModel):
    interfaces: List[Dict[str, Any]]
    ip_addresses: List[Dict[str, Any]]
    nat_rules: List[Dict[str, Any]]
    pppoe_servers: List[Dict[str, Any]]
    ppp_profiles: List[Dict[str, Any]]
    simple_queues: List[Dict[str, Any]]
    ip_pools: List[Dict[str, Any]]
    bridge_ports: List[Dict[str, Any]]
    pppoe_secrets: List[Dict[str, Any]]
    pppoe_active: List[Dict[str, Any]]
    users: List[Dict[str, Any]]
    files: List[Dict[str, Any]]
    static_resources: Dict[str, Any]


class CreatePlanRequest(BaseModel):
    plan_name: str
    rate_limit: Optional[str] = None
    parent_queue: Optional[str] = None
    local_address: Optional[str] = None
    comment: str
    pool_range: Optional[str] = None
    remote_address: Optional[str] = None


class AddSimpleQueueRequest(BaseModel):
    name: str
    target: str
    max_limit: str
    parent: Optional[str] = None
    comment: Optional[str] = None


class AddIpRequest(BaseModel):
    address: str
    interface: str
    comment: str


class AddNatRequest(BaseModel):
    out_interface: str
    comment: str


class AddPppoeServerRequest(BaseModel):
    service_name: str
    interface: str
    default_profile: str
    one_session_per_host: bool = True
    keepalive_timeout: int = 10


# --- Models from pppoe.py ---
class PppoeSecretCreate(BaseModel):
    username: str
    password: str
    profile: str
    comment: Optional[str] = None
    service: str = "pppoe"


class PppoeSecretUpdate(BaseModel):
    password: Optional[str] = None
    profile: Optional[str] = None
    comment: Optional[str] = None


class PppoeSecretDisable(BaseModel):
    disable: bool


# --- NEW: Service Management Models ---
class SuspendServiceRequest(BaseModel):
    """Request to suspend a client's service via address list."""
    address: str
    list_name: str
    strategy: str = "blacklist"  # 'blacklist' or 'whitelist'
    pppoe_username: Optional[str] = None  # If provided, also kills PPPoE session
    comment: str = "Suspended by UManager"


class RestoreServiceRequest(BaseModel):
    """Request to restore a suspended service."""
    address: str
    list_name: str
    strategy: str = "blacklist"
    comment: str = "Restored by UManager"


class ChangePlanRequest(BaseModel):
    """Request to change a PPPoE user's plan."""
    pppoe_username: str
    new_profile: str
    kill_connection: bool = True  # Force re-auth after profile change


class KillConnectionRequest(BaseModel):
    """Request to terminate an active PPPoE session."""
    username: str


class AddressListActionRequest(BaseModel):
    """Request for direct address list manipulation."""
    list_name: str
    address: str
    action: str  # 'add', 'remove', 'disable'
    comment: str = ""


# --- Models from system.py ---
class SystemResource(BaseModel):
    uptime: Optional[str] = None
    cpu_load: Optional[str] = Field(None, alias="cpu-load")
    free_memory: Optional[str] = Field(None, alias="free-memory")
    total_memory: Optional[str] = Field(None, alias="total-memory")
    board_name: Optional[str] = Field(None, alias="board-name")
    version: Optional[str] = None
    name: Optional[str] = None  # hostname
    serial_number: Optional[str] = Field(None, alias="serial-number")

    # --- CAMPOS AÑADIDOS PARA QUE PASEN EL FILTRO! ---
    platform: Optional[str] = None
    cpu: Optional[str] = None
    cpu_count: Optional[str] = Field(None, alias="cpu-count")
    cpu_frequency: Optional[str] = Field(None, alias="cpu-frequency")
    model: Optional[str] = None
    nlevel: Optional[str] = None
    voltage: Optional[str] = None
    temperature: Optional[str] = None

    # Campos de disco normalizados
    total_disk: Optional[str] = Field(None, alias="total-disk")
    free_disk: Optional[str] = Field(None, alias="free-disk")


class BackupCreateRequest(BaseModel):
    backup_type: str  # 'backup' or 'export'
    backup_name: str
    overwrite: bool = False


class RouterUserCreate(BaseModel):
    username: str
    password: str
    group: str  # 'full', 'write', 'read'

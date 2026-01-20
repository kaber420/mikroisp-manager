from typing import Any, Literal

from pydantic import BaseModel, Field


# --- Existing Router Models ---
class RouterResponse(BaseModel):
    id: int | None = None
    host: str
    username: str
    zona_id: int | None = None
    api_port: int
    api_ssl_port: int
    is_enabled: bool
    is_provisioned: bool = False
    hostname: str | None = None
    model: str | None = None
    firmware: str | None = None
    last_status: str | None = None
    zona_nombre: str | None = None
    wan_interface: str | None = None


class RouterCreate(BaseModel):
    host: str
    username: str
    password: str
    zona_id: int | None = None
    api_port: int
    is_enabled: bool = True


class RouterUpdate(BaseModel):
    username: str | None = None
    password: str | None = None
    zona_id: int | None = None
    api_port: int | None = None
    is_enabled: bool | None = None
    wan_interface: str | None = None


class ProvisionRequest(BaseModel):
    new_api_user: str
    new_api_password: str
    method: Literal["api", "ssh"] = (
        "api"  # 'api' uses existing API method, 'ssh' uses pure SSH method
    )


class ProvisionResponse(BaseModel):
    status: str
    message: str
    method_used: str | None = None


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
    ports: list[str]
    comment: str


class BridgeUpdate(BaseModel):
    name: str
    ports: list[str]


# --- Models from config.py ---
class RouterFullDetails(BaseModel):
    interfaces: list[dict[str, Any]]
    ip_addresses: list[dict[str, Any]]
    nat_rules: list[dict[str, Any]]
    pppoe_servers: list[dict[str, Any]]
    ppp_profiles: list[dict[str, Any]]
    simple_queues: list[dict[str, Any]]
    ip_pools: list[dict[str, Any]]
    bridge_ports: list[dict[str, Any]]
    pppoe_secrets: list[dict[str, Any]]
    pppoe_active: list[dict[str, Any]]
    users: list[dict[str, Any]]
    files: list[dict[str, Any]]
    static_resources: dict[str, Any]


class CreatePlanRequest(BaseModel):
    plan_name: str
    rate_limit: str | None = None
    parent_queue: str | None = None
    local_address: str | None = None
    comment: str
    pool_range: str | None = None
    remote_address: str | None = None


class AddSimpleQueueRequest(BaseModel):
    name: str
    target: str
    max_limit: str
    parent: str | None = None
    comment: str | None = None


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
    comment: str | None = None
    service: str = "pppoe"


class PppoeSecretUpdate(BaseModel):
    password: str | None = None
    profile: str | None = None
    comment: str | None = None


class PppoeSecretDisable(BaseModel):
    disable: bool


# --- NEW: Service Management Models ---
class SuspendServiceRequest(BaseModel):
    """Request to suspend a client's service via address list."""

    address: str
    list_name: str
    strategy: str = "blacklist"  # 'blacklist' or 'whitelist'
    pppoe_username: str | None = None  # If provided, also kills PPPoE session
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
    uptime: str | None = None
    cpu_load: str | None = Field(None, alias="cpu-load")
    free_memory: str | None = Field(None, alias="free-memory")
    total_memory: str | None = Field(None, alias="total-memory")
    board_name: str | None = Field(None, alias="board-name")
    version: str | None = None
    name: str | None = None  # hostname
    serial_number: str | None = Field(None, alias="serial-number")

    # --- CAMPOS AÑADIDOS PARA QUE PASEN EL FILTRO! ---
    platform: str | None = None
    cpu: str | None = None
    cpu_count: str | None = Field(None, alias="cpu-count")
    cpu_frequency: str | None = Field(None, alias="cpu-frequency")
    model: str | None = None
    nlevel: str | None = None
    voltage: str | None = None
    temperature: str | None = None

    # Campos de disco normalizados
    total_disk: str | None = Field(None, alias="total-disk")
    free_disk: str | None = Field(None, alias="free-disk")


class BackupCreateRequest(BaseModel):
    backup_type: str  # 'backup' or 'export'
    backup_name: str
    overwrite: bool = False


class RouterUserCreate(BaseModel):
    username: str
    password: str
    group: str  # 'full', 'write', 'read'

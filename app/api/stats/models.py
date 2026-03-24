# app/api/stats/models.py

from pydantic import BaseModel, ConfigDict


# --- Modelos Pydantic ---
class TopAP(BaseModel):
    hostname: str | None = None
    host: str
    airtime_total_usage: int | None = None
    model_config = ConfigDict(from_attributes=True)


class TopCPE(BaseModel):
    cpe_hostname: str | None = None
    cpe_mac: str
    ap_host: str
    signal: int | None = None
    model_config = ConfigDict(from_attributes=True)


class TopRouterConsumption(BaseModel):
    hostname: str | None = None
    host: str
    wan_rx_bytes: int | None = None
    wan_tx_bytes: int | None = None
    wan_rx_bps: int | None = None
    wan_tx_bps: int | None = None
    total_bytes: int | None = None
    total_bps: int | None = None
    model_config = ConfigDict(from_attributes=True)


class TopOfflineDevice(BaseModel):
    hostname: str | None = None
    host: str
    device_type: str
    last_checked: str | None = None
    model_config = ConfigDict(from_attributes=True)


class CPECount(BaseModel):
    total_cpes: int
    active: int
    offline: int
    disabled: int


class SwitchCount(BaseModel):
    total_switches: int
    online: int
    offline: int


class TicketStats(BaseModel):
    total_tickets: int
    open_tickets: int
    resolved_tickets: int
    pending_tickets: int
    support_tickets: int
    installation_tickets: int
class RouterCount(BaseModel):
    total_routers: int
    online: int
    offline: int


class APCount(BaseModel):
    total_aps: int
    online: int
    offline: int

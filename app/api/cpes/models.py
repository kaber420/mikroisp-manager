# app/api/cpes/models.py

from pydantic import BaseModel, ConfigDict


# (Modelos movidos desde cpes_api.py)
class CPEDetail(BaseModel):
    cpe_mac: str
    cpe_hostname: str | None = None
    ip_address: str | None = None
    signal: int | None = None
    signal_chain0: int | None = None
    signal_chain1: int | None = None
    noisefloor: int | None = None
    dl_capacity: int | None = None
    ul_capacity: int | None = None
    throughput_rx_kbps: int | None = None
    throughput_tx_kbps: int | None = None
    total_rx_bytes: int | None = None
    total_tx_bytes: int | None = None
    cpe_uptime: int | None = None
    eth_plugged: bool | None = None
    eth_speed: int | None = None
    ssid: str | None = None
    band: str | None = None
    model_config = ConfigDict(from_attributes=True)


class CPEGlobalInfo(CPEDetail):
    ap_host: str | None = None
    ap_hostname: str | None = None
    status: str | None = None  # 'active', 'offline', 'disabled'
    is_enabled: bool | None = None
    model_config = ConfigDict(from_attributes=True)


class AssignedCPE(BaseModel):
    mac: str
    hostname: str | None = None
    ip_address: str | None = None
    model_config = ConfigDict(from_attributes=True)


class CPEUpdate(BaseModel):
    """Model for partial CPE updates (manual IP, hostname, model)."""

    ip_address: str | None = None
    hostname: str | None = None
    model: str | None = None

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


class CPECount(BaseModel):
    total_cpes: int
    active: int
    offline: int
    disabled: int


class SwitchCount(BaseModel):
    total_switches: int
    online: int
    offline: int

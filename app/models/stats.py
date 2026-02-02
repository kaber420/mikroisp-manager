from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel


class RouterStats(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    router_host: str
    cpu_load: Optional[float] = None
    free_memory: Optional[int] = None
    total_memory: Optional[int] = None
    free_hdd: Optional[int] = None
    total_hdd: Optional[int] = None
    voltage: Optional[float] = None
    temperature: Optional[int] = None
    uptime: Optional[str] = None
    board_name: Optional[str] = None
    version: Optional[str] = None


class APStats(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    ap_host: str
    vendor: Optional[str] = "ubiquiti"
    uptime: Optional[int] = None
    cpuload: Optional[float] = None
    freeram: Optional[int] = None
    client_count: Optional[int] = None
    noise_floor: Optional[int] = None
    total_throughput_tx: Optional[float] = None
    total_throughput_rx: Optional[float] = None
    airtime_total_usage: Optional[float] = None
    airtime_tx_usage: Optional[float] = None
    airtime_rx_usage: Optional[float] = None
    frequency: Optional[int] = None
    chanbw: Optional[int] = None
    essid: Optional[str] = None
    total_tx_bytes: Optional[int] = None
    total_rx_bytes: Optional[int] = None
    gps_lat: Optional[float] = None
    gps_lon: Optional[float] = None
    gps_sats: Optional[int] = None


class CPEStats(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    ap_host: str
    vendor: Optional[str] = "ubiquiti"
    cpe_mac: str
    cpe_hostname: Optional[str] = None
    ip_address: Optional[str] = None
    signal: Optional[int] = None
    signal_chain0: Optional[int] = None
    signal_chain1: Optional[int] = None
    noisefloor: Optional[int] = None
    cpe_tx_power: Optional[int] = None
    distance: Optional[float] = None
    dl_capacity: Optional[int] = None
    ul_capacity: Optional[int] = None
    airmax_cinr_rx: Optional[int] = None
    airmax_usage_rx: Optional[int] = None
    airmax_cinr_tx: Optional[int] = None
    airmax_usage_tx: Optional[int] = None
    throughput_rx_kbps: Optional[float] = None
    throughput_tx_kbps: Optional[float] = None
    total_rx_bytes: Optional[int] = None
    total_tx_bytes: Optional[int] = None
    cpe_uptime: Optional[int] = None
    ccq: Optional[int] = None
    tx_rate: Optional[str] = None
    rx_rate: Optional[str] = None
    ssid: Optional[str] = None
    band: Optional[str] = None
    eth_plugged: Optional[bool] = None
    eth_speed: Optional[str] = None
    eth_cable_len: Optional[str] = None


class EventLog(SQLModel, table=True):
    __tablename__ = "event_logs"  # Keep exact table name for compatibility if needed
    id: Optional[int] = Field(default=None, primary_key=True)
    device_host: str
    device_type: str
    event_type: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DisconnectionEvent(SQLModel, table=True):
    __tablename__ = "disconnection_events"
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    ap_host: str
    cpe_mac: str
    cpe_hostname: Optional[str] = None
    reason_code: Optional[int] = None
    connection_duration: Optional[str] = None

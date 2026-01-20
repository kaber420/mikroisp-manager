# app/api/aps/models.py
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

"""
Este archivo contiene los modelos Pydantic (contratos de datos) 
que la API de APs utiliza.
"""


class AP(BaseModel):
    host: str
    username: str
    zona_id: int | None = None
    is_enabled: bool
    monitor_interval: int | None = None
    hostname: str | None = None
    model: str | None = None
    mac: str | None = None
    firmware: str | None = None
    last_status: str | None = None
    client_count: int | None = None
    airtime_total_usage: int | None = None
    airtime_tx_usage: int | None = None
    airtime_rx_usage: int | None = None
    total_throughput_tx: int | None = None
    total_throughput_rx: int | None = None
    noise_floor: int | None = None
    chanbw: int | None = None
    frequency: int | None = None
    essid: str | None = None
    total_tx_bytes: int | None = None
    total_rx_bytes: int | None = None
    gps_lat: float | None = None
    gps_lon: float | None = None
    gps_sats: int | None = None
    zona_nombre: str | None = None
    # Multi-vendor support
    vendor: str | None = "ubiquiti"  # "ubiquiti" or "mikrotik"
    role: str | None = "access_point"  # "access_point" or "switch"
    api_port: int | None = 443
    # Provisioning fields
    api_ssl_port: int | None = 8729
    is_provisioned: bool = False
    last_provision_attempt: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class APCreate(BaseModel):
    host: str
    username: str
    password: str
    zona_id: int
    is_enabled: bool = True
    monitor_interval: int | None = None
    api_port: int = 443
    api_ssl_port: int = 8729  # SSL API port for MikroTik
    vendor: str = "ubiquiti"  # "ubiquiti" or "mikrotik"
    role: str = "access_point"  # "access_point" or "switch"


class APUpdate(BaseModel):
    username: str | None = None
    password: str | None = None
    zona_id: int | None = None
    is_enabled: bool | None = None
    monitor_interval: int | None = None
    api_port: int | None = None
    api_ssl_port: int | None = None
    is_provisioned: bool | None = None
    vendor: str | None = None
    role: str | None = None


class CPEDetail(BaseModel):
    timestamp: datetime | None = None
    cpe_mac: str
    cpe_hostname: str | None = None
    ip_address: str | None = None
    signal: int | None = None
    signal_chain0: int | None = None
    signal_chain1: int | None = None
    noisefloor: int | None = None
    dl_capacity: int | None = None  # Ubiquiti AirMax
    ul_capacity: int | None = None  # Ubiquiti AirMax
    throughput_rx_kbps: int | None = None
    throughput_tx_kbps: int | None = None
    total_rx_bytes: int | None = None
    total_tx_bytes: int | None = None
    cpe_uptime: int | None = None
    eth_plugged: bool | None = None
    eth_speed: int | None = None
    # MikroTik-specific fields
    ccq: int | None = None  # Client Connection Quality (%)
    tx_rate: int | None = None  # TX rate in Mbps
    rx_rate: int | None = None  # RX rate in Mbps
    extra: dict[str, Any] | None = None
    model_config = ConfigDict(from_attributes=True)


class APLiveDetail(AP):
    clients: list[CPEDetail]
    extra: dict[str, Any] | None = None  # Vendor-specific data (MikroTik: cpu_load, memory, etc.)


class HistoryDataPoint(BaseModel):
    timestamp: datetime
    client_count: int | None = None
    airtime_total_usage: int | None = None
    total_throughput_tx: int | None = None
    total_throughput_rx: int | None = None
    model_config = ConfigDict(from_attributes=True)


class APHistoryResponse(BaseModel):
    host: str
    hostname: str | None = None
    history: list[HistoryDataPoint]
    model_config = ConfigDict(from_attributes=True)

# app/api/clients/models.py
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


# --- Modelos Pydantic (Cliente) ---
class Client(BaseModel):
    id: uuid.UUID
    name: str
    address: str | None = None
    phone_number: str | None = None
    whatsapp_number: str | None = None
    email: str | None = None
    service_status: str
    billing_day: int | None = None
    created_at: datetime
    cpe_count: int | None = 0
    model_config = ConfigDict(from_attributes=True)


class ClientCreate(BaseModel):
    name: str
    address: str | None = None
    phone_number: str | None = None
    whatsapp_number: str | None = None
    email: str | None = None
    service_status: str = "active"
    billing_day: int | None = None
    notes: str | None = None


class ClientUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    phone_number: str | None = None
    whatsapp_number: str | None = None
    email: str | None = None
    service_status: str | None = None
    billing_day: int | None = None
    notes: str | None = None


class AssignedCPE(BaseModel):
    mac: str
    hostname: str | None = None
    ip_address: str | None = None
    service_id: int | None = None  # CPE can be assigned to a specific service
    model_config = ConfigDict(from_attributes=True)


# --- Modelos Pydantic (Servicios) ---
class ClientServiceBase(BaseModel):
    router_host: str
    service_type: str
    pppoe_username: str | None = None
    router_secret_id: str | None = None
    profile_name: str | None = None
    plan_id: int | None = None
    ip_address: str | None = None
    suspension_method: str
    address: str | None = None
    status: str = "active"
    billing_day: int | None = None
    notes: str | None = None


class ClientServiceCreate(ClientServiceBase):
    pass


class ClientService(ClientServiceBase):
    id: int
    client_id: uuid.UUID
    created_at: datetime
    plan_name: str | None = None
    model_config = ConfigDict(from_attributes=True)


# --- Modelos Pydantic (Pagos) ---
class PaymentBase(BaseModel):
    monto: float
    mes_correspondiente: str
    metodo_pago: str | None = None
    notas: str | None = None


class PaymentCreate(PaymentBase):
    pass


class Payment(PaymentBase):
    id: int
    client_id: uuid.UUID
    fecha_pago: datetime
    model_config = ConfigDict(from_attributes=True)

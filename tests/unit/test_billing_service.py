import uuid
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest
from sqlmodel import Session, create_engine, SQLModel

from app.models.client import Client
from app.models.payment import Payment
from app.models.plan import Plan
from app.models.router import Router
from app.models.service import ClientService as ClientServiceModel
from app.models.setting import Setting

from app.services.business.billing_service import BillingService
from app.core.exceptions import ClientNotFoundError, PaymentNotFoundError

# --- SETUP FIXTURE PARA DB SINCRONA EN MEMORIA ---
@pytest.fixture(name="session_sync")
def session_sync_fixture():
    """Genera una sesión síncrona real en memoria para tests aislados."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="billing_service")
def billing_service_fixture(session_sync: Session):
    """Instancia del servicio de facturación inyectado con la BBDD síncrona."""
    return BillingService(session=session_sync)


# --- HELPERS PARA SEMBRAR DATOS FALSOS ---
def seed_basic_data(session: Session) -> dict:
    """Inserta configuraciones, planes, routers y un cliente inicial."""
    # Setting
    session.add(Setting(key="days_before_due", value="5", description="Días previos para pendiente"))
    session.add(Setting(key="company_name", value="Mi ISP Test"))
    
    # Router
    router = Router(
        host="192.168.1.1",
        api_port=8728,
        username="admin",
        password="secretpassword",
        status="online",
        name="Main Router"
    )
    session.add(router)
    
    # Plan
    plan = Plan(
        name="Plan 10M",
        price=1500,
        download_speed=10,
        upload_speed=10,
        max_limit="10M/10M",
        suspension_method="address_list",
        address_list_name="morosos",
        address_list_strategy="blacklist"
    )
    session.add(plan)
    session.commit()
    
    # Cliente
    client = Client(
        name="Juan Perez",
        service_status="suspended",
        billing_day=15
    )
    session.add(client)
    session.commit()
    
    # Servicio para el cliente
    service = ClientServiceModel(
        client_id=client.id,
        router_host=router.host,
        service_type="pppoe",
        pppoe_username="juan.perez",
        plan_id=plan.id,
        ip_address="10.0.0.2",
        suspension_method="address_list",
        status="active"
    )
    session.add(service)
    session.commit()
    
    return {
        "router": router,
        "plan": plan,
        "client": client,
        "service": service
    }


# --- TESTS: reactivate_client_services ---

@patch("app.services.business.billing_service.RouterService")
def test_reactivate_suspended_client(mock_router_service_class, session_sync, billing_service):
    """Prueba que un pago cambia un cliente 'suspended' a 'active' y quita cortes en RouterOS."""
    data = seed_basic_data(session_sync)
    client_id = data["client"].id
    
    # Configurar mock de RouterService para que no haga magia real
    mock_rs_instance = MagicMock()
    mock_router_service_class.return_value.__enter__.return_value = mock_rs_instance
    
    # Intentar reactivar con pago
    payment_data = {
        "monto": 1500,
        "metodo_pago": "Efectivo",
        "mes_correspondiente": "2026-02",
        "notas": "Pago puntual en oficina"
    }
    
    new_payment = billing_service.reactivate_client_services(client_id, payment_data)
    
    # 1. El pago debe haberse creado en DB
    assert new_payment["monto"] == 1500
    assert new_payment["mes_correspondiente"] == "2026-02"
    
    # 2. El estado del cliente debe haber pasado a 'active'
    session_sync.refresh(data["client"])
    assert data["client"].service_status == "active"
    
    # 3. La función técnica de Reactivación debe haber sido llamada en RouterService
    # Como el plan usa "address_list", se debe llamar activate_user_address_list
    mock_rs_instance.activate_user_address_list.assert_called_once_with(
        "10.0.0.2", list_name="morosos", strategy="blacklist"
    )


@patch("app.services.business.billing_service.RouterService")
def test_reactivate_active_client_no_router_calls(mock_router_service_class, session_sync, billing_service):
    """Si el cliente ya estaba activo, se registra el pago pero no se intenta contactar al Router."""
    data = seed_basic_data(session_sync)
    
    # Cambiar cliente a activo manualmente
    client_id = data["client"].id
    data["client"].service_status = "active"
    session_sync.add(data["client"])
    session_sync.commit()
    
    mock_rs_instance = MagicMock()
    mock_router_service_class.return_value.__enter__.return_value = mock_rs_instance
    
    payment_data = {
        "monto": 1500,
        "metodo_pago": "Transferencia",
        "mes_correspondiente": "2026-03"  # Pago adelantado
    }
    
    billing_service.reactivate_client_services(client_id, payment_data)
    
    # 1. RouterService NUNCA debe ser instanciado ni invocado porque no hay corte que levantar
    mock_router_service_class.assert_not_called()
    
    # 2. El cliente sigue activo
    session_sync.refresh(data["client"])
    assert data["client"].service_status == "active"


@patch("app.services.business.billing_service.RouterService")
def test_reactivate_suspended_client_queue_limit(mock_router_service_class, session_sync, billing_service):
    """Prueba que un pago cambia un cliente 'suspended' a 'active' reactivando Queue Limit."""
    data = seed_basic_data(session_sync)
    client_id = data["client"].id
    
    plan = data["plan"]
    plan.suspension_method = "queue_limit"
    plan.max_limit = "20M/20M"
    session_sync.add(plan)
    
    service = data["service"]
    service.suspension_method = "queue_limit"
    session_sync.add(service)
    session_sync.commit()
    
    mock_rs_instance = MagicMock()
    mock_router_service_class.return_value.__enter__.return_value = mock_rs_instance
    
    payment_data = {"monto": 1500, "mes_correspondiente": "2026-02"}
    billing_service.reactivate_client_services(client_id, payment_data)
    
    mock_rs_instance.activate_user_limit.assert_called_once_with("10.0.0.2", "20M/20M")


@patch("app.services.business.billing_service.RouterService")
def test_reactivate_suspended_client_pppoe(mock_router_service_class, session_sync, billing_service):
    """Prueba que un pago cambia un cliente 'suspended' a 'active' reactivando PPPoE."""
    data = seed_basic_data(session_sync)
    client_id = data["client"].id
    
    plan = data["plan"]
    plan.suspension_method = "pppoe_secret_disable"
    session_sync.add(plan)
    
    service = data["service"]
    service.router_secret_id = "*1A"
    session_sync.add(service)
    session_sync.commit()
    
    mock_rs_instance = MagicMock()
    mock_router_service_class.return_value.__enter__.return_value = mock_rs_instance
    
    payment_data = {"monto": 1500, "mes_correspondiente": "2026-02"}
    billing_service.reactivate_client_services(client_id, payment_data)
    
    mock_rs_instance.set_pppoe_secret_status.assert_called_once_with("*1A", disable=False)


# --- TESTS: process_daily_suspensions ---

@patch("app.services.business.billing_service.RouterService")
# Truco: usar freezegun o patch a datetime para fijar la "fecha actual"
@patch("app.services.business.billing_service.datetime")
def test_process_daily_suspensions_cuts_service(mock_datetime, mock_router_service_class, session_sync, billing_service):
    """Simular una fecha en la que el cliente no ha pagado su mes y sobrepasa la fecha de corte."""
    data = seed_basic_data(session_sync)
    client = data["client"]
    
    # Cambiamos su estado inicial a active y dia de factura el 10
    client.billing_day = 10
    client.service_status = "active"
    session_sync.add(client)
    session_sync.commit()
    
    # Mockear fecha actual: "2026-02-12" (El cliente debió pagar el 10 de Feb)
    # Por ende está retrasado 2 días (difference is negative en el código original: today_day=12, due=10 -> due-today = -2)
    fake_now = datetime(2026, 2, 12, 10, 0, 0)
    mock_datetime.now.return_value = fake_now
    
    # Mock Router
    mock_rs_instance = MagicMock()
    mock_router_service_class.return_value.__enter__.return_value = mock_rs_instance
    
    stats = billing_service.process_daily_suspensions()
    
    # 1. El cliente debe haber pasado a suspendido
    session_sync.refresh(client)
    assert client.service_status == "suspended"
    assert stats["suspended"] == 1
    
    # 2. El Router debió ser llamado para suspender y matar conexion PPPoE
    mock_rs_instance.suspend_user_address_list.assert_called_once_with(
        "10.0.0.2", list_name="morosos", strategy="blacklist"
    )
    mock_rs_instance.kill_pppoe_connection.assert_called_once_with("juan.perez")


@patch("app.services.business.billing_service.RouterService")
@patch("app.services.business.billing_service.datetime")
def test_process_daily_suspensions_status_pendiente(mock_datetime, mock_router_service_class, session_sync, billing_service):
    """Simular que faltan menos de 5 días para su pago de mes, cambia a 'pendiente'."""
    data = seed_basic_data(session_sync)
    client = data["client"]
    
    # Dia de pago 15. Estado: activo
    client.billing_day = 15
    client.service_status = "active"
    session_sync.add(client)
    session_sync.commit()
    
    # Mockear "2026-02-12". Faltan 3 dias para el 15. (3 <= 5) -> PENDIENTE
    fake_now = datetime(2026, 2, 12, 10, 0, 0)
    mock_datetime.now.return_value = fake_now
    
    stats = billing_service.process_daily_suspensions()
    
    # 1. Cliente pasa a PENDIENTE
    session_sync.refresh(client)
    assert client.service_status == "pendiente"
    assert stats["pendiente"] == 1
    
    # 2. NO se toca el router (porque solo avisa al sistema de morosidad pronta, no corta internet)
    mock_router_service_class.assert_not_called()


@patch("app.services.business.billing_service.RouterService")
@patch("app.services.business.billing_service.datetime")
def test_process_daily_suspensions_queue_limit(mock_datetime, mock_router_service_class, session_sync, billing_service):
    """Simular corte por caducidad con método queue limit."""
    data = seed_basic_data(session_sync)
    client = data["client"]
    client.billing_day = 10
    client.service_status = "active"
    session_sync.add(client)
    
    plan = data["plan"]
    plan.suspension_method = "queue_limit"
    session_sync.add(plan)
    session_sync.commit()
    
    fake_now = datetime(2026, 2, 12, 10, 0, 0)
    mock_datetime.now.return_value = fake_now
    
    mock_rs_instance = MagicMock()
    mock_router_service_class.return_value.__enter__.return_value = mock_rs_instance
    
    billing_service.process_daily_suspensions()
    
    mock_rs_instance.suspend_user_limit.assert_called_once_with("10.0.0.2")

@patch("app.services.business.billing_service.RouterService")
@patch("app.services.business.billing_service.datetime")
def test_process_daily_suspensions_pppoe(mock_datetime, mock_router_service_class, session_sync, billing_service):
    """Simular corte por caducidad con método pppoe limit."""
    data = seed_basic_data(session_sync)
    client = data["client"]
    client.billing_day = 10
    client.service_status = "active"
    session_sync.add(client)
    
    plan = data["plan"]
    plan.suspension_method = "pppoe_secret_disable"
    session_sync.add(plan)
    
    service = data["service"]
    service.router_secret_id = "*1A"
    session_sync.add(service)
    session_sync.commit()
    
    fake_now = datetime(2026, 2, 12, 10, 0, 0)
    mock_datetime.now.return_value = fake_now
    
    mock_rs_instance = MagicMock()
    mock_router_service_class.return_value.__enter__.return_value = mock_rs_instance
    
    billing_service.process_daily_suspensions()
    
    mock_rs_instance.set_pppoe_secret_status.assert_called_once_with("*1A", disable=True)


# --- TESTS: get_payment_receipt_context ---

def test_get_payment_receipt_context(session_sync, billing_service):
    """Probar ensamblado de datos para recibos PDF (cálculos de fechas)."""
    data = seed_basic_data(session_sync)
    client = data["client"]
    client.billing_day = 1
    session_sync.add(client)
    
    # Crear un pago que corresponde a Febrero
    payment = Payment(
        client_id=client.id,
        monto=1500,
        mes_correspondiente="2026-02"
    )
    session_sync.add(payment)
    session_sync.commit()
    
    context = billing_service.get_payment_receipt_context(payment.id)
    
    # Validar fechas de ciclo correctamente deducidas del mes de pago
    assert context["client"].id == client.id
    assert context["start_date"] == "01 de February de 2026"  # Note: strftime("01 de %B de %Y") might use english locale depending on env.
    
    # Fin de ciclo es un mes despues del inicio (01 de Marzo)
    assert context["end_date"] == "01 de March de 2026"

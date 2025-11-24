# app/services/client_service.py
"""
Client service layer using SQLModel ORM.
Refactored to use SQLModel instead of raw SQL from clients_db.
"""
import logging
from typing import List, Dict, Any, Optional
from sqlmodel import Session, select
from app.models import Client
from ..models.service import ClientService as ClientServiceModel
from ..models.router import Router
from ..db import plans_db, cpes_db
from ..db.base import get_db_connection # Added for legacy DB access
from ..services.router_service import RouterService

logger = logging.getLogger(__name__)


class ClientService:
    """
    Service layer for Client and ClientService operations using SQLModel ORM.
    """
    
    def __init__(self, session: Session):
        """
        Initialize with a SQLModel session.
        
        Args:
            session: SQLModel Session instance
        """
        self.session = session
    
    def get_all_clients(self) -> List[Dict[str, Any]]:
        """
        Get all clients with their CPE count.
        """
        statement = select(Client).order_by(Client.name)
        clients = self.session.exec(statement).all()
        
        # Convert to dict format for compatibility
        clients_dict = []
        for client in clients:
            client_dict = client.model_dump()
            # Get CPE count using the legacy cpes_db
            client_dict['cpe_count'] = cpes_db.get_cpe_count_for_client(client.id)
            clients_dict.append(client_dict)
        
        return clients_dict
    
    def get_client_by_id(self, client_id: int) -> Dict[str, Any]:
        """Get a single client by ID."""
        client = self.session.get(Client, client_id)
        if not client:
            raise FileNotFoundError(f"Client {client_id} not found.")
        return client.model_dump()
    
    def create_client(self, client_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new client."""
        try:
            # Remove any fields that shouldn't be set manually
            client_data_clean = {k: v for k, v in client_data.items() if k != 'id'}
            
            new_client = Client(**client_data_clean)
            self.session.add(new_client)
            self.session.commit()
            self.session.refresh(new_client)
            
            result = new_client.model_dump()
            result['cpe_count'] = 0  # New clients start with 0 CPEs
            return result
        except Exception as e:
            self.session.rollback()
            raise ValueError(f"Database error: {e}")
    
    def update_client(self, client_id: int, client_update: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing client."""
        if not client_update:
            raise ValueError("No fields to update provided.")
        
        client = self.session.get(Client, client_id)
        if not client:
            raise FileNotFoundError("Client not found.")
        
        # Update fields
        for key, value in client_update.items():
            if hasattr(client, key) and key != 'id':
                setattr(client, key, value)
        
        self.session.add(client)
        self.session.commit()
        self.session.refresh(client)
        
        result = client.model_dump()
        # TODO: Add real CPE count when CPE model exists
        result['cpe_count'] = 0
        return result
    
    def delete_client(self, client_id: int):
        """Delete a client."""
        client = self.session.get(Client, client_id)
        if not client:
            raise FileNotFoundError("Client not found to delete.")
        
        # TODO: Handle CPE updates when CPE model is migrated
        self.session.delete(client)
        self.session.commit()
    
    def get_cpes_for_client(self, client_id: int) -> List[Dict[str, Any]]:
        """
        Get CPEs for a client using the legacy cpes_db.
        """
        return cpes_db.get_cpes_for_client(client_id)
    
    # --- Service Methods ---
    def create_client_service(
        self, client_id: int, service_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Crea un nuevo servicio para un cliente.
        - Si el tipo es PPPoE, fuerza el método de suspensión a
          'pppoe_secret_disable' y crea o adopta el secret en el router.
        - Si el tipo es simple_queue, aplica la configuración de cola.
        """
        try:
            # Añadimos el client_id al payload
            service_data_full = {**service_data, "client_id": client_id}
            # Eliminamos id si viene por accidente
            service_data_full.pop("id", None)

            # **FORZAR MÉTODO DE SUSPENSIÓN PARA PPPoE**
            if service_data_full.get("service_type") == "pppoe":
                # El método correcto es desactivar el secret
                service_data_full["suspension_method"] = "pppoe_secret_disable"

            new_service = ClientServiceModel(**service_data_full)
            self.session.add(new_service)
            self.session.commit()
            self.session.refresh(new_service)

            # -------------------------------------------------
            # 1️⃣  Si es SIMPLE_QUEUE → configuración de cola
            # -------------------------------------------------
            if service_data.get("service_type") == "simple_queue":
                self._apply_simple_queue_on_router(
                    new_service.model_dump(), service_data
                )
                # No necesitamos nada más para simple_queue
                return new_service.model_dump()

            # -------------------------------------------------
            # 2️⃣  Si es PPPoE → crear/adoptar secret y guardar su ID
            # -------------------------------------------------
            if service_data.get("service_type") == "pppoe":
                # Necesitamos los datos del router
                router_host = service_data.get("router_host")
                if not router_host:
                    raise ValueError("router_host es requerido para PPPoE")

                username = service_data.get("pppoe_username")
                if not username:
                    raise ValueError("pppoe_username es requerido para PPPoE")

                # Obtener credenciales del router desde la BD
                router_obj: Router = self.session.get(Router, router_host)
                if not router_obj:
                    raise ValueError(f"Router {router_host} no encontrado en BD")

                secret_id = None
                with RouterService(router_host, router_obj) as rs:
                    # Verificar si el secret ya existe
                    existing_secrets = rs.get_pppoe_secrets(username=username)
                    
                    if existing_secrets:
                        secret_id = existing_secrets[0].get("id") # CORRECCIÓN: de .id a id
                        logger.info(
                            f"ℹ️  Secret PPPoE para '{username}' ya existe en el router. Adoptando ID: {secret_id}"
                        )
                    else:
                        # Crear el secret si no existe
                        secret = rs.create_pppoe_secret(
                            username=username,
                            password=service_data.get("router_secret_password", ""),
                            profile=service_data.get("profile_name", ""),
                            service_name=service_data.get("service_name", ""),
                        )
                        # La creación puede devolver una lista o un dict
                        if isinstance(secret, list) and secret:
                            secret_id = secret[0].get("id")
                        elif isinstance(secret, dict):
                            secret_id = secret.get("id")

                        if not secret_id:
                            raise RuntimeError(
                                f"No se obtuvo 'id' del secret PPPoE creado. Respuesta del router: {secret}"
                            )
                        logger.info(
                            f"✅ Secret PPPoE creado en router {router_host} → id={secret_id}"
                        )

                # Guardar router_secret_id en la tabla
                new_service.router_secret_id = secret_id
                self.session.add(new_service)
                self.session.commit()
                self.session.refresh(new_service)

                logger.info(
                    f"🔧 router_secret_id actualizado en DB para service_id={new_service.id}"
                )
                return new_service.model_dump()

            # Si llega aquí, el tipo no es ni simple_queue ni pppoe
            return new_service.model_dump()

        except Exception as e:
            self.session.rollback()
            # Mensajes claros para el frontend
            if "UNIQUE constraint failed: client_services.pppoe_username" in str(e):
                raise ValueError(
                    f"El nombre de usuario PPPoE '{service_data.get('pppoe_username')}' ya existe en la base de datos local."
                )
            raise ValueError(f"Error al crear servicio: {e}")
    
    def _apply_simple_queue_on_router(
        self, service_db_obj: Dict[str, Any], service_input: Dict[str, Any]
    ):
        """Apply simple queue configuration on router."""
        plan_id = service_input.get("plan_id")
        if not plan_id:
            raise ValueError("Se requiere un plan_id para servicios de cola simple")

        plan = plans_db.get_plan_by_id(plan_id)
        if not plan:
            raise ValueError(f"Plan con ID {plan_id} no encontrado.")

        target_ip = service_input.get("ip_address")
        if not target_ip:
            raise ValueError(
                "Se requiere una dirección IP (target) para servicios de cola simple"
            )

        router_host = service_input["router_host"]
        
        # Obtener credenciales del router desde la BD
        router_obj: Router = self.session.get(Router, router_host)
        if not router_obj:
            raise ValueError(f"Router {router_host} no encontrado en BD")

        # Correctly instantiate RouterService using a context manager
        with RouterService(router_host, router_obj) as router_service:
            queue_name = f"cli_{service_db_obj['client_id']}_srv_{service_db_obj['id']}"

            router_service.add_simple_queue(
                name=queue_name,
                target=target_ip,
                max_limit=plan["max_limit"],
                parent=plan.get("parent_queue", "none"),
                comment=f"Service {service_db_obj['id']} - Plan {plan['name']}",
            )
    
    def get_client_services(self, client_id: int) -> List[Dict[str, Any]]:
        """Get all services for a specific client."""
        statement = (
            select(ClientServiceModel)
            .where(ClientServiceModel.client_id == client_id)
            .order_by(ClientServiceModel.created_at.desc())
        )
        services = self.session.exec(statement).all()
        return [service.model_dump() for service in services]
    
    # --- Payment Methods (will be moved to PaymentService later) ---
    def get_payment_history(self, client_id: int) -> List[Dict[str, Any]]:
        """
        Get payment history for a client.
        TODO: Move to PaymentService
        """
        from ..db import payments_db
        return payments_db.get_payments_for_client(client_id)


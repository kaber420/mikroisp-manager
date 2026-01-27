# app/services/client_service.py
"""
Client service layer using SQLModel ORM.
Refactored to use SQLModel instead of raw SQL from clients_db.
"""

import logging
import uuid
from typing import Any

from sqlmodel import Session, func, select, or_

from app.models import Client

from ..models.cpe import CPE
from ..models.router import Router
from ..models.service import ClientService as ClientServiceModel
from ..services.router_service import RouterService
from .payment_service import PaymentService

logger = logging.getLogger(__name__)


class ClientService:
    """
    Service layer for Client and ClientService operations using SQLModel ORM.
    """

    def __init__(self, session: Session, payment_service: PaymentService | None = None):
        """
        Initialize with a SQLModel session.

        Args:
            session: SQLModel Session instance
            payment_service: Optional PaymentService instance (auto-created if not provided)
        """
        self.session = session
        self.payment_service = payment_service or PaymentService(session=self.session)
        from .plan_service import PlanService

        self.plan_service = PlanService(session)

    def get_clients_paginated(
        self,
        page: int = 1,
        page_size: int = 10,
        search: str | None = None,
        status_filter: str | None = None,
    ) -> dict[str, Any]:
        """
        Get paginated clients with filtering.
        """
        # Build filters
        filters = []
        if search:
            search_term = f"%{search}%"
            filters.append(
                or_(
                    Client.name.ilike(search_term),
                    Client.address.ilike(search_term),
                    Client.phone_number.ilike(search_term),
                )
            )

        if status_filter and status_filter != "all":
            filters.append(Client.service_status == status_filter)

        # Count total items
        count_stmt = select(func.count()).select_from(Client)
        for f in filters:
            count_stmt = count_stmt.where(f)
        total_items = self.session.exec(count_stmt).one()

        # Get page items
        statement = select(Client).order_by(Client.name)
        for f in filters:
            statement = statement.where(f)

        statement = statement.offset((page - 1) * page_size).limit(page_size)
        clients = self.session.exec(statement).all()

        # Enhance with extra data
        clients_dict_list = []
        for client in clients:
            client_dict = client.model_dump()
            
            # CPE Count
            cpe_count_stmt = select(func.count()).select_from(CPE).where(CPE.client_id == client.id)
            client_dict["cpe_count"] = self.session.exec(cpe_count_stmt).one()

            # Billing Day from latest service
            service_stmt = (
                select(ClientServiceModel)
                .where(ClientServiceModel.client_id == client.id)
                .order_by(ClientServiceModel.created_at.desc())
                .limit(1)
            )
            latest_service = self.session.exec(service_stmt).first()
            if latest_service and latest_service.billing_day:
                client_dict["billing_day"] = latest_service.billing_day

            clients_dict_list.append(client_dict)

        total_pages = (total_items + page_size - 1) // page_size if page_size > 0 else 1

        return {
            "items": clients_dict_list,
            "total": total_items,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    def get_all_clients(self) -> list[dict[str, Any]]:
        """
        Get all clients with their CPE count.
        """
        statement = select(Client).order_by(Client.name)
        clients = self.session.exec(statement).all()

        # Convert to dict format for compatibility
        clients_dict = []
        for client in clients:
            client_dict = client.model_dump()
            cpe_count_stmt = select(func.count()).select_from(CPE).where(CPE.client_id == client.id)
            client_dict["cpe_count"] = self.session.exec(cpe_count_stmt).one()

            # Fetch billing_day from latest service
            service_stmt = (
                select(ClientServiceModel)
                .where(ClientServiceModel.client_id == client.id)
                .order_by(ClientServiceModel.created_at.desc())
                .limit(1)
            )
            latest_service = self.session.exec(service_stmt).first()
            if latest_service and latest_service.billing_day:
                client_dict["billing_day"] = latest_service.billing_day

            clients_dict.append(client_dict)

        return clients_dict

    def get_client_by_id(self, client_id: uuid.UUID) -> dict[str, Any]:
        """Get a single client by ID."""
        client = self.session.get(Client, client_id)
        if not client:
            raise FileNotFoundError(f"Client {client_id} not found.")
        return client.model_dump()

    def create_client(self, client_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new client."""
        try:
            client_data_clean = {k: v for k, v in client_data.items() if k != "id"}

            new_client = Client(**client_data_clean)
            self.session.add(new_client)
            self.session.commit()
            self.session.refresh(new_client)

            result = new_client.model_dump()
            result["cpe_count"] = 0
            return result
        except Exception as e:
            self.session.rollback()
            raise ValueError(f"Database error: {e}")

    def update_client(self, client_id: uuid.UUID, client_update: dict[str, Any]) -> dict[str, Any]:
        """Update an existing client."""
        if not client_update:
            raise ValueError("No fields to update provided.")

        client = self.session.get(Client, client_id)
        if not client:
            raise FileNotFoundError("Client not found.")

        # Update fields
        for key, value in client_update.items():
            if hasattr(client, key) and key != "id":
                setattr(client, key, value)

        self.session.add(client)
        self.session.commit()
        self.session.refresh(client)

        result = client.model_dump()
        result["cpe_count"] = 0
        return result

    def delete_client(self, client_id: uuid.UUID):
        """Delete a client."""
        client = self.session.get(Client, client_id)
        if not client:
            raise FileNotFoundError("Client not found to delete.")

        self.session.delete(client)
        self.session.commit()

    def get_cpes_for_client(self, client_id: uuid.UUID) -> list[dict[str, Any]]:
        """
        Get CPEs for a client using SQLModel.
        """
        statement = select(CPE).where(CPE.client_id == client_id).order_by(CPE.hostname)
        cpes = self.session.exec(statement).all()
        return [cpe.model_dump() for cpe in cpes]

    # --- Service Methods ---
    def create_client_service(
        self, client_id: uuid.UUID, service_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Crea un nuevo servicio para un cliente.
        - Si el tipo es PPPoE, crea o adopta el secret en el router.
        - Si el tipo es simple_queue, aplica la configuración de cola.
        Note: suspension_method is now determined by the Plan, not the service.
        """
        try:
            service_data_full = {**service_data, "client_id": client_id}
            service_data_full.pop("id", None)

            # Set default suspension_method for backward compatibility
            # (The actual method used comes from the Plan, this is legacy)
            if "suspension_method" not in service_data_full:
                service_data_full["suspension_method"] = "queue_limit"

            new_service = ClientServiceModel(**service_data_full)
            self.session.add(new_service)
            self.session.commit()
            self.session.refresh(new_service)

            if service_data.get("service_type") == "simple_queue":
                self._apply_simple_queue_on_router(new_service.model_dump(), service_data)
                return new_service.model_dump()

            if service_data.get("service_type") == "pppoe":
                router_host = service_data.get("router_host")
                if not router_host:
                    raise ValueError("router_host es requerido para PPPoE")

                username = service_data.get("pppoe_username")
                if not username:
                    raise ValueError("pppoe_username es requerido para PPPoE")

                router_obj: Router = self.session.get(Router, router_host)
                if not router_obj:
                    raise ValueError(f"Router {router_host} no encontrado en BD")

                secret_id = None
                with RouterService(router_host, router_obj) as rs:
                    existing_secrets = rs.get_pppoe_secrets(username=username)

                    if existing_secrets:
                        secret_id = existing_secrets[0].get("id")  # CORRECCIÓN: de .id a id
                        logger.info(
                            f"ℹ️  Secret PPPoE para '{username}' ya existe en el router. Adoptando ID: {secret_id}"
                        )
                    else:
                        secret = rs.create_pppoe_secret(
                            username=username,
                            password=service_data.get("router_secret_password", ""),
                            profile=service_data.get("profile_name", ""),
                            service_name=service_data.get("service_name", ""),
                        )
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

                new_service.router_secret_id = secret_id
                self.session.add(new_service)
                self.session.commit()
                self.session.refresh(new_service)

                return new_service.model_dump()

            return new_service.model_dump()

        except Exception as e:
            self.session.rollback()
            self.session.rollback()
            if "UNIQUE constraint failed: client_services.pppoe_username" in str(e):
                raise ValueError(
                    f"El nombre de usuario PPPoE '{service_data.get('pppoe_username')}' ya existe en la base de datos local."
                )
            raise ValueError(f"Error al crear servicio: {e}")

    def _get_queue_type_for_router(self, plan: dict[str, Any], router: Router) -> str:
        """
        Determines the appropriate queue type based on router firmware version.
        
        Args:
            plan: Plan dict with v6_queue_type and v7_queue_type
            router: Router model with firmware field
            
        Returns:
            Queue type string (e.g., "default-small" or "cake-default")
        """
        firmware = router.firmware
        
        if firmware:
            # RouterOS v7 firmware typically starts with "7." or contains "v7"
            firmware_lower = firmware.lower()
            if firmware_lower.startswith("7.") or "ros7" in firmware_lower or "/7." in firmware_lower:
                logger.info(f"🔧 Router {router.host} detected as v7 (firmware: {firmware})")
                return plan.get("v7_queue_type") or "cake-default"
            else:
                logger.info(f"🔧 Router {router.host} detected as v6 (firmware: {firmware})")
                return plan.get("v6_queue_type") or "default-small"
        
        # Fallback: assume v6 if firmware is unknown
        logger.warning(f"⚠️ Router {router.host} firmware unknown, defaulting to v6 queue type")
        return plan.get("v6_queue_type") or "default-small"

    def _apply_simple_queue_on_router(
        self, service_db_obj: dict[str, Any], service_input: dict[str, Any]
    ):
        """Apply simple queue configuration on router."""
        plan_id = service_input.get("plan_id")
        if not plan_id:
            raise ValueError("Se requiere un plan_id para servicios de cola simple")

        plan_obj = self.plan_service.get_by_id(plan_id)
        # Convert to dict for compatibility with existing code
        plan = plan_obj.model_dump()

        target_ip = service_input.get("ip_address")
        if not target_ip:
            raise ValueError("Se requiere una dirección IP (target) para servicios de cola simple")

        router_host = service_input["router_host"]

        router_obj: Router = self.session.get(Router, router_host)
        if not router_obj:
            raise ValueError(f"Router {router_host} no encontrado en BD")

        # Determine queue type based on router version (for Universal Plans)
        queue_type = self._get_queue_type_for_router(plan, router_obj)
        logger.info(f"📊 Using queue type '{queue_type}' for router {router_host}")

        # Fetch Client to get the name
        client = self.session.get(Client, service_db_obj['client_id'])
        if not client:
             raise ValueError(f"Client {service_db_obj['client_id']} not found")

        queue_name = client.name
        # Sanitize queue name? Mikrotik accepts spaces but let's be safe if it's empty
        if not queue_name:
            queue_name = f"cli_{service_db_obj['client_id']}"

        queue_comment = f"ID: {client.id} | Plan: {plan['name']} | Service: {service_db_obj['id']}"

        # Correctly instantiate RouterService using a context manager
        with RouterService(router_host, router_obj) as router_service:
            
            # Check for existing queue with different name (duplicate cleanup)
            existing_by_ip = router_service.get_simple_queue_stats(target_ip)
            if existing_by_ip:
                existing_name = existing_by_ip.get('name')
                existing_id = existing_by_ip.get('.id') or existing_by_ip.get('id')
                
                if existing_name != queue_name:
                    logger.warning(f"⚠️ Found duplicate queue for IP {target_ip} with name '{existing_name}'. Removing it to enforce unique queue per IP.")
                    router_service.remove_simple_queue(existing_id)

            router_service.add_simple_queue(
                name=queue_name,
                target=target_ip,
                max_limit=plan["max_limit"],
                parent=plan.get("parent_queue", "none"),
                comment=queue_comment,
                queue_type=queue_type,
            )

    def get_client_services(self, client_id: uuid.UUID) -> list[dict[str, Any]]:
        """Get all services for a specific client, including plan names and prices."""
        statement = (
            select(ClientServiceModel)
            .where(ClientServiceModel.client_id == client_id)
            .order_by(ClientServiceModel.created_at.desc())
        )
        services = self.session.exec(statement).all()

        result = []
        for service in services:
            service_dict = service.model_dump()
            # Fetch plan name and price if plan_id is set
            if service.plan_id:
                try:
                    plan = self.plan_service.get_by_id(service.plan_id)
                    service_dict["plan_name"] = plan.name
                    service_dict["plan_price"] = plan.price
                except Exception:
                    service_dict["plan_name"] = None
                    service_dict["plan_price"] = None
            else:
                service_dict["plan_name"] = None
                service_dict["plan_price"] = None
            result.append(service_dict)

        return result

    # --- Payment Methods ---
    def get_payment_history(self, client_id: uuid.UUID) -> list[dict[str, Any]]:
        """
        Get payment history for a client using PaymentService (SQLModel).

        Returns:
            List of payment records, most recent first
        """
        return self.payment_service.get_payments_for_client(client_id)

    # --- Plan Change Methods ---
    def change_client_service_plan(self, service_id: int, new_plan_id: int) -> dict[str, Any]:
        """
        Changes the plan for an existing client service.

        - Updates the plan_id in the database
        - For PPPoE: Updates the profile on the router and kills connection
        - For Simple Queue: Updates the queue limit on the router

        Args:
            service_id: ID of the client service to update
            new_plan_id: ID of the new plan to assign

        Returns:
            dict with status and details of actions taken
        """
        # Get the service
        service = self.session.get(ClientServiceModel, service_id)
        if not service:
            raise FileNotFoundError(f"Service {service_id} not found")

        # Get the new plan
        new_plan_obj = self.plan_service.get_by_id(new_plan_id)
        new_plan = new_plan_obj.model_dump()

        old_plan_id = service.plan_id
        router_host = service.router_host

        # Get router credentials
        router = self.session.get(Router, router_host)
        if not router:
            raise ValueError(f"Router {router_host} not found")

        results = {
            "service_id": service_id,
            "old_plan_id": old_plan_id,
            "new_plan_id": new_plan_id,
            "router_updates": {},
        }

        with RouterService(router_host, router) as rs:
            # PPPoE: Update profile and kill connection
            if service.service_type == "pppoe" and service.pppoe_username:
                profile_name = (
                    new_plan.get("profile_name")
                    or f"profile-{new_plan['name'].lower().replace(' ', '-')}"
                )

                logger.info(
                    f"📊 Changing PPPoE profile for {service.pppoe_username} to {profile_name}"
                )
                results["router_updates"]["profile"] = rs.update_pppoe_profile(
                    username=service.pppoe_username, new_profile=profile_name
                )

                # Kill connection to force re-auth with new profile
                logger.info(f"🔪 Killing PPPoE connection for {service.pppoe_username}")
                results["router_updates"]["kill"] = rs.kill_pppoe_connection(service.pppoe_username)

            # Simple Queue: Update limit
            elif service.service_type == "simple_queue" and service.ip_address:
                max_limit = new_plan.get("max_limit", "10M/10M")

                logger.info(f"📊 Updating queue limit for {service.ip_address} to {max_limit}")
                results["router_updates"]["queue"] = rs.update_queue_limit(
                    target=service.ip_address, max_limit=max_limit
                )

        # Update database
        service.plan_id = new_plan_id
        self.session.add(service)
        self.session.commit()
        self.session.refresh(service)

        results["service"] = service.model_dump()
        logger.info(
            f"✅ Plan change completed for service {service_id}: {old_plan_id} → {new_plan_id}"
        )

        return results

    def change_pppoe_service_profile(self, service_id: int, new_profile: str) -> dict[str, Any]:
        """
        Changes the PPPoE profile for a service directly by profile name.

        This is used when selecting a profile from the router rather than
        a plan from the local database.

        Args:
            service_id: ID of the client service to update
            new_profile: Name of the PPPoE profile on the router

        Returns:
            dict with status and details of actions taken
        """
        # Get the service
        service = self.session.get(ClientServiceModel, service_id)
        if not service:
            raise FileNotFoundError(f"Service {service_id} not found")

        if service.service_type != "pppoe":
            raise ValueError("This method is only for PPPoE services")

        if not service.pppoe_username:
            raise ValueError("Service does not have a PPPoE username")

        router_host = service.router_host

        # Get router credentials
        router = self.session.get(Router, router_host)
        if not router:
            raise ValueError(f"Router {router_host} not found")

        old_profile = service.profile_name

        results = {
            "service_id": service_id,
            "old_profile": old_profile,
            "new_profile": new_profile,
            "router_updates": {},
        }

        with RouterService(router_host, router) as rs:
            # Update profile on router and kill connection
            logger.info(f"📊 Changing PPPoE profile for {service.pppoe_username} to {new_profile}")
            results["router_updates"]["profile"] = rs.update_pppoe_profile(
                username=service.pppoe_username, new_profile=new_profile
            )

            # Kill connection to force re-auth with new profile
            logger.info(f"🔪 Killing PPPoE connection for {service.pppoe_username}")
            results["router_updates"]["kill"] = rs.kill_pppoe_connection(service.pppoe_username)

        # Update database with new profile name
        service.profile_name = new_profile
        self.session.add(service)
        self.session.commit()
        self.session.refresh(service)

        results["service"] = service.model_dump()
        logger.info(
            f"✅ PPPoE profile change completed for service {service_id}: {old_profile} → {new_profile}"
        )

        return results

    def update_client_service(self, service_id: int, update_data: dict[str, Any]) -> dict[str, Any]:
        """
        Update an existing client service.

        Args:
            service_id: ID of the service to update
            update_data: Fields to update

        Returns:
            Updated service as dict
        """
        service = self.session.get(ClientServiceModel, service_id)
        if not service:
            raise FileNotFoundError(f"Service {service_id} not found")

        # Fields that cannot be updated
        protected_fields = {"id", "client_id", "created_at"}

        for key, value in update_data.items():
            if hasattr(service, key) and key not in protected_fields:
                setattr(service, key, value)

        self.session.add(service)
        self.session.commit()
        self.session.refresh(service)

        logger.info(f"✅ Service {service_id} updated successfully")
        return service.model_dump()

    def delete_client_service(self, service_id: int) -> None:
        """
        Delete a client service.

        For PPPoE services, this will also attempt to remove the secret from
        the router if router_secret_id is set.

        Args:
            service_id: ID of the service to delete
        """
        service = self.session.get(ClientServiceModel, service_id)
        if not service:
            raise FileNotFoundError(f"Service {service_id} not found")

        # If it's a PPPoE service with a router secret, try to remove it
        if service.service_type == "pppoe" and service.router_secret_id and service.router_host:
            try:
                router = self.session.get(Router, service.router_host)
                if router:
                    with RouterService(service.router_host, router) as rs:
                        rs.remove_pppoe_secret(service.router_secret_id)
                        logger.info(
                            f"🗑️ Deleted PPPoE secret {service.router_secret_id} from router {service.router_host}"
                        )
            except Exception as e:
                # Log but don't fail the deletion
                logger.warning(f"⚠️ Could not delete PPPoE secret from router: {e}")

        self.session.delete(service)
        self.session.commit()

        logger.info(f"🗑️ Service {service_id} deleted successfully")

    def sync_client_service_to_router(self, service_id: int) -> dict[str, Any]:
        """
        Synchronize a client service configuration to the router.
        
        This method re-applies the service configuration to the router,
        useful when the original provisioning failed or was incomplete.
        
        Args:
            service_id: ID of the service to sync
            
        Returns:
            dict with sync status and details
        """
        service = self.session.get(ClientServiceModel, service_id)
        if not service:
            raise FileNotFoundError(f"Service {service_id} not found")
        
        router_host = service.router_host
        if not router_host:
            raise ValueError("Service has no router_host configured")
        
        router = self.session.get(Router, router_host)
        if not router:
            raise ValueError(f"Router {router_host} not found")
        
        results = {
            "service_id": service_id,
            "service_type": service.service_type,
            "router_host": router_host,
            "actions": [],
        }
        
        if service.service_type == "simple_queue":
            # Sync Simple Queue
            if not service.plan_id:
                raise ValueError("Service has no plan_id configured")
            
            plan_obj = self.plan_service.get_by_id(service.plan_id)
            plan = plan_obj.model_dump()
            
            if not service.ip_address:
                raise ValueError("Service has no IP address configured")
            
            queue_type = self._get_queue_type_for_router(plan, router)

            # Fetch Client to get the name
            client = self.session.get(Client, service.client_id)
            if not client:
                 raise ValueError(f"Client {service.client_id} not found")

            queue_name = client.name
            if not queue_name:
                 queue_name = f"cli_{service.client_id}"

            queue_comment = f"ID: {client.id} | Plan: {plan['name']} | Service: {service.id}"
            
            with RouterService(router_host, router) as rs:
                # Check for existing queue by IP (duplicate cleanup)
                existing_by_ip = rs.get_simple_queue_stats(service.ip_address)
                if existing_by_ip:
                    existing_name = existing_by_ip.get('name')
                    existing_id = existing_by_ip.get('.id') or existing_by_ip.get('id')
                    
                    if existing_name != queue_name:
                        logger.warning(f"⚠️ Found duplicate queue for IP {service.ip_address} with name '{existing_name}'. Removing it to enforce unique queue per IP.")
                        rs.remove_simple_queue(existing_id)

                result = rs.add_simple_queue(
                    name=queue_name,
                    target=service.ip_address,
                    max_limit=plan["max_limit"],
                    parent=plan.get("parent_queue", "none"),
                    comment=queue_comment,
                    queue_type=queue_type,
                )
                results["actions"].append({
                    "action": "sync_simple_queue",
                    "queue_name": queue_name,
                    "target": service.ip_address,
                    "max_limit": plan["max_limit"],
                    "queue_type": queue_type,
                    "result": result,
                })
            
            logger.info(f"🔄 Synced Simple Queue service {service_id} to router {router_host}")
            
        elif service.service_type == "pppoe":
            # Sync PPPoE secret
            username = service.pppoe_username
            if not username:
                raise ValueError("PPPoE service has no username configured")
            
            with RouterService(router_host, router) as rs:
                # Check if secret exists
                existing = rs.get_pppoe_secrets(username=username)
                
                if existing:
                    results["actions"].append({
                        "action": "pppoe_secret_exists",
                        "username": username,
                        "message": "PPPoE secret already exists on router"
                    })
                    logger.info(f"ℹ️ PPPoE secret '{username}' already exists on router")
                else:
                    # Get profile name from plan if available
                    profile_name = service.profile_name or "default"
                    if service.plan_id:
                        plan_obj = self.plan_service.get_by_id(service.plan_id)
                        profile_name = plan_obj.profile_name or profile_name
                    
                    # Create secret
                    secret = rs.create_pppoe_secret(
                        username=username,
                        password="",  # Empty password - admin must set
                        profile=profile_name,
                        service_name="",
                    )
                    
                    results["actions"].append({
                        "action": "create_pppoe_secret",
                        "username": username,
                        "profile": profile_name,
                        "result": secret,
                    })
                    logger.info(f"✅ Created PPPoE secret '{username}' on router {router_host}")
        
        results["status"] = "success"
        results["message"] = f"Service {service_id} synchronized to router"
        return results

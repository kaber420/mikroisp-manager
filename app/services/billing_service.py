# app/services/billing_service.py
"""
Billing service for managing client billing, payments, and service suspensions.
Refactored to use SQLModel ORM.
"""

import logging
import uuid
from datetime import datetime
from typing import Any

from sqlmodel import Session

from ..db import settings_db  # Keep until migrated
from ..models.router import Router
from .client_service import ClientService
from .payment_service import PaymentService
from .router_service import RouterService

logger = logging.getLogger(__name__)


class BillingService:
    """
    Service for billing operations using SQLModel ORM.
    """

    def __init__(self, session: Session):
        """
        Initialize with a SQLModel session.

        Args:
            session: SQLModel Session instance
        """
        self.session = session
        self.client_service = ClientService(session)
        self.payment_service = PaymentService(session)
        # Import here to avoid circular dependency
        from .plan_service import PlanService

        self.plan_service = PlanService(session)

    def _get_router_by_host(self, host: str) -> Router:
        """Helper to get router credentials from database."""
        router = self.session.get(Router, host)
        if not router:
            raise ValueError(f"Router {host} not found in database")
        return router

    def reactivate_client_services(
        self, client_id: uuid.UUID, payment_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Register a payment and reactivate service if necessary.
        """
        # 1. Get current client status
        client = self.client_service.get_client_by_id(client_id)
        if not client:
            raise ValueError(f"Cliente {client_id} no encontrado.")

        previous_status = client.get("service_status")

        # 2. Register payment (always done)
        new_payment = self.payment_service.create_payment(client_id, payment_data)
        logger.info(f"Pago registrado (ID: {new_payment['id']}) para el cliente {client_id}.")

        # 3. Update status to 'active' in DB (always done)
        self.client_service.update_client(client_id, {"service_status": "active"})

        # 4. Technical reactivation (only if was suspended or cancelled)
        if previous_status in ["suspended", "cancelled"]:
            logger.info(
                f"El cliente estaba '{previous_status}'. Iniciando reactivación técnica en router..."
            )
            services = self.client_service.get_client_services(client_id)

            activation_errors = []
            if services:
                for service in services:
                    try:
                        host = service["router_host"]
                        ip = service.get("ip_address")

                        # Get suspension method from PLAN (not service)
                        method = None
                        plan_obj = None
                        if service.get("plan_id"):
                            plan_obj = self.plan_service.get_by_id(service["plan_id"])
                            if plan_obj:
                                method = getattr(plan_obj, "suspension_method", None)

                        # Fallback to service's method for backward compatibility
                        if not method:
                            method = service.get("suspension_method", "queue_limit")

                        # Get router credentials
                        router = self._get_router_by_host(host)

                        with RouterService(host, router) as rs:
                            if method == "address_list" and ip:
                                # Get address list config from plan
                                plan_strategy = (
                                    getattr(plan_obj, "address_list_strategy", "blacklist")
                                    if plan_obj
                                    else "blacklist"
                                )
                                plan_list_name = (
                                    getattr(plan_obj, "address_list_name", "morosos")
                                    if plan_obj
                                    else "morosos"
                                )

                                rs.activate_user_address_list(
                                    ip, list_name=plan_list_name, strategy=plan_strategy
                                )
                                logger.info(
                                    f"Servicio {service['id']} (IP: {ip}) reactivado via Address List."
                                )

                            elif method == "queue_limit" and ip:
                                # Need to know the original plan speed
                                plan_obj = self.plan_service.get_by_id(service["plan_id"])
                                plan = plan_obj.model_dump()
                                if plan:
                                    rs.activate_user_limit(ip, plan["max_limit"])
                                    logger.info(
                                        f"Servicio {service['id']} (IP: {ip}) reactivado via Queue Limit."
                                    )
                                else:
                                    logger.warning(
                                        f"No se encontró plan para el servicio {service['id']}, no se pudo restaurar el límite de velocidad."
                                    )

                            elif method == "pppoe_secret_disable":
                                if service.get("router_secret_id"):
                                    rs.set_pppoe_secret_status(
                                        service["router_secret_id"], disable=False
                                    )
                                    logger.info(
                                        f"Servicio PPPoE reactivado para {service.get('pppoe_username', 'N/A')}"
                                    )

                    except Exception as e:
                        logger.error(f"Error reactivando servicio {service['id']}: {e}")
                        activation_errors.append(str(e))

            if activation_errors:
                # Leave note in payment if there was technical error
                notas = new_payment.get("notas", "") or ""
                self.payment_service.update_payment_notes(
                    new_payment["id"],
                    f"{notas}\nWARN: Fallo reactivación técnica.".strip(),
                )
        else:
            logger.info(
                f"El cliente estaba '{previous_status}'. No se requiere acción en el router."
            )

        return new_payment

    def process_daily_suspensions(self) -> dict[str, int]:
        """
        Review ALL clients and update their status (Active/ Pending/Suspended).
        """
        logger.info("Iniciando auditoría de estados de facturación...")

        try:
            days_before = int(settings_db.get_setting("days_before_due") or 5)
        except ValueError:
            days_before = 5

        today = datetime.now().date()
        all_clients = self.client_service.get_all_clients()
        stats = {"active": 0, "pendiente": 0, "suspended": 0, "processed": 0}

        for client in all_clients:
            if client["service_status"] == "cancelled":
                continue

            cid = client["id"]
            billing_day = client["billing_day"]

            if not billing_day:
                continue

            try:
                due_date = today.replace(day=billing_day)
            except ValueError:
                due_date = today.replace(day=28)

            # Billing cycle is usually "current month" for recurring services
            cycle_str = due_date.strftime("%Y-%m")
            has_paid = self.payment_service.check_payment_exists(cid, cycle_str)

            new_status = client["service_status"]
            should_suspend_technically = False

            if has_paid:
                if new_status != "active":
                    new_status = "active"
                    # If paid, technically reactivate in case it was cut
                    self._ensure_service_enabled(cid)
            else:
                # Calculate day difference
                days_diff = (due_date - today).days

                if days_diff < 0:
                    # Past due date -> SUSPEND
                    if new_status != "suspended":
                        new_status = "suspended"
                        should_suspend_technically = True

                elif days_diff <= days_before:
                    # X days remaining -> PENDING
                    if new_status != "suspended":
                        new_status = "pendiente"

                else:
                    # Many days remaining -> ACTIVE (assuming previous cycle ok)
                    if new_status == "pendiente":
                        new_status = "active"

            if new_status != client["service_status"]:
                self.client_service.update_client(cid, {"service_status": new_status})
                if should_suspend_technically:
                    self._suspend_technically(cid)

            stats[new_status] = stats.get(new_status, 0) + 1
            stats["processed"] += 1

        return stats

    def _suspend_technically(self, client_id: uuid.UUID):
        """Suspend service according to configured method."""
        logger.info(f"🔴 _suspend_technically called for client_id={client_id}")
        services = self.client_service.get_client_services(client_id)
        logger.info(f"🔴 Found {len(services)} services for client {client_id}")

        for service in services:
            try:
                host = service["router_host"]
                ip = service.get("ip_address")
                secret_id = service.get("router_secret_id")
                pppoe_username = service.get("pppoe_username")

                # Get suspension method from PLAN (not service)
                method = None
                plan_obj = None
                if service.get("plan_id"):
                    plan_obj = self.plan_service.get_by_id(service["plan_id"])
                    if plan_obj:
                        method = getattr(plan_obj, "suspension_method", None)

                # Fallback to service's method for backward compatibility
                if not method:
                    method = service.get("suspension_method", "queue_limit")

                logger.info(
                    f"🔴 Processing service {service['id']}: method={method}, host={host}, ip={ip}, secret_id={secret_id}"
                )

                # Get router credentials from database
                router = self._get_router_by_host(host)
                logger.info(f"🔴 Router credentials fetched for {host}")

                with RouterService(host, router) as rs:
                    # CASE 1: Address List (Total cut with warning)
                    if method == "address_list" and ip:
                        # Get address list config from plan
                        plan_strategy = (
                            getattr(plan_obj, "address_list_strategy", "blacklist")
                            if plan_obj
                            else "blacklist"
                        )
                        plan_list_name = (
                            getattr(plan_obj, "address_list_name", "morosos")
                            if plan_obj
                            else "morosos"
                        )

                        logger.info(
                            f"🔴 Suspending via address_list: {ip} (Plan: {plan_list_name}/{plan_strategy})"
                        )
                        rs.suspend_user_address_list(
                            ip, list_name=plan_list_name, strategy=plan_strategy
                        )
                        logger.info(f"✅ Address list suspension completed for {ip}")

                    # CASE 2: Queue Limit (Extreme slowness)
                    elif method == "queue_limit" and ip:
                        logger.info(f"🔴 Suspending via queue_limit: {ip}")
                        rs.suspend_user_limit(ip)
                        logger.info(f"✅ Queue limit suspension completed for {ip}")

                    # CASE 3: PPPoE (The classic)
                    elif method == "pppoe_secret_disable":
                        logger.info(
                            f"🔴 Suspending via pppoe_secret_disable: secret_id={secret_id}"
                        )
                        if secret_id:
                            rs.set_pppoe_secret_status(secret_id, disable=True)
                            logger.info(f"✅ PPPoE secret {secret_id} disabled successfully")
                        else:
                            logger.warning(
                                f"⚠️ No router_secret_id found for service {service['id']}"
                            )
                    else:
                        logger.warning(
                            f"⚠️ Suspension method '{method}' not handled or missing required data"
                        )

                    # Kill active PPPoE connection to force immediate disconnect
                    if pppoe_username:
                        logger.info(f"🔪 Killing active PPPoE connection for {pppoe_username}")
                        kill_result = rs.kill_pppoe_connection(pppoe_username)
                        logger.info(f"✅ PPPoE connection kill result: {kill_result}")

            except Exception as e:
                logger.error(f"❌ Error suspendiendo servicio {service['id']}: {e}", exc_info=True)

    def _ensure_service_enabled(self, client_id: uuid.UUID):
        """Helper to ensure service is active (useful for nightly sweep)."""
        services = self.client_service.get_client_services(client_id)
        for service in services:
            try:
                if service["service_type"] == "pppoe" and service["router_secret_id"]:
                    # Get router credentials
                    router = self._get_router_by_host(service["router_host"])

                    # Only activate if not active, but RouterOS handles idempotency well
                    with RouterService(service["router_host"], router) as rs:
                        rs.set_pppoe_secret_status(
                            secret_id=service["router_secret_id"], disable=False
                        )
            except Exception as e:
                logger.error(f"Error asegurando servicio activo {service['id']}: {e}")

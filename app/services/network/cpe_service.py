
import os
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlmodel import Session, func, select

from ...core.constants import CPEStatus
from ...core.exceptions import InvalidOperationError, DeviceNotFoundError
from ...models.cpe import CPE
from ...models.stats import CPEStats, APStats # Import stats models
from ...models.ap import AP


class CPEService:
    def __init__(self, session: Session):
        self.session = session

    def get_unassigned_cpes(self) -> list[CPE]:
        """Obtiene todos los CPEs que no están asignados a ningún cliente."""
        statement = select(CPE).where(CPE.client_id == None).order_by(CPE.hostname)
        return list(self.session.exec(statement).all())

    def get_cpe_by_mac(self, mac: str) -> CPE | None:
        """Obtiene un CPE por su dirección MAC."""
        return self.session.get(CPE, mac)

    def assign_cpe_to_client(self, mac: str, client_id: uuid.UUID) -> CPE:
        """Asigna un CPE a un cliente."""
        cpe = self.session.get(CPE, mac)
        if not cpe:
            raise DeviceNotFoundError("CPE not found.")

        cpe.client_id = client_id
        self.session.add(cpe)
        self.session.commit()
        self.session.refresh(cpe)
        return cpe

    def unassign_cpe(self, mac: str) -> CPE:
        """Desasigna un CPE de cualquier cliente."""
        cpe = self.session.get(CPE, mac)
        if not cpe:
            raise DeviceNotFoundError("CPE not found.")

        cpe.client_id = None
        self.session.add(cpe)
        self.session.commit()
        self.session.refresh(cpe)
        return cpe

    def disable_cpe(self, mac: str) -> bool:
        """Deshabilita un CPE (soft-delete) en la base de datos."""
        cpe = self.session.get(CPE, mac)
        if not cpe:
            raise DeviceNotFoundError("CPE not found.")

        cpe.is_enabled = False
        self.session.add(cpe)
        self.session.commit()
        return True

    def hard_delete_cpe(self, mac: str) -> bool:
        """Elimina permanentemente un CPE de la base de datos."""
        cpe = self.session.get(CPE, mac)
        if not cpe:
            raise DeviceNotFoundError("CPE not found.")
        
        if cpe.is_enabled:
            raise InvalidOperationError("CPE must be disabled before it can be permanently deleted.")
        
        self.session.delete(cpe)
        self.session.commit()
        return True

    def get_cpes_for_client(self, client_id: uuid.UUID) -> list[CPE]:
        """Obtiene los CPEs asignados a un cliente específico."""
        statement = select(CPE).where(CPE.client_id == client_id).order_by(CPE.hostname)
        return list(self.session.exec(statement).all())

    def get_cpe_count_for_client(self, client_id: uuid.UUID) -> int:
        """Cuenta los CPEs asignados a un cliente específico."""
        statement = select(func.count()).select_from(CPE).where(CPE.client_id == client_id)
        return self.session.exec(statement).one()

    def update_cpe(self, mac: str, update_data: dict[str, Any]) -> CPE:
        """Actualiza campos de un CPE existente."""
        cpe = self.session.get(CPE, mac)
        if not cpe:
            raise DeviceNotFoundError("CPE not found.")

        allowed_fields = {"ip_address", "hostname", "model"}
        for key, value in update_data.items():
            if key in allowed_fields and value is not None:
                setattr(cpe, key, value)

        cpe.last_seen = datetime.now()
        self.session.add(cpe)
        self.session.commit()
        self.session.refresh(cpe)
        return cpe

    def get_all_cpes_globally(
        self,
        page: int = 1,
        page_size: int = 10,
        search: str | None = None,
        status_filter: str | None = None,
    ) -> dict[str, Any]:
        """
        Obtiene todos los CPEs con sus datos de estado más recientes y nombre del AP.
        Unified DB version using SQL JOINs, with pagination.
        """
        conditions = []
        params = {}

        if search:
            search_term = f"%{search}%"
            conditions.append("(c.mac LIKE :search OR c.hostname LIKE :search OR c.ip_address LIKE :search OR a.hostname LIKE :search OR s.cpe_hostname LIKE :search)")
            params["search"] = search_term

        if status_filter and status_filter != "all":
            if status_filter == "disabled":
                conditions.append("(c.is_enabled = 0 OR c.is_enabled IS FALSE)")
            else:
                conditions.append("((c.is_enabled = 1 OR c.is_enabled IS TRUE) AND c.status = :status)")
                params["status"] = status_filter

        where_clause = ""
        if conditions:
            where_clause = " WHERE " + " AND ".join(conditions)

        count_query_sql = f"""
            WITH LatestCPEStats AS (
                SELECT *, ROW_NUMBER() OVER(PARTITION BY cpe_mac ORDER BY timestamp DESC) as rn
                FROM cpestats
            )
            SELECT COUNT(*)
            FROM cpes c
            LEFT JOIN LatestCPEStats s ON s.cpe_mac = c.mac AND s.rn = 1
            LEFT JOIN aps a ON s.ap_host = a.host
            {where_clause}
        """

        count_query = text(count_query_sql)
        if params:
            count_query = count_query.bindparams(**params)
            
        total_items = self.session.exec(count_query).one()
        if isinstance(total_items, tuple) or hasattr(total_items, "__getitem__"):
            total_items = total_items[0]
            
        total_pages = (total_items + page_size - 1) // page_size if page_size > 0 else 1

        data_query_sql = f"""
            WITH LatestCPEStats AS (
                SELECT *, ROW_NUMBER() OVER(PARTITION BY cpe_mac ORDER BY timestamp DESC) as rn
                FROM cpestats
            )
            SELECT s.*, a.hostname as ap_hostname, c.is_enabled, c.status as c_status, c.last_seen,
                    c.ip_address as db_ip_address, c.mac as real_mac, c.hostname as real_hostname
            FROM cpes c
            LEFT JOIN LatestCPEStats s ON s.cpe_mac = c.mac AND s.rn = 1
            LEFT JOIN aps a ON s.ap_host = a.host
            {where_clause}
            ORDER BY c.hostname, c.mac
            LIMIT :limit OFFSET :offset
        """
        
        params["limit"] = page_size
        params["offset"] = (page - 1) * page_size
        
        data_query = text(data_query_sql)
        if params:
            data_query = data_query.bindparams(**params)
            
        cursor = self.session.exec(data_query)
        rows = []
        for row in cursor.mappings():
            cpe = dict(row)
            
            # Fallback if no stats
            if not cpe.get("cpe_mac"):
                cpe["cpe_mac"] = cpe.get("real_mac")
            if not cpe.get("cpe_hostname"):
                cpe["cpe_hostname"] = cpe.get("real_hostname")

            if not cpe.get("ip_address") and cpe.get("db_ip_address"):
                cpe["ip_address"] = cpe.get("db_ip_address")
            
            # Clean up temporary keys
            cpe.pop("db_ip_address", None)
            cpe.pop("real_mac", None)
            cpe.pop("real_hostname", None)
            cpe.pop("rn", None)
            
            c_status = cpe.pop("c_status", None)
            is_enabled = cpe.get("is_enabled")
            if is_enabled == 1 or is_enabled is True:
                is_enabled = True
            else:
                is_enabled = False

            if not is_enabled:
               cpe["status"] = CPEStatus.DISABLED
            else:
               cpe["status"] = c_status
               
            rows.append(cpe)

        return {
            "items": rows,
            "total": total_items,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    def update_inventory_from_monitor(self, data: dict):
        """
        Updates CPE inventory based on raw monitor data (dict).
        """
        now = datetime.utcnow()
        for cpe_data in data.get("wireless", {}).get("sta", []):
            mac = cpe_data.get("mac")
            remote = cpe_data.get("remote", {})
            
            if not mac:
                continue
                
            cpe = self.session.get(CPE, mac)
            if not cpe:
                cpe = CPE(mac=mac, first_seen=now)
                self.session.add(cpe)
            
            cpe.hostname = remote.get("hostname")
            cpe.model = remote.get("platform") or remote.get("model")
            cpe.firmware = cpe_data.get("version")
            cpe.ip_address = cpe_data.get("lastip")
            cpe.last_seen = now
            cpe.status = "active"
            
        self.session.commit()
        self.mark_stale_cpes_offline()

    def update_inventory_from_status(self, status):
        """
        Updates CPE inventory from a DeviceStatus object.
        """
        if not status.clients:
            self.mark_stale_cpes_offline()
            return

        now = datetime.utcnow()
        
        for client in status.clients:
            if not client.mac:
                continue
                
            cpe = self.session.get(CPE, client.mac)
            if not cpe:
                cpe = CPE(mac=client.mac, first_seen=now)
                self.session.add(cpe)
                
            if client.hostname:
                cpe.hostname = client.hostname
            
            # Safe access to extra dict
            extra = getattr(client, "extra", {}) or {}

            model = extra.get("model") or extra.get("platform")
            if model:
                cpe.model = model
                
            fw = extra.get("firmware") or extra.get("version")
            if fw:
                cpe.firmware = fw
                
            if client.ip_address:
                cpe.ip_address = client.ip_address
                
            cpe.last_seen = now
            cpe.status = "active"
            
        self.session.commit()
        self.mark_stale_cpes_offline()

    def mark_stale_cpes_offline(self):
        """
        Marks CPEs as 'offline' if they haven't been seen for configured threshold.
        """
        from datetime import timedelta
        from ...models.setting import Setting
        
        # Get settings via session
        monitor_interval_setting = self.session.get(Setting, "default_monitor_interval")
        stale_cycles_setting = self.session.get(Setting, "cpe_stale_cycles")
        
        monitor_interval = int(monitor_interval_setting.value) if monitor_interval_setting else 300
        stale_cycles = int(stale_cycles_setting.value) if stale_cycles_setting else 3
        
        threshold_seconds = monitor_interval * stale_cycles
        threshold_time = datetime.utcnow() - timedelta(seconds=threshold_seconds)
        
        statement = select(CPE).where(
            CPE.status == "active",
            CPE.is_enabled == True,
            CPE.last_seen < threshold_time
        )
        stale_cpes = self.session.exec(statement).all()
        
        for cpe in stale_cpes:
            cpe.status = "offline"
            self.session.add(cpe)
            
        if stale_cpes:
            self.session.commit()

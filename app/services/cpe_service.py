
import os
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlmodel import Session, func, select

from ..core.constants import CPEStatus
from ..models.cpe import CPE
from ..models.stats import CPEStats, APStats # Import stats models
from ..models.ap import AP


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
            raise FileNotFoundError("CPE not found.")

        cpe.client_id = client_id
        self.session.add(cpe)
        self.session.commit()
        self.session.refresh(cpe)
        return cpe

    def unassign_cpe(self, mac: str) -> CPE:
        """Desasigna un CPE de cualquier cliente."""
        cpe = self.session.get(CPE, mac)
        if not cpe:
            raise FileNotFoundError("CPE not found.")

        cpe.client_id = None
        self.session.add(cpe)
        self.session.commit()
        self.session.refresh(cpe)
        return cpe

    def disable_cpe(self, mac: str) -> bool:
        """Deshabilita un CPE (soft-delete) en la base de datos."""
        cpe = self.session.get(CPE, mac)
        if not cpe:
            raise FileNotFoundError("CPE not found.")

        cpe.is_enabled = False
        self.session.add(cpe)
        self.session.commit()
        return True

    def hard_delete_cpe(self, mac: str) -> bool:
        """Elimina permanentemente un CPE de la base de datos."""
        cpe = self.session.get(CPE, mac)
        if not cpe:
            raise FileNotFoundError("CPE not found.")
        
        if cpe.is_enabled:
            raise ValueError("CPE must be disabled before it can be permanently deleted.")
        
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
            raise FileNotFoundError("CPE not found.")

        allowed_fields = {"ip_address", "hostname", "model"}
        for key, value in update_data.items():
            if key in allowed_fields and value is not None:
                setattr(cpe, key, value)

        cpe.last_seen = datetime.now()
        self.session.add(cpe)
        self.session.commit()
        self.session.refresh(cpe)
        return cpe

    def get_all_cpes_globally(self, status_filter: str | None = None) -> list[dict[str, Any]]:
        """
        Obtiene todos los CPEs con sus datos de estado más recientes y nombre del AP.
        Unified DB version using SQL JOINs.
        """
        # Note: Using raw SQL with text() because SQLModel doesn't easily support 
        # complex Window Functions + CTEs + Joins + Selecting everything easily yet.
        # But we can query from same DB now!

        query = text("""
            WITH LatestCPEStats AS (
                SELECT *, ROW_NUMBER() OVER(PARTITION BY cpe_mac ORDER BY timestamp DESC) as rn
                FROM cpestats
            )
            SELECT s.*, a.hostname as ap_hostname, c.is_enabled, c.status, c.last_seen,
                    c.ip_address as db_ip_address, c.mac as real_mac, c.hostname as real_hostname
            FROM cpes c
            LEFT JOIN LatestCPEStats s ON s.cpe_mac = c.mac AND s.rn = 1
            LEFT JOIN aps a ON s.ap_host = a.host
            ORDER BY c.hostname, c.mac;
        """)
        
        cursor = self.session.exec(query)
        rows = []
        for row in cursor.mappings():
            cpe = dict(row)
            
            # Fix keys because "SELECT s.*" brings in 'cpe_mac' and 'cpe_hostname' from stats
            # But we also have 'real_mac' and 'real_hostname' from cpes table.
            # We want to prioritize real_mac/hostname if stats are missing.
            
            # Mapping result of s.* might be prefix-less if not careful? 
            # Actually '*' in sqlalchemy text() returns columns as is.
            # If CPEStats has 'cpe_mac', it returns 'cpe_mac'.
            
            # Fallback if no stats
            if not cpe.get("cpe_mac"):
                cpe["cpe_mac"] = cpe.get("real_mac")
            if not cpe.get("cpe_hostname"):
                cpe["cpe_hostname"] = cpe.get("real_hostname")

            # Merge IP: use live IP from stats (ip_address) if available, otherwise fall back to DB IP
            # 's.*' has ip_address. 'c.ip_address' is db_ip_address.
            if not cpe.get("ip_address") and cpe.get("db_ip_address"):
                cpe["ip_address"] = cpe.get("db_ip_address")
            
            # Clean up temporary keys
            cpe.pop("db_ip_address", None)
            cpe.pop("real_mac", None)
            cpe.pop("real_hostname", None)
            cpe.pop("rn", None) # Remove row number

            # Use is_enabled to override status to 'disabled'
            is_enabled = cpe.get("is_enabled")
            # Handle boolean conversion if sqlite returns 1/0
            if is_enabled == 1 or is_enabled is True:
                is_enabled = True
            else:
                is_enabled = False

            if not is_enabled:
               cpe["status"] = CPEStatus.DISABLED
               
            # If status is not overwritten by disabled, it stays as what comes from DB ('active'/'offline')
            # The query selects c.status.
            
            rows.append(cpe)

        return self._apply_status_filter(rows, status_filter)

    def _apply_status_filter(
        self, rows: list[dict[str, Any]], status_filter: str | None
    ) -> list[dict[str, Any]]:
        """Helper to filter rows by status."""
        if not status_filter:
            return rows
        return [row for row in rows if row.get("status") == status_filter]

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
        from ..models.setting import Setting
        
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

import os
import sqlite3
import uuid
from datetime import datetime
from typing import Any

from sqlmodel import Session, func, select

from ..core.constants import CPEStatus
from ..db.base import get_db_connection, get_stats_db_file
from ..models.cpe import CPE


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
        """Elimina permanentemente un CPE de la base de datos.
        
        El CPE debe estar deshabilitado antes de poder eliminarlo.
        
        Raises:
            FileNotFoundError: Si el CPE no existe.
            ValueError: Si se intenta eliminar un CPE habilitado.
        """
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
        """
        Actualiza campos de un CPE existente (ip_address, hostname, model).

        Args:
            mac: MAC address of the CPE to update
            update_data: Dictionary with fields to update

        Returns:
            Updated CPE object
        """
        from datetime import datetime

        cpe = self.session.get(CPE, mac)
        if not cpe:
            raise FileNotFoundError("CPE not found.")

        # Only update allowed fields
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
        Obtiene todos los CPEs con sus datos de estado más recientes, nombre del AP, y estado persistido.

        Args:
            status_filter: Opcional. Filtrar por estado: 'active', 'offline', 'disabled', o None para todos.

        Returns:
            Lista de CPEs con campo 'status': 'active', 'offline', o 'disabled'.

        Nota: Esta función usa SQL crudo porque hace ATTACH DATABASE a stats_db.
        """

        stats_db_file = get_stats_db_file()

        if not os.path.exists(stats_db_file):
            # Return only CPEs from inventory (no stats available) using SQLModel
            statement = select(CPE).order_by(CPE.hostname, CPE.mac)
            results = self.session.exec(statement).all()
            
            rows = []
            for cpe_obj in results:
                cpe = cpe_obj.model_dump()
                cpe["cpe_mac"] = cpe.pop("mac")
                cpe["cpe_hostname"] = cpe.pop("hostname", None)
                
                # Use is_enabled to override status to 'disabled'
                if not cpe.get("is_enabled", True):
                    cpe["status"] = CPEStatus.DISABLED
                # status is already set from DB ('active' or 'offline')
                rows.append(cpe)
            return self._apply_status_filter(rows, status_filter)

        conn = get_db_connection()
        try:
            conn.execute(f"ATTACH DATABASE '{stats_db_file}' AS stats_db")
            query = """
                WITH LatestCPEStats AS (
                    SELECT *, ROW_NUMBER() OVER(PARTITION BY cpe_mac ORDER BY timestamp DESC) as rn
                    FROM stats_db.cpe_stats_history
                )
                SELECT s.*, a.hostname as ap_hostname, c.is_enabled, c.status, c.last_seen,
                       c.ip_address as db_ip_address
                FROM cpes c
                LEFT JOIN LatestCPEStats s ON s.cpe_mac = c.mac AND s.rn = 1
                LEFT JOIN aps a ON s.ap_host = a.host
                ORDER BY s.cpe_hostname, c.mac;
            """
            cursor = conn.execute(query)
            rows = []
            for row in cursor.fetchall():
                cpe = dict(row)
                # Merge IP: use live IP if available, otherwise fall back to DB IP
                if not cpe.get("ip_address") and cpe.get("db_ip_address"):
                    cpe["ip_address"] = cpe["db_ip_address"]
                # Clean up the temporary db_ip_address key
                cpe.pop("db_ip_address", None)
                # Use is_enabled to override status to 'disabled'
                if not cpe.get("is_enabled", True):
                    cpe["status"] = CPEStatus.DISABLED
                # status is already set from DB ('active' or 'offline')
                rows.append(cpe)
            return self._apply_status_filter(rows, status_filter)
        except sqlite3.OperationalError as e:
            raise RuntimeError(f"Error al adjuntar la base de datos de estadísticas: {e}")
        finally:
            conn.close()

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
        from sqlmodel import select
        
        # Determine model/platform key
        # Depending on how DeviceStatus is structured, usually client.extra['model'] or 'platform'
        
        for client in status.clients:
            if not client.mac:
                continue
                
            cpe = self.session.get(CPE, client.mac)
            if not cpe:
                cpe = CPE(mac=client.mac, first_seen=now)
                self.session.add(cpe)
                
            if client.hostname:
                cpe.hostname = client.hostname
            
            model = client.extra.get("model") or client.extra.get("platform")
            if model:
                cpe.model = model
                
            fw = client.extra.get("firmware") or client.extra.get("version")
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
        from datetime import datetime, timedelta
        from ..models.setting import Setting
        
        # Get settings via session
        monitor_interval_setting = self.session.get(Setting, "default_monitor_interval")
        stale_cycles_setting = self.session.get(Setting, "cpe_stale_cycles")
        
        monitor_interval = int(monitor_interval_setting.value) if monitor_interval_setting else 300
        stale_cycles = int(stale_cycles_setting.value) if stale_cycles_setting else 3
        
        threshold_seconds = monitor_interval * stale_cycles
        threshold_time = datetime.utcnow() - timedelta(seconds=threshold_seconds)
        
        # Update statement
        # select(CPE).where(CPE.status == 'active', CPE.is_enabled == True, CPE.last_seen < threshold_time)
        # Iterate and update or use update statement (if supported by SQLModel/dialect)
        # SQLModel doesn't have direct update() yet, iterate is safer
        
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
            # print(f"Marcados {len(stale_cpes)} CPEs como offline.")

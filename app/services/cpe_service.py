# app/services/cpe_service.py
from typing import List, Dict, Any, Optional
from sqlmodel import Session, select, func
import sqlite3
import os
import uuid

from ..models.cpe import CPE
from ..db.base import get_db_connection, get_stats_db_file


class CPEService:
    def __init__(self, session: Session):
        self.session = session

    def get_unassigned_cpes(self) -> List[CPE]:
        """Obtiene todos los CPEs que no están asignados a ningún cliente."""
        statement = select(CPE).where(CPE.client_id == None).order_by(CPE.hostname)
        return list(self.session.exec(statement).all())

    def get_cpe_by_mac(self, mac: str) -> Optional[CPE]:
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

    def delete_cpe(self, mac: str) -> bool:
        """Deshabilita un CPE (soft-delete) en la base de datos."""
        cpe = self.session.get(CPE, mac)
        if not cpe:
            raise FileNotFoundError("CPE not found.")
        
        cpe.is_enabled = False
        self.session.add(cpe)
        self.session.commit()
        return True

    def get_cpes_for_client(self, client_id: uuid.UUID) -> List[CPE]:
        """Obtiene los CPEs asignados a un cliente específico."""
        statement = select(CPE).where(CPE.client_id == client_id).order_by(CPE.hostname)
        return list(self.session.exec(statement).all())

    def get_cpe_count_for_client(self, client_id: uuid.UUID) -> int:
        """Cuenta los CPEs asignados a un cliente específico."""
        statement = select(func.count()).select_from(CPE).where(CPE.client_id == client_id)
        return self.session.exec(statement).one()

    def update_cpe(self, mac: str, update_data: Dict[str, Any]) -> CPE:
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
        allowed_fields = {'ip_address', 'hostname', 'model'}
        for key, value in update_data.items():
            if key in allowed_fields and value is not None:
                setattr(cpe, key, value)
        
        cpe.last_seen = datetime.now()
        self.session.add(cpe)
        self.session.commit()
        self.session.refresh(cpe)
        return cpe


    def get_all_cpes_globally(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Obtiene todos los CPEs con sus datos de estado más recientes, nombre del AP, y estado persistido.
        
        Args:
            status_filter: Opcional. Filtrar por estado: 'active', 'offline', 'disabled', o None para todos.
        
        Returns:
            Lista de CPEs con campo 'status': 'active', 'offline', o 'disabled'.
        
        Nota: Esta función usa SQL crudo porque hace ATTACH DATABASE a stats_db.
        """
        from ..db.base import get_db_connection, get_stats_db_file
        
        conn = get_db_connection()
        stats_db_file = get_stats_db_file()

        if not os.path.exists(stats_db_file):
            # Return only CPEs from inventory (no stats available)
            try:
                query = "SELECT mac, hostname, model, firmware, ip_address, is_enabled, status, last_seen FROM cpes ORDER BY hostname, mac"
                cursor = conn.execute(query)
                rows = []
                for row in cursor.fetchall():
                    cpe = dict(row)
                    cpe['cpe_mac'] = cpe.pop('mac')
                    cpe['cpe_hostname'] = cpe.pop('hostname', None)
                    # Use is_enabled to override status to 'disabled'
                    if not cpe.get('is_enabled', True):
                        cpe['status'] = 'disabled'
                    # status is already set from DB ('active' or 'offline')
                    rows.append(cpe)
                return self._apply_status_filter(rows, status_filter)
            finally:
                conn.close()

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
                if not cpe.get('ip_address') and cpe.get('db_ip_address'):
                    cpe['ip_address'] = cpe['db_ip_address']
                # Clean up the temporary db_ip_address key
                cpe.pop('db_ip_address', None)
                # Use is_enabled to override status to 'disabled'
                if not cpe.get('is_enabled', True):
                    cpe['status'] = 'disabled'
                # status is already set from DB ('active' or 'offline')
                rows.append(cpe)
            return self._apply_status_filter(rows, status_filter)
        except sqlite3.OperationalError as e:
            raise RuntimeError(f"Error al adjuntar la base de datos de estadísticas: {e}")
        finally:
            conn.close()

    def _apply_status_filter(self, rows: List[Dict[str, Any]], status_filter: Optional[str]) -> List[Dict[str, Any]]:
        """Helper to filter rows by status."""
        if not status_filter:
            return rows
        return [row for row in rows if row.get('status') == status_filter]


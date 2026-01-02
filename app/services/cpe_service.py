# app/services/cpe_service.py
from typing import List, Dict, Any, Optional
from sqlmodel import Session, select, func
import sqlite3
import os

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

    def assign_cpe_to_client(self, mac: str, client_id: int) -> CPE:
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

    def get_cpes_for_client(self, client_id: int) -> List[CPE]:
        """Obtiene los CPEs asignados a un cliente específico."""
        statement = select(CPE).where(CPE.client_id == client_id).order_by(CPE.hostname)
        return list(self.session.exec(statement).all())

    def get_cpe_count_for_client(self, client_id: int) -> int:
        """Cuenta los CPEs asignados a un cliente específico."""
        statement = select(func.count()).select_from(CPE).where(CPE.client_id == client_id)
        return self.session.exec(statement).one()

    def get_all_cpes_globally(self) -> List[Dict[str, Any]]:
        """
        Obtiene todos los CPEs con sus datos de estado más recientes y el nombre del AP.
        Nota: Esta función usa SQL crudo porque hace ATTACH DATABASE a stats_db.
        """
        from ..db.base import get_db_connection, get_stats_db_file
        
        conn = get_db_connection()
        stats_db_file = get_stats_db_file()

        if not os.path.exists(stats_db_file):
            conn.close()
            return []

        try:
            conn.execute(f"ATTACH DATABASE '{stats_db_file}' AS stats_db")
            query = """
                WITH LatestCPEStats AS (
                    SELECT *, ROW_NUMBER() OVER(PARTITION BY cpe_mac ORDER BY timestamp DESC) as rn
                    FROM stats_db.cpe_stats_history
                )
                SELECT s.*, a.hostname as ap_hostname
                FROM LatestCPEStats s
                INNER JOIN cpes c ON s.cpe_mac = c.mac AND c.is_enabled = 1
                LEFT JOIN aps a ON s.ap_host = a.host
                WHERE s.rn = 1
                ORDER BY s.cpe_hostname, s.cpe_mac;
            """
            cursor = conn.execute(query)
            rows = [dict(row) for row in cursor.fetchall()]
            return rows
        except sqlite3.OperationalError as e:
            raise RuntimeError(f"Error al adjuntar la base de datos de estadísticas: {e}")
        finally:
            conn.close()

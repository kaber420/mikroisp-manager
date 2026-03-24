from fastapi import HTTPException, status
from app.core.config import settings

def verify_not_degraded():
    """
    Dependencia de FastAPI que bloquea la ejecución si el sistema está en modo degradado
    (fallback de emergencia a SQLite).
    """
    if settings.DEGRADED_MODE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sistema operando en MODO DE EMERGENCIA (Degradado). Las transacciones de escritura crítica están deshabilitadas hasta que se restablezcan los servicios principales (PostgreSQL/Redis)."
        )
    return True

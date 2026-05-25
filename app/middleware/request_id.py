# app/middleware/request_id.py
import uuid
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logging_config import request_id_ctx_var

logger = logging.getLogger("app.middleware.request_id")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware que genera y asocia un UUID único para cada petición HTTP.
    Este ID se almacena en variables de contexto para correlacionar logs 
    y se retorna en la cabecera 'X-Request-ID' de la respuesta.
    """
    async def dispatch(self, request: Request, call_next):
        # Intentar obtener el ID desde las cabeceras (por si viene de un proxy inverso) o generar uno nuevo
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Guardar en variable de contexto
        token = request_id_ctx_var.set(request_id)
        request.state.request_id = request_id

        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            # Restaurar el estado anterior de la variable de contexto
            request_id_ctx_var.reset(token)

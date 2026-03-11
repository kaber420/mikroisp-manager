# app/core/exceptions.py
"""
Excepciones de dominio tipadas.

Cada excepción tiene un status_code que el handler global de FastAPI
usa para generar la respuesta HTTP correcta automáticamente.
Esto elimina la necesidad de try/except en routers y de parsear strings.
"""


class AppError(Exception):
    """Base para todos los errores de dominio de la aplicación."""

    status_code: int = 500

    def __init__(self, detail: str = "Error interno del servidor"):
        self.detail = detail
        super().__init__(detail)


# ---------------------------------------------------------------------------
# 404 Not Found
# ---------------------------------------------------------------------------
class NotFoundError(AppError):
    """Recurso no encontrado."""

    status_code = 404

    def __init__(self, detail: str = "Recurso no encontrado"):
        super().__init__(detail)


class ClientNotFoundError(NotFoundError):
    """Cliente no encontrado."""

    def __init__(self, detail: str = "Cliente no encontrado"):
        super().__init__(detail)


class RouterNotFoundError(NotFoundError):
    """Router no encontrado."""

    def __init__(self, detail: str = "Router no encontrado"):
        super().__init__(detail)


class ServiceNotFoundError(NotFoundError):
    """Servicio de cliente no encontrado."""

    def __init__(self, detail: str = "Servicio no encontrado"):
        super().__init__(detail)


class PlanNotFoundError(NotFoundError):
    """Plan no encontrado."""

    def __init__(self, detail: str = "Plan no encontrado"):
        super().__init__(detail)


class PaymentNotFoundError(NotFoundError):
    """Pago no encontrado."""

    def __init__(self, detail: str = "Pago no encontrado"):
        super().__init__(detail)


class DeviceNotFoundError(NotFoundError):
    """Dispositivo de red no encontrado."""

    def __init__(self, detail: str = "Dispositivo no encontrado"):
        super().__init__(detail)


class ZoneNotFoundError(NotFoundError):
    """Zona no encontrada."""

    def __init__(self, detail: str = "Zona no encontrada"):
        super().__init__(detail)


class UserNotFoundError(NotFoundError):
    """Usuario no encontrado."""

    def __init__(self, detail: str = "Usuario no encontrado"):
        super().__init__(detail)


# ---------------------------------------------------------------------------
# 400 Bad Request – validación de datos / campos faltantes
# ---------------------------------------------------------------------------
class ValidationError(AppError):
    """Error de validación de datos de entrada."""

    status_code = 400

    def __init__(self, detail: str = "Datos de entrada inválidos"):
        super().__init__(detail)


class MissingFieldError(ValidationError):
    """Campo requerido faltante."""

    def __init__(self, detail: str = "Campo requerido faltante"):
        super().__init__(detail)


class InvalidOperationError(ValidationError):
    """Operación no válida para el estado actual del recurso."""

    def __init__(self, detail: str = "Operación no válida"):
        super().__init__(detail)


# ---------------------------------------------------------------------------
# 409 Conflict – duplicados
# ---------------------------------------------------------------------------
class ConflictError(AppError):
    """Conflicto con el estado actual del recurso."""

    status_code = 409

    def __init__(self, detail: str = "Conflicto con recurso existente"):
        super().__init__(detail)


class DuplicateError(ConflictError):
    """El recurso ya existe."""

    def __init__(self, detail: str = "El recurso ya existe"):
        super().__init__(detail)


# ---------------------------------------------------------------------------
# 422 Unprocessable Entity – reglas de negocio
# ---------------------------------------------------------------------------
class BusinessRuleError(AppError):
    """Violación de regla de negocio."""

    status_code = 422

    def __init__(self, detail: str = "Violación de regla de negocio"):
        super().__init__(detail)


class ServiceLimitExceeded(BusinessRuleError):
    """Límite de servicios excedido."""

    def __init__(self, detail: str = "Límite de servicios excedido"):
        super().__init__(detail)


class DeletionBlockedError(BusinessRuleError):
    """No se puede eliminar porque tiene dependencias."""

    def __init__(self, detail: str = "No se puede eliminar: tiene dependencias"):
        super().__init__(detail)


# ---------------------------------------------------------------------------
# 502 Bad Gateway – errores de comunicación con dispositivos externos
# ---------------------------------------------------------------------------
class DeviceError(AppError):
    """Error de comunicación con dispositivo de red."""

    status_code = 502

    def __init__(self, detail: str = "Error de comunicación con dispositivo"):
        super().__init__(detail)


class DeviceConnectionError(DeviceError):
    """No se pudo conectar al dispositivo."""

    def __init__(self, detail: str = "No se pudo conectar al dispositivo"):
        super().__init__(detail)


class DeviceCommandError(DeviceError):
    """Error ejecutando comando en dispositivo."""

    def __init__(self, detail: str = "Error ejecutando comando en dispositivo"):
        super().__init__(detail)


class DeviceNotSubscribedError(DeviceError):
    """Dispositivo no está suscrito para monitoreo."""

    status_code = 403

    def __init__(self, detail: str = "Dispositivo no suscrito"):
        super().__init__(detail)


# ---------------------------------------------------------------------------
# 503 Service Unavailable
# ---------------------------------------------------------------------------
class ServiceUnavailableError(AppError):
    """Servicio no disponible temporalmente."""

    status_code = 503

    def __init__(self, detail: str = "Servicio no disponible"):
        super().__init__(detail)

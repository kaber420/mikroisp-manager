# app/core/logging_config.py
import os
import logging
import logging.config
import contextvars

# Contexto para correlación de logs por petición HTTP/WebSocket
request_id_ctx_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """
    Filtro de logging para inyectar dinámicamente el `request_id` actual
    desde el contextvar en cada registro de log.
    """
    def filter(self, record):
        record.request_id = request_id_ctx_var.get("-")
        return True


def setup_logging(env: str = "development") -> None:
    """
    Inicializa y unifica la configuración de logging de la aplicación.
    Soporta salida estructurada por consola y rotación de archivos en logs/app.log.
    """
    # Asegurar la existencia del directorio de logs
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "app.log")

    # Determinar niveles de logs según entorno
    log_level = logging.DEBUG if env == "development" else logging.INFO

    # Estructuración de configuración mediante dictConfig
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "request_id_filter": {
                "()": RequestIdFilter
            }
        },
        "formatters": {
            "console_formatter": {
                "format": "%(asctime)s [%(levelname)s] [%(name)s] [%(request_id)s] - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "file_formatter": {
                "format": "%(asctime)s [%(levelname)s] [%(name)s] [%(request_id)s] [%(pathname)s:%(lineno)d] - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "console_formatter",
                "filters": ["request_id_filter"],
                "level": log_level,
                "stream": "ext://sys.stdout"
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "file_formatter",
                "filters": ["request_id_filter"],
                "level": log_level,
                "filename": log_file,
                "maxBytes": 5 * 1024 * 1024,  # 5 MB
                "backupCount": 5,
                "encoding": "utf-8"
            }
        },
        "loggers": {
            "": {  # Root logger
                "handlers": ["console", "file"],
                "level": log_level,
            },
            "uvicorn": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False
            },
            "uvicorn.error": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False
            },
            "uvicorn.access": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False
            },
            "sqlalchemy.engine": {
                "handlers": ["console", "file"],
                "level": "WARNING",
                "propagate": False
            },
            "apscheduler": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False
            }
        }
    }

    logging.config.dictConfig(logging_config)
    logging.getLogger("app.logging").info(f"📊 Sistema de logging centralizado inicializado en entorno: '{env}'")

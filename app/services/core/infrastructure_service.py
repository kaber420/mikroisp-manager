import os
import time
from typing import Dict, Any

from app.core.config import settings

class InfrastructureService:
    """
    Servicio de Infraestructura responsable de comprobar el estado de los
    servicios (PostgreSQL y Redict) y gestionar la persistencia de configuraciones
    en data/services.json, sin interactuar con el demonio Docker del host.
    """

    def __init__(self):
        # Desacoplado del Demonio Docker local
        self.client = None

    def check_services_status(self) -> Dict[str, Any]:
        """
        Devuelve el estado de disponibilidad por red TCP de PostgreSQL y Redict.
        """
        PORTS = {"postgres": 5432, "redict": 6379}

        import os
        from app.utils.services_config import read_services_config
        srv = read_services_config()
        if srv.get("db") and srv["db"].get("provider") == "postgres":
            suggested_pass = srv["db"].get("password")
            suggested_user = srv["db"].get("user", "umanager")
            suggested_db = srv["db"].get("database", "umanager_db")
        else:
            suggested_pass = os.environ.get("POSTGRES_PASSWORD", None)
            suggested_user = "umanager"
            suggested_db = "umanager_db"

        services: Dict[str, Any] = {
            "postgres": {
                "port": PORTS["postgres"], 
                "omniwisp_container": "missing", 
                "conflict": None,
                "suggested": {
                    "user": suggested_user,
                    "db": suggested_db,
                    "password": suggested_pass
                }
            },
            "redict": {
                "port": PORTS["redict"], 
                "omniwisp_container": "missing", 
                "conflict": None
            },
        }

        from app.core.config import settings
        from app.utils.services_config import read_services_config as _rsc
        from sqlalchemy import create_engine, text
        _srv_cfg = _rsc()

        # Leer qué proveedor tiene el usuario CONFIGURADO
        _db_cfg = _srv_cfg.get("db", {})
        configured_provider = _db_cfg.get("provider", "sqlite")

        db_warning = None
        active_db = configured_provider  # Asumir que la config se cumple

        # Probe PostgreSQL
        if configured_provider == "postgres":
            try:
                _pg_pass = _db_cfg.get("password", "")
                _pg_user = _db_cfg.get("user", "umanager")
                _pg_db   = _db_cfg.get("database", "umanager_db")
                _pg_host = _db_cfg.get("host", "127.0.0.1")
                _pg_port = _db_cfg.get("port", 5432)
                _test_url = f"postgresql+psycopg://{_pg_user}:{_pg_pass}@{_pg_host}:{_pg_port}/{_pg_db}"
                _eng = create_engine(_test_url, connect_args={"connect_timeout": 3})
                with _eng.connect() as _conn:
                    _conn.execute(text("SELECT 1"))
                active_db = "postgres"
                db_warning = None
                services["postgres"]["omniwisp_container"] = "running"
            except Exception as _e:
                active_db = "sqlite"
                db_warning = f"⚠️ PostgreSQL configurado pero sin conexión: {str(_e)[:80]}. Usando SQLite de emergencia."
                services["postgres"]["omniwisp_container"] = "error"

        # Probe Redict
        _cache_cfg = _srv_cfg.get("cache", {})
        configured_cache = _cache_cfg.get("provider", "memory")
        active_cache = "memory"
        
        if configured_cache == "redict":
            import redis
            try:
                _rd_host = _cache_cfg.get("host", "127.0.0.1")
                _rd_port = _cache_cfg.get("port", 6379)
                _rd_pass = _cache_cfg.get("password", "")
                _r = redis.Redis(host=_rd_host, port=_rd_port, password=_rd_pass, socket_timeout=3.0)
                _r.ping()
                active_cache = "redict"
                services["redict"]["omniwisp_container"] = "running"
            except Exception:
                active_cache = "memory"
                services["redict"]["omniwisp_container"] = "error"

        return {
            "status": "success",
            "services": services,
            "system_state": {
                "active_db": active_db,
                "active_cache": active_cache,
                "db_warning": db_warning,
                "degraded": active_db != configured_provider
            }
        }

    def deploy_production_stack(
        self, 
        postgres_password: str, 
        postgres_user: str = "umanager", 
        postgres_db: str = "umanager_db", 
        actions: Dict[str, str] = None,
        advanced_configs: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Guarda la configuración de servicios en data/services.json de manera lógica.
        No intenta instanciar contenedores en el host.
        """
        if actions is None:
            actions = {"postgres": "skip", "redict": "skip"}
        
        if advanced_configs is None:
            advanced_configs = {"postgres": {}, "redict": {}}

        results = {}

        from app.utils.services_config import read_services_config, write_services_config
        srv_config = read_services_config()
        if not srv_config.get("db"): srv_config["db"] = {}
        if not srv_config.get("cache"): srv_config["cache"] = {}

        # --- Redict ---
        act_rd = actions.get("redict", "create")
        if act_rd == "skip":
            results["redict"] = "skipped"
        elif act_rd == "reuse":
            results["redict"] = "reused_existing"
            srv_config["cache"]["provider"] = "redict"
        elif act_rd == "delete":
            results["redict"] = "deleted"
            srv_config["cache"]["provider"] = "memory"
        elif act_rd == "stop":
            results["redict"] = "stopped"
            srv_config["cache"]["provider"] = "memory"
        elif act_rd == "reset":
            results["redict"] = "created"
            srv_config["cache"]["provider"] = "redict"
            srv_config["cache"]["host"] = "localhost"
            srv_config["cache"]["port"] = 6379
        else: # create
            rd_adv = advanced_configs.get("redict", {})
            rd_port = rd_adv.get("port", 6379)
            results["redict"] = "created"
            srv_config["cache"]["provider"] = "redict"
            srv_config["cache"]["host"] = "localhost"
            srv_config["cache"]["port"] = rd_port
            srv_config["cache"]["advanced"] = rd_adv

        # --- Postgres ---
        act_pg = actions.get("postgres", "create")
        if act_pg == "skip":
            results["postgres"] = "skipped"
        elif act_pg == "reuse":
            results["postgres"] = "reused_existing"
            srv_config["db"]["provider"] = "postgres"
            srv_config["db"]["password"] = postgres_password
            srv_config["db"]["user"] = postgres_user
            srv_config["db"]["database"] = postgres_db
            srv_config["db"]["host"] = "localhost"
            srv_config["db"]["port"] = 5432
        elif act_pg == "delete":
            results["postgres"] = "deleted"
            srv_config["db"]["provider"] = "sqlite"
        elif act_pg == "stop":
            results["postgres"] = "stopped"
            srv_config["db"]["provider"] = "sqlite"
        elif act_pg == "reset":
            results["postgres"] = "created"
            srv_config["db"]["provider"] = "postgres"
            srv_config["db"]["password"] = postgres_password
            srv_config["db"]["user"] = postgres_user
            srv_config["db"]["database"] = postgres_db
            srv_config["db"]["host"] = "localhost"
            srv_config["db"]["port"] = 5432
        else: # create
            pg_adv = advanced_configs.get("postgres", {})
            pg_port = pg_adv.get("port", 5432)
            results["postgres"] = "created"
            srv_config["db"]["provider"] = "postgres"
            srv_config["db"]["password"] = postgres_password
            srv_config["db"]["user"] = postgres_user
            srv_config["db"]["database"] = postgres_db
            srv_config["db"]["host"] = "localhost"
            srv_config["db"]["port"] = pg_port
            srv_config["db"]["advanced"] = pg_adv

        write_services_config(srv_config)

        return {
            "status": "success",
            "message": "Operación completada de manera lógica. Configure la infraestructura física mediante el Launcher o Portainer.",
            "details": results,
            "postgres_password": postgres_password if act_pg not in ["skip", "delete", "stop"] else None
        }

    def get_container_logs_stream(self, container_name: str):
        """
        Servicio deshabilitado en modo contenedorizado.
        """
        yield f"Logs stream disabled inside backend container. Check logs via 'docker compose logs {container_name}' on the host.\n"

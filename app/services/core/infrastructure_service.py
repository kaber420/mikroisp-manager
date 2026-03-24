import os
import docker
import time
from typing import Dict, Any

from app.core.config import settings

class InfrastructureService:
    """
    Servicio de Infraestructura responsable de controlar despliegues
    y contenedores para el escalado de OmniWisp.
    """

    def __init__(self):
        try:
            self.client = docker.from_env()
        except Exception as e:
            self.client = None
            print(f"⚠️ Error conectando al Demonio de Docker: {e}")

    def check_services_status(self) -> Dict[str, Any]:
        """
        Devuelve el estado general del demónio Docker y los contenedores requeridos.
        """
        if not self.client:
            return {"status": "error", "message": "Docker no está disponible."}

        PORTS = {"postgres": 5432, "redict": 6379}

        services: Dict[str, Dict[str, Any]] = {
            "postgres": {"omniwisp_container": "missing", "conflict": None},
            "redict": {"omniwisp_container": "missing", "conflict": None}
        }
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

        try:
            containers = self.client.containers.list(all=True)
        except Exception as e:
            return {"status": "error", "message": f"Error leyendo contenedores: {str(e)}"}

        for container in containers:
            name = container.name
            status = container.status

            if name == "omniwisp_postgres":
                services["postgres"]["omniwisp_container"] = status
            elif name == "omniwisp_redict":
                services["redict"]["omniwisp_container"] = status
            else:
                try:
                    ports = container.ports
                    for proto_port, bindings in (ports or {}).items():
                        if not bindings: continue
                        for binding in bindings:
                            host_port = int(binding.get("HostPort", 0))
                            if host_port == PORTS["postgres"] and services["postgres"]["conflict"] is None:
                                services["postgres"]["conflict"] = {"name": name, "status": status}
                            elif host_port == PORTS["redict"] and services["redict"]["conflict"] is None:
                                services["redict"]["conflict"] = {"name": name, "status": status}
                except Exception: pass
        from app.core.config import settings
        from app.utils.services_config import read_services_config as _rsc
        from sqlalchemy import create_engine, text
        _srv_cfg = _rsc()

        # Leer qué proveedor tiene el usuario CONFIGURADO (no el que usó el fallback)
        _db_cfg = _srv_cfg.get("db", {})
        configured_provider = _db_cfg.get("provider", "sqlite")

        db_warning = None
        active_db = configured_provider  # Asumir que la config se cumple

        if configured_provider == "postgres":
            # Hacer probe real ahora mismo para saber si realmente conecta
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
            except Exception as _e:
                active_db = "sqlite"
                db_warning = f"⚠️ PostgreSQL configurado pero sin conexión: {str(_e)[:80]}. Usando SQLite de emergencia."

        _cache_cfg = _srv_cfg.get("cache", {})
        configured_cache = _cache_cfg.get("provider", "memory")
        active_cache = "redict" if configured_cache == "redict" and "redict" in getattr(settings, "REDICT_URL", "") else "memory"

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
        Despliega servicios según acciones. Si hay conflicto y la acción es 'create', remueve el viejo.
        Soporta 'reset' para empezar de cero borrando volúmenes.
        """
        if not self.client:
            return {"status": "error", "message": "Docker no disponible."}

        if actions is None:
            actions = {"postgres": "skip", "redict": "skip"}
        
        if advanced_configs is None:
            advanced_configs = {"postgres": {}, "redict": {}}

        # Diagnóstico previo
        status = self.check_services_status()
        srv = status.get("services", {})
        results = {}

        # Log para depuración
        print(f"🚀 Deploying stack with request: user={postgres_user}, db={postgres_db}, actions={actions}")

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
            self._reset_service("omniwisp_redict", "deployments_redict_data")
            results["redict"] = "deleted"
            srv_config["cache"]["provider"] = "memory"
        elif act_rd == "stop":
            self._stop_only("omniwisp_redict")
            results["redict"] = "stopped"
            srv_config["cache"]["provider"] = "memory"
        elif act_rd == "reset":
            self._reset_service("omniwisp_redict", "deployments_redict_data")
            try:
                results["redict"] = self._ensure_container(
                    name="omniwisp_redict",
                    image="registry.redict.io/redict:7.3.0",
                    ports={"6379/tcp": ("127.0.0.1", 6379)},
                    command="redict-server --save 60 1 --loglevel warning",
                    volumes={"deployments_redict_data": {"bind": "/data", "mode": "rw"}}
                )
                srv_config["cache"]["provider"] = "redict"
                srv_config["cache"]["host"] = "localhost"
                srv_config["cache"]["port"] = 6379
            except Exception as e:
                results["redict"] = f"error: {str(e)}"
        else: # create
            conf = srv.get("redict", {}).get("conflict")
            if conf:
                self._stop_and_remove(conf["name"])
            try:
                # Combinar configs avanzadas de Redict
                rd_adv = advanced_configs.get("redict", {})
                rd_env = rd_adv.get("env", {})
                rd_net = rd_adv.get("network", "bridge")
                rd_port = rd_adv.get("port", 6379)
                rd_vols = rd_adv.get("volumes", {"deployments_redict_data": {"bind": "/data", "mode": "rw"}})

                results["redict"] = self._ensure_container(
                    name="omniwisp_redict",
                    image="registry.redict.io/redict:7.3.0",
                    ports={"6379/tcp": ("127.0.0.1", rd_port)},
                    command="redict-server --save 60 1 --loglevel warning",
                    volumes=rd_vols,
                    environment=rd_env,
                    network_mode=rd_net
                )
                srv_config["cache"]["provider"] = "redict"
                srv_config["cache"]["host"] = "localhost"
                srv_config["cache"]["port"] = rd_port
                srv_config["cache"]["advanced"] = rd_adv
            except Exception as e:
                results["redict"] = f"error: {str(e)}"

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
            self._reset_service("omniwisp_postgres", "deployments_postgres_data")
            results["postgres"] = "deleted"
            srv_config["db"]["provider"] = "sqlite"
        elif act_pg == "stop":
            self._stop_only("omniwisp_postgres")
            results["postgres"] = "stopped"
            srv_config["db"]["provider"] = "sqlite"
        elif act_pg == "reset":
            # ELIMINACIÓN FÍSICA Y CREACIÓN DESDE CERO
            print(f"🧹 Realizando RESET (NUKE) de PostgreSQL...")
            self._reset_service("omniwisp_postgres", "deployments_postgres_data")
            try:
                results["postgres"] = self._ensure_container(
                    name="omniwisp_postgres",
                    image="postgres:15-alpine",
                    ports={"5432/tcp": ("127.0.0.1", 5432)},
                    environment={
                        "POSTGRES_USER": postgres_user,
                        "POSTGRES_PASSWORD": postgres_password,
                        "POSTGRES_DB": postgres_db,
                    },
                    volumes={"deployments_postgres_data": {"bind": "/var/lib/postgresql/data", "mode": "rw"}}
                )
                srv_config["db"]["provider"] = "postgres"
                srv_config["db"]["password"] = postgres_password
                srv_config["db"]["user"] = postgres_user
                srv_config["db"]["database"] = postgres_db
                srv_config["db"]["host"] = "localhost"
                srv_config["db"]["port"] = 5432
            except Exception as e:
                results["postgres"] = f"error: {str(e)}"
        else: # create
            conf = srv.get("postgres", {}).get("conflict")
            if conf:
                self._stop_and_remove(conf["name"])
            try:
                # Config avanzada de Postgres
                pg_adv = advanced_configs.get("postgres", {})
                pg_net = pg_adv.get("network", "bridge")
                pg_port = pg_adv.get("port", 5432)
                pg_env = pg_adv.get("env", {})
                
                # Inyectar variables base si no están en las avanzadas
                final_env = {
                    "POSTGRES_USER": postgres_user,
                    "POSTGRES_PASSWORD": postgres_password,
                    "POSTGRES_DB": postgres_db,
                    **pg_env
                }

                results["postgres"] = self._ensure_container(
                    name="omniwisp_postgres",
                    image="postgres:15-alpine",
                    ports={"5432/tcp": ("127.0.0.1", pg_port)},
                    environment=final_env,
                    volumes=pg_adv.get("volumes", {"deployments_postgres_data": {"bind": "/var/lib/postgresql/data", "mode": "rw"}}),
                    network_mode=pg_net
                )
                srv_config["db"]["provider"] = "postgres"
                srv_config["db"]["password"] = postgres_password
                srv_config["db"]["user"] = postgres_user
                srv_config["db"]["database"] = postgres_db
                srv_config["db"]["host"] = "localhost"
                srv_config["db"]["port"] = pg_port
                srv_config["db"]["advanced"] = pg_adv
            except Exception as e:
                results["postgres"] = f"error: {str(e)}"

        write_services_config(srv_config)

        has_err = any("error" in str(v) for v in results.values())
        return {
            "status": "warning" if has_err else "success",
            "message": "Operación completada." if not has_err else "Hubo errores en el despliegue.",
            "details": results,
            "postgres_password": postgres_password if act_pg not in ["skip", "delete", "stop"] else None
        }

    def get_container_logs_stream(self, container_name: str):
        """
        Devuelve un generador que emite los logs del contenedor en tiempo real.
        """
        if not self.client:
            yield "Error: Docker no disponible.\n"
            return

        try:
            container = self.client.containers.get(container_name)
            # Logs en modo stream
            for line in container.logs(stream=True, follow=True, tail=100):
                yield line.decode("utf-8", errors="replace")
        except Exception as e:
            yield f"Error leyendo logs de {container_name}: {str(e)}\n"

    def _reset_service(self, container_name: str, volume_name: str):
        """Detiene, remueve y borra el volumen persistente (NUKE)."""
        print(f"🛑 Deteniendo y eliminando contenedor: {container_name}")
        self._stop_and_remove(container_name)
        try:
            print(f"🗑️ Eliminando volumen persistente: {volume_name}")
            v = self.client.volumes.get(volume_name)
            v.remove(force=True)
            print(f"✅ Volumen {volume_name} eliminado.")
        except Exception as e:
            print(f"⚠️ No se pudo eliminar el volumen {volume_name} (quizás no existía): {e}")

    def _stop_only(self, name: str):
        try:
            c = self.client.containers.get(name)
            if c.status == "running":
                c.stop(timeout=5)
            time.sleep(1)
        except: pass

    def _stop_and_remove(self, name: str):
        try:
            c = self.client.containers.get(name)
            if c.status == "running":
                c.stop(timeout=5)
            c.remove(force=True)
            time.sleep(1) # Pequeña espera para liberación de socket
        except: pass

    def _ensure_container(self, name: str, image: str, **kwargs) -> str:
        try:
            c = self.client.containers.get(name)
            if c.status == "running": 
                # Si existe pero los argumentos podrían haber cambiado (ej: password), 
                # lo recreamos para asegurar consistencia
                print(f"♻️ Recreando contenedor {name} para asegurar nueva configuración...")
                c.stop(timeout=2)
                c.remove()
            else:
                c.remove()
        except: pass

        try:
            self.client.images.get(image)
        except:
            print(f"📥 Descargando imagen {image}...")
            self.client.images.pull(image)

        run_args = {
            "name": name,
            "detach": True,
            "restart_policy": {"Name": "always"},
            **kwargs
        }
        self.client.containers.run(image, **run_args)
        return "created"

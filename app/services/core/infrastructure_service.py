import os
import docker
import time
from typing import Dict, Any

from app.core.config import settings
from app.utils.env_manager import update_env_file

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
        Escanea contenedores para detectar estado y conflictos de puertos.
        """
        if not self.client:
            return {"status": "error", "message": "Docker no está disponible."}

        PORTS = {"postgres": 5432, "redict": 6379}
        import os
        from app.utils.services_config import read_services_config
        srv = read_services_config()
        suggested_pass = None
        if srv.get("db") and srv["db"].get("provider") == "postgres":
            suggested_pass = srv["db"].get("password")
        if not suggested_pass:
            suggested_pass = os.environ.get("POSTGRES_PASSWORD", None)

        services: Dict[str, Any] = {
            "postgres": {
                "port": PORTS["postgres"], 
                "omniwisp_container": "missing", 
                "conflict": None,
                "suggested": {
                    "user": "umanager",
                    "db": "umanager_db",
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

        return {"status": "success", "services": services}

    def deploy_production_stack(self, postgres_password: str, actions: dict = None) -> Dict[str, Any]:
        """
        Despliega servicios según acciones. Si hay conflicto y la acción es 'create', remueve el viejo.
        """
        if not self.client:
            return {"status": "error", "message": "Docker no disponible."}

        if actions is None:
            actions = {"postgres": "create", "redict": "create"}

        # Diagnóstico previo
        status = self.check_services_status()
        srv = status.get("services", {})
        results = {}

        # --- Redict ---
        act_rd = actions.get("redict", "create")
        if act_rd == "skip":
            results["redict"] = "skipped"
        elif act_rd == "reuse":
            results["redict"] = "reused_existing"
            update_env_file({"CACHE_BACKEND": "redict"})
        elif act_rd == "delete":
            self._stop_and_remove("omniwisp_redict")
            results["redict"] = "deleted"
            update_env_file({"CACHE_BACKEND": "memory"})
        elif act_rd == "stop":
            self._stop_only("omniwisp_redict")
            results["redict"] = "stopped"
            update_env_file({"CACHE_BACKEND": "memory"})
        else: # create
            conf = srv.get("redict", {}).get("conflict")
            if conf:
                self._stop_and_remove(conf["name"])
            try:
                results["redict"] = self._ensure_container(
                    name="omniwisp_redict",
                    image="registry.redict.io/redict:7.3.0",
                    ports={"6379/tcp": ("127.0.0.1", 6379)},
                    command="redict-server --save 60 1 --loglevel warning",
                    volumes={"deployments_redict_data": {"bind": "/data", "mode": "rw"}}
                )
            except Exception as e:
                results["redict"] = f"error: {str(e)}"

        # --- Postgres ---
        act_pg = actions.get("postgres", "create")
        if act_pg == "skip":
            results["postgres"] = "skipped"
        elif act_pg == "reuse":
            results["postgres"] = "reused_existing"
            update_env_file({"POSTGRES_PASSWORD": postgres_password})
        elif act_pg == "delete":
            self._stop_and_remove("omniwisp_postgres")
            results["postgres"] = "deleted"
            update_env_file({"DB_PROVIDER": "sqlite"})
        elif act_pg == "stop":
            self._stop_only("omniwisp_postgres")
            results["postgres"] = "stopped"
            update_env_file({"DB_PROVIDER": "sqlite"})
        else: # create
            conf = srv.get("postgres", {}).get("conflict")
            if conf:
                self._stop_and_remove(conf["name"])
            try:
                results["postgres"] = self._ensure_container(
                    name="omniwisp_postgres",
                    image="postgres:15-alpine",
                    ports={"5432/tcp": ("127.0.0.1", 5432)},
                    environment={
                        "POSTGRES_USER": "umanager",
                        "POSTGRES_PASSWORD": postgres_password,
                        "POSTGRES_DB": "umanager_db",
                    },
                    volumes={"deployments_postgres_data": {"bind": "/var/lib/postgresql/data", "mode": "rw"}}
                )
                update_env_file({"POSTGRES_PASSWORD": postgres_password})
                update_env_file({"DB_PROVIDER": "postgres"})
            except Exception as e:
                results["postgres"] = f"error: {str(e)}"

        has_err = any("error" in str(v) for v in results.values())
        return {
            "status": "warning" if has_err else "success",
            "message": "Operación completada." if not has_err else "Hubo errores en el despliegue.",
            "details": results,
            "postgres_password": postgres_password if act_pg != "skip" else None
        }

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
            if c.status == "running": return "already_running"
            c.start()
            return "started"
        except: pass

        try:
            self.client.images.get(image)
        except:
            self.client.images.pull(image)

        run_args = {
            "name": name,
            "detach": True,
            "restart_policy": {"Name": "always"},
            **kwargs
        }
        self.client.containers.run(image, **run_args)
        return "created"

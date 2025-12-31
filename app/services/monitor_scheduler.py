import asyncio
import logging
from typing import Dict, List
from datetime import datetime

# New imports
from ..utils.cache import cache_manager
from ..utils.device_clients.mikrotik.channels import readonly_channels

logger = logging.getLogger(__name__)

class MonitorScheduler:
    """
    Scheduler centralizado que consulta routers suscritos (vía ReadOnly Channel)
    y actualiza el CacheIn-Memory.
    
    Características:
    - 1 conexion persistente por router (gestión por RefCount)
    - Polling paralelo (asyncio.gather)
    - Fallback: Si falla un router, no bloquea a los demás
    """
    
    def __init__(self, poll_interval: float = 2.0):
        self._running = False
        self._subscribed_routers: Dict[str, dict] = {} # host -> creds
        self.poll_interval = poll_interval
        logger.info(f"[MonitorScheduler] Inicializado (Intervalo: {poll_interval}s)")
    
    async def subscribe(self, host: str, creds: dict) -> None:
        """
        Suscribe un router. El canal ReadOnly gestiona internamente el ref_count
        del socket, aquí gestionamos el ref_count lógico de la tarea.
        Método ASYNC para no bloquear el event loop con la conexión o SSL handshake.
        """
        # Actualizamos credenciales si cambian (e.g. password update)
        if host not in self._subscribed_routers:
            self._subscribed_routers[host] = {
                "creds": creds,
                "ref_count": 0
            }
        
        self._subscribed_routers[host]["ref_count"] += 1
        
        # Iniciamos conexión física en el canal
        # (El canal es inteligente: si ya existe, reutiliza; si no, conecta)
        try:
            # Offload blocking I/O (SSL handshake, socket connect) to thread pool
            await asyncio.to_thread(
                readonly_channels.acquire,
                host, 
                creds["username"], 
                creds["password"], 
                creds.get("port", 8729)
            )
        except Exception as e:
            logger.error(f"[MonitorScheduler] Falla al adquirir canal para {host}: {e}")

    async def unsubscribe(self, host: str) -> None:
        """
        Desuscribe un router. 
        Método ASYNC para no bloquear si hay que cerrar socket.
        """
        if host not in self._subscribed_routers:
            return

        # Obtener puerto antes de modificar nada
        creds = self._subscribed_routers[host]["creds"]
        port = creds.get("port", 8729)

        self._subscribed_routers[host]["ref_count"] -= 1
        
        # Liberamos conexión física en el canal (con el puerto correcto)
        # Offload blocking I/O (socket close can block)
        await asyncio.to_thread(readonly_channels.release, host, port)

        if self._subscribed_routers[host]["ref_count"] <= 0:
            del self._subscribed_routers[host]
            # Limpiamos cache también
            cache_manager.get_store("router_stats").delete(host)

    async def run(self):
        """Loop principal Async."""
        self._running = True
        logger.info("[MonitorScheduler] Iniciando loop de polling...")
        
        # Cache store para stats
        stats_cache = cache_manager.get_store("router_stats", default_ttl=5)

        while self._running:
            # Copia para iterar seguro
            targets = list(self._subscribed_routers.items())
            
            if not targets:
                await asyncio.sleep(1)
                continue
            
            # Crear tareas de polling paralelo
            tasks = []
            for host, info in targets:
                tasks.append(self._poll_host(host, info["creds"]))
            
            # Ejecutar todas (paralelismo real I/O)
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Procesar resultados
            for host, result in zip([t[0] for t in targets], results):
                if isinstance(result, Exception):
                    logger.error(f"[MonitorScheduler] Error polling {host}: {result}")
                    stats_cache.set(host, {"error": str(result)})
                elif result:
                    # Guardar en cache
                    stats_cache.set(host, result)

            await asyncio.sleep(self.poll_interval)
            
        logger.info("[MonitorScheduler] Detenido.")

    async def _poll_host(self, host: str, creds: dict) -> dict:
        """
        Ejecuta la consulta al API.
        Usa run_in_executor para no bloquear el loop principal con RLock o llamadas síncronas.
        """
        return await asyncio.to_thread(self._sync_fetch, host, creds)

    def _sync_fetch(self, host: str, creds: dict) -> dict:
        try:
            api = readonly_channels.acquire(host, creds["username"], creds["password"], creds.get("port", 8729))
            try:
                # Ejecutar comando resource
                resource_list = api.get_resource("/system/resource").get()
                if not resource_list:
                    return {"error": "No data"}
                r = resource_list[0]

                # Ejecutar comando health (para temperatura CPU en ciertos modelos)
                health_list = []
                try:
                    health_list = api.get_resource("/system/health").get()
                except:
                    pass  # Algunos routers no tienen /system/health

                # --- Robust health parsing (handles both MikroTik formats) ---
                # Format A (Flat): [{'voltage': '24.5', 'temperature': '30'}]
                # Format B (Modular): [{'name': 'voltage', 'value': '24'}, {'name': 'cpu-temperature', 'value': '53'}]
                voltage = None
                temperature = None
                cpu_temperature = None

                for sensor in health_list:
                    # Logic for Format B (Modular)
                    if "name" in sensor and "value" in sensor:
                        name = sensor["name"]
                        value = sensor["value"]
                        if name == "voltage":
                            voltage = value
                        elif name == "temperature":
                            temperature = value
                        elif name in ["cpu-temperature", "cpu-temp"]:
                            cpu_temperature = value
                    # Logic for Format A (Flat)
                    else:
                        if "voltage" in sensor:
                            voltage = sensor["voltage"]
                        if "temperature" in sensor:
                            temperature = sensor["temperature"]
                        if "cpu-temperature" in sensor:
                            cpu_temperature = sensor["cpu-temperature"]
                        if "cpu-temp" in sensor:
                            cpu_temperature = sensor["cpu-temp"]

                return {
                    "cpu_load": r.get("cpu-load"),
                    "free_memory": r.get("free-memory"),
                    "total_memory": r.get("total-memory"),
                    "uptime": r.get("uptime"),
                    "version": r.get("version"),
                    "board_name": r.get("board-name"),
                    "total_disk": r.get("total-hdd-space", r.get("total-disk-space")),
                    "free_disk": r.get("free-hdd-space", r.get("free-disk-space")),
                    "voltage": voltage,
                    "temperature": temperature,
                    "cpu_temperature": cpu_temperature,
                    "timestamp": datetime.now().isoformat()
                }
            finally:
                readonly_channels.release(host, creds.get("port", 8729))

        except Exception as e:
            raise e

# Singleton
monitor_scheduler = MonitorScheduler()

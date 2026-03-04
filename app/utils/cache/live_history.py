# app/utils/cache/live_history.py
"""
LiveHistoryStore: Almacena historiales circulares de métricas en vivo.

Estrategia dual:
  - Si Redict/Redis está disponible (CACHE_BACKEND=redict): usa listas Redis
    con LPUSH + LTRIM. Persiste entre workers, ideal para producción.
  - Si no (CACHE_BACKEND=memory o sin redis-py): usa deques en memoria.
    Simple y cero-config, ideal para dev y pequeños ISPs.

Estructura de datos:
  Cada "key" (ej: "192.168.1.1") tiene una lista de N puntos, donde cada
  punto es un dict con timestamp y los valores de interés.
  
  Ejemplo de punto para router:
    {"ts": 1709500000.0, "cpu": 12.0, "ram_pct": 44.0, "tx": 1024.0, "rx": 512.0}
  
  Ejemplo de punto para AP:
    {"ts": 1709500000.0, "clients": 8, "tx_kbps": 2048.0, "rx_kbps": 1024.0}
"""

import json
import logging
import time
from collections import deque
from typing import Any

logger = logging.getLogger(__name__)

# Cuántos puntos mantener por dispositivo (default: 5 minutos a 2s por tick = 150 puntos)
DEFAULT_MAX_POINTS = 150
# TTL en Redis para la lista (segundos). Si el dispositivo no se actualiza, expira.
DEFAULT_TTL = 600  # 10 minutos


class InMemoryRingBuffer:
    """Buffer circular en memoria para un solo dispositivo."""

    def __init__(self, max_points: int):
        self._data: deque[dict] = deque(maxlen=max_points)

    def append(self, point: dict) -> None:
        self._data.append(point)

    def to_list(self) -> list[dict]:
        return list(self._data)

    def clear(self) -> None:
        self._data.clear()


class LiveHistoryStore:
    """
    Almacén de historial en vivo para múltiples dispositivos.
    
    Usa Redis/Redict si CACHE_BACKEND=redict, sino memoria pura.
    La API es siempre asíncrona para funcionar en ambos contextos.
    """

    def __init__(
        self,
        namespace: str,
        max_points: int = DEFAULT_MAX_POINTS,
        ttl: int = DEFAULT_TTL,
    ):
        self.namespace = namespace
        self.max_points = max_points
        self.ttl = ttl
        # Fallback en memoria
        self._memory: dict[str, InMemoryRingBuffer] = {}
        # Detectar si Redis está disponible
        self._use_redict = self._check_redict()

    def _check_redict(self) -> bool:
        """Verifica si Redict está disponible y activo."""
        try:
            from .redict_store import redict_manager
            return redict_manager.is_connected
        except ImportError:
            return False

    def _get_key(self, host: str) -> str:
        return f"live_history:{self.namespace}:{host}"

    # ── Métodos Redis ──────────────────────────────────────────────────────────

    async def _redis_append(self, host: str, point: dict) -> None:
        try:
            from .redict_store import redict_manager
            client = redict_manager.get_client()
            try:
                key = self._get_key(host)
                serialized = json.dumps(point, default=str)
                # RPUSH: añadir al final de la lista
                await client.rpush(key, serialized)
                # LTRIM: mantener solo los últimos max_points
                await client.ltrim(key, -self.max_points, -1)
                # Renovar TTL en cada inserción
                await client.expire(key, self.ttl)
            finally:
                await client.aclose()
        except Exception as e:
            logger.debug(f"[LiveHistory] Redis append fallback para {host}: {e}")
            # Caer a memoria
            self._memory_append(host, point)

    async def _redis_get(self, host: str) -> list[dict]:
        try:
            from .redict_store import redict_manager
            client = redict_manager.get_client()
            try:
                key = self._get_key(host)
                raw_list = await client.lrange(key, 0, -1)
                result = []
                for item in raw_list:
                    try:
                        result.append(json.loads(item))
                    except json.JSONDecodeError:
                        pass
                return result
            finally:
                await client.aclose()
        except Exception as e:
            logger.debug(f"[LiveHistory] Redis get fallback para {host}: {e}")
            return self._memory_get(host)

    async def _redis_clear(self, host: str) -> None:
        try:
            from .redict_store import redict_manager
            client = redict_manager.get_client()
            try:
                await client.delete(self._get_key(host))
            finally:
                await client.aclose()
        except Exception:
            pass

    # ── Métodos Memoria ────────────────────────────────────────────────────────

    def _memory_append(self, host: str, point: dict) -> None:
        if host not in self._memory:
            self._memory[host] = InMemoryRingBuffer(self.max_points)
        self._memory[host].append(point)

    def _memory_get(self, host: str) -> list[dict]:
        if host not in self._memory:
            return []
        return self._memory[host].to_list()

    def _memory_clear(self, host: str) -> None:
        if host in self._memory:
            del self._memory[host]

    # ── API Pública ────────────────────────────────────────────────────────────

    async def append(self, host: str, point: dict) -> None:
        """Añade un punto de datos al historial del dispositivo."""
        # Siempre añadir timestamp si no viene
        if "ts" not in point:
            point["ts"] = time.time()

        if self._use_redict:
            await self._redis_append(host, point)
        else:
            self._memory_append(host, point)

    async def get_all(self, host: str) -> list[dict]:
        """Obtiene todo el historial del dispositivo (lista ordenada, más antiguo primero)."""
        if self._use_redict:
            return await self._redis_get(host)
        return self._memory_get(host)

    async def clear(self, host: str) -> None:
        """Limpia el historial de un dispositivo."""
        if self._use_redict:
            await self._redis_clear(host)
        self._memory_clear(host)  # Limpiar ambos siempre

    @property
    def backend(self) -> str:
        return "redict" if self._use_redict else "memory"


# ── Singletons por tipo de dispositivo ────────────────────────────────────────

# Para routers: CPU%, RAM%, bytes TX/RX acumulados (para calcular throughput)
router_live_history = LiveHistoryStore(namespace="router", max_points=150, ttl=600)

# Para APs: clientes, throughput TX/RX kbps
ap_live_history = LiveHistoryStore(namespace="ap", max_points=150, ttl=600)

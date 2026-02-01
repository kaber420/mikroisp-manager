# app/utils/cache/redict_store.py
"""
Backend de caché usando Redict (fork libre de Redis).
Implementa la misma interfaz que CacheStore pero con almacenamiento centralizado.
"""

import asyncio
import json
import logging
import os
from typing import Any

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class RedictManager:
    """
    Gestor de conexión para Redict usando Connection Pool.
    Loop-Aware: Maneja pools compartidos para el loop principal y conexiones frescas para loops efímeros.
    """

    _instance = None
    _pool: redis.ConnectionPool | None = None
    _url: str | None = None
    _connected: bool = False
    _pid: int | None = None
    _pool_loop: asyncio.AbstractEventLoop | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._pool = None
            cls._instance._url = None
            cls._instance._connected = False
            cls._instance._pid = None
            cls._instance._pool_loop = None
        return cls._instance

    def _get_main_pool(self) -> redis.ConnectionPool:
        """
        Gestiona el Pool Principal para el proceso y loop actuales.
        Si cambia el PID o el Loop Principal muere, recrea el pool.
        """
        current_pid = os.getpid()
        
        # Intentamos obtener el loop actual, necesario para el pool
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        # Si detectamos cambio de proceso (fork), invalidamos todo
        if self._pid != current_pid:
            self._pool = None
            self._pool_loop = None
            self._pid = current_pid
        
        # Si no hay pool, crearlo
        if self._pool is None:
            if not self._url:
                 self._url = os.getenv("REDICT_URL", "redis://localhost:6379/0")
            
            logger.info(f"🔄 Inicializando Redict Pool Principal (PID: {current_pid})")
            self._pool = redis.ConnectionPool.from_url(
                self._url, 
                encoding="utf-8", 
                decode_responses=False,
                max_connections=50
            )
            # Solo asignamos el loop si existe. Si es None, esperamos al primer uso con loop.
            self._pool_loop = current_loop
            self._pid = current_pid

        return self._pool

    async def connect(self, url: str | None = None) -> bool:
        """Configura la conexión."""
        self._url = url or os.getenv("REDICT_URL", "redis://localhost:6379/0")
        try:
            # Forzamos creación del pool
            pool = self._get_main_pool()
            client = redis.Redis(connection_pool=pool)
            await client.ping()
            await client.aclose()
            
            self._connected = True
            logger.info(f"✅ Redict Configurado: {self._url.split('@')[-1]}")
            return True
        except redis.RedisError as e:
            logger.error(f"❌ Error configurando Redict: {e}")
            self._connected = False
            return False

    def get_client(self) -> redis.Redis:
        """
        Obtiene un cliente Redis adecuado para el contexto actual.
        - Si estamos en el Main Loop (donde se creó el pool): Usa el Pool Compartido.
        - Si estamos en un Loop Efímero (asyncio.run en wrappers sync): Crea conexión fresca y aislada.
        """
        if not self._connected:
             raise RuntimeError("RedictManager not connected. Call connect() first.")

        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            raise RuntimeError("Redict client requested outside event loop")

        main_pool = self._get_main_pool() # Asegura init

        # Si el pool aún no tiene dueño (creado en init sync), lo adoptamos
        if self._pool_loop is None:
            self._pool_loop = current_loop
        
        # Verificación de Loop
        if self._pool_loop == current_loop:
            # ✅ Safe: Mismo loop, usar pool compartido
            return redis.Redis(connection_pool=main_pool)
        else:
            # ⚠️ Loop diferente detectado (ej. wrapper sync): NO USAR POOL
            # Crear conexión fresca para este contexto
            return redis.from_url(
                self._url,
                encoding="utf-8",
                decode_responses=False,
            )

    async def disconnect(self) -> None:
        """Desconecta y libera recursos."""
        self._connected = False
        if self._pool:
            try:
                await self._pool.disconnect()
            except Exception:
                pass
            self._pool = None
            self._pool_loop = None
        logger.info("Redict desconectado")

    @property
    def is_connected(self) -> bool:
        return self._connected and self._url is not None

    def get_store(self, name: str, **kwargs) -> "RedictStore | None":
        """Crea un store. El store pedirá clientes al manager dinámicamente."""
        if not self.is_connected:
            return None
        return RedictStore(name=name, **kwargs)

    async def get_stats(self) -> dict[str, Any]:
        if not self.is_connected:
            return {"connected": False}
        try:
            client = self.get_client()
            info = await client.info("memory")
            await client.aclose()
            return {"connected": True, "used_memory": info.get("used_memory_human", "N/A")}
        except Exception:
            return {"connected": False}
    
    # Pub/Sub methods
    async def publish(self, channel: str, message: Any) -> None:
        if not self.is_connected:
            return
        client = self.get_client()
        try:
            serialized = json.dumps(message, default=str)
            await client.publish(channel, serialized)
        finally:
            await client.aclose()

    def get_pubsub(self) -> redis.client.PubSub | None:
        if not self.is_connected:
            return None
        try:
            client = self.get_client()
            return client.pubsub()
        except RuntimeError:
            return None


class RedictStore:
    """
    Store de caché individual usando Redict.
    Delega la obtención de clientes al Manager para garantizar Thread/Loop safety.
    """

    def __init__(
        self,
        name: str,
        default_ttl: int = 300,
    ):
        # No guardamos pool ni client, los pedimos on-demand
        self.name = name
        self.default_ttl = default_ttl
        self._prefix = f"{name}:"

    def _get_client(self) -> redis.Redis:
        """Solicita cliente seguro al Manager."""
        return RedictManager().get_client()

    def _make_key(self, key: str) -> str:
        """Genera key con prefijo de namespace."""
        return f"{self._prefix}{key}"

    async def get_async(self, key: str) -> Any | None:
        """Obtiene valor de forma asíncrona."""
        client = self._get_client()
        try:
            data = await client.get(self._make_key(key))
            if data is None:
                return None
            return json.loads(data)
        except redis.RedisError as e:
            logger.warning(f"Redict GET error for {key}: {e}")
            return None
        except json.JSONDecodeError:
            return data
        finally:
            await client.aclose()

    async def set_async(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Guarda valor de forma asíncrona."""
        client = self._get_client()
        try:
            expire = ttl if ttl is not None else self.default_ttl
            serialized = json.dumps(value, default=str)
            await client.set(self._make_key(key), serialized, ex=expire)
        except redis.RedisError as e:
            logger.warning(f"Redict SET error for {key}: {e}")
        except (TypeError, ValueError) as e:
            logger.warning(f"Serialization error for {key}: {e}")
        finally:
            await client.aclose()

    async def delete_async(self, key: str) -> bool:
        """Elimina key de forma asíncrona."""
        client = self._get_client()
        try:
            result = await client.delete(self._make_key(key))
            return result > 0
        except redis.RedisError as e:
            logger.warning(f"Redict DELETE error for {key}: {e}")
            return False
        finally:
            await client.aclose()

    async def clear_async(self) -> None:
        """Elimina todas las keys del namespace."""
        client = self._get_client()
        try:
            cursor = 0
            pattern = f"{self._prefix}*"
            while True:
                cursor, keys = await client.scan(cursor, match=pattern, count=100)
                if keys:
                    await client.delete(*keys)
                if cursor == 0:
                    break
        except redis.RedisError as e:
            logger.warning(f"Redict CLEAR error: {e}")
        finally:
            await client.aclose()

    # Métodos síncronos (Wrappers)
    # Importante: Estos métodos usan asyncio.run() que crea un NUEVO loop efímero.
    # El Manager detectará esto y entregará una conexión fresca en lugar del pool compartido.

    def get(self, key: str) -> Any | None:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # No podemos bloquear el loop, y llamar async desde sync en loop es tricky.
                # Lo ideal es evitar este caso, pero si ocurre, forzamos context switch via thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(
                        asyncio.run, self.get_async(key)
                    ).result(timeout=5)
            else:
                return loop.run_until_complete(self.get_async(key))
        except Exception as e:
            logger.warning(f"Sync get failed for {key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    pool.submit(
                        asyncio.run, self.set_async(key, value, ttl)
                    ).result(timeout=5)
            else:
                loop.run_until_complete(self.set_async(key, value, ttl))
        except Exception as e:
            logger.warning(f"Sync set failed for {key}: {e}")

    def delete(self, key: str) -> bool:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(
                        asyncio.run, self.delete_async(key)
                    ).result(timeout=5)
            else:
                return loop.run_until_complete(self.delete_async(key))
        except Exception as e:
            logger.warning(f"Sync delete failed for {key}: {e}")
            return False


# Singleton instance for module-level import
redict_manager = RedictManager()

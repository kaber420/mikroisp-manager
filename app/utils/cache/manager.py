# app/utils/cache/manager.py
"""
Gestor de caché con soporte para backend en memoria o Redict.
El backend se selecciona mediante la variable de entorno CACHE_BACKEND.
"""

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import RLock
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .redict_store import RedictStore


@dataclass
class CacheEntry:
    value: Any
    expires_at: datetime | None = None
    created_at: datetime = field(default_factory=datetime.now)


class CacheStore:
    """Cache store en memoria (fallback cuando Redict no está disponible)."""

    def __init__(self, name: str, default_ttl: int = 300, max_size: int = 1000):
        self.name = name
        self.default_ttl = default_ttl  # segundos
        self.max_size = max_size
        self._data: dict[str, CacheEntry] = {}
        self._lock = RLock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            if entry.expires_at and datetime.now() > entry.expires_at:
                del self._data[key]
                return None
            return entry.value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        with self._lock:
            # Evicción LRU si excede max_size
            if len(self._data) >= self.max_size:
                # Simple eviction: remove oldest created
                oldest = min(self._data.items(), key=lambda x: x[1].created_at)
                del self._data[oldest[0]]

            expires = None
            if ttl is not None:
                expires = datetime.now() + timedelta(seconds=ttl)
            elif self.default_ttl:
                expires = datetime.now() + timedelta(seconds=self.default_ttl)

            self._data[key] = CacheEntry(value=value, expires_at=expires)

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._data:
                del self._data[key]
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._data)


class CacheManager:
    """
    Gestor global de caches con soporte dual: memoria o Redict.

    El backend se selecciona mediante CACHE_BACKEND=redict|memory.
    Si Redict no está disponible, hace fallback automático a memoria.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._stores = {}
            cls._instance._memory_stores = {}
            cls._instance._use_redict = os.getenv("CACHE_BACKEND", "memory") == "redict"
        return cls._instance

    def get_store(self, name: str, **kwargs) -> "CacheStore | RedictStore":
        """
        Obtiene un store de caché por nombre.

        Si CACHE_BACKEND=redict y la conexión está activa, retorna RedictStore.
        De lo contrario, retorna CacheStore en memoria.
        """
        # Intentar usar Redict si está configurado
        if self._use_redict:
            try:
                from .redict_store import redict_manager

                if redict_manager.is_connected:
                    redict_store = redict_manager.get_store(name, **kwargs)
                    if redict_store is not None:
                        return redict_store
            except ImportError:
                pass  # Fallback a memoria

        # Fallback: usar store en memoria
        if name not in self._memory_stores:
            self._memory_stores[name] = CacheStore(name=name, **kwargs)
        return self._memory_stores[name]

    def get_stats(self) -> dict[str, Any]:
        """Retorna estadísticas de todos los stores."""
        stats = {"backend": "redict" if self._use_redict else "memory"}

        if self._use_redict:
            try:
                from .redict_store import redict_manager

                if redict_manager.is_connected:
                    stats["redict_connected"] = True
                    stats["stores"] = list(redict_manager._stores.keys())
                    return stats
            except ImportError:
                pass

        stats["redict_connected"] = False
        stats["memory_stores"] = {
            name: store.size for name, store in self._memory_stores.items()
        }
        return stats

    def clear_all(self) -> None:
        """Limpia todos los stores."""
        for store in self._memory_stores.values():
            store.clear()

    @property
    def is_using_redict(self) -> bool:
        """Retorna True si está usando Redict como backend."""
        if not self._use_redict:
            return False
        try:
            from .redict_store import redict_manager

            return redict_manager.is_connected
        except ImportError:
            return False


# Singleton global
cache_manager = CacheManager()

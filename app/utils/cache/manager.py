from typing import Any, Dict, Optional
from datetime import datetime, timedelta
from threading import RLock
from dataclasses import dataclass, field

@dataclass
class CacheEntry:
    value: Any
    expires_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)

class CacheStore:
    """Cache store sin dependencias externas (sin Redis)."""
    
    def __init__(self, name: str, default_ttl: int = 300, max_size: int = 1000):
        self.name = name
        self.default_ttl = default_ttl  # segundos
        self.max_size = max_size
        self._data: Dict[str, CacheEntry] = {}
        self._lock = RLock()
    
    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            if entry.expires_at and datetime.now() > entry.expires_at:
                del self._data[key]
                return None
            return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
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
    """Gestor global de caches."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._stores = {}
        return cls._instance
    
    def get_store(self, name: str, **kwargs) -> CacheStore:
        if name not in self._stores:
            self._stores[name] = CacheStore(name=name, **kwargs)
        return self._stores[name]
    
    def get_stats(self) -> Dict[str, int]:
        return {name: store.size for name, store in self._stores.items()}
    
    def clear_all(self) -> None:
        for store in self._stores.values():
            store.clear()


# Singleton global
cache_manager = CacheManager()

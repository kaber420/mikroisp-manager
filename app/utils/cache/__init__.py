# app/utils/cache/__init__.py
"""
Cache module with optional Redict backend.
Falls back gracefully when redis-py is not installed.
"""

from .manager import CacheStore, cache_manager

__all__ = ["CacheStore", "cache_manager"]

# Optional Redict exports (only if redis-py is installed)
try:
    from .redict_store import RedictStore, redict_manager

    __all__.extend(["RedictStore", "redict_manager"])
except ImportError:
    # redis-py not installed, Redict features unavailable
    RedictStore = None  # type: ignore
    redict_manager = None  # type: ignore

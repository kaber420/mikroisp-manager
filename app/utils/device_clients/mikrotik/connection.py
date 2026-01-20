# app/utils/device_clients/mikrotik/connection.py
"""
Centralized MikroTik connection manager.

Provides a shared connection pool cache for MikroTik devices,
eliminating duplication between RouterService and device adapters.
"""

import logging
import ssl

from routeros_api import RouterOsApiPool
from routeros_api.api import RouterOsApi

logger = logging.getLogger(__name__)

# Global connection pool cache
# Key: (host, port, username), Value: RouterOsApiPool
_pool_cache: dict[tuple, RouterOsApiPool] = {}


def get_pool(
    host: str, username: str, password: str, port: int = 8729, force_new: bool = False
) -> RouterOsApiPool:
    """
    Get or create a cached connection pool for a MikroTik device.
    """
    cache_key = (host, port, username)

    if force_new or cache_key not in _pool_cache:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        new_pool = RouterOsApiPool(
            host,
            username=username,
            password=password,
            port=port,
            use_ssl=True,
            ssl_context=ssl_context,
            plaintext_login=True,
        )

        if force_new:
            return new_pool

        _pool_cache[cache_key] = new_pool
        logger.debug(f"[MikroTik] Created new pool for {host}:{port}")

    return _pool_cache[cache_key]


def get_api(host: str, username: str, password: str, port: int = 8729) -> RouterOsApi:
    cache_key = (host, port, username)

    # DISABLE POOLING: Always create a fresh connection to avoid thread-safety issues
    # caches are causing "Bad file descriptor" and "Malformed sentence" errors
    # when mixing WebSocket (long-lived) and HTTP (short-lived) threads.
    try:
        # NOTE: Adapter is now bypassing this to manage pool lifecycle directly
        # This remains for legacy support or one-off scripts
        pool = get_pool(host, username, password, port, force_new=True)
        return pool.get_api()
    except (ssl.SSLError, OSError, Exception) as e:
        error_str = str(e).lower()
        logger.warning(f"[MikroTik] Connection error for {host}: {e}")

        # Check if it's an SSL-related error that warrants a retry
        ssl_errors = [
            "ssl",
            "record_layer",
            "bad file descriptor",
            "connection closed",
            "broken pipe",
        ]
        is_ssl_error = any(err in error_str for err in ssl_errors)

        if is_ssl_error and cache_key in _pool_cache:
            logger.warning(f"[MikroTik] SSL error on {host}, flushing pool and retrying: {e}")

            # CRITICAL FIX: Do NOT call disconnect() on the pool here.
            # Other threads/tasks might be using it. If we close the socket,
            # they will crash with "Bad file descriptor".
            # Just remove it from cache so NEW requests get a fresh pool.
            # The old pool will be garbage collected eventually or closed by its own tasks.
            del _pool_cache[cache_key]

            # Retry with fresh connection
            try:
                pool = get_pool(host, username, password, port)
                return pool.get_api()
            except Exception as retry_error:
                logger.error(f"[MikroTik] Retry failed for {host}: {retry_error}")
                raise retry_error
        else:
            # Not an SSL error or no cached pool, just re-raise
            raise


def remove_pool(host: str, port: int = 8729, username: str = None):
    """
    Remove a cached pool (e.g., when credentials change or on error).

    Args:
        host: IP address or hostname.
        port: API port (optional, matches any if not specified).
        username: Username (optional, matches any if not specified).
    """
    keys_to_remove = [
        key
        for key in _pool_cache
        if key[0] == host
        and (port is None or key[1] == port)
        and (username is None or key[2] == username)
    ]
    for key in keys_to_remove:
        try:
            _pool_cache[key].disconnect()
            logger.debug(f"[MikroTik] Disconnected pool for {key[0]}:{key[1]}")
        except Exception:
            pass
        del _pool_cache[key]


def clear_all_pools():
    """
    Clear all cached pools. Useful for shutdown or testing.
    """
    for key, pool in list(_pool_cache.items()):
        try:
            pool.disconnect()
        except Exception:
            pass
    _pool_cache.clear()
    logger.debug("[MikroTik] All connection pools cleared")

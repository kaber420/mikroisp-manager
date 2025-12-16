# app/utils/device_clients/mikrotik/connection.py
"""
Centralized MikroTik connection manager.

Provides a shared connection pool cache for MikroTik devices,
eliminating duplication between RouterService and device adapters.
"""

import ssl
import logging
from typing import Dict, Optional

from routeros_api import RouterOsApiPool
from routeros_api.api import RouterOsApi

logger = logging.getLogger(__name__)

# Global connection pool cache
# Key: (host, port, username), Value: RouterOsApiPool
_pool_cache: Dict[tuple, RouterOsApiPool] = {}


def get_pool(host: str, username: str, password: str, port: int = 8729) -> RouterOsApiPool:
    """
    Get or create a cached connection pool for a MikroTik device.
    
    This prevents creating new SSL connections on every request.
    The pool is cached by (host, port, username) tuple.
    
    Args:
        host: IP address or hostname of the MikroTik device.
        username: API username.
        password: API password.
        port: API SSL port (default: 8729).
    
    Returns:
        RouterOsApiPool instance (cached or newly created).
    """
    cache_key = (host, port, username)
    
    if cache_key not in _pool_cache:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        _pool_cache[cache_key] = RouterOsApiPool(
            host,
            username=username,
            password=password,
            port=port,
            use_ssl=True,
            ssl_context=ssl_context,
            plaintext_login=True,
        )
        logger.debug(f"[MikroTik] Created new pool for {host}:{port}")
    
    return _pool_cache[cache_key]


def get_api(host: str, username: str, password: str, port: int = 8729) -> RouterOsApi:
    """
    Get an API connection from the cached pool.
    
    Convenience wrapper around get_pool().get_api().
    
    Args:
        host: IP address or hostname of the MikroTik device.
        username: API username.
        password: API password.
        port: API SSL port (default: 8729).
    
    Returns:
        RouterOsApi instance ready for use.
    """
    pool = get_pool(host, username, password, port)
    return pool.get_api()


def remove_pool(host: str, port: int = 8729, username: str = None):
    """
    Remove a cached pool (e.g., when credentials change or on error).
    
    Args:
        host: IP address or hostname.
        port: API port (optional, matches any if not specified).
        username: Username (optional, matches any if not specified).
    """
    keys_to_remove = [
        key for key in _pool_cache 
        if key[0] == host and (port is None or key[1] == port) and (username is None or key[2] == username)
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

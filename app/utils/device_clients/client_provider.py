# app/utils/device_clients/client_provider.py

from .ap_client import UbiquitiClient

# A simple in-memory cache for Ubiquiti clients.
# A dictionary where keys are device IPs and values are UbiquitiClient instances.
_client_cache = {}


def get_ubiquiti_client(host, username, password, port=443, http_mode=False):
    """
    Retrieves a cached UbiquitiClient instance or creates a new one if not found.
    """
    if host not in _client_cache:
        # If the client is not in the cache, create a new one and store it.
        _client_cache[host] = UbiquitiClient(host, username, password, port, http_mode)

    # Return the cached client.
    # The client itself will handle session state internally.
    return _client_cache[host]


def remove_ubiquiti_client(host):
    """
    Removes a UbiquitiClient instance from the cache.
    """
    if host in _client_cache:
        del _client_cache[host]

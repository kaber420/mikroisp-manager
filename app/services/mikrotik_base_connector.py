import asyncio
import contextlib

from ..core.constants import CredentialKeys
from ..utils.device_clients.mikrotik.channels import readonly_channels
from .base_connector import BaseDeviceConnector


class MikrotikBaseConnector(BaseDeviceConnector):
    """
    MikroTik specific connector.
    Implements connection logic using ReadOnlyChannelManager.
    """

    async def _connect(self, host: str, creds: dict) -> None:
        # Offload blocking acquire to thread
        await asyncio.to_thread(
            readonly_channels.acquire,
            host,
            creds[CredentialKeys.USERNAME],
            creds[CredentialKeys.PASSWORD],
            creds.get(CredentialKeys.PORT, 8729),
        )

    async def _disconnect(self, host: str) -> None:
        creds = self.get_credentials(host)
        port = creds.get(CredentialKeys.PORT, 8729)
        await asyncio.to_thread(readonly_channels.release, host, port)

    @contextlib.contextmanager
    def api_session(self, host: str):
        """
        Context manager to aquire/release API access for a block of code.
        The subscription keeps the connection alive, but we still use acquire/release
        pattern here to get the API object locally and ensure thread safety if needed
        by the manager.
        """
        creds = self.get_credentials(host)
        try:
            # Sync call as per original code's usage in fetch_router_stats
            # But wait, original code ran this in asyncio.to_thread implicitly?
            # No, fetch_router_stats was a synchronous method running in a thread pool managed by the scheduler?
            # Original: def fetch_router_stats(self, host: str) -> dict:
            # logic...
            # The scheduler calls it via: data = await loop.run_in_executor(None, self.connector.fetch_router_stats, host)
            # So `fetch_router_stats` IS synchronous and blocking.

            # So my `api_session` should be synchronous context manager.

            api = readonly_channels.acquire(
                host,
                creds[CredentialKeys.USERNAME],
                creds[CredentialKeys.PASSWORD],
                creds.get(CredentialKeys.PORT, 8729),
            )
            yield api
        finally:
            readonly_channels.release(host, creds.get(CredentialKeys.PORT, 8729))

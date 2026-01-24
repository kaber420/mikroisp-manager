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
    def api_session(self, host: str, creds: dict = None):
        """
        Context manager to aquire/release API access for a block of code.
        The subscription keeps the connection alive, but we still use acquire/release
        pattern here to get the API object locally and ensure thread safety if needed
        by the manager.

        Args:
            host: The router IP/hostname.
            creds: Optional dict with keys 'username', 'password', 'port'.
                   If provided, uses these credentials directly (ad-hoc).
                   If None, looks up credentials from active subscriptions.
        """
        if creds:
             # Ad-hoc connection (no subscription needed)
             username = creds.get(CredentialKeys.USERNAME)
             password = creds.get(CredentialKeys.PASSWORD)
             port = creds.get(CredentialKeys.PORT, 8729)
        else:
             # Subscription-based connection
             stored_creds = self.get_credentials(host)
             username = stored_creds[CredentialKeys.USERNAME]
             password = stored_creds[CredentialKeys.PASSWORD]
             port = stored_creds.get(CredentialKeys.PORT, 8729)

        try:
            api = readonly_channels.acquire(
                host,
                username,
                password,
                port,
            )
            yield api
        finally:
            readonly_channels.release(host, port)

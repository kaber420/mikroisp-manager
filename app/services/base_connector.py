import abc
import logging

# Create specific logger for this module if needed, or use a shared one
logger = logging.getLogger(__name__)


class BaseDeviceConnector(abc.ABC):
    """
    Abstract base class for device connectors.
    Handles common logic for credential storage, connection lifecycle logging,
    and cleanup.
    """

    def __init__(self):
        # host -> credentials dict
        self._credentials: dict[str, dict] = {}
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("Initialized")

    async def subscribe(self, host: str, creds: dict) -> None:
        """
        Subscribe to a device.
        Stores credentials and calls the specific _connect implementation.
        """
        self._credentials[host] = creds
        try:
            await self._connect(host, creds)
            self.logger.info(f"Subscribed to {host}")
        except Exception as e:
            self.logger.error(f"Failed to subscribe to {host}: {e}")
            # If connection fails, we remove credentials so we don't think we are subscribed
            if host in self._credentials:
                del self._credentials[host]
            raise

    async def unsubscribe(self, host: str) -> None:
        """
        Unsubscribe from a device.
        Calls the specific _disconnect implementation.
        Does NOT delete credentials immediately (allows for scheduler cleanup).
        """
        if host not in self._credentials:
            self.logger.warning(f"Attempted to unsubscribe from unknown host: {host}")
            return

        try:
            await self._disconnect(host)
            self.logger.debug(f"Released connection for {host}")
        except Exception as e:
            self.logger.error(f"Error releasing connection for {host}: {e}")

    def cleanup_credentials(self, host: str) -> None:
        """
        Clean up stored credentials for a host.
        """
        if host in self._credentials:
            del self._credentials[host]
            self.logger.info(f"Cleaned up credentials for {host}")

    def get_credentials(self, host: str) -> dict:
        """
        Helper to get credentials for a host. Raises ValueError if not found.
        """
        if host not in self._credentials:
            raise ValueError(f"Device {host} is not subscribed")
        return self._credentials[host]

    @abc.abstractmethod
    async def _connect(self, host: str, creds: dict) -> None:
        """
        Implementation specific connection logic (e.g. acquire socket/channel).
        Should be implemented by subclasses (VendorBaseConnector).
        """
        pass

    @abc.abstractmethod
    async def _disconnect(self, host: str) -> None:
        """
        Implementation specific disconnection logic.
        """
        pass

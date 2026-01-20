# app/utils/device_clients/mikrotik/ssh_client.py
"""
Reusable SSH client for MikroTik devices.

This class centralizes paramiko SSH connection logic to avoid code duplication
across different modules (spectral scan, backup service, etc.).
"""

import logging
from pathlib import Path
from typing import Any

import paramiko

logger = logging.getLogger(__name__)


class MikrotikSSHClient:
    """
    Reusable SSH client for MikroTik devices.

    Supports:
    - Standard SSH connection with configurable timeouts.
    - Command execution (exec_command).
    - SFTP access for file transfers.
    - Context manager for automatic cleanup.

    Example:
        with MikrotikSSHClient(host, username, password) as client:
            stdin, stdout, stderr = client.exec_command("/system/resource/print")
            print(stdout.read().decode())
    """

    # Default path for storing known host keys (relative to project root)
    DEFAULT_KNOWN_HOSTS_PATH = Path(__file__).resolve().parents[4] / "data" / "known_hosts"

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        port: int = 22,
        connect_timeout: int = 10,
        banner_timeout: int = 10,
        known_hosts_file: Path | None = None,
    ):
        """
        Initialize the SSH client.

        Args:
            host: IP address or hostname of the MikroTik device.
            username: SSH username.
            password: SSH password.
            port: SSH port (default: 22).
            connect_timeout: Connection timeout in seconds (default: 10).
            banner_timeout: Banner timeout in seconds (default: 10).
            known_hosts_file: Path to known_hosts file for TOFU security.
                              Defaults to data/known_hosts in project root.
        """
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.connect_timeout = connect_timeout
        self.banner_timeout = banner_timeout
        self.known_hosts_file = known_hosts_file or self.DEFAULT_KNOWN_HOSTS_PATH
        self._client: paramiko.SSHClient | None = None
        self._sftp: paramiko.SFTPClient | None = None

    def connect(self) -> bool:
        """
        Establish SSH connection to the device.

        Returns:
            True if connection was successful, False otherwise.
        """
        try:
            self._client = paramiko.SSHClient()

            # TOFU (Trust On First Use): Load known host keys if file exists
            if self.known_hosts_file.exists():
                self._client.load_host_keys(str(self.known_hosts_file))
                logger.debug(f"[SSH] Loaded known hosts from {self.known_hosts_file}")

            # AutoAddPolicy: Trust new hosts on first connection, save their key
            self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            self._client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=self.connect_timeout,
                banner_timeout=self.banner_timeout,
                look_for_keys=False,
                allow_agent=False,
            )

            # Persist host keys after successful connection
            self.known_hosts_file.parent.mkdir(parents=True, exist_ok=True)
            self._client.save_host_keys(str(self.known_hosts_file))
            logger.debug(f"[SSH] Saved host keys to {self.known_hosts_file}")

            logger.info(f"[SSH] Connected to {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"[SSH] Connection failed for {self.host}:{self.port}: {e}")
            self._client = None
            return False

    def disconnect(self):
        """Close SSH and SFTP connections."""
        if self._sftp:
            try:
                self._sftp.close()
            except Exception:
                pass
            self._sftp = None

        if self._client:
            try:
                self._client.close()
                logger.info(f"[SSH] Disconnected from {self.host}")
            except Exception:
                pass
            self._client = None

    def is_connected(self) -> bool:
        """Check if the SSH connection is active."""
        if self._client is None:
            return False
        transport = self._client.get_transport()
        return transport is not None and transport.is_active()

    def exec_command(
        self, command: str, get_pty: bool = False, timeout: float | None = None
    ) -> tuple[Any, Any, Any]:
        """
        Execute a command on the remote device.

        Args:
            command: The command to execute.
            get_pty: If True, request a pseudo-terminal (needed for interactive commands).
            timeout: Command timeout in seconds.

        Returns:
            Tuple of (stdin, stdout, stderr) file-like objects.

        Raises:
            RuntimeError: If not connected.
        """
        if not self.is_connected():
            raise RuntimeError("SSH client is not connected")

        return self._client.exec_command(command, get_pty=get_pty, timeout=timeout)  # nosec B601

    def open_sftp(self) -> paramiko.SFTPClient:
        """
        Open an SFTP session over the existing SSH connection.

        Returns:
            SFTPClient instance.

        Raises:
            RuntimeError: If not connected.
        """
        if not self.is_connected():
            raise RuntimeError("SSH client is not connected")

        if self._sftp is None:
            self._sftp = self._client.open_sftp()
        return self._sftp

    def get_channel(self) -> paramiko.Channel | None:
        """
        Get the underlying transport channel (for advanced use cases).

        Returns:
            The Channel object or None if not connected.
        """
        if not self.is_connected():
            return None
        return self._client.get_transport().open_channel("session")

    @property
    def client(self) -> paramiko.SSHClient | None:
        """Access the underlying paramiko SSHClient (for advanced use cases)."""
        return self._client

    # Context manager support
    def __enter__(self) -> "MikrotikSSHClient":
        """Enter context manager - connect to the device."""
        if not self.connect():
            raise ConnectionError(f"Failed to connect to {self.host}:{self.port}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager - disconnect from the device."""
        self.disconnect()
        return False  # Don't suppress exceptions

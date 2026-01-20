# app/api/aps/spectral.py
"""
WebSocket endpoint for MikroTik Spectral Scan.
Streams real-time spectrum data to the frontend for visualization.
"""

import asyncio
import logging
import re
import threading
import time
from queue import Empty, Queue

from fastapi import APIRouter, Cookie, Query, WebSocket, WebSocketDisconnect, status

from ...db.aps_db import get_ap_by_host_with_stats, get_ap_credentials
from ...utils.device_clients.mikrotik.ssh_client import MikrotikSSHClient

logger = logging.getLogger(__name__)

router = APIRouter()

# Regex to parse spectral-scan output: "5172.5  -102  -88   :.."
# Format: FREQ  MAGN  PEAK  GRAPH
SPECTRAL_PATTERN = re.compile(r"^\s*(\d+\.?\d*)\s+(-?\d+)\s+(-?\d+)")


class SpectralScanManager:
    """
    Manages SSH connection and spectral-scan command execution for MikroTik devices.
    Uses (reusable) MikrotikSSHClient and a background thread to read SSH output.
    """

    def __init__(self, host: str, username: str, password: str):
        self.host = host
        self.username = username
        self.password = password
        self._ssh_client: MikrotikSSHClient | None = None
        self.channel = None
        self._running = False
        self._data_queue = Queue()
        self._reader_thread = None
        self._wireless_type = None
        self._interface_name = None

    def connect(self) -> bool:
        """Establish SSH connection to the device using reusable client."""
        self._ssh_client = MikrotikSSHClient(
            host=self.host,
            username=self.username,
            password=self.password,
            port=22,
            connect_timeout=5,
            banner_timeout=5,
        )
        if self._ssh_client.connect():
            logger.info(f"[SpectralScan] SSH connected to {self.host}")
            return True
        else:
            logger.error(f"[SpectralScan] SSH connection failed for {self.host}")
            return False

    # NOTE: _detect_wireless_interface and get_all_interfaces were removed.
    # Interface detection is now done via RouterOS API in APService.get_wireless_interfaces().
    # The frontend always provides the interface from the dropdown.

    def _reader_loop(self, channel):
        """Background thread to read SSH output and parse spectral data."""
        logger.info(f"[SpectralScan] Reader thread started for {self.host}")
        buffer = ""
        total_bytes = 0
        parsed_count = 0

        try:
            while self._running and not channel.closed:
                if channel.recv_ready():
                    data = channel.recv(8192).decode("utf-8", errors="ignore")
                    total_bytes += len(data)
                    buffer += data

                    # Log only first data received (reduced verbosity for performance)
                    if total_bytes == len(data):
                        logger.info(f"[SpectralScan] First data received ({len(data)} bytes)")

                    # Check for errors
                    if "bad command" in buffer.lower() or "no such command" in buffer.lower():
                        logger.error("[SpectralScan] Command not supported")
                        self._data_queue.put({"error": "command_not_supported"})
                        break

                    # Normalize line endings: \r\n -> \n, \r -> \n
                    buffer = buffer.replace("\r\n", "\n").replace("\r", "\n")

                    # Process complete lines
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        # Remove ANSI escape sequences
                        line = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", line)
                        line = line.strip()

                        # Skip empty lines
                        if not line:
                            continue

                        # Skip headers and noise
                        if "FREQ" in line or "Columns" in line or "spectral" in line.lower():
                            continue
                        if line.startswith("[") or line.startswith(">"):
                            # Prompt line
                            continue

                        # Try to parse spectral data
                        match = SPECTRAL_PATTERN.match(line)
                        if match:
                            data_point = {
                                "freq": float(match.group(1)),
                                "signal": int(match.group(2)),
                                "peak": int(match.group(3)),
                            }
                            self._data_queue.put(data_point)
                            parsed_count += 1
                            # Log only first parsed point
                            if parsed_count == 1:
                                logger.info(
                                    f"[SpectralScan] First data parsed: freq={data_point['freq']} MHz"
                                )
                else:
                    time.sleep(0.05)

        except Exception as e:
            logger.error(f"[SpectralScan] Reader error: {e}", exc_info=True)

        logger.info(f"[SpectralScan] Reader thread ended (parsed {parsed_count} points)")

    def start_scan(
        self, interface: str, duration_seconds: int = 300, scan_range: str = None
    ) -> tuple[bool, str]:
        """
        Start the spectral-scan command.

        Args:
            interface: Interface to scan (e.g., 'wifi1'). Required.
            duration_seconds: Scan duration in seconds. Max 300 (5 min) for safety.
            scan_range: Optional frequency range (e.g., "5150-5875" or "current").
        """
        if not self._ssh_client or not self._ssh_client.is_connected():
            return False, "No conectado"

        if not interface:
            return False, "Se requiere especificar una interfaz"

        # Enforce max duration of 5 minutes for safety
        max_duration = 300
        duration_seconds = min(duration_seconds, max_duration)

        # Set interface info
        self._interface_name = interface
        # Detect type based on name
        if interface.startswith("wifi"):
            self._wireless_type = "wifi"
        else:
            self._wireless_type = "wireless"

        try:
            # Convert seconds to duration format (e.g., "2m" or "30s")
            if duration_seconds >= 60:
                duration_str = f"{duration_seconds // 60}m"
            else:
                duration_str = f"{duration_seconds}s"

            # Base command with without-paging to get all data at once
            if self._wireless_type == "wifi":
                base_cmd = f"/interface/wifi/spectral-scan {interface} duration={duration_str} without-paging"
            else:
                base_cmd = f"/interface/wireless/spectral-scan {interface} duration={duration_str} without-paging"

            # Add range if specified and not 'current'
            cmd = base_cmd
            range_info = "canal actual"

            if scan_range and scan_range != "current":
                # Handle special 'full' value - omit range parameter to scan entire band
                if scan_range.lower() == "full":
                    # Don't add range parameter - MikroTik will scan entire band
                    range_info = "banda completa"
                # Validate range format to prevent injection
                # Allow:
                #   - numeric ranges: 2412-2472, 5180,5200
                #   - band names: 2.4ghz, 5ghz (MikroTik standard)
                elif re.match(r"^[0-9\-,]+$", scan_range) or scan_range.lower() in [
                    "2.4ghz",
                    "5ghz",
                ]:
                    cmd += f" range={scan_range}"
                    range_info = f"rango {scan_range}"
                else:
                    logger.warning(f"[SpectralScan] Invalid range format ignored: {scan_range}")

            logger.info(f"[SpectralScan] Ejecutando: {cmd}")

            # Use exec_command which bypasses the interactive shell (no banner)
            stdin, stdout, stderr = self._ssh_client.exec_command(cmd, get_pty=True, timeout=None)

            # Store stdout channel for reading
            self.channel = stdout.channel
            self._running = True

            # Start reader thread
            self._reader_thread = threading.Thread(
                target=self._reader_loop, args=(self.channel,), daemon=True
            )
            self._reader_thread.start()

            return True, f"Escaneando {interface} ({range_info}) por {duration_str}"

        except Exception as e:
            logger.error(f"Error al iniciar spectral-scan: {e}")
            return False, str(e)

    def get_data(self, timeout: float = 0.1) -> list[dict]:
        """Get available data points from the queue."""
        results = []
        try:
            while True:
                data = self._data_queue.get_nowait()
                results.append(data)
        except Empty:
            pass
        return results

    def stop(self):
        """Stop the scan and close connections properly."""
        self._running = False

        if self.channel and not self.channel.closed:
            try:
                # MikroTik interactive commands use 'q' to quit properly
                # Ctrl+C can interrupt SSH or leave radio in bad state
                try:
                    self.channel.send("q")  # Quit command
                    time.sleep(0.5)
                except:
                    pass

                # Wait for MikroTik to restore radio to normal operation
                # This is critical - rushing this can leave the radio in a bad state
                time.sleep(1.0)

                # Try to read any remaining output to confirm stop
                try:
                    if self.channel.recv_ready():
                        self.channel.recv(8192)
                except:
                    pass

                logger.info(f"[SpectralScan] Quit signal sent to {self.host}")

            except Exception as e:
                logger.warning(f"[SpectralScan] Error sending quit signal: {e}")
            finally:
                try:
                    self.channel.close()
                except:
                    pass

        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=3)

        if self._ssh_client:
            self._ssh_client.disconnect()
            self._ssh_client = None


@router.websocket("/ws/aps/{host}/spectral-scan")
async def spectral_scan_websocket(
    websocket: WebSocket,
    host: str,
    umonitorpro_access_token_v2: str = Cookie(None),
    token: str = Query(None),
):
    """WebSocket endpoint for real-time spectral scan data."""

    # Auth check: Cookie OR Query param
    auth_token = umonitorpro_access_token_v2 or token

    if auth_token is None:
        logger.warning(f"[SpectralScan] Rejected: No auth cookie or token for {host}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    # Get AP details
    ap_data = get_ap_by_host_with_stats(host)
    if not ap_data:
        await websocket.send_json({"status": "error", "message": f"AP '{host}' not found"})
        await websocket.close()
        return

    # Check vendor
    vendor = ap_data.get("vendor", "ubiquiti")
    if vendor != "mikrotik":
        await websocket.send_json(
            {
                "status": "unsupported",
                "message": f"Spectral Scan not available for {vendor.capitalize()}. Requires MikroTik with wifi/wireless package.",
            }
        )
        await websocket.close()
        return

    # Get credentials
    creds = get_ap_credentials(host)
    if not creds:
        await websocket.send_json({"status": "error", "message": "Could not retrieve credentials"})
        await websocket.close()
        return

    scanner = SpectralScanManager(host, creds["username"], creds["password"])
    data_count = 0  # Define here for finally block

    try:
        await websocket.send_json({"status": "connecting"})

        if not scanner.connect():
            await websocket.send_json({"status": "error", "message": "Fallo la conexión SSH"})
            await websocket.close()
            return

        # Wait for configuration message from client
        await websocket.send_json({"status": "waiting_config"})

        try:
            config_msg = await asyncio.wait_for(websocket.receive_text(), timeout=10)
            import json

            config = json.loads(config_msg)
            interface = config.get("interface")
            duration = config.get("duration", 120)  # Default 2 min
            scan_range = config.get("range", "current")
        except asyncio.TimeoutError:
            interface = None
            duration = 120
            scan_range = "current"
        except:
            interface = None
            duration = 120
            scan_range = "current"

        await websocket.send_json({"status": "starting", "message": "Iniciando comando..."})

        success, message = scanner.start_scan(
            interface=interface, duration_seconds=duration, scan_range=scan_range
        )
        if not success:
            await websocket.send_json({"status": "unsupported", "message": message})
            await websocket.close()
            return

        # Send preparing status - MikroTik takes ~10-15s to calibrate radio
        await websocket.send_json(
            {
                "status": "preparing",
                "message": "Preparando scanner (calibrando radio)...",
                "interface": scanner._interface_name,
            }
        )

        await websocket.send_json(
            {
                "status": "scanning",
                "message": message,
                "duration": duration,
                "interface": scanner._interface_name,
            }
        )

        # Stream data
        no_data_ticks = 0
        start_time = time.time()

        while True:
            # Check for stop message
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=0.05)
                if msg == "stop":
                    await websocket.send_json(
                        {"status": "stopped", "message": "Escaneo detenido por el usuario"}
                    )
                    break
            except asyncio.TimeoutError:
                pass

            # Check if duration exceeded (frontend timer + 10s buffer)
            elapsed = time.time() - start_time
            if elapsed > duration + 10:
                await websocket.send_json({"status": "completed", "message": "Escaneo completado"})
                break

            # Get data from queue
            data_points = scanner.get_data()

            if data_points:
                no_data_ticks = 0
                for dp in data_points:
                    if "error" in dp:
                        await websocket.send_json(
                            {
                                "status": "unsupported",
                                "message": "Este dispositivo no soporta spectral-scan",
                            }
                        )
                        return
                    else:
                        data_count += 1
                        await websocket.send_json({"status": "data", "data": dp})
            else:
                no_data_ticks += 1
                # 600 ticks * 0.05s = 30 seconds timeout for no data
                if no_data_ticks > 600:
                    await websocket.send_json(
                        {"status": "completed", "message": "Escaneo completado (sin más datos)"}
                    )
                    break

            await asyncio.sleep(0.05)

    except WebSocketDisconnect:
        logger.info(f"[SpectralScan] Cliente desconectado para {host}")
    except Exception as e:
        logger.error(f"[SpectralScan] Error: {e}", exc_info=True)
        try:
            await websocket.send_json({"status": "error", "message": str(e)})
        except:
            pass
    finally:
        scanner.stop()
        try:
            await websocket.close()
        except:
            pass
        logger.info(f"[SpectralScan] Sesión terminada para {host} ({data_count} puntos)")

import logging
from datetime import datetime
from .mikrotik_base_connector import MikrotikBaseConnector

logger = logging.getLogger(__name__)

class RouterConnector(MikrotikBaseConnector):
    """
    Router specific connector.
    Fetches /system/resource and /system/health.
    """

    def fetch_router_stats(self, host: str) -> dict:
        """
        Fetch monitoring statistics from a router.
        This is a synchronous method (runs in thread pool from scheduler).
        """
        try:
            with self.api_session(host) as api:
                # Execute /system/resource command
                resource_list = api.get_resource("/system/resource").get()
                if not resource_list:
                    return {"error": "No data from /system/resource"}
                
                r = resource_list[0]
                
                # Execute /system/identity command to get hostname
                identity_list = []
                try:
                    identity_list = api.get_resource("/system/identity").get()
                except Exception:
                    pass

                hostname = identity_list[0].get("name") if identity_list else None

                # Execute /system/health command
                health_list = []
                try:
                    health_list = api.get_resource("/system/health").get()
                except Exception:
                    pass  # Some routers don't have /system/health
                
                # Parse health data (handles both MikroTik formats)
                voltage = None
                temperature = None
                cpu_temperature = None
                
                for sensor in health_list:
                    # Format B (Modular with name/value pairs)
                    if "name" in sensor and "value" in sensor:
                        name = sensor["name"]
                        value = sensor["value"]
                        if name == "voltage":
                            voltage = value
                        elif name == "temperature":
                            temperature = value
                        elif name in ["cpu-temperature", "cpu-temp"]:
                            cpu_temperature = value
                    # Format A (Flat dictionary)
                    else:
                        if "voltage" in sensor:
                            voltage = sensor["voltage"]
                        if "temperature" in sensor:
                            temperature = sensor["temperature"]
                        if "cpu-temperature" in sensor:
                            cpu_temperature = sensor["cpu-temperature"]
                        if "cpu-temp" in sensor:
                            cpu_temperature = sensor["cpu-temp"]
                
                # Build response
                return {
                    "cpu_load": r.get("cpu-load"),
                    "free_memory": r.get("free-memory"),
                    "total_memory": r.get("total-memory"),
                    "uptime": r.get("uptime"),
                    "version": r.get("version"),
                    "board_name": r.get("board-name"),
                    "board-name": r.get("board-name"),
                    "name": hostname,
                    "hostname": hostname,
                    "total_disk": r.get("total-hdd-space", r.get("total-disk-space")),
                    "free_disk": r.get("free-hdd-space", r.get("free-disk-space")),
                    "voltage": voltage,
                    "temperature": temperature,
                    "cpu_temperature": cpu_temperature,
                    "timestamp": datetime.now().isoformat()
                }

        except Exception as e:
            # self.logger is available from BaseDeviceConnector
            self.logger.error(f"Error fetching stats from {host}: {e}")
            raise

# Singleton instance
router_connector = RouterConnector()

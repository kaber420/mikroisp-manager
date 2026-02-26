import logging
from typing import Any

from routeros_api.api import RouterOsApi

from . import ip as mikrotik_ip

# Import shared parsers and interfaces
from . import parsers as mikrotik_parsers
from .interfaces import MikrotikInterfaceManager

logger = logging.getLogger(__name__)

# --- Wireless Connection & Status Management ---


def get_wireless_type(api: RouterOsApi) -> str | None:
    """
    Detects the type of wireless package installed (wireless vs wifi/wifiwave2).
    Uses the InterfaceManager for detection.
    """
    manager = MikrotikInterfaceManager(api)
    _, wtype = manager.get_wireless_interfaces()
    return wtype


def get_wireless_interfaces_detailed(api: RouterOsApi) -> list[dict[str, Any]]:
    """
    Returns a normalized list of wireless interfaces with details (frequency, band, etc.).
    Handles both legacy 'wireless' and new 'wifi' packages.
    """
    manager = MikrotikInterfaceManager(api)
    raw_interfaces, wtype = manager.get_wireless_interfaces()

    if not wtype:
        return []

    detailed_interfaces = []

    # helper for monitor commands
    def _get_monitor_data(path: str, iface_name: str) -> dict[str, Any]:
        try:
            res = api.get_resource(path).call("monitor", {"numbers": iface_name, "once": ""})
            return res[0] if res else {}
        except Exception:
            return {}

    resource_path = manager.get_wireless_interface_path(wtype)

    for iface in raw_interfaces:
        name = iface.get("name") or iface.get("default-name")
        if not name:
            continue

        freq = ""
        band = "unknown"
        width = ""
        tx_power = None

        # --- Modern 'wifi' / 'wifiwave2' logic ---
        if wtype in ["wifi", "wifiwave2"]:
            # Band parsing
            config_band = iface.get("channel.band") or iface.get("band") or ""
            if "5" in config_band or "6" in config_band:
                band = "5ghz"
            elif "2" in config_band:
                band = "2ghz"

            # Fallback band from config strings
            if band == "unknown":
                config = str(iface.get("configuration", "")).lower()
                if "5ghz" in config or "5g" in config:
                    band = "5ghz"
                elif "2ghz" in config or "2.4" in config or "2g" in config:
                    band = "2ghz"

            # Get real-time data from monitor
            mon_data = _get_monitor_data(resource_path, name)
            if mon_data:
                # Parse channel string "5220/ax/eeCe"
                channel_info = mon_data.get("channel", "")
                if "/" in channel_info:
                    freq_str = channel_info.split("/")[0]
                    freq = freq_str
                    try:
                        freq_int = int(freq_str)
                        if 2400 <= freq_int <= 2500:
                            band = "2ghz"
                        elif 5000 <= freq_int <= 6000:
                            band = "5ghz"
                    except ValueError:
                        pass

                tx_power = mon_data.get("tx-power")
                width = iface.get("channel.width") or iface.get("channel-width")

            # SSID extraction for ROS7 wifi/wifiwave2
            # Try various locations where SSID might be stored
            ssid = (
                iface.get("configuration.ssid")  # Flattened config
                or iface.get("ssid")  # Direct field
                or None
            )

        # --- Legacy 'wireless' logic ---
        else:
            freq = iface.get("frequency", "")
            width = iface.get("channel-width", "")

            # SSID for legacy wireless
            ssid = iface.get("ssid") or iface.get("mode")  # In AP mode, ssid is directly available

            # Band parsing from frequency
            if freq:
                # Try to reuse the parse_frequency helpers if needed, but simple band check here is fine
                try:
                    f_int = int("".join(filter(str.isdigit, str(freq))))
                    if 2400 <= f_int <= 2500:
                        band = "2ghz"
                    elif 5000 <= f_int <= 6000:
                        band = "5ghz"
                except ValueError:
                    pass

            # Fallback band
            if band == "unknown":
                b_field = iface.get("band", "")
                if "5ghz" in b_field:
                    band = "5ghz"
                elif "2ghz" in b_field:
                    band = "2ghz"

        detailed_interfaces.append(
            {
                "name": name,
                "type": wtype,  # 'wifi' or 'wireless'
                "band": band,
                "frequency": freq,
                "width": width,
                "ssid": ssid,  # Now directly available
                "tx_power": tx_power,
                "original_record": iface,  # keep reference if needed
            }
        )

    return detailed_interfaces


def get_connected_clients(api: RouterOsApi, fetch_arp: bool = True) -> list[dict[str, Any]]:
    """
    Returns a unified list of connected clients (CPEs) with parsed statistics.
    Handles legacy and modern wireless packages transparently.
    For legacy (v6), SSID and band are backfilled from interface details.

    Args:
        api: RouterOS API connection.
        fetch_arp: If True, fetches ARP table to enrich hostname/IP. Default True.
                   Set to False for lightweight polling where names come from DB.
    """
    manager = MikrotikInterfaceManager(api)
    # Detect type first
    _, wtype = manager.get_wireless_interfaces()
    if not wtype:
        return []


    reg_path = manager.get_registration_table_path(wtype)
    if not reg_path:
        return []

    # Build interface map for backfilling SSID/band on legacy devices
    interface_map: dict[str, dict[str, Any]] = {}
    try:
        detailed_interfaces = get_wireless_interfaces_detailed(api)
        interface_map = {iface["name"]: iface for iface in detailed_interfaces}
    except Exception as e:
        logger.warning(f"Failed to get detailed interface info for backfill: {e}")

    registrations = []
    try:
        # Try retrieving with stats (needed for ROS7 wifi throughput)
        registrations = api.get_resource(reg_path).call("print", {"stats": ""})
    except Exception:
        # Fallback to simple get if print stats fails
        try:
            registrations = api.get_resource(reg_path).get()
        except Exception:
            return []

    # Fetch ARP table for enrichment (only if fetch_arp=True)
    arp_map = {}
    dhcp_map = {}
    if fetch_arp:
        try:
            arp_entries = mikrotik_ip.get_arp_entries(api)
            for entry in arp_entries:
                if mac := entry.get("mac-address"):
                    # Normalize MAC to uppercase for consistent matching
                    arp_map[mac.upper()] = entry
        except Exception as e:
            logger.warning(f"Failed to fetch ARP table for enrichment: {e}")
        
        # Fetch DHCP leases for hostname (especially useful for v6)
        try:
            dhcp_leases = mikrotik_ip.get_dhcp_leases(api)
            for lease in dhcp_leases:
                if mac := lease.get("mac-address"):
                    # Normalize MAC to uppercase for consistent matching
                    dhcp_map[mac.upper()] = lease
        except Exception as e:
            logger.warning(f"Failed to fetch DHCP leases for enrichment: {e}")

    clients = []
    for reg in registrations:
        # Parse fields using the shared parser module
        signal = mikrotik_parsers.parse_signal(reg.get("signal-strength") or reg.get("signal"))
        tx_rate = mikrotik_parsers.parse_rate(reg.get("tx-rate"))
        rx_rate = mikrotik_parsers.parse_rate(reg.get("rx-rate"))

        # Byte parsing
        tx_bytes, rx_bytes = mikrotik_parsers.parse_bytes(reg.get("bytes"))

        # Throughput parsing (ROS7 uses tx-bits-per-second, etc)
        tx_throughput = mikrotik_parsers.parse_throughput_bps(reg.get("tx-bits-per-second"))
        rx_throughput = mikrotik_parsers.parse_throughput_bps(reg.get("rx-bits-per-second"))

        # If not found (legacy wireless sometimes calculates p-throughput or similar, but often doesn't give realtime rate in table)
        # We leave as None if not available.

        mac = reg.get("mac-address")
        client_ip = reg.get("last-ip")
        client_comment = reg.get("comment")
        
        # Extract radio-name (Mikrotik System Identity of the connected device)
        # This is available in registration table for Mikrotik CPEs
        radio_name = reg.get("radio-name")

        # ARP Enrichment: fill missing IP/hostname from ARP table
        # Normalize MAC lookup to uppercase
        arp_comment = None
        if mac and (arp_info := arp_map.get(mac.upper())):
            if not client_ip:
                client_ip = arp_info.get("address")
            arp_comment = arp_info.get("comment")

        # DHCP Enrichment: get hostname from DHCP lease
        dhcp_hostname = None
        if mac and (dhcp_info := dhcp_map.get(mac.upper())):
            # DHCP lease has 'host-name' field with hostname the device reported
            dhcp_hostname = dhcp_info.get("host-name")
            # Also fill IP from DHCP if missing
            if not client_ip:
                client_ip = dhcp_info.get("address")

        # Hostname resolution priority:
        # 1. Registration table comment (manually set on AP)
        # 2. ARP comment (manually set or dynamic)
        # 3. Radio name (device's own Mikrotik identity - ROS7)
        # 4. DHCP hostname (device reported name - works on all versions)
        # 5. None (UI will show "Unnamed Device")
        resolved_hostname = client_comment or arp_comment or radio_name or dhcp_hostname

        # Get SSID and band from registration (available in ROS7)
        client_ssid = reg.get("ssid")
        client_band = reg.get("band")
        client_interface = reg.get("interface")

        # Backfill SSID/band from interface details for legacy (ROS6) devices
        if (not client_ssid or not client_band) and client_interface:
            if iface_info := interface_map.get(client_interface):
                if not client_ssid:
                    client_ssid = iface_info.get("ssid")
                if not client_band:
                    client_band = iface_info.get("band")

        # Signal chains and SNR
        signal_ch0 = mikrotik_parsers.parse_signal(reg.get("signal-strength-ch0"))
        signal_ch1 = mikrotik_parsers.parse_signal(reg.get("signal-strength-ch1"))
        snr_val = mikrotik_parsers.parse_snr(reg.get("signal-to-noise"))
        noise_floor = mikrotik_parsers.parse_signal(reg.get("noise-floor"))

        client = {
            "mac": mac,
            "hostname": resolved_hostname,
            "ip_address": client_ip,
            "signal": signal,
            "signal_chain0": signal_ch0,
            "signal_chain1": signal_ch1,
            "snr": snr_val,
            "noise_floor": noise_floor,
            "tx_rate": tx_rate,
            "rx_rate": rx_rate,
            "ccq": mikrotik_parsers.parse_int(reg.get("tx-ccq") or reg.get("ccq")),
            "tx_bytes": tx_bytes,
            "rx_bytes": rx_bytes,
            "tx_throughput_kbps": int(tx_throughput) if tx_throughput else None,
            "rx_throughput_kbps": int(rx_throughput) if rx_throughput else None,
            "uptime": mikrotik_parsers.parse_uptime(reg.get("uptime", "0s")),
            "interface": client_interface,
            # Use backfilled values
            "ssid": client_ssid,
            "band": client_band,
            # Include raw extra data for adapters to use if needed
            "extra": {
                "rx_signal": reg.get("signal-strength"),
                "signal_ch0": reg.get("signal-strength-ch0"),
                "signal_ch1": reg.get("signal-strength-ch1"),
                "signal_to_noise": reg.get("signal-to-noise"),
                "noise_floor": reg.get("noise-floor"),
                "p_throughput": reg.get("p-throughput"),
                "distance": reg.get("distance"),
                "auth_type": reg.get("auth-type"),
            },
        }
        clients.append(client)

    return clients


def get_aggregate_interface_stats(api: RouterOsApi) -> dict[str, int]:
    """
    Calculates total TX/RX bytes from physical wireless interfaces.
    Returns: {"tx_bytes": int, "rx_bytes": int, "tx_throughput": int, "rx_throughput": int}
    """
    manager = MikrotikInterfaceManager(api)
    raw_interfaces, wtype = manager.get_wireless_interfaces()

    total_tx = 0
    total_rx = 0
    total_tx_speed = 0
    total_rx_speed = 0

    if not wtype:
        return {"tx_bytes": 0, "rx_bytes": 0, "tx_throughput": 0, "rx_throughput": 0}

    # Helper: Check if interface is a physical master (simplistic check for wifi1, wlan1 etc)
    # or check if it has no master.
    physical_interfaces = []

    for iface in raw_interfaces:
        name = iface.get("name", "")
        # A simple heuristic: physical interfaces often don't have a 'master-interface'
        # But in ROS7 wifi, 'master' might be used differently.
        # For simplicity, we trust the 'monitor-traffic' to give us data if we ask it.
        # We can sum up all "running" interfaces that look like wireless.
        if iface.get("running") == "true" or iface.get("disabled") == "false":
            physical_interfaces.append(name)

    # Note: Summing ALL interface traffic might double count if VLANs/Virtual APs are involved.
    # A safer bet for "Physical Throughput" is to filter by standard naming conventions OR check for master.
    # However, to replicate the Adapter logic, we'll try to match "wifiX" or "wlanX".

    filtered_interfaces = [
        n
        for n in physical_interfaces
        if (n.startswith("wifi") or n.startswith("wlan")) and n[-1].isdigit()
    ]

    # If no standard names found, use all found wireless
    if not filtered_interfaces:
        filtered_interfaces = [i.get("name") for i in raw_interfaces]

    # Batch get stats
    try:
        all_stats = api.get_resource("/interface").call("print", {"stats": ""})
        for stat in all_stats:
            if stat.get("name") in filtered_interfaces:
                t = mikrotik_parsers.parse_int(stat.get("tx-byte"))
                r = mikrotik_parsers.parse_int(stat.get("rx-byte"))
                if t:
                    total_tx += t
                if r:
                    total_rx += r

                # Traffic monitor is separate command usually, but 'stats' print might have packet rates but NOT current bits/sec.
                # Current bits/sec usually requires /interface/monitor-traffic or is in 'print stats' in newer versions?
                # 'print stats' usually has cumulative bytes.
                # 'monitor-traffic' is needed for live throughput.
    except Exception as e:
        logger.warning(f"Failed to get interface stats: {e}")

    # Monitor traffic for throughput (expensive if many interfaces, but accurate)
    for iface_name in filtered_interfaces:
        try:
            res = api.get_resource("/interface").call(
                "monitor-traffic", {"interface": iface_name, "once": ""}
            )
            if res:
                data = res[0]
                tx_bps = mikrotik_parsers.parse_throughput_bps(data.get("tx-bits-per-second")) or 0
                rx_bps = mikrotik_parsers.parse_throughput_bps(data.get("rx-bits-per-second")) or 0
                total_tx_speed += tx_bps
                total_rx_speed += rx_bps
        except Exception as e:
            logger.warning(f"Failed to monitor traffic for {iface_name}: {e}")

    return {
        "tx_bytes": total_tx,
        "rx_bytes": total_rx,
        "tx_throughput": int(total_tx_speed),
        "rx_throughput": int(total_rx_speed),
    }

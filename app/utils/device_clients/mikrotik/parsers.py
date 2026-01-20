# app/utils/device_clients/mikrotik/parsers.py
"""
Centralized parsing utilities for MikroTik data.

These functions convert RouterOS-formatted strings into Python-native types
for consistent handling across all modules (RouterService, adapters, etc.).
"""

import re


def parse_uptime(uptime_str: str) -> int:
    """
    Parse RouterOS uptime string to seconds.

    Examples:
        "1w2d3h4m5s" -> 788645
        "5d10h" -> 468000
        "30m" -> 1800

    Args:
        uptime_str: RouterOS uptime format string.

    Returns:
        Total seconds as integer.
    """
    if not uptime_str:
        return 0

    seconds = 0

    weeks = re.search(r"(\d+)w", uptime_str)
    days = re.search(r"(\d+)d", uptime_str)
    hours = re.search(r"(\d+)h", uptime_str)
    minutes = re.search(r"(\d+)m", uptime_str)
    secs = re.search(r"(\d+)s", uptime_str)

    if weeks:
        seconds += int(weeks.group(1)) * 7 * 24 * 3600
    if days:
        seconds += int(days.group(1)) * 24 * 3600
    if hours:
        seconds += int(hours.group(1)) * 3600
    if minutes:
        seconds += int(minutes.group(1)) * 60
    if secs:
        seconds += int(secs.group(1))

    return seconds


def parse_throughput_bps(throughput_str: str | None) -> float | None:
    """
    Parse throughput string to kbps.

    Handles both:
    - Raw bps numbers: '1032104' -> 1032.104 kbps
    - Formatted strings: '2.7Mbps', '89.1kbps', '0bps'

    Args:
        throughput_str: Throughput value from RouterOS.

    Returns:
        Throughput in kbps (kilobits per second), or None if unparseable.
    """
    if not throughput_str:
        return None
    try:
        throughput_str = str(throughput_str).strip()

        # First try: if it's a plain number, treat as bps
        if throughput_str.isdigit() or (throughput_str.replace(".", "", 1).isdigit()):
            value_bps = float(throughput_str)
            return value_bps / 1000.0  # Convert bps to kbps

        # Second try: Pattern matches numbers (with optional decimals) and unit
        match = re.match(r"([\d.]+)\s*(Gbps|Mbps|kbps|bps)", throughput_str, re.IGNORECASE)
        if not match:
            return None

        value = float(match.group(1))
        unit = match.group(2).lower()

        # Convert to kbps
        if unit == "gbps":
            return value * 1_000_000
        elif unit == "mbps":
            return value * 1_000
        elif unit == "kbps":
            return value
        elif unit == "bps":
            return value / 1_000
        return None
    except (ValueError, AttributeError):
        return None


def parse_signal(signal_str: str | None) -> int | None:
    """
    Parse signal strength string to dBm.

    Examples:
        "-50dBm" -> -50
        "-72" -> -72

    Args:
        signal_str: Signal strength from RouterOS.

    Returns:
        Signal in dBm as integer, or None.
    """
    if not signal_str:
        return None
    try:
        match = re.search(r"(-?\d+)", str(signal_str))
        return int(match.group(1)) if match else None
    except (ValueError, AttributeError):
        return None


def parse_frequency(freq_str: str | None) -> int | None:
    """
    Parse frequency string to MHz.

    Examples:
        "5180" -> 5180
        "5180MHz" -> 5180

    Args:
        freq_str: Frequency value from RouterOS.

    Returns:
        Frequency in MHz as integer, or None.
    """
    if not freq_str:
        return None
    try:
        match = re.search(r"(\d+)", str(freq_str))
        return int(match.group(1)) if match else None
    except (ValueError, AttributeError):
        return None


def parse_channel_width(width_str: str | None) -> int | None:
    """
    Parse channel width string to MHz.

    Examples:
        "20MHz" -> 20
        "40" -> 40
        "20/40/80MHz-eeCe" -> 20

    Args:
        width_str: Channel width from RouterOS.

    Returns:
        Channel width in MHz as integer, or None.
    """
    if not width_str:
        return None
    try:
        match = re.search(r"(\d+)", str(width_str))
        return int(match.group(1)) if match else None
    except (ValueError, AttributeError):
        return None


def parse_rate(rate_str: str | None) -> int | None:
    """
    Parse rate string to Mbps.

    Examples:
        "300Mbps" -> 300
        "144.4Mbps" -> 144
        "1200" -> 1200

    Args:
        rate_str: Rate value from RouterOS.

    Returns:
        Rate in Mbps as integer, or None.
    """
    if not rate_str:
        return None
    try:
        s = str(rate_str).strip()
        # Try to find number with unit first for better accuracy
        # Matches: 144.4Mbps, 300Mbps
        match = re.search(r"([\d\.]+)\s*Mbps", s, re.IGNORECASE)
        if match:
            return int(float(match.group(1)))

        match_gbps = re.search(r"([\d\.]+)\s*Gbps", s, re.IGNORECASE)
        if match_gbps:
            return int(float(match_gbps.group(1)) * 1000)

        # Fallback: find the first number (integer or float)
        match_num = re.search(r"(\d+(\.\d+)?)", s)
        if match_num:
            return int(float(match_num.group(1)))

        return None
    except (ValueError, AttributeError):
        return None


def parse_bytes(bytes_str: str | None) -> tuple[int | None, int | None]:
    """
    Parse bytes string which may be 'tx,rx' format.

    RouterOS registration table 'bytes' field format: "tx_bytes,rx_bytes"
    Where tx = bytes sent TO the client (Downlink), rx = bytes received FROM client (Uplink).

    Examples:
        "100,200" -> (100, 200) meaning (tx_bytes=100, rx_bytes=200)

    Args:
        bytes_str: Bytes value from RouterOS registration table.

    Returns:
        Tuple of (tx_bytes, rx_bytes), or (None, None) if unparseable.
    """
    if not bytes_str:
        return None, None
    try:
        if "," in str(bytes_str):
            parts = str(bytes_str).split(",")
            tx = parse_int(parts[0]) if len(parts) > 0 else None
            rx = parse_int(parts[1]) if len(parts) > 1 else None
            return tx, rx
        return None, None
    except Exception:
        return None, None


def parse_int(value: str | None) -> int | None:
    """
    Safely parse an integer from string.

    Args:
        value: String value to parse.

    Returns:
        Integer value, or None if unparseable.
    """
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def parse_snr(snr_str: str | None) -> int | None:
    """
    Parse Signal-to-Noise Ratio (SNR).

    Args:
        snr_str: SNR value from RouterOS.

    Returns:
        SNR in dB as integer, or None.
    """
    if not snr_str:
        return None
    try:
        return int(str(snr_str).strip())
    except (ValueError, TypeError):
        return None

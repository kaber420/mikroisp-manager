from typing import Any

from routeros_api.api import RouterOsApi

from .base import find_resource_id


def get_ip_addresses(api: RouterOsApi) -> list[dict[str, Any]]:
    return api.get_resource("/ip/address").get()


def get_ip_pools(api: RouterOsApi) -> list[dict[str, Any]]:
    return api.get_resource("/ip/pool").get()


def get_arp_entries(api: RouterOsApi) -> list[dict[str, Any]]:
    """
    Returns the full ARP table.
    Useful for enriching Connected Client data when registration table lacks IP/Hostname.
    """
    try:
        return api.get_resource("/ip/arp").get()
    except Exception:
        return []


def get_dhcp_leases(api: RouterOsApi) -> list[dict[str, Any]]:
    """
    Returns DHCP server leases.
    The 'host-name' field contains the hostname the device sent when requesting DHCP.
    Useful for v6 where registration table lacks hostname info.
    """
    try:
        return api.get_resource("/ip/dhcp-server/lease").get()
    except Exception:
        return []


def add_ip_address(api: RouterOsApi, interface: str, address: str, comment: str):
    return api.get_resource("/ip/address").add(
        interface=interface, address=address, comment=comment
    )


def remove_ip_address(api: RouterOsApi, address: str) -> bool:
    if resource_id := find_resource_id(api.get_resource("/ip/address"), address=address):
        api.get_resource("/ip/address").remove(id=resource_id)
        return True
    return False

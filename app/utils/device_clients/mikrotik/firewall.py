from routeros_api import RouterOsApiPool


def add_ip_to_address_list(
    api: RouterOsApiPool, list_name: str, address: str, comment: str
):
    """Agrega una IP a una lista negra (Address List)."""
    res = api.get_resource("/ip/firewall/address-list")
    # Verificar si ya existe para no duplicar errores
    if not res.get(list=list_name, address=address):
        res.add(list=list_name, address=address, comment=comment)


def remove_ip_from_address_list(api: RouterOsApiPool, list_name: str, address: str):
    """Saca una IP de la lista negra."""
    res = api.get_resource("/ip/firewall/address-list")
    # Buscar y borrar todas las entradas que coincidan
    for item in res.get(list=list_name, address=address):
        res.remove(id=item[".id"])


def get_nat_rules(api: RouterOsApiPool):
    """Obtiene todas las reglas NAT."""
    res = api.get_resource("/ip/firewall/nat")
    return res.get()


def remove_nat_rule(api: RouterOsApiPool, comment: str):
    """Elimina una regla NAT por su comentario."""
    res = api.get_resource("/ip/firewall/nat")
    rules = res.get(comment=comment)
    for rule in rules:
        res.remove(id=rule[".id"])


def add_nat_masquerade(api: RouterOsApiPool, **kwargs):
    """Añade una regla NAT de tipo masquerade."""
    res = api.get_resource("/ip/firewall/nat")
    # Los parámetros se pasan directamente desde el servicio
    # Valores esperados en kwargs: chain, action, out_interface, comment, etc.
    res.add(**kwargs)

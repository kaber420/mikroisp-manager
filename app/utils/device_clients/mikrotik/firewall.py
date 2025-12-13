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


def update_address_list_entry(
    api: RouterOsApiPool, list_name: str, address: str, action: str, comment: str = ""
):
    """
    Updates an address list entry based on the action.
    
    Args:
        api: RouterOS API connection
        list_name: Name of the address list
        address: IP address to manage
        action: 'add', 'remove', or 'disable'
        comment: Optional comment for the entry
    
    Returns:
        dict with status and message
    """
    res = api.get_resource("/ip/firewall/address-list")
    existing = res.get(list=list_name, address=address)
    
    if action == "add":
        if not existing:
            res.add(list=list_name, address=address, comment=comment)
            return {"status": "success", "message": f"Added {address} to {list_name}"}
        else:
            # Re-enable if disabled
            entry_id = existing[0][".id"]
            res.set(id=entry_id, disabled="no")
            return {"status": "success", "message": f"{address} already in {list_name}, enabled"}
    
    elif action == "remove":
        if existing:
            for item in existing:
                res.remove(id=item[".id"])
            return {"status": "success", "message": f"Removed {address} from {list_name}"}
        return {"status": "success", "message": f"{address} not in {list_name}"}
    
    elif action == "disable":
        if existing:
            for item in existing:
                res.set(id=item[".id"], disabled="yes")
            return {"status": "success", "message": f"Disabled {address} in {list_name}"}
        return {"status": "warning", "message": f"{address} not in {list_name}"}
    
    else:
        return {"status": "error", "message": f"Unknown action: {action}"}


def get_address_list_entries(api: RouterOsApiPool, list_name: str = None):
    """Gets address list entries, optionally filtered by list name."""
    res = api.get_resource("/ip/firewall/address-list")
    if list_name:
        return res.get(list=list_name)
    return res.get()


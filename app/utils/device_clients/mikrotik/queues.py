from routeros_api import RouterOsApiPool
from logging import getLogger

logger = getLogger(__name__)


def _handle_response(result: any, success_message: str) -> dict:
    """
    Workaround for routeros-api returning an empty list on success.
    Ensures a dict is returned to satisfy FastAPI response models.
    """
    if isinstance(result, list) and not result:
        return {"status": "success", "message": success_message}
    # If it's already a dict (like from a get or a proper add response)
    if isinstance(result, dict):
        return result
    # Fallback for other unexpected types
    return {"status": "success", "details": result}


def _get_or_create_pcq_queue_type(
    api: RouterOsApiPool, name: str, rate: str, classifier: str
) -> str:
    """
    Busca un queue type PCQ por nombre. Si no existe, lo crea.
    Retorna el nombre del queue type.
    """
    qt_resource = api.get_resource("/queue/type")
    existing = qt_resource.get(name=name)

    if not existing:
        logger.info(f"PCQ Queue Type '{name}' no encontrado. Creando...")
        qt_resource.add(name=name, kind="pcq", pcq_rate=rate, pcq_classifier=classifier)
        logger.info(f"PCQ Queue Type '{name}' creado con rate {rate}.")
    else:
        logger.debug(f"PCQ Queue Type '{name}' ya existe.")

    return name


def add_simple_queue_with_pcq(
    api: RouterOsApiPool,
    name: str,
    target: str,
    max_limit_upload: str,
    max_limit_download: str,
    parent: str = "none",
    comment: str = "",
):
    """
    Crea una Simple Queue para un cliente utilizando PCQ para la gestión de ancho de banda.
    """
    rate_upload_val = max_limit_upload.replace("M", "000k")
    rate_download_val = max_limit_download.replace("M", "000k")

    pcq_upload_name = f"pcq-upload-{max_limit_upload}"
    pcq_download_name = f"pcq-download-{max_limit_download}"

    _get_or_create_pcq_queue_type(
        api=api, name=pcq_upload_name, rate=rate_upload_val, classifier="src-address"
    )
    _get_or_create_pcq_queue_type(
        api=api,
        name=pcq_download_name,
        rate=rate_download_val,
        classifier="dst-address",
    )

    simple_q_resource = api.get_resource("/queue/simple")
    result = simple_q_resource.add(
        name=name,
        target=target,
        parent=parent,
        queue=f"{pcq_upload_name}/{pcq_download_name}",
        max_limit=f"{max_limit_upload}/{max_limit_download}",
        comment=comment,
    )
    return _handle_response(result, f"PCQ Queue '{name}' created successfully.")


def add_simple_queue(
    api: RouterOsApiPool,
    name: str,
    target: str,
    max_limit: str,
    parent: str = "none",
    comment: str = "",
):
    """Crea una nueva Simple Queue (sin PCQ)."""
    res = api.get_resource("/queue/simple")
    result = res.add(
        name=name, target=target, max_limit=max_limit, parent=parent, comment=comment
    )
    return _handle_response(result, f"Simple Queue '{name}' created successfully.")


def get_simple_queues(api: RouterOsApiPool):
    """Obtiene todas las Simple Queues."""
    res = api.get_resource("/queue/simple")
    return res.get()


def remove_simple_queue(api: RouterOsApiPool, queue_id: str):
    """Elimina una Simple Queue por su ID."""
    res = api.get_resource("/queue/simple")
    result = res.remove(id=queue_id)
    return _handle_response(result, f"Queue ID '{queue_id}' removed successfully.")


def set_simple_queue_limit(api: RouterOsApiPool, target: str, max_limit: str):
    """
    Cambia el límite de velocidad de una cola existente.
    Busca la cola por target en diferentes formatos y actualiza su límite.
    """
    res = api.get_resource("/queue/simple")

    # Intentar diferentes formatos de búsqueda
    target_variations = [target, f"{target}/32"]
    queue = None
    found_target = None

    for target_variant in target_variations:
        queues = res.get(target=target_variant)
        if queues:
            queue = queues[0]
            found_target = target_variant

            # Si no tiene ID (caso extraño), intentar buscar por nombre
            if not queue.get(".id") and not queue.get("id") and queue.get("name"):
                logger.warning(
                    f"Cola encontrada por target '{target_variant}' pero sin ID. Intentando buscar por nombre '{queue['name']}'..."
                )
                by_name = res.get(name=queue["name"])
                if by_name:
                    queue = by_name[0]

            queue_id = queue.get(".id") or queue.get("id")
            logger.info(
                f"Cola encontrada para target '{target_variant}': {queue.get('name', 'N/A')} (ID: {queue_id})"
            )
            break

    if not queue:
        logger.error(
            f"No se encontró ninguna Simple Queue para target '{target}' ni sus variaciones. Buscando todas las colas..."
        )
        # Intento adicional: listar todas las colas para debug
        all_queues = res.get()
        logger.error(f"Total de colas en el sistema: {len(all_queues)}")
        for q in all_queues[:5]:  # Mostrar solo las primeras 5 para no saturar logs
            logger.error(
                f"  - Cola: {q.get('name', 'N/A')}, Target: {q.get('target', 'N/A')}"
            )
        return {"status": "error", "message": f"Queue for target {target} not found"}

    queue_id = queue.get(".id") or queue.get("id")
    if not queue_id:
        logger.error(
            f"No se pudo obtener el ID de la cola '{queue.get('name')}' para actualizarla. Datos: {queue}"
        )
        return {"status": "error", "message": "Could not retrieve Queue ID"}

    try:
        # Actualizar usando el método correcto de la API
        logger.info(
            f"Actualizando cola '{queue.get('name')}' (ID: {queue_id}) - Límite anterior: {queue.get('max-limit', 'N/A')} -> Nuevo: {max_limit}"
        )
        res.set(id=queue_id, **{"max-limit": max_limit})
        logger.info(
            f"✓ Límite actualizado exitosamente a '{max_limit}' para cola '{queue.get('name')}' (target: {found_target})"
        )
        return _handle_response({}, f"Queue limit for '{target}' set to {max_limit}.")
    except Exception as e:
        logger.error(f"Error al actualizar límite de cola '{queue.get('name')}': {e}")
        return {"status": "error", "message": str(e)}

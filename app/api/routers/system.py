# app/api/routers/system.py
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import List, Dict, Any

from ...services.router_service import (
    RouterService,
    get_router_service,
    RouterCommandError,
)  # <-- LÍNEA CAMBIADA
from ...models.user import User
from ...core.users import current_active_user as get_current_active_user
from ...db import router_db

# --- ¡IMPORTACIÓN MODIFICADA! ---
from .models import (
    SystemResource,
    BackupCreateRequest,
    RouterUserCreate,
    PppoeSecretDisable,
)

router = APIRouter()


@router.get("/resources", response_model=SystemResource)
def get_router_resources(
    host: str,
    service: RouterService = Depends(get_router_service),
    user: User = Depends(get_current_active_user),
):
    try:
        resources = service.get_system_resources()
        # Actualizamos la DB con la info obtenida
        update_data = {
            "hostname": resources.get("name"),
            "model": resources.get("board-name"),
            "firmware": resources.get("version"),
        }
        router_db.update_router_in_db(host, update_data)
        return resources
    except RouterCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system/files", response_model=List[Dict[str, Any]])
def api_get_backup_files(
    service: RouterService = Depends(get_router_service),
    user: User = Depends(get_current_active_user),
):
    try:
        return service.get_backup_files()
    except RouterCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/system/create-backup", response_model=Dict[str, str])
def api_create_backup(
    request: BackupCreateRequest,
    service: RouterService = Depends(get_router_service),
    user: User = Depends(get_current_active_user),
):
    try:
        # Verificar si el archivo ya existe
        existing_files = service.get_backup_files()
        target_name = request.backup_name
        
        # Asegurar extensión correcta para la búsqueda
        if request.backup_type == "backup" and not target_name.endswith(".backup"):
            target_name += ".backup"
        elif request.backup_type == "export" and not target_name.endswith(".rsc"):
            target_name += ".rsc"

        # Buscar coincidencia exacta
        file_exists = any(f['name'] == target_name for f in existing_files)

        if file_exists and not request.overwrite:
            raise HTTPException(
                status_code=409,
                detail=f"El archivo '{target_name}' ya existe."
            )

        if request.backup_type == "backup":
            if not request.backup_name.endswith(".backup"):
                request.backup_name += ".backup"
            service.create_backup(request.backup_name)
            message = f"Archivo .backup '{request.backup_name}' creado."
        elif request.backup_type == "export":
            if not request.backup_name.endswith(".rsc"):
                request.backup_name += ".rsc"
            service.create_export_script(request.backup_name)
            message = f"Archivo .rsc '{request.backup_name}' creado."
        else:
            raise HTTPException(
                status_code=400,
                detail="Tipo de backup no válido. Usar 'backup' o 'export'.",
            )

        return {"status": "success", "message": message}
    except RouterCommandError as e:
        raise HTTPException(status_code=500, detail=f"Error al crear el archivo: {e}")


@router.delete("/system/files/{file_id:path}", status_code=status.HTTP_204_NO_CONTENT)
def api_remove_backup_file(
    file_id: str,
    host: str,
    request: Request,
    service: RouterService = Depends(get_router_service),
    user: User = Depends(get_current_active_user),
):
    from ...core.audit import log_action
    try:
        service.remove_file(file_id)
        log_action("DELETE", "backup_file", f"{host}/{file_id}", user=user, request=request)
        return
    except RouterCommandError as e:
        raise HTTPException(
            status_code=404, detail=f"No se pudo eliminar el archivo: {e}"
        )


@router.get("/system/users", response_model=List[Dict[str, Any]])
def api_get_router_users(
    service: RouterService = Depends(get_router_service),
    user: User = Depends(get_current_active_user),
):
    try:
        return service.get_router_users()
    except RouterCommandError as e:
        raise HTTPException(
            status_code=500, detail=f"Error al leer usuarios del router: {e}"
        )


@router.post("/system/users", response_model=Dict[str, Any])
def api_create_router_user(
    user_data: RouterUserCreate,
    service: RouterService = Depends(get_router_service),
    user: User = Depends(get_current_active_user),
):
    try:
        return service.add_router_user(**user_data.model_dump())
    except (RouterCommandError, ValueError) as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.delete("/system/users/{user_id:path}", status_code=status.HTTP_204_NO_CONTENT)
def api_remove_router_user(
    user_id: str,
    host: str,
    request: Request,
    service: RouterService = Depends(get_router_service),
    user: User = Depends(get_current_active_user),
):
    from ...core.audit import log_action
    try:
        service.remove_router_user(user_id)
        log_action("DELETE", "router_user", f"{host}/{user_id}", user=user, request=request)
        return
    except RouterCommandError as e:
        raise HTTPException(
            status_code=404, detail=f"No se pudo eliminar el usuario: {e}"
        )


# --- ¡ENDPOINTS MODIFICADOS AQUÍ! ---


@router.patch("/interfaces/{interface_id:path}", status_code=status.HTTP_204_NO_CONTENT)
def api_set_interface_status(
    interface_id: str,
    status_update: PppoeSecretDisable,  # Reutilizamos este modelo (espera {"disable": true/false})
    type: str = Query(
        ..., description="El tipo de interfaz, ej. 'ether', 'bridge'"
    ),  # <-- AÑADIDO
    service: RouterService = Depends(get_router_service),
    user: User = Depends(get_current_active_user),
):
    """Habilita o deshabilita una interfaz."""
    try:
        # Pasar el tipo al servicio
        service.set_interface_status(
            interface_id, status_update.disable, interface_type=type
        )  # <-- AÑADIDO
        return
    except (RouterCommandError, ValueError) as e:
        raise HTTPException(
            status_code=400,
            detail=f"No se pudo actualizar la interfaz {interface_id}. Causa: {e}",
        )


@router.delete(
    "/interfaces/{interface_id:path}", status_code=status.HTTP_204_NO_CONTENT
)
def api_remove_interface(
    interface_id: str,
    host: str,
    request: Request,
    type: str = Query(
        ..., description="El tipo de interfaz, ej. 'vlan', 'bridge'"
    ),
    service: RouterService = Depends(get_router_service),
    user: User = Depends(get_current_active_user),
):
    """Elimina una interfaz (VLAN, Bridge, etc.)."""
    from ...core.audit import log_action
    try:
        service.remove_interface(interface_id, interface_type=type)
        log_action("DELETE", "interface", f"{host}/{interface_id}", user=user, request=request, details={"type": type})
        return
    except (RouterCommandError, ValueError) as e:
        raise HTTPException(
            status_code=400,
            detail=f"No se pudo eliminar la interfaz {interface_id}. Causa: {e}",
        )


# --- LOCAL BACKUP FILES (Server-side) ---

import os
from pathlib import Path
from fastapi.responses import FileResponse

# Base path for backups
BACKUP_BASE_DIR = Path(os.getcwd()) / "data"


@router.get("/system/local-backups", response_model=List[Dict[str, Any]])
def api_get_local_backup_files(
    host: str,
    user: User = Depends(get_current_active_user),
):
    """
    Lista archivos de backup locales (en el servidor) para un router específico.
    """
    # Obtener datos del router para encontrar su carpeta
    router_info = router_db.get_router_by_host(host)
    if not router_info:
        raise HTTPException(status_code=404, detail="Router no encontrado")
    
    # Determinar la carpeta del router
    zona_id = router_info.get("zona_id")
    hostname = router_info.get("hostname") or host
    
    # Buscar la carpeta por zona (misma lógica que backup_service)
    zona_folder = None
    if zona_id:
        from ...db.base import get_db_connection
        conn = get_db_connection()
        cursor = conn.execute("SELECT nombre FROM zonas WHERE id = ?", (zona_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            zona_folder = row["nombre"].replace(" ", "_").replace("/", "-")
    
    if not zona_folder:
        zona_folder = f"Zona_{zona_id}" if zona_id else "Sin_Zona"
    
    router_folder = hostname.replace(" ", "_").replace("/", "-")
    backup_path = BACKUP_BASE_DIR / zona_folder / router_folder
    
    # Debug logging
    import logging
    logging.info(f"Looking for backups in: {backup_path}")
    
    files = []
    if backup_path.exists() and backup_path.is_dir():
        for f in sorted(backup_path.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if f.is_file() and (f.suffix in [".backup", ".rsc"]):
                stat = f.stat()
                files.append({
                    "name": f.name,
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                    "type": "backup" if f.suffix == ".backup" else "script",
                    "path": str(f.relative_to(BACKUP_BASE_DIR))
                })
    else:
        logging.warning(f"Backup path does not exist: {backup_path}")
    
    return files


@router.get("/system/local-backups/download")
def api_download_local_backup(
    host: str,
    filename: str = Query(..., description="Nombre del archivo a descargar"),
    user: User = Depends(get_current_active_user),
):
    """
    Descarga un archivo de backup local.
    """
    # Obtener datos del router para encontrar su carpeta
    router_info = router_db.get_router_by_host(host)
    if not router_info:
        raise HTTPException(status_code=404, detail="Router no encontrado")
    
    zona_id = router_info.get("zona_id")
    hostname = router_info.get("hostname") or host
    
    # Determinar carpeta de zona
    zona_folder = None
    if zona_id:
        from ...db.base import get_db_connection
        conn = get_db_connection()
        cursor = conn.execute("SELECT nombre FROM zonas WHERE id = ?", (zona_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            zona_folder = row["nombre"].replace(" ", "_").replace("/", "-")
    
    if not zona_folder:
        zona_folder = f"Zona_{zona_id}" if zona_id else "Sin_Zona"
    
    router_folder = hostname.replace(" ", "_").replace("/", "-")
    file_path = BACKUP_BASE_DIR / zona_folder / router_folder / filename
    
    # Validación de seguridad: asegurar que el archivo está dentro de BACKUP_BASE_DIR
    try:
        file_path.resolve().relative_to(BACKUP_BASE_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Ruta de archivo inválida")
    
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/octet-stream"
    )


@router.delete("/system/local-backups", status_code=status.HTTP_204_NO_CONTENT)
def api_delete_local_backup(
    host: str,
    filename: str = Query(..., description="Nombre del archivo a eliminar"),
    request: Request = None,
    user: User = Depends(get_current_active_user),
):
    """
    Elimina un archivo de backup local del servidor.
    """
    from ...core.audit import log_action
    
    # Obtener datos del router para encontrar su carpeta
    router_info = router_db.get_router_by_host(host)
    if not router_info:
        raise HTTPException(status_code=404, detail="Router no encontrado")
    
    zona_id = router_info.get("zona_id")
    hostname = router_info.get("hostname") or host
    
    # Determinar carpeta de zona
    zona_folder = None
    if zona_id:
        from ...db.base import get_db_connection
        conn = get_db_connection()
        cursor = conn.execute("SELECT nombre FROM zonas WHERE id = ?", (zona_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            zona_folder = row["nombre"].replace(" ", "_").replace("/", "-")
    
    if not zona_folder:
        zona_folder = f"Zona_{zona_id}" if zona_id else "Sin_Zona"
    
    router_folder = hostname.replace(" ", "_").replace("/", "-")
    file_path = BACKUP_BASE_DIR / zona_folder / router_folder / filename
    
    # Validación de seguridad: asegurar que el archivo está dentro de BACKUP_BASE_DIR
    try:
        file_path.resolve().relative_to(BACKUP_BASE_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Ruta de archivo inválida")
    
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    # Eliminar el archivo
    try:
        file_path.unlink()
        log_action("DELETE", "local_backup", f"{host}/{filename}", user=user, request=request)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar archivo: {e}")
    
    return


@router.post("/system/save-to-server", response_model=Dict[str, Any])
def api_save_backup_to_server(
    host: str,
    filename: str = Query(..., description="Nombre del archivo en el router"),
    user: User = Depends(get_current_active_user),
):
    """
    Descarga un archivo de backup del router y lo guarda en el servidor local.
    """
    from ...services.backup_service import save_file_to_server
    from ...utils.security import decrypt_data
    
    # Obtener datos del router
    router_info = router_db.get_router_by_host(host)
    if not router_info:
        raise HTTPException(status_code=404, detail="Router no encontrado")
    
    zona_id = router_info.get("zona_id")
    hostname = router_info.get("hostname") or host
    username = router_info.get("username")
    password = router_info.get("password")  # Ya decryptada por get_router_by_host
    
    # Obtener nombre de zona
    zona_name = "Sin_Zona"
    if zona_id:
        from ...db.base import get_db_connection
        conn = get_db_connection()
        cursor = conn.execute("SELECT nombre FROM zonas WHERE id = ?", (zona_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            zona_name = row["nombre"]
    
    # Llamar al servicio de backup
    result = save_file_to_server(
        host=host,
        username=username,
        password=password,
        remote_filename=filename,
        zona_name=zona_name,
        hostname=hostname
    )
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    
    return result


# app/api/routers/system.py
from typing import Any
import logging
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.users import current_active_user as get_current_active_user
from ...db import router_db
from ...db.engine import get_session
from ...models.user import User
from ...models.zona import Zona
from ...services.router_service import (
    RouterCommandError,
    RouterService,
    get_router_service,
)

from .models import (
    BackupCreateRequest,
    PppoeSecretDisable,
    RouterUserCreate,
    SystemResource,
)

router = APIRouter()

# Base path for backups
BACKUP_BASE_DIR = Path(os.getcwd()) / "data"


@router.get("/resources", response_model=SystemResource)
async def get_router_resources(
    host: str,
    service: RouterService = Depends(get_router_service),
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        # service is already connected via dependency
        resources = service.get_system_resources()
        # Actualizamos la DB con la info obtenida
        update_data = {
            "hostname": resources.get("name"),
            "model": resources.get("board-name"),
            "firmware": resources.get("version"),
        }
        await router_db.update_router_in_db(session, host, update_data)
        return resources
    except RouterCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system/files", response_model=list[dict[str, Any]])
async def api_get_backup_files(
    service: RouterService = Depends(get_router_service),
    user: User = Depends(get_current_active_user),
):
    try:
        return service.get_backup_files()
    except RouterCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/system/create-backup", response_model=dict[str, str])
async def api_create_backup(
    request: BackupCreateRequest,
    service: RouterService = Depends(get_router_service),
    user: User = Depends(get_current_active_user),
):
    try:
        existing_files = service.get_backup_files()
        target_name = request.backup_name

        if request.backup_type == "backup" and not target_name.endswith(".backup"):
            target_name += ".backup"
        elif request.backup_type == "export" and not target_name.endswith(".rsc"):
            target_name += ".rsc"

        file_exists = any(f["name"] == target_name for f in existing_files)

        if file_exists and not request.overwrite:
            raise HTTPException(status_code=409, detail=f"El archivo '{target_name}' ya existe.")

        if request.backup_type == "backup":
            if not request.backup_name.endswith(".backup"):
                request.backup_name += ".backup"
            service.create_backup(request.backup_name, overwrite=request.overwrite)
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
async def api_remove_backup_file(
    file_id: str,
    host: str,
    request: Request,
    service: RouterService = Depends(get_router_service),
    user: User = Depends(get_current_active_user),
):
    from ...core.audit import log_action

    try:
        service.remove_file(file_id)
        # Note: log_action might be sync, assuming it handles itself or we might need asyncio.to_thread if passing DB session
        # For now, keeping as is (audit log usually separate)
        log_action("DELETE", "backup_file", f"{host}/{file_id}", user=user, request=request)
        return
    except RouterCommandError as e:
        raise HTTPException(status_code=404, detail=f"No se pudo eliminar el archivo: {e}")


@router.get("/system/users", response_model=list[dict[str, Any]])
async def api_get_router_users(
    service: RouterService = Depends(get_router_service),
    user: User = Depends(get_current_active_user),
):
    try:
        return service.get_router_users()
    except RouterCommandError as e:
        raise HTTPException(status_code=500, detail=f"Error al leer usuarios del router: {e}")


@router.post("/system/users", response_model=dict[str, Any])
async def api_create_router_user(
    user_data: RouterUserCreate,
    service: RouterService = Depends(get_router_service),
    user: User = Depends(get_current_active_user),
):
    try:
        return service.add_router_user(**user_data.model_dump())
    except (RouterCommandError, ValueError) as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.delete("/system/users/{user_id:path}", status_code=status.HTTP_204_NO_CONTENT)
async def api_remove_router_user(
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
        raise HTTPException(status_code=404, detail=f"No se pudo eliminar el usuario: {e}")


@router.patch("/interfaces/{interface_id:path}", status_code=status.HTTP_204_NO_CONTENT)
async def api_set_interface_status(
    interface_id: str,
    status_update: PppoeSecretDisable,
    type: str = Query(..., description="El tipo de interfaz, ej. 'ether', 'bridge'"),
    service: RouterService = Depends(get_router_service),
    user: User = Depends(get_current_active_user),
):
    """Habilita o deshabilita una interfaz."""
    try:
        service.set_interface_status(
            interface_id, status_update.disable, interface_type=type
        )
        return
    except (RouterCommandError, ValueError) as e:
        raise HTTPException(
            status_code=400,
            detail=f"No se pudo actualizar la interfaz {interface_id}. Causa: {e}",
        )


@router.delete("/interfaces/{interface_id:path}", status_code=status.HTTP_204_NO_CONTENT)
async def api_remove_interface(
    interface_id: str,
    host: str,
    request: Request,
    type: str = Query(..., description="El tipo de interfaz, ej. 'vlan', 'bridge'"),
    service: RouterService = Depends(get_router_service),
    user: User = Depends(get_current_active_user),
):
    """Elimina una interfaz (VLAN, Bridge, etc.)."""
    from ...core.audit import log_action

    try:
        service.remove_interface(interface_id, interface_type=type)
        log_action(
            "DELETE",
            "interface",
            f"{host}/{interface_id}",
            user=user,
            request=request,
            details={"type": type},
        )
        return
    except (RouterCommandError, ValueError) as e:
        raise HTTPException(
            status_code=400,
            detail=f"No se pudo eliminar la interfaz {interface_id}. Causa: {e}",
        )


# --- LOCAL BACKUP FILES (Server-side) ---

@router.get("/system/local-backups", response_model=list[dict[str, Any]])
async def api_get_local_backup_files(
    host: str,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Lista archivos de backup locales (en el servidor) para un router específico.
    """
    # Obtener datos del router para encontrar su carpeta
    router_info = await router_db.get_router_by_host(session, host)
    if not router_info:
        raise HTTPException(status_code=404, detail="Router no encontrado")

    # Determinar la carpeta del router
    zona_id = router_info.zona_id
    hostname = router_info.hostname or host

    # Buscar la carpeta por zona
    zona_folder = None
    if zona_id:
        zona = await session.get(Zona, zona_id)
        if zona:
            zona_folder = zona.nombre.replace(" ", "_").replace("/", "-")

    if not zona_folder:
        zona_folder = f"Zona_{zona_id}" if zona_id else "Sin_Zona"

    router_folder = hostname.replace(" ", "_").replace("/", "-")
    backup_path = BACKUP_BASE_DIR / zona_folder / router_folder

    logging.info(f"Looking for backups in: {backup_path}")

    files = []
    if backup_path.exists() and backup_path.is_dir():
        for f in sorted(backup_path.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if f.is_file() and (f.suffix in [".backup", ".rsc"]):
                stat = f.stat()
                files.append(
                    {
                        "name": f.name,
                        "size": stat.st_size,
                        "modified": stat.st_mtime,
                        "type": "backup" if f.suffix == ".backup" else "script",
                        "path": str(f.relative_to(BACKUP_BASE_DIR)),
                    }
                )
    else:
        logging.warning(f"Backup path does not exist: {backup_path}")

    return files


@router.get("/system/local-backups/download")
async def api_download_local_backup(
    host: str,
    filename: str = Query(..., description="Nombre del archivo a descargar"),
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Descarga un archivo de backup local.
    """
    router_info = await router_db.get_router_by_host(session, host)
    if not router_info:
        raise HTTPException(status_code=404, detail="Router no encontrado")

    zona_id = router_info.zona_id
    hostname = router_info.hostname or host

    zona_folder = None
    if zona_id:
        zona = await session.get(Zona, zona_id)
        if zona:
            zona_folder = zona.nombre.replace(" ", "_").replace("/", "-")

    if not zona_folder:
        zona_folder = f"Zona_{zona_id}" if zona_id else "Sin_Zona"

    router_folder = hostname.replace(" ", "_").replace("/", "-")
    file_path = BACKUP_BASE_DIR / zona_folder / router_folder / filename

    try:
        file_path.resolve().relative_to(BACKUP_BASE_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Ruta de archivo inválida")

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    return FileResponse(
        path=str(file_path), filename=filename, media_type="application/octet-stream"
    )


@router.delete("/system/local-backups", status_code=status.HTTP_204_NO_CONTENT)
async def api_delete_local_backup(
    host: str,
    filename: str = Query(..., description="Nombre del archivo a eliminar"),
    request: Request = None,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Elimina un archivo de backup local del servidor.
    """
    from ...core.audit import log_action

    router_info = await router_db.get_router_by_host(session, host)
    if not router_info:
        raise HTTPException(status_code=404, detail="Router no encontrado")

    zona_id = router_info.zona_id
    hostname = router_info.hostname or host

    zona_folder = None
    if zona_id:
        zona = await session.get(Zona, zona_id)
        if zona:
            zona_folder = zona.nombre.replace(" ", "_").replace("/", "-")
            
    if not zona_folder:
        zona_folder = f"Zona_{zona_id}" if zona_id else "Sin_Zona"

    router_folder = hostname.replace(" ", "_").replace("/", "-")
    file_path = BACKUP_BASE_DIR / zona_folder / router_folder / filename

    try:
        file_path.resolve().relative_to(BACKUP_BASE_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Ruta de archivo inválida")

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    try:
        file_path.unlink()
        log_action("DELETE", "local_backup", f"{host}/{filename}", user=user, request=request)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar archivo: {e}")

    return


@router.post("/system/save-to-server", response_model=dict[str, Any])
async def api_save_backup_to_server(
    host: str,
    filename: str = Query(..., description="Nombre del archivo en el router"),
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Descarga un archivo de backup del router y lo guarda en el servidor local.
    """
    from ...services.backup_service import save_file_to_server

    router_info = await router_db.get_router_by_host(session, host)
    if not router_info:
        raise HTTPException(status_code=404, detail="Router no encontrado")

    zona_id = router_info.zona_id
    hostname = router_info.hostname or host
    username = router_info.username
    password = router_info.password  # Already decrypted

    # Obtener nombre de zona
    zona_name = "Sin_Zona"
    if zona_id:
        zona = await session.get(Zona, zona_id)
        if zona:
            zona_name = zona.nombre

    # Llamar al servicio de backup (Blocking function must be run in thread?)
    # Since save_file_to_server is blocking, we should wrap it to avoid blocking async loop.
    import asyncio
    
    result = await asyncio.to_thread(
        save_file_to_server,
        host=host,
        username=username,
        password=password,
        remote_filename=filename,
        zona_name=zona_name,
        hostname=hostname,
    )

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])

    return result

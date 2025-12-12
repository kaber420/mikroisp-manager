import os
import time
import logging
import paramiko
from datetime import datetime
from ..db.router_db import get_routers_for_backup

# Configura logger local
logger = logging.getLogger("BackupService")

BACKUP_BASE_DIR = os.path.join(os.getcwd(), "data")

def run_backup_cycle():
    """
    Función principal llamada por el scheduler.
    Recorre todos los routers y ejecuta el respaldo.
    """
    logger.info("Iniciando ciclo de respaldo de routers...")
    routers = get_routers_for_backup()
    
    success_count = 0
    fail_count = 0
    
    for router in routers:
        try:
            result = process_router_backup(router)
            if result["status"] == "success":
                success_count += 1
                logger.info(f"✅ Respaldo exitoso para {router['host']}: {result['files']}")
            else:
                fail_count += 1
                logger.error(f"❌ Error en {router['host']}: {result['message']}")
        except Exception as e:
            fail_count += 1
            logger.error(f"❌ Excepción crítica procesando {router['host']}: {e}")
            
    logger.info(f"Ciclo de respaldo finalizado. Éxitos: {success_count}, Fallos: {fail_count}")


def process_router_backup(router_data: dict):
    """
    Conecta por SSH, genera backup y export, descarga y limpia.
    """
    host = router_data["host"]
    username = router_data["username"]
    password = router_data["password"]
    
    # Estructura de carpetas: data/{Zona}/{NombreRouter}/
    zona_name = router_data.get("zona_nombre", "Sin_Zona").replace(" ", "_").replace("/", "-")
    router_name = (router_data.get("hostname") or host).replace(" ", "_").replace("/", "-")
    
    save_path = os.path.join(BACKUP_BASE_DIR, zona_name, router_name)
    os.makedirs(save_path, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    base_filename = f"{router_name}-{timestamp}"
    
    # Nombres de archivos
    backup_file_name = f"{base_filename}.backup"
    export_file_name = f"{base_filename}.rsc"
    
    # Nombre temporal en el router
    temp_name = "umanager_auto"
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        # 1. Conectar SSH
        ssh.connect(
            hostname=host,
            username=username,
            password=password,
            port=22, # Asumimos puerto estándar, podría agregarse a la DB
            timeout=20
        )
        
        # 2. Generar Backup Binario (.backup)
        # /system backup save name=umanager_auto
        stdin, stdout, stderr = ssh.exec_command(f"/system backup save name={temp_name}")
        exit_status = stdout.channel.recv_exit_status()
        if exit_status != 0:
            return {"status": "error", "message": f"Fallo al crear backup binario: {stderr.read().decode()}"}
        
        # 3. Generar Export (.rsc)
        # /export file=umanager_auto
        # Nota: 'export' puede tardar y no siempre devuelve exit code 0 limpio en versiones viejas, pero probamos.
        stdin, stdout, stderr = ssh.exec_command(f"/export file={temp_name}")
        # Esperamos un poco porque export es lento
        time.sleep(2) 
        
        # 4. Descargar archivos por SFTP
        sftp = ssh.open_sftp()
        downloaded_files = []
        
        # Descargar .backup
        remote_backup = f"{temp_name}.backup"
        local_backup = os.path.join(save_path, backup_file_name)
        try:
            # Intentar raíz
            try:
                sftp.get(remote_backup, local_backup)
            except FileNotFoundError:
                # Intentar flash/ (común en nuevos routers)
                remote_backup = f"flash/{temp_name}.backup"
                sftp.get(remote_backup, local_backup)
            downloaded_files.append(backup_file_name)
        except Exception as e:
            logger.warning(f"No se pudo descargar .backup de {host}: {e}")

        # Descargar .rsc
        remote_export = f"{temp_name}.rsc"
        local_export = os.path.join(save_path, export_file_name)
        try:
            try:
                sftp.get(remote_export, local_export)
            except FileNotFoundError:
                remote_export = f"flash/{temp_name}.rsc"
                sftp.get(remote_export, local_export)
            downloaded_files.append(export_file_name)
        except Exception as e:
            logger.warning(f"No se pudo descargar .rsc de {host}: {e}")

        sftp.close()
        
        # 5. Limpiar archivos remotos
        # /file remove [find name~"umanager_auto"]
        ssh.exec_command(f'/file remove [find name~"{temp_name}"]')
        
        ssh.close()
        
        if not downloaded_files:
            return {"status": "error", "message": "No se descargó ningún archivo"}
            
        return {
            "status": "success", 
            "files": downloaded_files,
            "path": save_path
        }

    except Exception as e:
        if ssh:
            ssh.close()
        return {"status": "error", "message": str(e)}

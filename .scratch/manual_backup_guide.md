# Guía de Respaldo Manual de Base de Datos

Esta guía detalla cómo realizar un respaldo manual seguro de la base de datos de µMonitor Pro (`inventory.sqlite`) sin detener el servicio.

## Proceso Manual Paso a Paso

### A. Respaldo en Caliente (Recomendado)

SQLite permite hacer respaldos mientras la base de datos está en uso mediante el comando `.backup` o `VACUUM INTO`.

**Comando:**

```bash
# Crear directorio de respaldos si no existe
mkdir -p data/backups/manual

# Ejecutar respaldo (reemplaza TIMESTAMP con la fecha actual si lo deseas)
sqlite3 data/db/inventory.sqlite ".backup 'data/backups/manual/inventory_backup.sqlite'"
```

### B. Respaldo "Offline" (Requiere detener servicio)

Si prefieres copiar el archivo directamente, **debes detener el servicio** para evitar copiar una base de datos corrupta (especialmente si en el futuro activas modo WAL).

1. Detener el servicio:

   ```bash
   sudo systemctl stop umonitor
   # O si usas ejecución manual: Ctrl+C en la terminal del servicio
   ```

2. Copiar el archivo:

   ```bash
   cp data/db/inventory.sqlite data/backups/manual/inventory_backup_offline.sqlite
   ```

3. Iniciar servicio:

   ```bash
   sudo systemctl start umonitor
   ```

## Restauración

**¡PELIGRO!** Restaurar la base de datos sobrescribirá todos los datos actuales.

1. Detener el servicio: `sudo systemctl stop umonitor`
2. Renombrar la DB actual (por seguridad):

   ```bash
   mv data/db/inventory.sqlite data/db/inventory.sqlite.old
   ```

3. Copiar el respaldo a la ubicación original:

   ```bash
   cp data/backups/manual/inventory_backup.sqlite data/db/inventory.sqlite
   ```

4. Restaurar permisos (importante para que la app pueda escribir):

   ```bash
   chown umonitor:umonitor data/db/inventory.sqlite
   chmod 664 data/db/inventory.sqlite
   ```

5. Iniciar servicio: `sudo systemctl start umonitor`

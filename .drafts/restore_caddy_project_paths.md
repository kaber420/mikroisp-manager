# Restauración de Configuración Caddy: Lectura Directa desde el Proyecto

> [!NOTE]
> **Estado: ✅ IMPLEMENTADO** - El script `apply_caddy_config.sh` ha sido actualizado para usar ACLs.

Este documento detalla los pasos para corregir la configuración de Caddy y permitir que lea los certificados directamente desde `data/certs` dentro del directorio del proyecto, en lugar de copiarlos a `/etc/caddy`. Esto restaura la funcionalidad original de mantener el proyecto autocontenido.

## Problema Original

Anteriormente, el script `apply_caddy_config.sh` copiaba los certificados a `/etc/caddy/certs` y modificaba el `Caddyfile` del sistema para apuntar a esa copia. Esto rompía la filosofía de diseño donde la aplicación debería controlar sus propios recursos.

## Solución Implementada

Se utiliza **ACLs (Access Control Lists)** para otorgar al usuario `caddy` permisos de ejecución (+x) en la ruta de directorios hasta llegar a los certificados, y permisos de lectura (+r) en los archivos `.pem`, sin abrir los permisos generales ni cambiar el grupo propietario.

### Características del Nuevo Script

El script [apply_caddy_config.sh](file:///home/kaber420/Documentos/python/umanager6/scripts/apply_caddy_config.sh) ahora:

1. **Instala herramientas ACL** si no están presentes (`acl` package)
2. **Configura `cap_net_bind_service`** automáticamente para que Caddy pueda usar puertos 80/443 sin root
3. **Copia el Caddyfile SIN modificar rutas** - mantiene las rutas absolutas al proyecto
4. **Aplica ACLs quirúrgicos**:
   - `+x` (traverse) en todos los directorios padre hasta `data/certs/`
   - `+r` (read) en cada archivo `.pem`
5. **Valida el Caddyfile** antes de reiniciar
6. **Reinicia Caddy** con la nueva configuración

### Uso

```bash
# Ejecutar desde el directorio del proyecto
sudo ./scripts/apply_caddy_config.sh
```

## Beneficios

- **Autocontención:** Los certificados se quedan en `data/certs`. Si los regeneras con el launcher, Caddy los ve inmediatamente tras un reload.
- **Seguridad:** No se exponen archivos personales, solo se permite el paso (`+x`) a través de los directorios necesarios.
- **Mantenibilidad:** El `Caddyfile` del repositorio es la fuente de verdad.
- **Puertos privilegiados:** El script configura automáticamente `setcap` para que Caddy use puertos 80/443.

## Verificación

Después de ejecutar el script, puedes verificar:

```bash
# Ver ACLs aplicados
getfacl /home/kaber420/Documentos/python/umanager6/data/certs/

# Ver capacidades de Caddy
getcap $(which caddy)

# Estado del servicio
sudo systemctl status caddy
```

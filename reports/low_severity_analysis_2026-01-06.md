# Análisis de Hallazgos de Baja Severidad (Bandit)
**Fecha:** 2026-01-06
**Contexto:** Revisión manual de 48 hallazgos "Media/Baja" severidad (principalmente `try...except pass`).

## Resumen
La mayoría de los hallazgos corresponden al patrón **"Error Suppression"** (`try: ... except: pass`). Tras analizar el código, se han clasificado en tres categorías:

1.  **✅ Limpieza Segura (Safe Cleanup):** Errores ignorados intencionalmente durante la limpieza de recursos. No requieren acción.
2.  **🛡️ Protección de Secretos (Security Masking):** Errores silenciados para evitar que credenciales aparezcan en logs. Requieren refactorización segura.
3.  **⚠️ Fallos Silenciosos (Silent Failures):** Errores que ocultan fallos funcionales (ej. métricas vacías). Deben ser arreglados.

---

## 1. ✅ Limpieza Segura (Safe Sanitization)
*Se recomienda mantener el `pass` o cambiar a `logger.debug` para depuración.*

### Archivo: `app/utils/device_clients/mikrotik/ssl.py`
*   **Línea 53 (`generate_csr`)**: Intenta borrar un template antiguo. Si no existe, falla, lo cual es esperado.
    ```python
    try: cert_resource.remove(...) 
    except Exception: pass
    ```
*   **Línea 242, 244, 263 (`import_certificate`)**: Bloques `finally` para borrar archivos temporales (`.crt`, `.key`) y cerrar SSH. Es correcto que no fallen si el archivo ya no existe.

### Archivo: `app/utils/device_clients/mikrotik/system.py`
*   **Línea 301 (`kill_zombie_sessions`)**: Intenta cerrar sesiones. Si la sesión ya cayó por timeout, lanzar error sería incorrecto.

---

## 2. 🛡️ Protección de Secretos (Security Masking)
*El usuario indicó que algunos errores se ocultan para no revelar passwords. Esta práctica es arriesgada si oculta la causa raíz.*

### Riesgo Identificado
En librerías de conexión (como `routeros_api` o `paramiko`), una excepción de "Authentication Failed" podría contener el usuario/password en el mensaje del error si la librería no es cuidadosa.

**Recomendación:**
En lugar de `pass`, usar:
```python
except Exception:
    # Log genérico sin incluir la excepción 'e' que podría tener secretos
    logger.error("Falló la operación sensible (detalles ocultos por seguridad)")
```

---

## 3. ⚠️ Fallos Silenciosos (Silent Failures)
*Estos deben ser corregidos porque dificultan el diagnóstico de problemas en producción.*

### Archivo: `app/utils/device_clients/mikrotik/wireless.py`

#### Problema 1: Métricas de Tráfico perdidas
*   **Ubicación:** Líneas 260 y 273 en `get_aggregate_interface_stats`.
*   **Código:**
    ```python
    try:
        res = api...call("monitor-traffic"...)
        # ... cálculo de velocidades ...
    except Exception:
        pass 
    ```
*   **Impacto:** Si la API de MikroTik falla (timeout, sobrecarga), la función devuelve `0 Mbps` en lugar de indicar error. El sistema de monitoreo creerá que no hay tráfico, lo cual es un **falso negativo**.
*   **Fix Sugerido:** Agregar `logger.warning(f"Failed to monitor traffic for {iface_name}: {e}")`.

---

## Conclusión y Acciones
1.  **Ignorar** los bloques de limpieza en `ssl.py` y `ssh_client.py` (marcarlos con `# nosec` si se desea limpiar el reporte).
2.  **Refactorizar** los bloques en `wireless.py` para incluir logging, ya que afectan la observabilidad del sistema.

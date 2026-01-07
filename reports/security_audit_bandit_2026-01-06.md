# Reporte de Auditoría de Seguridad (Bandit)
**Fecha:** 2026-01-06
**Herramienta:** Bandit (Análisis Estático SAST)
**Objetivo:** Evaluación de seguridad del código fuente en `app/`

## Resumen Ejecutivo
Se realizó un escaneo automatizado del código fuente utilizando **Bandit**. Se encontraron vulnerabilidades que requieren atención, destacando problemas en la gestión de conexiones SSH y manejo de excepciones.

- **Total de Problemas:** 56
- **🔴 Alta Severidad:** 1
- **🟠 Media Severidad:** 7
- **🟡 Baja Severidad:** 48

---

## 🔴 Hallazgos de Alta Severidad (High)

### 1. Conexión SSH Insegura (Posible Man-in-the-Middle)
- **Ubicación:** `app/utils/device_clients/mikrotik/ssh_client.py:71`
- **Problema:** Uso de `paramiko.AutoAddPolicy()`.
- **Descripción:** La aplicación está configurada para confiar automáticamente en cualquier clave de host SSH desconocida sin verificación. Esto permite que un atacante intercepte la conexión sin ser detectado.
- **Recomendación:** Implementar verificación estricta de host keys (`RejectPolicy` o cargar `known_hosts`) o, si es una red interna controlada, documentar el riesgo aceptado.

---

## 🟠 Hallazgos de Media Severidad (Medium)

### 1. Posible Inyección de Comandos (Shell Injection)
- **Ubicación:** `app/utils/device_clients/mikrotik/ssh_client.py:136`
- **Problema:** Llamada a `exec_command` con datos potencialmente no saneados.
- **Descripción:** Se ejecutan comandos en el sistema remoto. Si la variable `command` contiene input de usuario no validado, un atacante podría ejecutar comandos arbitrarios en los equipos Mikrotik.
- **Recomendación:** Asegurar que todos los inputs que forman el comando estén estrictamente validados y saneados.

---

## 🟡 Hallazgos de Baja Severidad (Low)

### 1. Manejo Incorrecto de Excepciones (`try...except pass`)
- **Cantidad:** 48 ocurrencias.
- **Ubicaciones Principales:** 
    - `app/utils/device_clients/mikrotik/ssl.py`
    - `app/utils/device_clients/mikrotik/ssh_client.py`
    - `app/utils/device_clients/mikrotik/wireless.py`
- **Problema:** Cláusulas `except:` o `except Exception:` seguidas de `pass`.
- **Descripción:** Los errores son silenciados sin ser logueados. Esto dificulta enormemente la depuración y puede ocultar fallos de seguridad o comportamiento inesperado del sistema.
- **Recomendación:** Siempre registrar el error (logging) aunque no se interrumpa el flujo, o capturar excepciones específicas en lugar de `Exception` genérico.

---

## Conclusiones
La aplicación es funcional pero presenta riesgos de seguridad en la capa de comunicación con dispositivos (SSH). Se recomienda priorizar la **validación de inputs** en los comandos SSH y evaluar si se puede endurecer la política de conexión SSH. El manejo de errores debe mejorarse para facilitar el mantenimiento y la detección de fallos.

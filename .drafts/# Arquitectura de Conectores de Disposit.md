# Arquitectura de Conectores de Dispositivos (Propuesta)

Este documento detalla la estrategia de refactorización para los conectores de dispositivos, diseñada para soportar múltiples marcas (Vendor Agnostic) y reducir la deuda técnica.

## Jerarquía de Clases Propuesta

La solución se basa en una jerarquía de herencia de 3 niveles para maximizar la reutilización de código y facilitar la adición de nuevos fabricantes (ej. Huawei, Ubiquiti) sin duplicar lógica.

### 1. Nivel Base: `BaseDeviceConnector` (Abstracto)

**Responsabilidad:** "Fontanería" común a cualquier dispositivo de red.
**Contiene:**

* Gestión de credenciales (diccionario `host` -> `creds`).
* Estado de conexión (conectado/desconectado).
* Logging estandarizado (`logger`).
* Definición de interfaz abstracta (`subscribe`, `unsubscribe`).

### 2. Nivel Fabricante: `MikrotikBaseConnector` (Específico)

**Responsabilidad:** Implementar el "cómo hablar" con una marca específica.
**Contiene:**

* Lógica específica del protocolo de MikroTik (API, puertos 8728/8729).
* Manejo de reintentos y errores propios de la librería de conexión (ej. `ros_api` o sockets).
* *Futuro:* Aquí es donde se crearía `HuaweiBaseConnector` o `UbiquitiBaseConnector`.

### 3. Nivel Dispositivo: `RouterConnector`, `SwitchConnector` (Concreto)

**Responsabilidad:** Definir "qué datos pedir".
**Contiene:**

* Solo los comandos específicos para ese tipo de aparato.
* Ejemplo `RouterConnector`: Pide `/system/resource`.
* Ejemplo `SwitchConnector`: Pide `/interface/bridge`.
* Heredan de su "Nivel Fabricante" correspondiente.

## Beneficios para el Futuro

### Escenario: Agregar soporte para Huawei

Si en el futuro se desea agregar equipos Huawei, el proceso sería limpio y seguro:

1. **No se toca el código base:** `BaseDeviceConnector` sigue igual.
2. **No se toca MikroTik:** Todo lo que funciona actualmente queda aislado en `MikrotikBaseConnector`.
3. **Solo se agrega:**
    * Una clase `HuaweiBaseConnector` (que sepa usar SSH o NETCONF).
    * Clases hijas como `HuaweiRouterConnector`.

Esto evita el problema actual donde la lógica de "cómo conectarse" está copiada y pegada en cada archivo, haciendo que corregir un bug requiera editar 3 lugares distintos.

---
*Documento generado a partir del análisis de deuda técnica.*

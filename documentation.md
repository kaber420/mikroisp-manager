# Documentación del Bot de Diagnóstico CPE

Este documento detalla los comandos disponibles en el bot, basados en el análisis del código fuente actual.

## 📋 Comandos Generales

### `/search <término>`
Busca clientes en la base de datos local del bot.
- **Uso:** `/search <nombre | ID | IP>`
- **Ejemplos:**
  - `/search Romero`
  - `/search 48397`
  - `/search 192.168.20.197`
- **Función:** Muestra una lista de clientes coincidentes con botones para iniciar diagnóstico o ver historial.

### `/history`
Consulta el historial de diagnósticos realizados.
- **Uso:** `/history [dias=<N>] [ID | IP]`
- **Opciones:**
  - `dias=<N>`: Filtra por los últimos N días (por defecto 1).
  - `ID` o `IP`: Filtra por un cliente específico.
- **Ejemplos:**
  - `/history` (Muestra historial de hoy de todos)
  - `/history dias=7` (Últimos 7 días)
  - `/history 192.168.20.197` (Historial específico de esa IP)
- **Extras:** Incluye opción para exportar a CSV.

---

## 🔬 Diagnóstico y Herramientas

### `/diag <IP>`
Ejecuta un diagnóstico completo en un CPE (Versión 1).
- **Uso:** `/diag <IP> [usr <usuario> pw <contraseña>]`
- **Argumentos opcionales:**
  - `usr <usuario> pw <contraseña>`: Para especificar credenciales si no son las por defecto.
- **Qué hace:**
  - Verifica conexión SSH.
  - Ejecuta `mca-status`, `ethtool`.
  - Lee configuración del sistema y estado NTP/PortFwd.
  - Detecta router interior.
  - Evalúa calidad de señal y guarda registro en historial.

### `/diagn <IP>`
Ejecuta un diagnóstico completo en un CPE (Versión 2 - Motores nuevos).
- **Uso:** `/diagn <IP>`
- **Qué hace:** Similar a `/diag` pero utiliza módulos de lectura directa de configuración (`system.cfg`) y parser optimizado.

### `/ping <IP>`
Realiza pruebas de conectividad desde el CPE remoto.
- **Uso:** `/ping <IP>`
- **Qué hace:**
  - El bot se conecta al CPE.
  - El CPE hace ping a su Gateway.
  - El CPE hace ping a `8.8.8.8` (Google DNS).
  - Reporta los resultados de latencia y pérdida de paquetes.

### `/portfw <IP>`
Gestiona las reglas de reenvío de puertos (Port Forwarding) en el CPE.
- **Ver reglas actuales:**
  - `/portfw <IP>`
- **Agregar regla:**
  - `/portfw <IP> add <puerto_dst> <ip_dst> <puerto_int>`
  - *Ejemplo:* `/portfw 192.168.20.197 add 8080 192.168.1.50 80`
- **Eliminar regla:**
  - `/portfw <IP> remove <puerto_dst>`
  - *Ejemplo:* `/portfw 192.168.20.197 remove 8080`
- **Nota:** Los cambios se guardan en el historial de configuraciones.

---

## ⚙️ Gestión de Clientes

### `/import_clients <archivo>`
Importa o actualiza la base de datos de clientes desde un CSV.
- **Uso:** `/import_clients <nombre_archivo>`
- **Ejemplo:** `/import_clients clientes_argus.csv`

### `/client_stats`
Muestra estadísticas rápidas de la base de datos de clientes.
- **Uso:** `/client_stats`
- **Salida:** Total de clientes, activos e inactivos.

### `/update_client`
Actualiza manualmente un campo específico de un cliente.
- **Uso:** `/update_client <ID> <campo> <valor>`
- **Campos válidos:** `telefono`, `latitud`, `longitud`, `plataforma`, `external_id`.
- **Ejemplo:** `/update_client 48397 telefono 5512345678`

---

## 🛡️ Administración (Whitelist)
*Estos comandos solo pueden ser ejecutados por el Administrador Principal (`MASTER_TECH_ID`).*

### `/add_tech`
Autoriza a un nuevo técnico para usar el bot.
- **Uso:** `/add_tech <ID_Telegram> <Nombre>`
- **Ejemplo:** `/add_tech 123456789 Juan Perez`
- **Nota:** Requiere el ID numérico de Telegram, no el alias.

### `/remove_tech`
Revoca el acceso a un técnico.
- **Uso:** `/remove_tech <ID_Telegram>`

### `/list_techs`
Muestra la lista de todos los técnicos autorizados.
- **Uso:** `/list_techs`

### `/debug`
Muestra información de depuración del usuario actual.
- **Uso:** `/debug`
- **Salida:** ID de usuario, estado de autorización, y (si es admin) estado del sistema.

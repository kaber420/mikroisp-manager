# µMonitor Pro

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-AGPL_v3-orange)

**µMonitor Pro** es un sistema avanzado de monitoreo y gestión de redes diseñado para ISPs y WISPs. Combina una arquitectura híbrida que potencia tanto la gestión visual a través de una interfaz web moderna como el control robusto mediante una terminal interactiva (TUI).

## ✨ Características Clave

- **📡 Monitoreo en Tiempo Real**: Supervisión activa de Routers (MikroTik), APs (Ubiquiti/MikroTik) y Switches.
- **💼 Gestión Comercial Integral**: Administración completa de clientes (PPPoE/IP Estática), planes de servicio y contratos.
- **🖥️ Launcher TUI**: Nueva interfaz de terminal para gestión del servidor, logs en vivo y diagnósticos.
- **🚀 API RESTful**: Backend de alto rendimiento construido con FastAPI.
- **🤖 Integración con Telegram**: Bots para soporte técnico y notificaciones a clientes/empleados.
- **⚡ Alto Rendimiento**: Soporte de caché con Redict/Redis y actualizaciones vía WebSockets.

---

## 📋 Instalación y Requisitos

### Prerrequisitos

- **Python 3.10+**
- **Base de Datos**: PostgreSQL (Producción) o SQLite (Desarrollo).
- **Caché**: Redict (Recomendado) o Redis.

### ⚡ Instalación Rápida

```bash
# 1. Clonar el repositorio
git clone https://github.com/tu-usuario/xxxx.git
cd xxxx

# 2. Crear entorno virtual
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configuración inicial

  Ejecuta el launcher para configurar interactivamente
python launcher.py setup
```

---

## 🎮 El Launcher (Centro de Comando)

El archivo `launcher.py` es el nuevo punto de entrada principal del sistema.

### Modos de Ejecución

- **Modo TUI (Por defecto)**: `python launcher.py`
  - Interfaz gráfica en terminal con widgets de estado, logs en tiempo real y monitor de recursos.
  - Presiona `m` para abrir el menú de mantenimiento rápido.

- **Modo Headless (Servidor)**: `python launcher.py --headless`
  - Ejecución silenciosa ideal para servicios de sistema (systemd) o entornos Docker.

### 🖥️ Referencia de Comandos (CLI)

El sistema se gestiona principalmente a través de `launcher.py`. A continuación, la lista completa de comandos y argumentos disponibles:

#### Comandos Principales

- **`python launcher.py`**  
  Inicia el sistema. Por defecto abre la TUI, salvo que se haya guardado otra configuración o se use el flag `--headless`.

- **`python launcher.py setup`**  
  Inicia el asistente interactivo de configuración inicial.
  - `--network-only`: Configura solo IP y Puerto.
  - `--ssl-only`: Ejecuta solo el asistente para certificados HTTPS.

- **`python launcher.py diagnose`**  
  Ejecuta pruebas de diagnóstico rápido del sistema y sale.
  - Verifica: Archivo .env, Conexión a Base de Datos, Disponibilidad del Puerto Web, Permisos de Logs.

- **`python launcher.py manage`**  
  Ejecuta tareas de mantenimiento específicas.
  - `--clean-logs`: Elimina archivos de log con más de 7 días de antigüedad.
  - `--vacuum-db`: Ejecuta `VACUUM` en la base de datos (SQLite) para optimizar espacio.

#### Argumentos y Flags Globales

Estos argumentos pueden combinarse con el comando principal de inicio:

- **Modo de Ejecución:**
  - `--headless`: Inicia el servidor sin interfaz gráfica.
  - `--tui`: Fuerza el inicio con la interfaz gráfica de terminal (ignora configuración guardada).
  - `--save`: Guarda los flags de modo (`--headless`/`--tui`), `--port` y `--webworkers` en la configuración persistente del launcher.
  - `--interactive`: Fuerza la creación interactiva del usuario administrador al inicio si no existe.

- **Configuración del Servidor:**
  - `--port <numero>`: Define el puerto de escucha para el servidor web (ej. `--port 8080`).
  - `--webworkers <numero>`: Define la cantidad de procesos workers de Uvicorn.
  
- **Información:**
  - `--show`: Muestra la configuración actual cargada (base de datos, variables de entorno) y sale.

---

## ⚙️ Configuración Avanzada

Las variables clave en el archivo `.env`:

### Base de Datos

- **PostgreSQL**: `DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname`
- **SQLite**: `DATABASE_URL=sqlite+aiosqlite:///data/db/inventory.sqlite`

### Caché (Redict/Redis)

- `CACHE_BACKEND`: `redict` (Recomendado) o `memory`.
- `REDICT_URL`: URL de conexión (ej. `redis://localhost:6379/0`).

---

## 🧩 Módulos del Sistema

### 1. Gestión de Red

- **Routers**: Soporte nativo y profundo para equipos **MikroTik**. *Integración con Ubiquiti proyectada a futuro.*
- **APs**: Monitoreo de Puntos de Acceso **MikroTik** y **Ubiquiti**.
- **Switches**: Gestión de switches **MikroTik**. *Integración con Ubiquiti proyectada a futuro.*
- **Rack Virtual**: Visualización SVG dinámica de puertos y conexiones físicas.

### 2. Gestión WISP

- **Clientes**: Control de ancho de banda, suspensión automática por falta de pago y notificaciones.
- **Infraestructura**: Gestión jerárquica de Zonas, Torres y Nodos. Documentación con soporte Markdown y archivos adjuntos.

### 3. Seguridad

- Roles y permisos granulares.
- Autenticación segura (JWT + Cookies) con protección CSRF.

### 4. Comunicación

- **Difusión**: Envío masivo de avisos segmentados por Nodo o estado del cliente.
- **Telegram Bot**: Sistema de tickets con respuestas automáticas y forwarding de mensajes a técnicos.

---

## 🛠️ Solución de Problemas (Troubleshooting)

- **Logs**: Revisa la carpeta `logs/` o usa el visor de logs integrado en el Launcher TUI.
- **Conexión**: Usa `python launcher.py diagnose` para verificar conectividad con la BD y Redis.
- **Errores Comunes**:
  - *Redis Connection Refused*: Asegúrate de que el servicio `redict` o `redis-server` esté corriendo.

---

## 👨‍💻 Guía de Desarrollo

Estructura básica del proyecto:

- `app/`: Código fuente del backend (FastAPI).
- `launcher/`: Lógica del lanzador y la interfaz TUI.
- `static/` & `templates/`: Frontend (Jinja2 + TailwindCSS).

Para contribuir, por favor revisa `CONTRIBUTING.md`.

---
Desarrollado con ❤️ para la comunidad WISP.

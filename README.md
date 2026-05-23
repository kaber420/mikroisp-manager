# 📡 OmniWISP Pro

![Build Status](https://img.shields.io/badge/build-passing-brightgreen?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![SvelteKit](https://img.shields.io/badge/SvelteKit-FF3E00?style=for-the-badge&logo=svelte)
![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![Database](https://img.shields.io/badge/Postgres%20%7C%20SQLite-4169E1?style=for-the-badge&logo=postgresql)
![Cache](https://img.shields.io/badge/Redict%20%7C%20Redis-D82C20?style=for-the-badge&logo=redis)
![License](https://img.shields.io/badge/license-AGPL_v3-orange?style=for-the-badge)

**OmniWISP Pro** es una plataforma integral de última generación para el monitoreo, aprovisionamiento y gestión comercial de redes, diseñada específicamente para Proveedores de Servicios de Internet (ISPs) y WISPs. 

Combina una potente arquitectura híbrida que integra un backend de alto rendimiento con FastAPI, una interfaz web moderna e intuitiva construida en SvelteKit con DaisyUI, y una interfaz de terminal interactiva (TUI) robusta y fluida para la administración y diagnóstico en tiempo real.

---

## ✨ Características Clave

- **📡 Monitoreo Inteligente (Caché V2)**: Supervisión constante y asíncrona de Routers (MikroTik), Puntos de Acceso (AP - Ubiquiti/MikroTik) y Switches. Utiliza una arquitectura optimizada que almacena el estado en caché (Redict/Redis) para evitar saturar el hardware con peticiones concurrentes.
- **🖥️ Launcher TUI (Textual)**: Interfaz gráfica de terminal integrada que proporciona control total del servidor, visor de recursos en tiempo real, gestión rápida de servicios y visor de logs unificado.
- **🤖 Arquitectura de Bots de Telegram**:
  - **Bot de Técnicos (Lightweight)**: Permite a los técnicos autorizados interactuar de manera segura con el sistema. Incluye gestión de tickets en movilidad (`/tickets`), búsqueda rápida de información de clientes (`/cliente`) y actualización de coordenadas geográficas (`/here`) en tiempo real.
  - **Bot de Clientes (Lightweight)**: Interfaz interactiva para usuarios finales que les permite reportar fallas, verificar sus tickets activos, solicitar cambios de contraseña de WiFi y abrir canales de chat directo con agentes de soporte técnico.
- **💼 Gestión Comercial Integral**: Administración completa de clientes (conexiones PPPoE, IP Estática), planes de ancho de banda, contratos e infraestructura jerárquica (Zonas, Torres y Nodos) con documentación técnica en formato Markdown.
- **🛡️ Seguridad de Nivel de Producción**:
  - Autenticación segura mediante cookies de sesión HttpOnly y JWT.
  - Middleware **Origin Shield** para el bloqueo estricto de ataques CSRF.
  - Generación dinámica de cabeceras de Content Security Policy (CSP) con Nonces por petición.
  - Seguridad reforzada para el almacenamiento y descarga de archivos de documentación.
- **⚡ Arquitectura de Alto Rendimiento**: Integración nativa con `uvloop` (en plataformas Linux/macOS) para optimizar la gestión del bucle de eventos, compresión automática mediante GZip, y comunicación bidireccional instantánea a través de WebSockets.

---

## 📂 Estructura del Proyecto

El repositorio está estructurado modularmente para separar de forma limpia las responsabilidades:

```text
├── app/                      # Núcleo del Backend (FastAPI)
│   ├── api/                  # Endpoints de la REST API (Routers, APs, Switches, CPEs, etc.)
│   ├── bot/                  # Controladores y lógica de los bots de Telegram (Clientes y Técnicos)
│   ├── core/                 # Configuración del sistema, bootstrap, middlewares y seguridad
│   ├── models/               # Definiciones de bases de datos (SQLModel)
│   ├── schemas/              # Modelos de validación Pydantic para la API
│   ├── services/             # Lógica de negocio (MikroTik Connectors, Monitor Schedulers)
│   └── utils/                # Utilidades compartidas (caché, criptografía)
├── launcher/                 # CLI / TUI del Servidor (Textual)
│   ├── commands/             # Comandos del CLI (setup, diagnose, manage)
│   ├── tui/                  # Widgets e interfaz gráfica en terminal
│   └── main.py               # Lógica del punto de entrada principal del Launcher
├── frontend-v2-daisy/        # Aplicación Web Frontend (SvelteKit + DaisyUI + TailwindCSS)
├── deployments/              # Archivos de despliegue para producción (Docker Compose)
├── scripts/                  # Scripts de automatización y herramientas de sistema
└── launcher.py               # Script wrapper principal en la raíz
```

---

## 📋 Instalación y Configuración Rápida

### Prerrequisitos

* **Python 3.10+** (con pip)
* **Base de datos**: PostgreSQL (Producción) o SQLite (Desarrollo/Pruebas)
* **Caché**: Redict (Recomendado) o Redis

### ⚡ Pasos para iniciar el sistema

```bash
# 1. Clonar el repositorio
git clone https://github.com/tu-usuario/OmniWISP.git
cd OmniWISP

# 2. Crear y activar el entorno virtual
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar el sistema
# Inicia el asistente interactivo en terminal para configurar redes y certificados SSL
python launcher.py setup
```

---

## 🎮 El Launcher (Centro de Comando)

El archivo `launcher.py` en la raíz es el punto de entrada principal del sistema y ofrece modos interactivos y CLI.

### Modos de Ejecución

1. **Modo TUI (Por defecto)**: `python launcher.py`
   - Levanta el backend y arranca una interfaz de terminal con widgets para ver el estado del servidor web, uso de recursos de CPU/RAM, logs en tiempo real y menú rápido de mantenimiento.
2. **Modo Headless (Servidor silencioso)**: `python launcher.py --headless`
   - Ideal para ejecutar OmniWISP en segundo plano a través de servicios de sistema (como systemd) o dentro de contenedores Docker.

### 🖥️ Referencia Completa de Comandos

#### Subcomandos del Sistema

- **`python launcher.py setup`**: Inicia el asistente interactivo de configuración.
  - `--network-only`: Configura únicamente IPs y puertos de escucha.
  - `--ssl-only`: Configura o renueva únicamente los certificados HTTPS.
- **`python launcher.py diagnose`**: Realiza pruebas rápidas para comprobar la salud del entorno.
  - Verifica la validez del archivo `.env`, conexión con bases de datos, disponibilidad del puerto y permisos de escritura en la carpeta de logs.
- **`python launcher.py manage`**: Ejecuta tareas de mantenimiento administrativo.
  - `--clean-logs`: Elimina archivos de log obsoletos con más de 7 días de antigüedad.
  - `--vacuum-db`: Ejecuta una optimización interna (VACUUM) si se utiliza SQLite.

#### Banderas y Argumentos Globales

- `--headless`: Inicia el servidor web sin abrir la TUI.
- `--tui`: Fuerza el inicio con la interfaz de terminal interactiva.
- `--save`: Guarda los parámetros pasados por consola (como `--headless`, `--port` y `--webworkers`) en la configuración permanente del launcher.
- `--port <N>`: Modifica el puerto de escucha del servidor web (por defecto: `7777`).
- `--webworkers <N>`: Modifica la cantidad de procesos workers de Uvicorn concurrentes.
- `--use-sqlite`: Fuerza el uso de SQLite para desarrollo rápido y local.
- `--use-local-cache`: Fuerza el uso de caché en memoria RAM, eliminando el requerimiento de Redis.
- `--frontend [v2|daisy|shadcn]`: Inicia y enlaza el frontend en el modo especificado.
- `--show`: Imprime la configuración actual cargada (Base de datos, Caché, Redes) y sale.
- `--interactive`: Fuerza la creación de la primera cuenta administrativa en terminal en caso de no existir.

---

## 🤖 Guía de los Bots de Telegram (Lightweight)

El bot de Telegram original ha sido reestructurado por completo, eliminando motores de diagnóstico pesado heredados en favor de una implementación optimizada y dividida en dos roles específicos:

### 🛠️ 1. Bot de Técnicos (`bot_tech.py`)
Permite a los operarios en campo interactuar con el sistema de soporte y clientes de forma segura. Requiere autorización previa del ID de Telegram:

* **`/tickets`**: Flujo conversacional interactivo para la visualización, respuesta y cierre de los tickets de soporte activos.
* **`/cliente`**: Búsqueda rápida de la ficha técnica de un cliente en base de datos.
* **`/here`**: Actualiza las coordenadas geográficas (latitud y longitud) del cliente en el mapa usando la localización GPS compartida por el dispositivo móvil del técnico.

### 👤 2. Bot de Clientes (`bot_client.py`)
Proporciona un canal de auto-atención interactivo para los suscriptores finales:

* **`/start`**: Despliega el menú principal con botones interactivos dinámicos:
  - **`📞 Reportar Falla / Solicitar Ayuda`**: Inicia un asistente para describir la incidencia y generar un ticket de soporte de manera automática.
  - **`📋 Ver Mis Tickets`**: Consulta rápida al historial y estado actual de los últimos tickets registrados por el cliente.
  - **`🔑 Solicitar Cambio Clave WiFi`**: Genera un ticket administrativo solicitando al equipo técnico la reconfiguración del SSID/Contraseña.
  - **`🙋 Solicitar Agente Humano`**: Abre una sesión de soporte de alta prioridad.
* **`/password`**: Inicia el flujo conversacional seguro para el restablecimiento de la contraseña de acceso al portal web de clientes.
* **`💬 Chat en Vivo integrado`**: Cuando un cliente tiene una sesión de soporte activo abierta ("*Solicitud de Soporte en Vivo*"), cualquier mensaje de texto común que envíe al bot será enrutado de forma automática como respuesta directa dentro de su ticket para que los técnicos puedan chatear en tiempo real.

---

## ⚙️ Despliegue en Producción

### Contenedores Docker (Recomendado)

OmniWISP incluye una configuración lista para producción en `deployments/omniwisp-prod.yml` que levanta los servicios críticos:

```bash
# Iniciar base de datos PostgreSQL y servicio de caché Redict
docker compose -f deployments/omniwisp-prod.yml up -d
```

### Inversa Proxy con Caddy

El launcher integra de forma automática la generación de archivos `Caddyfile` y la gestión del servidor **Caddy** para servir el sistema bajo HTTPS seguro, forzar redirecciones, implementar cabeceras de seguridad rigurosas y proteger las descargas en el servidor.

---

Desarrollado con ❤️ para la comunidad WISP e ISP.

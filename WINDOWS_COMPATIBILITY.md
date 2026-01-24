# Guía de Compatibilidad con Windows para µMonitor Pro

Esta guía detalla los pasos necesarios para instalar y ejecutar µMonitor Pro en un entorno Windows. Aunque el núcleo de la aplicación (Python) es compatible, los scripts de automatización de despliegue (Caddy, certificados SSL) están diseñados para Linux. Aquí explicamos cómo realizar esa configuración manualmente en Windows.

## 1. Prerrequisitos

Necesitarás instalar el siguiente software en tu máquina Windows:

* **Python 3.10 o superior**: [Descargar desde python.org](https://www.python.org/downloads/). Asegúrate de marcar la casilla "Add Python to PATH" durante la instalación.
* **Git**: [Descargar Git para Windows](https://git-scm.com/download/win).
* **Terminal**: PowerShell o Command Prompt (cmd).

## 2. Instalación de la Aplicación

1. **Clonar el repositorio**:
    Abre una terminal y ejecuta:

    ```powershell
    git clone https://github.com/tu-usuario/umanager6.git
    cd umanager6
    ```

2. **Crear entorno virtual**:
    Es recomendable aislar las dependencias.

    ```powershell
    python -m venv .venv
    .\.venv\Scripts\activate
    ```

    (Verás `(.venv)` al inicio de tu línea de comandos).

3. **Instalar dependencias**:
    El archivo `requirements.txt` está configurado para detectar tu sistema operativo. En Windows instalará `uvicorn` estándar y `watchfiles`, mientras que en Linux usará `uvicorn[standard]` (con `uvloop`) para máximo rendimiento.

    Simplemente ejecuta:

    ```powershell
    pip install -r requirements.txt
    ```

## 3. Ejecución Básica (Modo Desarrollo)

Para probar la aplicación localmente sin HTTPS complejo:

```powershell
python launcher.py
```

El asistente (`launcher.py`) detectará que no estás en Linux y saltará la configuración automática de Caddy.

* Responde a las preguntas del asistente.
* La aplicación estará disponible en `http://localhost:7777` (o el puerto que elijas).
* **Nota**: Sin HTTPS, algunas funciones como la geolocalización o Service Workers pueden no funcionar en otros dispositivos de la red, pero funcionarán en `localhost`.

## 4. Configuración Avanzada (Modo Producción con HTTPS)

En Linux, la configuración de Caddy y certificados se maneja vía Python (`app/services/pki_service.py` y `launcher.py`). En Windows, el soporte automático es limitado por ahora, así que para HTTPS completo recomendamos la configuración manual.

### Paso A: Instalar Caddy y mkcert

Recomendamos usar **Chocolatey** o **Scoop** para instalar estas herramientas, o descargar los ejecutables manualmente.

**Opción con Chocolatey** (Abrir PowerShell como Administrador):

```powershell
choco install caddy mkcert
```

**Opción manual**:

1. Descarga Caddy: [caddyserver.com](https://caddyserver.com/download)
2. Descarga mkcert: [GitHub mkcert](https://github.com/FiloSottile/mkcert/releases)
3. Coloca ambos `.exe` en una carpeta que esté en tu `PATH` o en la carpeta del proyecto.

### Paso B: Generación de Archivos (Automática)

Simplemente ejecuta `python launcher.py` y responde "Sí" a la configuración HTTPS.
El asistente:

1. Detectará `mkcert` (si está en tu PATH o Chocolatey).
2. Generará los certificados en `data/certs/`.
3. Validará la configuración y tratará de recargar Caddy si ya está ejecutándose.

*(Si Caddy no está corriendo, el lanzador te recordará iniciarlo manualmente en otra terminal).*

### Paso C: Ejecutar

Ahora tienes dos opciones:

**Opción 1: Todo en Uno (Recomendado)**
Ejecuta el lanzador como **Administrador** (Clic derecho -> Ejecutar como administrador).
El lanzador iniciará la API, el programador y Caddy automáticamente.

```powershell
python launcher.py
```

**Opción 2: Manual (Si no quieres dar permisos de admin al script de Python)**

1. **Terminal 1 (Backend)**:
    Ejecuta el lanzador (Usuario normal):

    ```powershell
    python launcher.py
    ```

2. **Terminal 2 (Proxy SSL)**:
    Ejecuta Caddy (Como Administrador):

    ```powershell
    caddy run
    ```

Tu aplicación estará disponible en `https://192.168.x.x` (la IP que indique el lanzador).

Tu aplicación estará disponible en `https://192.168.x.x` (la IP que indique el lanzador).

> [!TIP]
> **Automatización**: Puedes crear un archivo `start.bat` en la carpeta del proyecto.
>
> También hemos incluido `scripts/db_backup.py` para respaldos automáticos compatibles con Windows:
> `python scripts/db_backup.py`
>
> ```batch
> @echo off
> start "Backend" cmd /k python launcher.py
> start "Proxy SSL" cmd /k caddy run
> ```

* **Error "uvloop not supported"**: Si ves este error, asegúrate de haber instalado las dependencias limpiamente con `pip install -r requirements.txt`. Nuestro archivo de requisitos usa marcadores de entorno para evitar instalar `uvloop` en Windows.
* **Firewall**: Cuando ejecutes `python` o `caddy` por primera vez, Windows te pedirá permiso para acceder a redes. Permite el acceso a redes Privadas (domésticas).
* **Scripts .sh**: Los scripts de shell en `scripts/` son auxiliares para Linux. El `launcher.py` contiene ahora la lógica necesaria para validar y recargar Caddy en Windows nativamente, por lo que no necesitas ejecutar scripts .sh manualmente.
* **Rutas**: Python maneja bien las rutas, pero si editas código, usa siempre `os.path.join` o `pathlib` en lugar de concatenar strings con `/` o `\`.

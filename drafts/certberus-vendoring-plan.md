# Plan de Integración Nativa (Vendoring) de Certberus en OmniWISP

## 🎯 Objetivo
Integrar la lógica completa de firmado de **Certberus** como un módulo interno nativo dentro de **OmniWISP** (`app/services/business/pki/`). Esto elimina la dependencia externa directa a GitHub en `requirements.txt` (`certberus @ git+https://...`), haciendo que el proyecto sea autocontenido, fácil de desplegar en entornos corporativos/aislados y 100% auditable bajo los mismos estándares de seguridad de OmniWISP.

---

## 🔒 Beneficios de Seguridad y Operaciones

1. **Cumplimiento de Auditorías:** Los scanners de seguridad corporativos (SAST, Snyk, dependabot) marcan las descargas directas desde Git como vulnerabilidades en la cadena de suministro (*supply chain*). Integrando el código en el repositorio central se eliminan estas alertas.
2. **Despliegues Offline (Air-gapped):** No se requerirá acceso externo a GitHub ni herramientas de `git` instaladas en el contenedor Docker en tiempo de compilación.
3. **Consolidación de Base de Datos:** En lugar de manejar una base de datos SQLite separada para Certberus (`certs.db`), las tablas de autoridades, certificados y auditoría se integrarán directamente a la base de datos principal de OmniWISP (PostgreSQL/SQLite) mediante SQLAlchemy/SQLModel y migraciones de Alembic.
4. **Eliminación de Rutas Duplicadas:** Se unificará el flujo criptográfico interno. El actual fallback de `cryptography` en `pki_service.py` se fusionará con el motor de Certberus localmente.

---

## 📁 Nueva Estructura Propuesta

El código se moverá desde `.venv/lib/python3.14/site-packages/certberus/` a una carpeta de servicios dedicada en OmniWISP:

```text
app/
└── services/
    └── business/
        ├── pki_service.py  <-- (Modificado: Importará del motor local)
        └── pki/            <-- [NUEVO DIRECTORIO VENDORED]
            ├── __init__.py
            ├── engine.py   <-- (Copia adaptada de certberus/pki.py)
            ├── config.py   <-- (Copia adaptada de certberus/config.py)
            ├── models.py   <-- (Modelos de base de datos SQLModel locales)
            ├── audit.py    <-- (Lógica de logs de auditoría locales)
            └── api.py      <-- (Rutas de administración FastAPI locales)
```

---

## 🔧 Detalles de Adaptación Técnica

### 1. Modelos de Base de Datos y Migraciones (`pki/models.py`)
Mover los modelos `Authority`, `Certificate` y `AuditLog` al esquema de OmniWISP. Al usar ambos `SQLModel`, la integración es natural:
* Registrar estos modelos en el import de metadatos de OmniWISP.
* Ejecutar `alembic revision --autogenerate` para crear una nueva migración que configure estas tablas en la base de datos principal de OmniWISP.

### 2. Lógica de Base de Datos (`pki/audit.py` y `pki/api.py`)
Reemplazar el uso de `db_session.AsyncSessionLocal()` (que creaba una conexión SQLite independiente en Certberus) por la inyección de dependencias estándar de OmniWISP:
* Usar `Depends(get_db)` de la base de datos central en los endpoints de FastAPI.
* Utilizar la sesión de base de datos asíncrona compartida de OmniWISP para garantizar transacciones atómicas.

### 3. Autenticación y Autorización en API (`pki/api.py`)
En lugar de depender únicamente de la cabecera `X-Certberus-Token` estática, las rutas de administración de PKI se pueden proteger de dos formas concurrentes:
* **Token Estático:** Para compatibilidad de CLI o automatización externa (se lee de la configuración).
* **Sesión de Usuario OmniWISP:** Protegerlas usando el actual sistema de autenticación de OmniWISP (`Depends(get_current_active_superuser)` o `Depends(get_current_user)`).

---

## 📅 Plan de Acción (Fases)

### Fase 1: Creación del Módulo Local
1. Crear el directorio `app/services/business/pki/`.
2. Crear un archivo `__init__.py` en esa ruta.
3. Copiar la lógica core criptográfica:
   * Copiar `pki.py` de Certberus a `app/services/business/pki/engine.py`.
   * Copiar `config.py` de Certberus a `app/services/business/pki/config.py` (adecuando las rutas por defecto de guardado dentro de la carpeta `data/pki/` del proyecto en lugar de `~/.local/share/`).
   * Copiar `models.py` de Certberus a `app/services/business/pki/models.py`.
   * Copiar `db/audit.py` de Certberus a `app/services/business/pki/audit.py`.

### Fase 2: Integración a la Base de Datos Principal de OmniWISP
1. Importar los modelos de `app/services/business/pki/models.py` en el archivo central de modelos del sistema para asegurar que Alembic los detecte.
2. Adaptar la lógica de guardado y búsqueda en `pki/engine.py` y `pki/audit.py` para usar la sesión central.
3. Crear y aplicar la migración de Alembic:
   ```bash
   alembic revision --autogenerate -m "add_pki_certberus_tables"
   alembic upgrade head
   ```

### Fase 3: Integración de la API de PKI en FastAPI
1. Copiar `integrations/admin_api.py` a `app/services/business/pki/api.py`.
2. Adaptar las rutas para que utilicen la inyección de sesión de OmniWISP.
3. Registrar este router en el agregador principal de rutas de FastAPI de OmniWISP (por ejemplo, en `app/api/routers/ssl.py` o directamente en `app/main.py` bajo el prefijo `/api/v1/pki`).

### Fase 4: Refactorización y Limpieza
1. Modificar [pki_service.py](file:///home/kaberromero/Documentos/proyectos/OmniWISP/app/services/business/pki_service.py) para que:
   * Remueva el bloque `try/except ImportError` para `certberus`.
   * Ponga `HAS_CERTBERUS = True` de forma fija y apunte localmente:
     ```python
     from app.services.business.pki.engine import PKIService as CertberusPKI
     from app.services.business.pki.config import load_config as load_certberus_config
     ```
2. Eliminar la dependencia de `requirements.txt`:
   * Quitar la línea `certberus @ git+https://...`
3. Probar el correcto funcionamiento ejecutando los tests existentes (`test_pki.py` y `test_pki2.py`).

---

## 🧪 Plan de Verificación

* **Verificación de dependencias:** Correr `pip list` en `.venv` después de removerla en `requirements.txt` y verificar que el servidor de OmniWISP inicia sin problemas.
* **Prueba de firma local (CSR):** Correr `python test_pki.py` para validar que el motor de PKI local inicializa la CA raíz y firma CSRs correctamente usando la nueva estructura local.
* **Prueba de base de datos:** Verificar que los certificados y logs de auditoría queden persistidos en la base de datos de desarrollo unificada de OmniWISP en vez de un archivo SQLite externo.

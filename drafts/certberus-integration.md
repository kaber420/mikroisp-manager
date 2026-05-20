# Plan: Integración Completa de Certberus en OmniWISP

> **Objetivo:** Usar Certberus como motor PKI central para OmniWISP, persistiendo el estado de los certificados en base de datos y exponiendo una interfaz de gestión en el frontend.

---

## Estado Actual

| Componente | Estado |
|---|---|
| `certberus` en `requirements.txt` | ✅ Referenciado como dependencia git (`v0.1.0`) |
| Certberus instalado en el entorno | ❌ No instalado → cae al fallback interno |
| `pki_service.py` | ✅ Usa Certberus para firmar/generar certs, con fallback a `cryptography` |
| Modelo `Router` | ⚠️ Solo tiene `is_provisioned: bool`, sin metadata de certificado |
| Admin API de Certberus consumida | ❌ Nunca se llama a `/_certberus/admin/*` |
| Vista frontend de estado SSL | ❌ No existe |

---

## Fases

### Fase 0 — Instalación y Verificación del Entorno

**Objetivo:** Certberus disponible e importable en el entorno de desarrollo.

**Tareas:**
- [ ] Instalar certberus desde el repo git:
  ```bash
  pip install git+https://github.com/kaber420/certberus.git@v0.1.0
  ```
- [ ] Verificar que `HAS_CERTBERUS = True` al arrancar OmniWISP.
- [ ] Inicializar la Root CA si no existe:
  ```bash
  python -m certberus.cli init
  ```
- [ ] Sincronizar la CA con el path del sistema (`pki_service.sync_ca_files()`).
- [ ] Añadir al script de setup/launcher la verificación de certberus.

**Archivos afectados:**
- `launcher/setup_wizard.py`
- `requirements.txt` (ya está, solo instalar)

---

### Fase 1 — Persistencia de Metadata SSL en Base de Datos

**Objetivo:** Guardar en BD los datos relevantes de cada certificado emitido, para poder consultarlos sin llamar a certberus en cada request.

**Nuevos campos en el modelo `Router`:**

```python
# app/models/router.py

# SSL / PKI
ssl_serial: str | None = Field(default=None)          # Número de serie del certificado
ssl_cn: str | None = Field(default=None)               # Common Name (suele ser el host/IP)
ssl_fingerprint: str | None = Field(default=None)      # SHA-256 fingerprint
ssl_issued_at: datetime | None = Field(default=None)   # Fecha de emisión
ssl_expires_at: datetime | None = Field(default=None)  # Fecha de expiración
ssl_issuer: str | None = Field(default=None)           # Emisor (certberus CA / internal)
ssl_method: str | None = Field(default=None)           # "router-side" | "server-side" | "internal"
ssl_revoked: bool = Field(default=False)               # Si fue revocado
```

**Migraciones:**
- Crear migración Alembic con los nuevos campos.
- Actualizar `RouterSchema` / `RouterRead` en los schemas de Pydantic.

**Archivos afectados:**
- `app/models/router.py`
- `app/schemas/` (schema del router)
- Migración Alembic nueva

---

### Fase 2 — Actualizar `pki_service.py` para Retornar Metadata

**Objetivo:** Que al firmar/emitir un certificado, `pki_service` devuelva también los metadatos del cert (serial, expiración, fingerprint).

**Cambios en `PKIService`:**

```python
# Nuevo tipo de retorno
@dataclass
class CertResult:
    success: bool
    cert_pem: str
    key_pem: str | None
    serial: str | None
    common_name: str | None
    fingerprint: str | None
    issued_at: datetime | None
    expires_at: datetime | None
    issuer: str | None
    error: str | None
```

- `sign_router_csr()` → retorna `CertResult`
- `generate_full_cert_pair()` → retorna `CertResult`
- Parsear el cert PEM con `cryptography` para extraer los metadatos antes de retornar.

**Archivos afectados:**
- `app/services/business/pki_service.py`

---

### Fase 3 — Persistir Metadata al Provisionar

**Objetivo:** Guardar los datos del certificado en el `Router` justo después de una provisión exitosa.

**Flujo:**
```
POST /ssl/provision
  → PKIService.generate_full_cert_pair()  →  CertResult
  → adapter.import_certificate()          →  instala en MikroTik
  → repo.update_router_ssl_metadata()     →  persiste en BD
  → return SSLProvisionResponse (+ metadata)
```

**Cambios:**
- `ssl.py` (router API): guardar metadata en BD tras provisión exitosa.
- Nuevo método en el repositorio: `RouterRepository.update_ssl_metadata(host, cert_result)`.
- Actualizar `SSLProvisionResponse` para incluir la metadata del cert.

**Archivos afectados:**
- `app/api/routers/ssl.py`
- `app/repositories/` (router repository)

---

### Fase 4 — Endpoints de Gestión PKI

**Objetivo:** Exponer endpoints en OmniWISP que permitan ver y gestionar el estado SSL de todos los dispositivos, usando tanto la BD como la Admin API de certberus.

**Nuevos endpoints (`/ssl/...`):**

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/ssl/overview` | Lista todos los routers con su estado SSL (desde BD) |
| `GET` | `/ssl/expiring` | Routers con cert expirando en los próximos N días |
| `GET` | `/routers/{host}/ssl` | Estado SSL detallado de un router específico |
| `POST` | `/routers/{host}/ssl/revoke` | Revocar el certificado de un router |
| `POST` | `/ssl/sync` | Sincronizar estado BD con certberus Admin API |
| `GET` | `/ssl/pki/stats` | Estadísticas PKI desde certberus (`/_certberus/admin/stats`) |
| `GET` | `/ssl/pki/certificates` | Todos los certs emitidos por certberus |

**Lógica de `/ssl/overview`:**
```python
# Consulta local a BD — sin tocar certberus
# Retorna: host, is_provisioned, ssl_cn, ssl_expires_at, ssl_revoked, días_restantes
```

**Lógica de `/ssl/sync`:**
```python
# 1. Llama a GET /_certberus/admin/certificates
# 2. Por cada cert, busca el router en BD por CN/serial
# 3. Actualiza ssl_revoked, ssl_expires_at si hay discrepancias
```

**Archivos afectados:**
- `app/api/routers/ssl.py` (ampliar)
- `app/services/business/pki_service.py` (nuevo método `list_certificates`, `revoke_certificate`)

---

### Fase 5 — Frontend: Vista de Gestión PKI

**Objetivo:** Panel en el frontend donde se vea el estado SSL de cada dispositivo.

**Componentes a crear:**

1. **`SSLOverviewPanel`** — Tabla de routers con columnas:
   - Host / Hostname
   - Estado (badge: `✅ Válido` / `⚠️ Por expirar` / `❌ Expirado` / `🔴 Revocado` / `⬜ Sin cert`)
   - Common Name
   - Expiración (`ssl_expires_at` + días restantes)
   - Acciones: Provisionar / Revocar / Ver detalle

2. **`CertDetailModal`** — Modal con el detalle completo:
   - Serial, fingerprint, issuer, fechas, método de emisión

3. **`PKIStatsWidget`** — Widget en el dashboard admin con:
   - Total de certs activos/expirados/revocados
   - Próximas expiraciones

4. **Integración en el panel de cada Router** — Badge de estado SSL visible directamente en la card/detalle del router.

**Archivos afectados:**
- `frontend-v2-daisy/src/` (nuevos componentes Svelte)
- Añadir rutas en el router del frontend

---

### Fase 6 — Scheduler: Alertas de Expiración

**Objetivo:** Tarea periódica que detecte certificados próximos a expirar y notifique.

**Nueva tarea en `scheduler.py`:**
```python
# Cada día a las 08:00
async def check_ssl_expiry():
    # 1. Consulta BD: routers donde ssl_expires_at < now() + 30 días
    # 2. Para cada uno: loguear warning, opcionalmente enviar alerta Telegram
    # 3. Actualizar last_checked del estado SSL
```

**Archivos afectados:**
- `app/scheduler.py`

---

## Orden de Implementación Recomendado

```
Fase 0 (Instalación)
  → Fase 1 (Modelo BD + migración)
    → Fase 2 (pki_service retorna metadata)
      → Fase 3 (persistir al provisionar)
        → Fase 4 (endpoints gestión)
          → Fase 5 (frontend)
            → Fase 6 (scheduler alertas)
```

## Dependencias Técnicas

- `certberus >= v0.1.0` (ya en requirements.txt)
- `cryptography` (ya instalado — para parsear PEM y extraer metadata)
- `httpx` (ya instalado — para llamar a la Admin API de certberus si corre como servidor separado)
- Alembic (para la migración de BD)

---

## Notas

- La Admin API de certberus (`/_certberus/admin/*`) solo es necesaria para el **sync** y para listar certs directamente desde certberus. La mayoría de las operaciones se hacen con los datos ya persistidos en BD.
- Si certberus no está instalado, el fallback interno (`cryptography`) sigue funcionando, pero **no tendrá Admin API** — en ese caso los endpoints de sync y stats deben retornar un error gracioso indicando que certberus no está disponible.
- El modelo de datos en BD es la fuente de verdad para el frontend; certberus es la fuente de verdad para la PKI.

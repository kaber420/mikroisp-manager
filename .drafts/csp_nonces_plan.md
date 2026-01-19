# Implementación de CSP con Nonces y Eliminación de 'unsafe-inline'

Esta implementación mejora la seguridad de la aplicación reemplazando la directiva permisiva `unsafe-inline` con un sistema basado en **Nonces Criptográficos**.

---

## Revisión del Plan

> [!NOTE]
> **Estado actual**: El CSP actual en [main.py](file:///home/kaber420/Documentos/python/umanager6/app/main.py#L242-L262) usa `unsafe-inline` tanto para scripts como estilos, lo cual es permisivo pero funcional.

### ✅ Aspectos Positivos del Plan

1. **Mejora real de seguridad** - Pasar de `unsafe-inline` a nonces es la evolución correcta
2. **Separación de responsabilidades** - Mover CSP a un middleware dedicado mejora la organización
3. **Compatibilidad con Alpine.js** - Mantener `unsafe-eval` es necesario y bien documentado

### ⚠️ Puntos Críticos a Considerar

> [!IMPORTANT]
> **Scripts inline identificados** en [base.html](file:///home/kaber420/Documentos/python/umanager6/templates/base.html) que necesitan nonce:
>
> - Líneas 17-37: Configuración de Tailwind (`tailwind.config`)
> - Líneas 320-334: Efecto parallax de glows

> [!WARNING]
> **TailwindCSS Play CDN (local)**: Tu aplicación usa la versión "Play CDN" de Tailwind (`tailwindcss.js`) descargada localmente en `/static/js/vendor/`. Esta versión genera CSS dinámicamente en el navegador y **requiere `unsafe-eval`** para funcionar. El script inline `tailwind.config = {...}` necesitará un nonce para ejecutarse.

> [!CAUTION]
> **Posible rotura**: Si cualquier template hijo usa `<script>` inline sin nonce, la funcionalidad se romperá silenciosamente. Se debe auditar TODOS los templates.

---

## User Review Required

> [!IMPORTANT]
> **Compatibilidad con Alpine.js**: Esta implementación mantiene `unsafe-eval` en la política CSP. Esto es necesario para que Alpine.js (versión estándar) funcione con los atributos `x-data` y `x-on` que se usan extensivamente en las plantillas. Eliminar `unsafe-eval` requeriría reescribir todo el frontend para usar la versión CSP-build de Alpine, lo cual está fuera del alcance actual.

> [!NOTE]
> Se eliminará la cabecera CSP actual definida manualmente en [main.py](file:///home/kaber420/Documentos/python/umanager6/app/main.py#L252-L262) en favor de un nuevo Middleware dedicado `CSPMiddleware`.

---

## Proposed Changes

### App Core & Middleware

#### [NEW] [csp_middleware.py](file:///home/kaber420/Documentos/python/umanager6/app/csp_middleware.py)

Creación de un nuevo middleware que:

- Genera un nonce aleatorio (base64) para cada petición
- Lo inyecta en `request.state.csp_nonce`
- Construye la cabecera `Content-Security-Policy` dinámicamente incluyendo el nonce en `script-src` y `style-src`
- Define la política estricta: `default-src 'self'; script-src 'self' 'unsafe-eval' 'nonce-{nonce}'; ...`

```python
# Estructura propuesta
import secrets
import base64
from starlette.middleware.base import BaseHTTPMiddleware

class CSPMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Generar nonce aleatorio de 16 bytes, codificado en base64
        nonce = base64.b64encode(secrets.token_bytes(16)).decode('utf-8')
        request.state.csp_nonce = nonce
        
        response = await call_next(request)
        
        csp_policy = (
            f"default-src 'self'; "
            f"script-src 'self' 'unsafe-eval' 'nonce-{nonce}'; "
            f"style-src 'self' 'nonce-{nonce}'; "
            f"img-src 'self' data: blob:; "
            f"connect-src 'self' ws: wss:; "
            f"font-src 'self' data:; "
            f"object-src 'none'; "
            f"base-uri 'self';"
        )
        response.headers["Content-Security-Policy"] = csp_policy
        return response
```

---

#### [MODIFY] [main.py](file:///home/kaber420/Documentos/python/umanager6/app/main.py)

- Importar y añadir el nuevo `CSPMiddleware`
- **Eliminar** la lógica de CSP dentro de `add_security_headers` (líneas 252-262)
- Asegurar que el middleware se añada en el orden correcto

```diff
+ from .csp_middleware import CSPMiddleware

  # Añadir después de otros middlewares
+ app.add_middleware(CSPMiddleware)

  # En add_security_headers, ELIMINAR:
- csp_policy = (
-     "default-src 'self'; "
-     ...
- )
- response.headers["Content-Security-Policy"] = csp_policy
```

---

### Templates Frontend

#### [MODIFY] [base.html](file:///home/kaber420/Documentos/python/umanager6/templates/base.html)

Actualizar todas las etiquetas `<script>` para incluir el atributo `nonce="{{ request.state.csp_nonce }}"`:

```diff
- <script src="{{ url_for('static', path='/js/vendor/tailwindcss.js') }}"></script>
+ <script nonce="{{ request.state.csp_nonce }}" src="{{ url_for('static', path='/js/vendor/tailwindcss.js') }}"></script>

- <script>
-     tailwind.config = {...}
- </script>
+ <script nonce="{{ request.state.csp_nonce }}">
+     tailwind.config = {...}
+ </script>
```

**Scripts a modificar en base.html:**

| Línea | Tipo | Descripción |
|-------|------|-------------|
| 10-12 | Externo | Tailwind, Chart.js, date-fns adapter |
| 17-37 | Inline | Configuración de Tailwind |
| 39-40 | Externo | api.js, validators.js |
| 285-288 | Externo | toast.js, ws-client.js, session_monitor.js, Alpine |
| 320-334 | Inline | Efecto parallax de glows |

---

### Otros Templates a Auditar

> [!NOTE]
> Se debe verificar también estos templates por scripts inline:

- `templates/login.html`
- `templates/403.html`
- `templates/ticket.html`
- `templates/dashboard.html`
- Cualquier template que use `{% block scripts %}`

---

## Verification Plan

### Automated Tests

- No hay tests de navegador automatizados configurados actualmente

### Manual Verification

1. **Verificar Cabeceras:**
   - Abrir DevTools (F12) → Network
   - Recargar la página
   - Verificar que la cabecera `Content-Security-Policy` incluye `script-src 'nonce-...'` y **NO** incluye `'unsafe-inline'`

2. **Verificar Bloqueo:**
   - Intentar inyectar manualmente un script en la consola o editar el HTML para añadir `<script>alert(1)</script>` sin nonce
   - El navegador **debe bloquearlo** y mostrar error en consola

3. **Verificar Funcionalidad:**
   - Navegar por Dashboard, Clientes y Mapas
   - Verificar que Alpine.js funciona (menús desplegables, modales y gráficas cargan correctamente)
   - Verificar que **no hay errores** de "CSP violation" en la consola relacionados con scripts legítimos

---

## Orden de Implementación Recomendado

1. Crear `app/csp_middleware.py`
2. Modificar `app/main.py` (importar middleware, eliminar CSP antiguo)
3. Modificar `templates/base.html` (añadir nonces)
4. Auditar y modificar otros templates
5. Probar manualmente en cada página
6. Verificar en consola que no hay violaciones CSP

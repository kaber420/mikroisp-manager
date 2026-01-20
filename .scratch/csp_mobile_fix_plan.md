# Fix CSP for Mobile App Compatibility

## Problem

La aplicación móvil no funciona correctamente después de implementar CSP porque:

1. **CSP `connect-src 'self'`** - Restringe conexiones solo al mismo origen
2. **CSP headers en respuestas API** - Los endpoints `/api/*` y `/auth/*` incluyen headers CSP que confunden WebViews móviles

> [!IMPORTANT]
> Los headers CSP están diseñados para páginas web HTML, **no para respuestas JSON de API**.

## Proposed Changes

### [MODIFY] [csp_middleware.py](file:///home/kaber420/Documentos/python/umanager6/app/csp_middleware.py)

Modificar el middleware para **excluir rutas de API** del CSP:

```diff
 async def dispatch(self, request: Request, call_next):
+    # Skip CSP for API and auth endpoints (they return JSON, not HTML)
+    if request.url.path.startswith(("/api/", "/auth/")):
+        return await call_next(request)
+    
     # Generate a cryptographically secure random nonce
     nonce_bytes = secrets.token_bytes(16)
```

**Razonamiento:**

- Las respuestas JSON no ejecutan scripts ni cargan recursos
- CSP es irrelevante para APIs REST
- Elimina conflictos con clientes móviles/externos

## Verification Plan

### Automated Tests

```bash
# Verificar que la API responde sin CSP header
curl -s -I http://localhost:8000/api/stats/switch-count | grep -i content-security

# Verificar que páginas web SÍ tienen CSP
curl -s -I http://localhost:8000/login | grep -i content-security
```

### Manual Verification

- Probar login desde la app móvil
- Verificar que las llamadas API funcionan correctamente
- Confirmar que la interfaz web mantiene protección CSP

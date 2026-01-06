# Propuesta: SSH Provisioning para MikroTik APs

**Fecha**: 2026-01-06  
**Estado**: Propuesta / Ideas

---

## Contexto

Se ha implementado exitosamente el aprovisionamiento via SSH para **Routers MikroTik**. Ahora se evalúa extender esta funcionalidad a los **Access Points MikroTik** registrados en el módulo de APs.

---

## Análisis Actual

### Diferencias entre Routers y APs

| Aspecto | Routers | APs MikroTik |
|---------|---------|--------------|
| Modelo DB | `Router` con `is_provisioned` | `AP` sin campo `is_provisioned` |
| Conexión | API-SSL obligatorio | Varios vendors (Ubiquiti, MikroTik) |
| Vendor | Solo MikroTik | Multi-vendor (`vendor` field) |
| Puerto default | 8729 (API-SSL) | 443 (Ubiquiti) / 8729 (MikroTik) |

### Observaciones

1. **Los APs no tienen concepto de "aprovisionamiento"**: Actualmente, los APs se agregan con credenciales existentes y se conectan directamente. No hay un paso de "crear usuario + instalar certificados".

2. **Multi-vendor**: El módulo de APs soporta Ubiquiti y MikroTik. El SSH Provisioning solo aplica a MikroTik.

3. **Código reutilizable**: `ProvisioningService._run_provisioning_ssh_pure()` es genérico y podría reutilizarse.

---

## Opciones de Implementación

### Opción A: Agregar Botón "Provision" en APs (Similar a Routers)

**Descripción**: Agregar un flujo de aprovisionamiento similar al de routers, donde los APs MikroTik no aprovisionados muestran un botón "Provision".

**Cambios requeridos**:
- Agregar `is_provisioned` al modelo `AP`.
- Agregar `api_ssl_port` al modelo `AP`.
- Crear endpoint `POST /api/aps/{host}/provision`.
- Modificar UI de APs para mostrar botón de provisioning.
- Reutilizar `ProvisioningService` o crear una versión compartida.

**Pros**:
- Experiencia consistente entre Routers y APs.
- Seguridad mejorada (Zero Trust para APs).

**Contras**:
- Duplicación de lógica UI/API si no se refactoriza.
- Solo aplica a vendor=mikrotik.

---

### Opción B: Provisioning Unificado (Servicio Compartido)

**Descripción**: Crear un servicio de aprovisionamiento genérico que funcione tanto para Routers como para APs MikroTik.

**Arquitectura propuesta**:

```
app/services/
├── provisioning/
│   ├── __init__.py
│   ├── base.py           # ProvisioningService base class
│   ├── mikrotik.py       # MikroTik-specific provisioning logic
│   └── models.py         # ProvisionRequest, ProvisionResponse
```

**Cambios requeridos**:
- Refactorizar `provisioning_service.py` a módulo compartido.
- Crear endpoint genérico o endpoints específicos que usen el servicio compartido.
- Agregar campos necesarios al modelo AP.

**Pros**:
- Código DRY (Don't Repeat Yourself).
- Fácil de mantener y extender.

**Contras**:
- Requiere refactorización significativa.

---

### Opción C: Re-Provisioning desde Router Details (Sin cambios a AP module)

**Descripción**: Dado que los APs MikroTik son esencialmente routers con wireless, podrían registrarse en la tabla de `routers` en lugar de `aps`.

**Consideraciones**:
- Esto cambia la arquitectura actual donde APs tienen su propia tabla.
- No recomendado si se desea mantener la separación de roles.

---

## Recomendación

### Fase 1: Agregar Provisioning a APs MikroTik (Opción A - Simplificada)

1. **Agregar campos al modelo AP**:
   ```python
   is_provisioned: bool = Field(default=False)
   api_ssl_port: int = Field(default=8729)
   ```

2. **Crear endpoint de provisioning para APs**:
   ```python
   @router.post("/aps/{host}/provision")
   async def provision_ap(host: str, data: ProvisionRequest, ...):
       # Verificar que vendor == "mikrotik"
       # Reutilizar ProvisioningService._run_provisioning_ssh_pure()
   ```

3. **Actualizar UI de APs**:
   - Mostrar botón "Provision" solo para APs MikroTik no aprovisionados.
   - Reutilizar el modal de provisioning existente (copiar de routers).

### Fase 2: Refactorizar a Servicio Compartido (Futuro)

Una vez que ambos módulos funcionen, refactorizar para eliminar duplicación.

---

## Archivos a Modificar

| Archivo | Cambio |
|---------|--------|
| `app/models/ap.py` | Agregar `is_provisioned`, `api_ssl_port` |
| `app/api/aps/models.py` | Agregar campos a Pydantic models |
| `app/api/aps/main.py` | Agregar endpoint `/aps/{host}/provision` |
| `app/db/init_db.py` | Migración para nuevos campos |
| `templates/aps.html` | Agregar modal y botón de provisioning |
| `static/js/aps.js` | Agregar lógica de provisioning |

---

## Estimación de Esfuerzo

| Tarea | Tiempo Estimado |
|-------|-----------------|
| Modificar modelos | 15 min |
| Crear endpoint | 30 min |
| Migración DB | 10 min |
| UI (HTML + JS) | 45 min |
| Testing | 30 min |
| **Total** | ~2-2.5 horas |

---

## Preguntas para Usuario

1. ¿Desea proceder con la **Opción A** (agregar provisioning a APs)?
2. ¿Los APs MikroTik que actualmente tiene registrados ya tienen usuarios/certificados configurados, o necesitan aprovisionamiento desde cero?
3. ¿Prefiere que el botón "Provision" aparezca solo para APs MikroTik, o también mostrar un mensaje de "N/A" para Ubiquiti?

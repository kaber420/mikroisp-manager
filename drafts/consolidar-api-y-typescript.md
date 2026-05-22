# Plan: Consolidación de API del Dashboard y Corrección de TypeScript

Este documento describe la estrategia técnica para optimizar el rendimiento de carga del frontend consolidadando múltiples peticiones del Dashboard y solventando errores de TypeScript que afectan la estabilidad de compilación del proyecto.

---

## 🚀 1. Consolidación de la API de Estadísticas (Dashboard)

### 📌 Situación Actual
Actualmente, el archivo `src/routes/(app)/+page.ts` realiza un `Promise.all` con **12 consultas HTTP independientes** al arrancar el Dashboard:
```typescript
const [cpeRes, switchRes, ticketsRes, routerRes, apRes, topSignalRes, topAirtimeRes, topConsumptionRes, topOfflineRes, recentTicketsRes, settingsRes, routersListRes] = await Promise.all([
    fetch('/api/stats/cpe-count'),
    fetch('/api/stats/switch-count'),
    fetch('/api/stats/tickets'),
    fetch('/api/stats/router-count'),
    fetch('/api/stats/ap-count'),
    fetch('/api/stats/top-cpes-by-signal'),
    fetch('/api/stats/top-aps-by-airtime'),
    fetch('/api/stats/top-routers-by-consumption'),
    fetch('/api/stats/top-offline-devices'),
    fetch('/api/tickets/?limit=10'),
    fetch('/api/settings/public'),
    fetch('/api/routers')
]);
```
**Impacto:** En conexiones HTTP/1.1 (por defecto en navegadores locales sin HTTP/2 configurado), las peticiones se encolan debido al límite de **6 conexiones concurrentes por dominio**. Esto causa que el Dashboard tarde más de lo necesario en ser interactivo y multiplica las llamadas de autenticación y sesiones.

---

### 🛠️ Propuesta de Solución: Endpoint Unificado
Crear un endpoint consolidado `/api/stats/dashboard-summary` en el backend FastAPI que realice las consultas en paralelo a la base de datos y retorne un único payload JSON estructurado.

#### 1. Backend (FastAPI - `app/api/stats/models.py`)
Definiremos los modelos Pydantic agregados en `models.py`:

```python
class DashboardStatsSummary(BaseModel):
    cpes: CPECount
    switches: SwitchCount
    tickets: TicketStats
    routers: RouterCount
    aps: APCount

class DashboardTopsSummary(BaseModel):
    signal: list[TopCPE]
    airtime: list[TopAP]
    consumption: list[TopRouterConsumption]
    offline: list[TopOfflineDevice]

class DashboardSummaryResponse(BaseModel):
    stats: DashboardStatsSummary
    tops: DashboardTopsSummary
    recent_tickets: list
    routers_list: list
```

#### 2. Backend (FastAPI - `app/api/stats/main.py`)
Implementaremos el controlador usando `asyncio.gather` para mantener el paralelismo de la persistencia de datos:

```python
import asyncio

@router.get("/stats/dashboard-summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
):
    try:
        # Ejecutar peticiones de base de datos en paralelo eficientemente en el backend
        results = await asyncio.gather(
            get_cpe_total_count(session, current_user),
            get_switch_total_count(session, current_user),
            get_ticket_stats(session, current_user),
            get_router_total_count(session, current_user),
            get_ap_total_count(session, current_user),
            get_top_cpes_by_weak_signal(limit=5, session=session, current_user=current_user),
            get_top_aps_by_airtime(limit=5, session=session, current_user=current_user),
            get_top_routers_by_consumption(limit=5, session=session, current_user=current_user),
            get_top_offline_devices(limit=5, session=session, current_user=current_user),
        )
        
        # Consultas adicionales que requiere el Dashboard
        # (Para tickets recientes y lista de routers, se pueden reusar repositorios o queries simples)
        # Nota: Ajustar según correspondencia de base de datos
        
        return {
            "stats": {
                "cpes": results[0],
                "switches": results[1],
                "tickets": results[2],
                "routers": results[3],
                "aps": results[4]
            },
            "tops": {
                "signal": results[5],
                "airtime": results[6],
                "consumption": results[7],
                "offline": results[8]
            },
            "recent_tickets": [], # TODO: Mapear desde base de datos / repositorio
            "routers_list": []     # TODO: Mapear desde base de datos / repositorio
        }
    except Exception as e:
        logger.error(f"Error consolidando estadísticas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al generar resumen del dashboard")
```

#### 3. Frontend (SvelteKit - `src/routes/(app)/+page.ts`)
Refactorizaremos el cargador del frontend para hacer solo **3 llamadas** (el summary consolidado, la configuración pública y los datos de apoyo si se requiere mantenerlos separados):

```typescript
export const ssr = false;

export const load = async ({ fetch }) => {
    try {
        const [summaryRes, settingsRes] = await Promise.all([
            fetch('/api/stats/dashboard-summary'),
            fetch('/api/settings/public')
        ]);

        const summary = summaryRes.ok ? await summaryRes.json() : null;
        const publicSettings = settingsRes.ok ? await settingsRes.json() : {};

        return {
            stats: summary?.stats || {
                cpes: { total_cpes: 0, active: 0 },
                switches: { total_switches: 0, online: 0 },
                tickets: { open_tickets: 0, resolved_tickets: 0, pending_tickets: 0, total_tickets: 0 },
                routers: { total_routers: 0, online: 0 },
                aps: { total_aps: 0, online: 0 }
            },
            tops: summary?.tops || {
                signal: [],
                airtime: [],
                consumption: [],
                offline: []
            },
            publicSettings,
            recentTickets: summary?.recent_tickets || [],
            routersList: summary?.routers_list || []
        };
    } catch (e) {
        console.error('Failed to load consolidated dashboard stats:', e);
        return {
            stats: {
                cpes: { total_cpes: 0, active: 0 },
                switches: { total_switches: 0, online: 0 },
                tickets: { open_tickets: 0, resolved_tickets: 0, pending_tickets: 0, total_tickets: 0 },
                routers: { total_routers: 0, online: 0 },
                aps: { total_aps: 0, online: 0 }
            },
            tops: { signal: [], airtime: [], consumption: [], offline: [] },
            publicSettings: {},
            recentTickets: [],
            routersList: []
        };
    }
};
```

---

## 🛡️ 2. Corrección de Errores de Compilación de TypeScript

### 📌 Fallo Detectado en `VlanModal.svelte`
En `src/lib/components/routers/VlanModal.svelte:44`, el compilador falla porque el tipo de `i` en el filtro de interfaces no está explícitamente tipado y `noImplicitAny` está activo en el proyecto.

```typescript
const physicalInterfaces = $derived(
    interfaces.filter((i) => ["ether", "wlan", "bonding"].includes(i.type)),
);
```

### 🛠️ Solución
Asignar el tipo de interfaz importado (`InterfaceData`) al parámetro de la función flecha:

```typescript
const physicalInterfaces = $derived(
    interfaces.filter((i: InterfaceData) => ["ether", "wlan", "bonding"].includes(i.type)),
);
```

---

## 📈 Plan de Ejecución Sugerido

1. **Fase 1: Correcciones rápidas TypeScript (Frontend)**
   - Corregir el tipado en `VlanModal.svelte`.
   - Corregir cualquier otra advertencia de tipo implícito para dejar `pnpm svelte-check` a cero errores de TypeScript.

2. **Fase 2: Implementación de Pydantic y Rutas en Backend**
   - Definir los esquemas agregados en `app/api/stats/models.py`.
   - Crear el endpoint `/stats/dashboard-summary` en `app/api/stats/main.py`.
   - Utilizar el repositorio de tickets y routers existentes dentro del backend para poblar los campos `recent_tickets` y `routers_list`.

3. **Fase 3: Refactorización de Carga del Frontend**
   - Modificar la llamada en `src/routes/(app)/+page.ts` para que consuma la nueva ruta.
   - Verificar que no haya cambios disruptivos en la visualización de los datos del Dashboard.

4. **Fase 4: Pruebas y Validación**
   - Ejecutar `pnpm run check` para asegurar integridad tipográfica.
   - Monitorear la pestaña de *Red* del navegador para comprobar la reducción de latencia (TTFB) y el número de conexiones simultáneas.

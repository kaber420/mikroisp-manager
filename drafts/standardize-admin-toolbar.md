# Draft — Refactorización y Estandarización de Admin Toolbar

> Estado: **PLANIFICADO** 📝

---

## 🎯 Objetivo

Eliminar la duplicación masiva de código HTML y estilos inline en las cabeceras (el contenedor `glass-card-flat` con título, botones y contadores rápidos) de los diferentes dominios de la aplicación. 

Al encapsular esto en un componente global de **Svelte 5** (`AdminToolbar.svelte`), lograremos:
1. **Consistencia estética total:** Cualquier cambio de diseño (bordes, fondo, sombras, paddings) se aplicará instantáneamente en todas las pantallas.
2. **Alineación perfecta del botón Volver:** El botón de regreso se colocará a la izquierda del título dentro de un contenedor flexible (`flex`), evitando cualquier descuadre de layout o saltos de línea.
3. **Mantenibilidad:** Limpieza extrema en los archivos principales de cada módulo (`+page.svelte`).

---

## 📂 Estructura del Componente

Crearemos el componente de forma global en:
* `src/lib/components/AdminToolbar.svelte`

### Propiedades y Runas (Svelte 5)

El componente utilizará las siguientes propiedades con tipos estrictos de TypeScript y snippets flexibles:

```typescript
type Props = {
    title: string;          // Título principal de la sección
    subtitle?: string;       // Subtítulo, descripción o conteos simples
    backUrl?: string;        // URL opcional para el botón Volver (si no se pasa, no se renderiza)
    stats?: Snippet;        // Fragmento opcional para métricas complejas (ej. Routers Online/Offline)
    actions?: Snippet;      // Fragmento opcional para botones principales (ej. Nuevo Cliente)
    tabs?: Snippet;         // Fragmento opcional para menús de pestañas inferiores (ej. Detalle de Cliente)
};
```

---

## 🛠️ Detalle de las Áreas a Refactorizar

### 👥 1. Dominio de Clientes (`clientes/`)

#### A. Listado de Clientes (`src/routes/(app)/clientes/+page.svelte`)
* **Antes:** Una tarjeta `glass-card-flat` de 45 líneas conteniendo el título *"Gestión de Clientes"*, el conteo total dinámico de clientes y el botón `onclick={openCreate}` de *"Nuevo Cliente"*.
* **Después:**
  ```svelte
  <AdminToolbar 
      title="Gestión de Clientes" 
      subtitle="{data.clients.total} cliente{data.clients.total !== 1 ? 's' : ''} registrados"
  >
      {#snippet actions()}
          <button class="btn btn-primary btn-sm gap-2" onclick={openCreate}>
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
              </svg>
              Nuevo Cliente
          </button>
      {/snippet}
  </AdminToolbar>
  ```

#### B. Perfil/Detalle del Cliente (`src/routes/(app)/clientes/[id]/+page.svelte`)
* **Antes:** Una cabecera con botón volver inline que redirecciona a `/clientes`, título con el nombre del cliente, badge de estado y las pestañas horizontales (`Información`, `Servicios`, etc.) acopladas abajo.
* **Después:** El botón "Volver" quedará perfectamente integrado a la izquierda sin descuadres.
  ```svelte
  <AdminToolbar 
      title={client.name}
      backUrl="/clientes"
  >
      {#snippet stats()}
          <span class="badge {statusBadgeClass(client.service_status)} badge-sm" style="margin-top: 4px;">
              {statusLabel(client.service_status)}
          </span>
      {/snippet}

      {#snippet tabs()}
          <!-- Renderizado del menú de pestañas actual sin cambios en la lógica -->
          <div class="tabs tabs-border" style="padding: 0 1rem; border-top: 1px solid color-mix(in oklch, currentColor 10%, transparent);">
              <!-- ... tabs actual ... -->
          </div>
      {/snippet}
  </AdminToolbar>
  ```

---

### 📡 2. Dominio de Routers (`routers/`)

#### A. Listado de Routers (`src/routes/(app)/routers/+page.svelte`)
* **Antes:** Cabecera con título, bloque de estado de red complejo (`Total`, `Online`, `Offline`, `% OK`) que incluye animaciones ping, y el botón *"Nuevo Router"*.
* **Después:**
  ```svelte
  <AdminToolbar title="Routers">
      {#snippet stats()}
          {#if !loading}
              <div style="display:flex;align-items:center;gap:0.6rem;background:oklch(from var(--color-base-content) l c h / 0.03);padding:0.35rem 0.75rem;border-radius:0.75rem;border:1px solid oklch(from var(--color-base-content) l c h / 0.05);">
                  <span class="text-xs font-semibold text-slate-400">
                      Total: <span class="text-white font-extrabold">{totalRouters}</span>
                  </span>
                  <!-- ... indicador de estados online/offline ... -->
              </div>
          {/if}
      {/snippet}

      {#snippet actions()}
          <button class="btn btn-primary btn-sm gap-2" onclick={openCreate}>
              <!-- SVG más -->
              Nuevo Router
          </button>
      {/snippet}
  </AdminToolbar>
  ```

---

### 🗺️ 3. Otros Dominios Potenciales

Una vez probado y validado con `clientes` y `routers`, extenderemos este mismo componente a los demás dominios de la carpeta `src/routes/(app)` para lograr el 100% de uniformidad:
* **Zonas (`zonas/+page.svelte`)**
* **CPEs (`cpes/+page.svelte`)**
* **Access Points (`access-points/+page.svelte`)**
* **Planes (`planes/+page.svelte`)**
* **Usuarios (`usuarios/+page.svelte`)**
* **Tickets (`tickets/+page.svelte`)**

---

## 📈 Checklist de Ejecución

### Fase 1: Creación y Definición
- [ ] Crear el componente `$lib/components/AdminToolbar.svelte`.
- [ ] Verificar tipos de TypeScript y exportaciones de snippets.

### Fase 2: Implementación Base
- [ ] Refactorizar `clientes/+page.svelte` (Listado de Clientes).
- [ ] Refactorizar `clientes/[id]/+page.svelte` (Detalle y Pestañas del Cliente).
- [ ] Refactorizar `routers/+page.svelte` (Listado y Contadores de Routers).

### Fase 3: Pruebas y Limpieza
- [ ] Ejecutar compilación de desarrollo para asegurar compatibilidad.
- [ ] Realizar pruebas visuales (revisión de la perfecta alineación del botón volver en pantallas móviles y desktop).
- [ ] Confirmar la persistencia y clicks de los botones de acción integrados.

### Fase 4: Despliegue de Uniformidad (Opcional en fases posteriores)
- [ ] Aplicar en `zonas/+page.svelte` y `access-points/+page.svelte`.

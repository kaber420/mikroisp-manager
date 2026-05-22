# Plan Detallado — Refactorización y Estandarización de Admin Toolbar

> Estado: **PLANIFICADO Y DETALLADO** 📝
>
> **Resultado de la Auditoría:** Se ha revisado a fondo la estructura de directorios en `frontend-v2-daisy/src/` y se ha verificado mediante búsquedas de código que el componente global `AdminToolbar.svelte` **NO** ha sido implementado todavía, y los diferentes dominios siguen utilizando la cabecera `glass-card-flat` duplicada con estilos inline.

---

## 🎯 Objetivo

Eliminar la duplicación masiva de código HTML y estilos inline en las cabeceras (el contenedor `glass-card-flat` con título, botones y contadores rápidos) de los diferentes dominios de la aplicación.

Al encapsular esto en un componente global de **Svelte 5** (`AdminToolbar.svelte`), lograremos:
1. **Consistencia estética total:** Cualquier cambio de diseño (bordes, fondo, sombras, paddings) se aplicará instantáneamente en todas las pantallas.
2. **Alineación perfecta del botón Volver:** El botón de regreso se colocará a la izquierda del título dentro de un contenedor flexible (`flex`), evitando cualquier descuadre de layout o saltos de línea.
3. **Mantenibilidad:** Limpieza extrema en los archivos principales de cada módulo (`+page.svelte`).

---

## 📂 Diseño del Componente

Crearemos el componente de forma global en:
* [AdminToolbar.svelte](file:///home/kaberromero/Documentos/proyectos/OmniWISP/frontend-v2-daisy/src/lib/components/AdminToolbar.svelte)

### Propiedades y Runas (Svelte 5)

El componente utilizará las siguientes propiedades con tipos estrictos de TypeScript y snippets flexibles para garantizar compatibilidad con casos complejos:

```typescript
import type { Snippet } from "svelte";

export interface AdminToolbarProps {
    title: string;          // Título principal de la sección
    subtitle?: string;       // Subtítulo, descripción o conteos simples
    backUrl?: string;        // URL opcional para el botón Volver (si no se pasa, no se renderiza)
    stats?: Snippet;        // Fragmento opcional para métricas complejas (ej. Routers Online/Offline)
    actions?: Snippet;      // Fragmento opcional para botones principales (ej. Nuevo Cliente)
    tabs?: Snippet;         // Fragmento opcional para menús de pestañas inferiores (ej. Detalle de Cliente)
}
```

### Código Propuesto para el Componente

```svelte
<script lang="ts">
    import { goto } from "$app/navigation";
    import type { AdminToolbarProps } from "./AdminToolbar.svelte";

    let {
        title,
        subtitle,
        backUrl,
        stats,
        actions,
        tabs
    }: AdminToolbarProps = $props();
</script>

<div
    class="glass-card-flat"
    style="border-radius:1rem;display:flex;flex-direction:column;overflow:hidden;"
>
    <div style="padding:1.25rem 1.5rem;display:flex;flex-direction:column;gap:0.75rem;">
        <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:0.75rem;">
            <!-- Grupo Izquierdo: Volver, Título/Subtítulo y Métricas -->
            <div style="display:flex;align-items:center;gap:1.25rem;flex-wrap:wrap;">
                <div style="display:flex;align-items:center;gap:0.75rem;">
                    {#if backUrl}
                        <button
                            class="btn btn-ghost btn-sm btn-square"
                            onclick={() => goto(backUrl)}
                            title="Volver"
                        >
                            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
                            </svg>
                        </button>
                    {/if}
                    <div>
                        <h1 style="margin:0;font-size:1.5rem;font-weight:800;letter-spacing:-0.025em;line-height:1.2;">
                            {title}
                        </h1>
                        {#if subtitle}
                            <p style="margin:0.25rem 0 0;font-size:0.85rem;opacity:0.5;line-height:1.2;">
                                {subtitle}
                            </p>
                        {/if}
                    </div>
                </div>

                {#if stats}
                    {@render stats()}
                {/if}
            </div>

            <!-- Grupo Derecho: Botones y Acciones -->
            {#if actions}
                <div style="display:flex;align-items:center;gap:0.75rem;flex-wrap:wrap;">
                    {@render actions()}
                </div>
            {/if}
        </div>
    </div>

    <!-- Pestañas de Navegación Inferior (Opcional) -->
    {#if tabs}
        {@render tabs()}
    {/if}
</div>
```

---

## 🛠️ Detalle de las Áreas a Refactorizar (Fase Base)

### 👥 1. Dominio de Clientes (`clientes/`)

#### A. Listado de Clientes
* **Archivo:** [clientes/+page.svelte](file:///home/kaberromero/Documentos/proyectos/OmniWISP/frontend-v2-daisy/src/routes/(app)/clientes/+page.svelte)
* **Código Anterior (Líneas 121-165):**
  ```svelte
  <div
      class="glass-card-flat"
      style="border-radius:1rem;display:flex;flex-direction:column;overflow:hidden;"
  >
      ...
  </div>
  ```
* **Código Nuevo:**
  ```svelte
  <script lang="ts">
      ...
      import AdminToolbar from "$lib/components/AdminToolbar.svelte";
  </script>

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

#### B. Perfil/Detalle del Cliente
* **Archivo:** [clientes/[id]/+page.svelte](file:///home/kaberromero/Documentos/proyectos/OmniWISP/frontend-v2-daisy/src/routes/(app)/clientes/[id]/+page.svelte)
* **Código Anterior (Líneas 217-268):**
  Cabecera de 51 líneas con estilos manuales para alinear el botón volver e integrar tabs.
* **Código Nuevo:**
  ```svelte
  <script lang="ts">
      ...
      import AdminToolbar from "$lib/components/AdminToolbar.svelte";
  </script>

  <AdminToolbar
      title={client.name}
      backUrl="/clientes"
  >
      {#snippet stats()}
          <span class="badge {statusBadgeClass(client.service_status)} badge-sm" style="margin-top: 4px;">
              {statusLabel(client.service_status)}
          </span>
      {/snippet}

      {#snippet actions()}
          <div style="font-size:0.8rem;opacity:0.5;">
              Alta: {new Date(client.created_at).toLocaleDateString('es-MX')}
          </div>
      {/snippet}

      {#snippet tabs()}
          <div class="tabs tabs-border" style="padding:0 1rem;border-top:1px solid color-mix(in oklch, currentColor 10%, transparent);">
              <button class="tab {activeTab === 'info' ? 'tab-active' : ''}" onclick={() => switchTab('info')}>
                  <svg class="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                  Información
              </button>
              <button class="tab {activeTab === 'servicios' ? 'tab-active' : ''}" onclick={() => switchTab('servicios')}>
                  <svg class="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.14 0" />
                  </svg>
                  Servicios · <span class="ml-1 badge badge-sm {client.cpe_count > 0 ? 'badge-info' : 'badge-neutral'}">{client.cpe_count}</span>
              </button>
              <button class="tab {activeTab === 'pagos' ? 'tab-active' : ''}" onclick={() => switchTab('pagos')}>
                  <svg class="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2z" />
                  </svg>
                  Facturación
              </button>
              <button class="tab {activeTab === 'acceso' ? 'tab-active' : ''}" onclick={() => switchTab('acceso')}>
                  <svg class="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                  </svg>
                  Acceso Portal
              </button>
          </div>
      {/snippet}
  </AdminToolbar>
  ```

---

### 📡 2. Dominio de Routers (`routers/`)

#### A. Listado de Routers
* **Archivo:** [routers/+page.svelte](file:///home/kaberromero/Documentos/proyectos/OmniWISP/frontend-v2-daisy/src/routes/(app)/routers/+page.svelte)
* **Código Anterior (Líneas 163-243):**
  Cabecera de 80 líneas conteniendo lógica condicional para el cargando y el bloque de estados complejos de red.
* **Código Nuevo:**
  ```svelte
  <script lang="ts">
      ...
      import AdminToolbar from "$lib/components/AdminToolbar.svelte";
  </script>

  <AdminToolbar title="Routers">
      {#snippet stats()}
          {#if !loading}
              <div style="display:flex;align-items:center;gap:0.6rem;background:oklch(from var(--color-base-content) l c h / 0.03);padding:0.35rem 0.75rem;border-radius:0.75rem;border:1px solid oklch(from var(--color-base-content) l c h / 0.05);">
                  <span class="text-xs font-semibold text-slate-400" style="padding-right:0.25rem;">
                      Total: <span class="text-white font-extrabold">{totalRouters}</span>
                  </span>
                  
                  <div style="width:1px;height:12px;background:oklch(from var(--color-base-content) l c h / 0.12);"></div>
                  
                  <span class="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-400">
                      <span class="relative flex h-2 w-2">
                          <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                          <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                      </span>
                      {onlineRouters} <span class="font-medium text-slate-400">Online</span>
                  </span>
                  
                  <div style="width:1px;height:12px;background:oklch(from var(--color-base-content) l c h / 0.12);"></div>
                  
                  <span class="inline-flex items-center gap-1.5 text-xs font-bold text-rose-400">
                      <span class="h-2 w-2 rounded-full bg-rose-500"></span>
                      {offlineRouters} <span class="font-medium text-slate-400">Offline</span>
                  </span>

                  {#if totalRouters > 0}
                      <div style="width:1px;height:12px;background:oklch(from var(--color-base-content) l c h / 0.12);"></div>
                      <span class="badge badge-sm badge-primary font-bold text-[10px]">
                          {percentRouters}% OK
                      </span>
                  {/if}
              </div>
          {:else}
              <div style="height:1.75rem;width:120px;border-radius:0.5rem;background:oklch(from var(--color-base-content) l c h / 0.08);animation:pulseSkel 1.5s infinite;"></div>
          {/if}
      {/snippet}

      {#snippet actions()}
          <button class="btn btn-primary btn-sm gap-2" onclick={openCreate}>
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
              </svg>
              Nuevo Router
          </button>
      {/snippet}
  </AdminToolbar>
  ```

---

## 🗺️ 3. Otros Dominios Potenciales (Fase de Uniformidad Total)

Una vez probado y validado con `clientes` y `routers`, extenderemos este mismo componente a los demás dominios de la carpeta `src/routes/(app)` para lograr el 100% de uniformidad:

### A. Zonas
* **Archivo:** [zonas/+page.svelte](file:///home/kaberromero/Documentos/proyectos/OmniWISP/frontend-v2-daisy/src/routes/(app)/zonas/+page.svelte)
* **Código Nuevo:**
  ```svelte
  <AdminToolbar
      title="Gestión — Zonas de Cobertura"
      subtitle={loading ? "Cargando..." : `${zonas.length} zona${zonas.length !== 1 ? "s" : ""} registrada${zonas.length !== 1 ? "s" : ""}`}
  >
      {#snippet actions()}
          <button class="btn btn-primary btn-sm" onclick={() => (showModal = true)}>
              + Nueva Zona
          </button>
      {/snippet}
  </AdminToolbar>
  ```

### B. Planes de Internet
* **Archivo:** [planes/+page.svelte](file:///home/kaberromero/Documentos/proyectos/OmniWISP/frontend-v2-daisy/src/routes/(app)/planes/+page.svelte)
* **Código Nuevo:**
  ```svelte
  <AdminToolbar
      title="Gestión de Planes"
      subtitle="{globalCount} globales · {localCount} locales"
  >
      {#snippet actions()}
          <button class="btn btn-primary btn-sm gap-2" on:click={openCreate}>
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
              </svg>
              Nuevo Plan
          </button>
      {/snippet}
  </AdminToolbar>
  ```

---

## 📈 Checklist de Ejecución

### Fase 1: Creación y Definición
- [ ] Crear el componente `$lib/components/AdminToolbar.svelte` con TypeScript y Svelte 5.
- [ ] Validar importaciones de tipado en `tsconfig.json` y el correcto renderizado de snippets en Svelte 5.

### Fase 2: Implementación Base
- [ ] Refactorizar [clientes/+page.svelte](file:///home/kaberromero/Documentos/proyectos/OmniWISP/frontend-v2-daisy/src/routes/(app)/clientes/+page.svelte).
- [ ] Refactorizar [clientes/[id]/+page.svelte](file:///home/kaberromero/Documentos/proyectos/OmniWISP/frontend-v2-daisy/src/routes/(app)/clientes/[id]/+page.svelte).
- [ ] Refactorizar [routers/+page.svelte](file:///home/kaberromero/Documentos/proyectos/OmniWISP/frontend-v2-daisy/src/routes/(app)/routers/+page.svelte).

### Fase 3: Pruebas y Limpieza
- [ ] Ejecutar compilación de desarrollo (`pnpm run dev` o `npm run dev`) para asegurar compatibilidad total de TypeScript.
- [ ] Verificar la alineación del botón "Volver" en pantallas móviles y desktop.
- [ ] Validar la persistencia de snippets y que no haya pérdida de funcionalidad o eventos rotos en los botones.

### Fase 4: Uniformidad Global
- [ ] Aplicar en [zonas/+page.svelte](file:///home/kaberromero/Documentos/proyectos/OmniWISP/frontend-v2-daisy/src/routes/(app)/zonas/+page.svelte).
- [ ] Aplicar en [planes/+page.svelte](file:///home/kaberromero/Documentos/proyectos/OmniWISP/frontend-v2-daisy/src/routes/(app)/planes/+page.svelte).
- [ ] Extender secuencialmente a `access-points/+page.svelte`, `cpes/+page.svelte` y `usuarios/+page.svelte`.

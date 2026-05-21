# Draft — Refactorización `difusion/` y `cpes/`

> Estado: **COMPLETADO** ✅

---

## 📢 Dominio `difusion/` (848 líneas)

### Análisis del archivo actual

`difusion/+page.svelte` es una sola página de formulario de broadcast.
**No tiene pestañas reales** — es un layout de 2 columnas (formulario principal + sidebar de resumen).
La lógica completa vive en el script del `+page.svelte`.

### Secciones extraibles

| Nuevo componente | Líneas aprox. | Descripción | Props recibe | Emite |
|---|---|---|---|---|
| `DifusionHeader.svelte` | ~30 | Banner de encabezado con ícono y título | — | — |
| `DifusionDestinatariosCard.svelte` | ~185 | Card de selección de tipo, zonas y roles | `zones`, `targetType`, `allZones`, `selectedZoneIds`, `staffRoles` | eventos de cambio via bindables |
| `DifusionMensajeCard.svelte` | ~55 | Textarea del mensaje con contador | `message` (bindable) | — |
| `DifusionImagenCard.svelte` | ~155 | Upload de imagen + URL + preview | `selectedFile`, `imageUrl`, `imageError` (bindables) | — |
| `DifusionResumenCard.svelte` | ~165 | Sidebar con resumen, botón enviar, error y resultado | `targetLabel`, `message`, `selectedFile`, `imageUrl`, `canSend`, `sending`, `uploading`, `lastResult`, `errorMessage` | `onsend` |
| `DifusionConfirmModal.svelte` | ~50 | Modal de confirmación de envío | `targetLabel`, `recipientEstimate` | `onconfirm`, `oncancel` |

### Resultado esperado

`difusion/+page.svelte` quedará en ~50 líneas (solo lógica de estado + imports + layout grid).

### Props y estado compartido

La lógica de `handleSend()`, `handleFileSelect()`, `clearFile()`, `toggleZone()` se queda en `+page.svelte`.
Los componentes reciben estado via `bind:` para dos vías o props + callbacks para acciones.

```svelte
<!-- difusion/+page.svelte resultante (~50 líneas) -->
<script lang="ts">
  // ... lógica de estado y funciones ...
  import DifusionHeader from "$lib/components/difusion/DifusionHeader.svelte";
  import DifusionDestinatariosCard from "$lib/components/difusion/DifusionDestinatariosCard.svelte";
  import DifusionMensajeCard from "$lib/components/difusion/DifusionMensajeCard.svelte";
  import DifusionImagenCard from "$lib/components/difusion/DifusionImagenCard.svelte";
  import DifusionResumenCard from "$lib/components/difusion/DifusionResumenCard.svelte";
  import DifusionConfirmModal from "$lib/components/difusion/DifusionConfirmModal.svelte";
</script>

<DifusionHeader />
<div class="grid grid-cols-1 gap-6 lg:grid-cols-3">
  <div class="space-y-5 lg:col-span-2">
    <DifusionDestinatariosCard {zones} bind:targetType bind:allZones ... />
    <DifusionMensajeCard bind:message />
    <DifusionImagenCard bind:selectedFile bind:imageUrl ... />
  </div>
  <div>
    <DifusionResumenCard ... onsend={openConfirmModal} />
  </div>
</div>
<DifusionConfirmModal bind:this={confirmModal} ... onconfirm={handleSend} />
```

### Orden de ejecución

1. Crear `$lib/components/difusion/`
2. Extraer `DifusionHeader` (sin estado, trivial)
3. Extraer `DifusionDestinatariosCard` (más complejo, maneja zonas y roles)
4. Extraer `DifusionMensajeCard`
5. Extraer `DifusionImagenCard`
6. Extraer `DifusionResumenCard`
7. Extraer `DifusionConfirmModal`
8. Simplificar `+page.svelte`
9. Verificar build

---

## 📡 Dominio `cpes/` (571 líneas)

### Análisis del archivo actual

`cpes/+page.svelte` tiene:
- **Script:** lógica de filtros + 3 modales inline (editar, deshabilitar, eliminar) + helpers de display
- **Template:** DataTable + 3 bloques `{#if modal}` con modales inline

**No tiene sub-rutas propias** (todo en 1 archivo).

### Secciones extraibles

| Nuevo componente | Líneas aprox. | Descripción | Props recibe | Emite |
|---|---|---|---|---|
| `CPEEditModal.svelte` | ~85 | Modal para editar hostname/alias del CPE | `cpe: CPEGlobalInfo \| null`, `show` (bindable) | `onsave` |
| `CPEDisableModal.svelte` | ~60 | Modal de confirmación para deshabilitar | `cpe: CPEGlobalInfo \| null`, `show` (bindable) | `onconfirm` |
| `CPEDeleteModal.svelte` | ~60 | Modal de confirmación para eliminar | `cpe: CPEGlobalInfo \| null`, `show` (bindable) | `onconfirm` |

> **Nota:** La tabla principal (`DataTable` + snippets) NO se extrae — forma parte del layout de página y sus snippets dependen de helpers locales (`signalClass`, `statusLabel`, etc.). Sería demasiado acoplamiento para poco beneficio.

### Resultado esperado

`cpes/+page.svelte` quedará en ~280 líneas (DataTable + imports de modales + lógica de estado simplificada).

### Helpers a mantener en `+page.svelte`

Los helpers `signalClass`, `statusLabel`, `statusClass`, `displayName` se quedan en la página porque son usados en el snippet `row()` de la DataTable. Si en el futuro se necesitan en otro lugar, se pueden mover a `$lib/utils/cpe.ts`.

```svelte
<!-- cpes/+page.svelte resultante (~280 líneas) -->
<script lang="ts">
  import CPEEditModal from "$lib/components/cpes/CPEEditModal.svelte";
  import CPEDisableModal from "$lib/components/cpes/CPEDisableModal.svelte";
  import CPEDeleteModal from "$lib/components/cpes/CPEDeleteModal.svelte";
  // ... estado de modales reducido a show flags + targets ...
</script>

<!-- DataTable (sin cambios) -->

<CPEEditModal bind:show={editModal} cpe={editTarget} onsave={handleSaved} />
<CPEDisableModal bind:show={disableModal} cpe={disableTarget} onconfirm={handleDisabled} />
<CPEDeleteModal bind:show={deleteModal} cpe={deleteTarget} onconfirm={handleDeleted} />
```

### Orden de ejecución

1. Crear `$lib/components/cpes/`
2. Extraer `CPEEditModal` (incluye el estado de `editHostname`, `editSaving`, `editError`)
3. Extraer `CPEDisableModal`
4. Extraer `CPEDeleteModal`
5. Limpiar `cpes/+page.svelte` (eliminar bloques `{#if modal}` inline)
6. Verificar build

---

## Checklist de ejecución

### `difusion/`
- [x] `mkdir $lib/components/difusion/`
- [x] Crear `DifusionHeader.svelte`
- [x] Crear `DifusionDestinatariosCard.svelte`
- [x] Crear `DifusionMensajeCard.svelte`
- [x] Crear `DifusionImagenCard.svelte`
- [x] Crear `DifusionResumenCard.svelte`
- [x] Crear `DifusionConfirmModal.svelte`
- [x] Simplificar `difusion/+page.svelte`
- [x] `pnpm run build` ✅ (sin errores nuevos)

### `cpes/`
- [x] `mkdir $lib/components/cpes/`
- [x] Crear `CPEEditModal.svelte`
- [x] Crear `CPEDisableModal.svelte`
- [x] Crear `CPEDeleteModal.svelte`
- [x] Limpiar `cpes/+page.svelte`
- [x] `pnpm run build` ✅ (sin errores nuevos)

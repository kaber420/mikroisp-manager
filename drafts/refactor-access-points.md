# Plan de Refactorización: Modularizar Access Points

Este plan propone dividir la pantalla monolítica de **Access Points** (`src/routes/(app)/access-points/+page.svelte`), que actualmente cuenta con más de 850 líneas, en tres componentes pequeños, cohesivos y fáciles de mantener usando **Svelte 5** (Runas) y **DaisyUI**.

---

## 🎯 Objetivo
Hacer que el código sea mantenible, legible y escalable, eliminando la complejidad cognitiva de tener lógica de formularios, validación, pruebas de red y borrado mezclados en un solo archivo.

---

## 📂 Estructura Propuesta

El directorio quedará estructurado de la siguiente forma:

```text
access-points/
├── +page.svelte           <-- Componente principal (Orquestador y Tabla)
├── APFormModal.svelte     <-- Formulario de crear/editar y test de conexión
└── APDeleteModal.svelte   <-- Modal de confirmación de borrado
```

---

## 🛠️ Detalles de la División

### 1. `APFormModal.svelte`
Encapsulará toda la lógica de creación y edición del Access Point:
* **Estado local del formulario:** Bindings de los campos (`fHost`, `fUsername`, `fPassword`, `fVendor`, `fSshPort`, `fApiPort`, `fIsEnabled`, `fZonaId`, `fIsProvisioned`).
* **Acciones de validación:** Método `testConnection` para probar la conexión con el AP de forma interactiva con sus estados locales de carga (`testLoading`) y resultado (`testResult`).
* **Persistencia:** Llamadas API `createAP` o `updateAP` según corresponda. Al terminar con éxito, cierra el modal y notifica al padre a través de un callback (`onsave`).
* **Auto-puertos (Svelte 5):** Un `$effect` interno cambiará el puerto de API por defecto (443 para Ubiquiti, 8729 para MikroTik) al alternar el fabricante durante la creación.

### 2. `APDeleteModal.svelte`
Encapsulará la confirmación segura de eliminación:
* **Pantalla de confirmación:** Muestra advertencias claras y el host/hostname del AP a eliminar.
* **Acción de borrado:** Ejecuta `deleteAP(host)`, controlando su propio estado `deleteLoading` y errores locales. Al confirmar con éxito, ejecuta el callback `onconfirm`.

### 3. `+page.svelte` (Orquestador)
Se reducirá a menos de 220 líneas y solo manejará:
* Carga de datos de la API principal (`aps`, `zonas`).
* Métricas e indicadores del Header consolidados.
* Filtro de búsqueda por fabricantes en el Toolbar.
* Renderizado de la tabla principal y llamadas limpias a los nuevos modales:
  ```svelte
  <APFormModal bind:show={showModal} mode={modalMode} target={editTarget} {zonas} onsave={loadAPs} />
  <APDeleteModal bind:show={showDeleteModal} target={deleteTarget} onconfirm={loadAPs} />
  ```

---

## 🧪 Plan de Verificación
1. **Carga Inicial:** Validar la visualización correcta de la tabla de APs y las píldoras estadísticas en la cabecera.
2. **Crear AP:** Abrir el modal de creación, seleccionar una zona, realizar la prueba de conexión y guardarlo con éxito.
3. **Editar AP:** Clic en editar en un elemento de la tabla, comprobar que se cargan los datos correspondientes en el modal, editarlos y guardarlos.
4. **Eliminar AP:** Confirmar la eliminación del AP y verificar que desaparece de la lista tras recargar automáticamente.

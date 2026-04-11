<script lang="ts">
    import { onMount } from "svelte";
    import * as api from "$lib/api";
    import type { PortalAnnouncement, PortalAnnouncementCreate, PortalAnnouncementUpdate } from "$lib/types/portalAnnouncements";
    import { notify as notifications } from "$lib/stores/notifications";

    let items = $state<PortalAnnouncement[]>([]);
    let loading = $state(true);
    let selectedItem = $state<PortalAnnouncement | null>(null);
    let isEditing = $state(false);
    let showModal = $state(false);

    // Form data
    let fdType = $state<"critical" | "info" | "promotion" | "offer" | "notice" | "holiday" | "alert">("info");
    let fdTitle = $state("");
    let fdContent = $state("");
    let fdImageUrl = $state("");
    let fdPriority = $state(10);
    let fdStartDate = $state("");
    let fdEndDate = $state("");
    let fdIsActive = $state(true);

    onMount(async () => {
        await loadItems();
    });

    // Convierte una fecha genérica o string (UTC o local) a YYYY-MM-DDTHH:mm para inputs
    function toLocalISOString(date: Date | string | null | undefined): string {
        if (!date) return "";
        let d: Date;
        if (date instanceof Date) {
            d = date;
        } else {
            // Si el string no indica zona horaria (Z o +), el navegador lo asume local.
            // Forzamos que se interprete como UTC añadiendo 'Z' si falta.
            const hasTZ = date.includes('Z') || date.includes('+');
            d = new Date(hasTZ ? date : date + 'Z');
        }
        if (isNaN(d.getTime())) return "";
        
        // Ajustamos por el offset local para que el valor sea correcto en un input 'datetime-local'
        const tzo = d.getTimezoneOffset() * 60000;
        return new Date(d.getTime() - tzo).toISOString().slice(0, 16);
    }

    function fmtDate(date: string | null | undefined) {
        if (!date) return "--";
        // Asegurar que se interprete como UTC
        const hasTZ = date.includes('Z') || date.includes('+');
        const d = new Date(hasTZ ? date : date + 'Z');
        if (isNaN(d.getTime())) return date;
        return d.toLocaleDateString("es-ES", { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
    }

    async function loadItems() {
        loading = true;
        try {
            items = await api.getAdminPortalAnnouncements();
        } catch (error) {
            notifications.error("Error al cargar los anuncios. " + error);
        } finally {
            loading = false;
        }
    }

    function openCreate() {
        isEditing = false;
        selectedItem = null;
        
        fdType = "info";
        fdTitle = "";
        fdContent = "";
        fdImageUrl = "";
        fdPriority = 10;
        
        // Defaults: start now (local time correctly formatted)
        fdStartDate = toLocalISOString(new Date());
        fdEndDate = "";
        fdIsActive = true;
        showModal = true;
    }

    function openEdit(item: PortalAnnouncement) {
        isEditing = true;
        selectedItem = item;
        
        fdType = item.type;
        fdTitle = item.title;
        fdContent = item.content;
        fdImageUrl = item.image_url || "";
        fdPriority = item.priority;
        
        // Date formatting for input datetime-local
        fdStartDate = toLocalISOString(item.start_date) || toLocalISOString(new Date());
        fdEndDate = toLocalISOString(item.end_date);
        fdIsActive = item.is_active;
        
        showModal = true;
    }

    async function saveItem() {
        try {
            // Validate
            if (!fdTitle.trim() || !fdContent.trim() || !fdStartDate) {
                notifications.warning("Título, contenido y fecha de inicio son requeridos.");
                return;
            }

            const payload: PortalAnnouncementCreate | PortalAnnouncementUpdate = {
                type: fdType,
                title: fdTitle.trim(),
                content: fdContent.trim(),
                image_url: fdImageUrl.trim() || null,
                priority: fdPriority,
                start_date: new Date(fdStartDate).toISOString(),
                end_date: fdEndDate ? new Date(fdEndDate).toISOString() : null,
                is_active: fdIsActive
            };

            if (isEditing && selectedItem) {
                await api.updateAdminPortalAnnouncement(selectedItem.id, payload);
                notifications.success("Anuncio actualizado correctamente");
            } else {
                await api.createAdminPortalAnnouncement(payload as PortalAnnouncementCreate);
                notifications.success("Anuncio creado correctamente");
            }
            
            showModal = false;
            await loadItems();
            
        } catch (error) {
            notifications.error("Error al guardar el anuncio. Verifique la conexión.");
            console.error(error);
        }
    }

    async function toggleActive(item: PortalAnnouncement) {
        try {
            const newState = !item.is_active;
            await api.updateAdminPortalAnnouncement(item.id, { is_active: newState });
            item.is_active = newState;
            items = items; // trigger reactivity
            notifications.success(`Anuncio ${newState ? 'activado' : 'desactivado'}`);
        } catch (error) {
            notifications.error("Error al cambiar el estado");
        }
    }

    async function deleteItem(id: string) {
        if (!confirm("¿Está seguro de eliminar este anuncio permanentemente?")) return;
        try {
            await api.deleteAdminPortalAnnouncement(id);
            notifications.success("Anuncio eliminado");
            await loadItems();
        } catch (error) {
            notifications.error("Error al eliminar anuncio");
        }
    }

    function getBadgeColor(type: string) {
        switch(type) {
            case 'critical': return 'badge-error';
            case 'promotion': return 'badge-success';
            default: return 'badge-info';
        }
    }
</script>

<svelte:head>
    <title>CMS Portal - OmniWISP</title>
</svelte:head>

<div class="flex flex-col gap-6 max-w-7xl mx-auto">
    <!-- Header -->
    <div class="flex sm:flex-row flex-col items-center justify-between gap-4 p-6 bg-base-100/60 backdrop-blur-md rounded-2xl shadow-sm border border-base-200">
        <div>
            <h1 class="text-3xl font-black bg-gradient-to-br from-primary to-secondary bg-clip-text text-transparent drop-shadow-sm flex items-center gap-3">
                <span class="text-4xl text-primary drop-shadow-md">📰</span> Portal Web CMS
            </h1>
            <p class="text-base-content/60 font-medium mt-1">Gestión de avisos y promociones para el portal de clientes</p>
        </div>
        
        <button class="btn btn-primary" onclick={openCreate}>
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            Nuevo Anuncio
        </button>
    </div>

    <!-- Lista de anuncios -->
    {#if loading}
        <div class="flex justify-center p-12">
            <span class="loading loading-spinner text-primary loading-lg"></span>
        </div>
    {:else if items.length === 0}
        <div class="flex flex-col items-center justify-center p-12 bg-base-100 rounded-2xl border border-dashed border-base-300">
            <span class="text-6xl mb-4 opacity-50">📭</span>
            <h3 class="text-xl font-bold opacity-70">No hay anuncios</h3>
            <p class="text-sm opacity-50 mb-6">Crea tu primer anuncio para que los clientes lo vean en su portal.</p>
            <button class="btn btn-primary btn-outline" onclick={openCreate}>Crear Anuncio</button>
        </div>
    {:else}
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {#each items as item}
                <div class="card bg-base-100 shadow-sm border border-base-200 hover:shadow-md transition-shadow">
                    <div class="card-body p-5">
                        <div class="flex justify-between items-start mb-2">
                            <div class="flex items-center gap-2">
                                <span class="badge {getBadgeColor(item.type)} badge-sm uppercase font-bold text-xs">{item.type}</span>
                                {#if !item.is_active}
                                    <span class="badge badge-neutral badge-sm">Inactivo</span>
                                {/if}
                                {#if item.end_date && new Date(item.end_date) < new Date()}
                                    <span class="badge badge-warning badge-sm">Expirado</span>
                                {/if}
                            </div>
                            <div class="form-control">
                                <label class="cursor-pointer label p-0 gap-2">
                                  <span class="label-text text-xs opacity-70">Activo</span>
                                  <input type="checkbox" class="toggle toggle-primary toggle-sm" checked={item.is_active} onchange={() => toggleActive(item)} />
                                </label>
                            </div>
                        </div>
                        
                        <h2 class="card-title text-lg flex-1 line-clamp-1" title={item.title}>{item.title}</h2>
                        
                        <p class="text-sm opacity-70 line-clamp-2 mt-1 min-h-[2.5rem]">{item.content}</p>

                        <div class="mt-4 flex flex-wrap gap-2 text-xs opacity-60">
                            <div class="flex items-center gap-1">
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4"><path fill-rule="evenodd" d="M5.75 2a.75.75 0 011.5 0v1.5h5.5V2a.75.75 0 011.5 0v1.5h1.085a1.5 1.5 0 011.5 1.5v2.5H3.165V5a1.5 1.5 0 011.5-1.5h1.085V2zM3.165 9.5h13.67v6a1.5 1.5 0 01-1.5 1.5h-10.67a1.5 1.5 0 01-1.5-1.5v-6zM6 12a1 1 0 011-1h1a1 1 0 011 1v1a1 1 0 01-1 1H7a1 1 0 01-1-1v-1z" clip-rule="evenodd" /></svg>
                                {fmtDate(item.start_date)}
                            </div>
                            {#if item.end_date}
                                <span>-</span>
                                <div class="flex items-center gap-1 text-error">
                                    {fmtDate(item.end_date)}
                                </div>
                            {/if}
                        </div>
                        
                        <div class="card-actions justify-end mt-4 pt-4 border-t border-base-200">
                            <button class="btn btn-sm btn-ghost hover:text-info" onclick={() => openEdit(item)} aria-label="Editar" title="Editar">
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4"><path stroke-linecap="round" stroke-linejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L6.832 19.82a4.5 4.5 0 01-1.89 1.13l-2.685.8.8-2.685a4.5 4.5 0 011.13-1.89l10.68-10.68z" /><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 7.125L16.875 4.5" /></svg>
                            </button>
                            <button class="btn btn-sm btn-ghost hover:bg-error hover:text-error-content" onclick={() => deleteItem(item.id)} aria-label="Eliminar" title="Eliminar">
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4"><path stroke-linecap="round" stroke-linejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" /></svg>
                            </button>
                        </div>
                    </div>
                </div>
            {/each}
        </div>
    {/if}
</div>

<!-- Modal Crear/Editar -->
{#if showModal}
    <div class="modal modal-open modal-bottom sm:modal-middle">
        <div class="modal-box p-0 overflow-hidden max-w-3xl">
            <!-- Header Modal -->
            <div class="bg-base-200 px-6 py-4 border-b border-base-300 flex justify-between items-center">
                <h3 class="font-bold text-lg">{isEditing ? 'Editar Anuncio' : 'Nuevo Anuncio'}</h3>
                <button class="btn btn-sm btn-circle btn-ghost" onclick={() => showModal = false}>✕</button>
            </div>

            <!-- Body Modal -->
            <div class="p-6 bg-base-100 flex flex-col gap-4 overflow-y-auto max-h-[70vh]">
                
                <div class="flex flex-col sm:flex-row gap-4">
                    <div class="form-control w-full sm:w-1/3">
                        <label class="label" for="fdType"><span class="label-text font-bold">Tipo</span></label>
                        <select id="fdType" class="select select-bordered w-full" bind:value={fdType}>
                            <option value="info">Información</option>
                            <option value="promotion">Promoción</option>
                            <option value="critical">Alerta Crítica</option>
                        </select>
                    </div>
                    
                    <div class="form-control flex-1">
                        <label class="label" for="fdTitle">
                            <span class="label-text font-bold">Título</span>
                            <span class="label-text-alt opacity-70">Visible corto</span>
                        </label>
                        <input id="fdTitle" type="text" placeholder="Ej: Mantenimiento esta noche" class="input input-bordered w-full" bind:value={fdTitle} />
                    </div>
                </div>

                <div class="form-control">
                    <label class="label" for="fdContent">
                        <span class="label-text font-bold">Contenido (Markdown)</span>
                        <span class="label-text-alt opacity-70">Admite negritas, links, listas...</span>
                    </label>
                    <textarea 
                        id="fdContent"
                        class="textarea textarea-bordered h-32 font-mono" 
                        placeholder="**Atención:** El servicio se interrumpirá de 2AM a 4AM..." 
                        bind:value={fdContent}></textarea>
                </div>
                
                <div class="form-control">
                    <label class="label" for="fdImageUrl">
                        <span class="label-text font-bold">URL de Imagen (Opcional)</span>
                        <span class="label-text-alt opacity-70">Ideal para promociones</span>
                    </label>
                    <input id="fdImageUrl" type="url" placeholder="https://ejemplo.com/promo.jpg" class="input input-bordered w-full" bind:value={fdImageUrl} />
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 bg-base-200 p-4 rounded-xl mt-2">
                    <div class="form-control">
                        <label class="label" for="fdPriority"><span class="label-text font-bold text-xs">Prioridad</span></label>
                        <input id="fdPriority" type="number" class="input input-bordered input-sm" bind:value={fdPriority} title="Mayor número aparece arriba" />
                    </div>
                    
                    <div class="form-control">
                        <label class="label" for="fdStartDate"><span class="label-text font-bold text-xs">Inicio</span></label>
                        <input id="fdStartDate" type="datetime-local" class="input input-bordered input-sm" bind:value={fdStartDate} />
                    </div>
                    
                    <div class="form-control">
                        <label class="label" for="fdEndDate"><span class="label-text font-bold text-xs">Fin (Opcional)</span></label>
                        <input id="fdEndDate" type="datetime-local" class="input input-bordered input-sm" bind:value={fdEndDate} />
                    </div>
                    
                    <div class="form-control justify-end flex pb-1">
                        <label class="cursor-pointer label justify-start gap-3">
                          <input type="checkbox" class="toggle toggle-primary toggle-sm" bind:checked={fdIsActive} />
                          <span class="label-text font-bold text-xs">Activo</span>
                        </label>
                    </div>
                </div>

            </div>

            <!-- Footer Modal -->
            <div class="bg-base-200 px-6 py-4 border-t border-base-300 flex justify-end gap-3">
                <button class="btn btn-ghost" onclick={() => showModal = false}>Cancelar</button>
                <button class="btn btn-primary shadow-lg shadow-primary/30" onclick={saveItem}>
                    {isEditing ? 'Guardar Cambios' : 'Crear Anuncio'}
                </button>
            </div>
        </div>
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div class="modal-backdrop" onclick={() => showModal = false}></div>
    </div>
{/if}

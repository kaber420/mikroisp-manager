<script lang="ts">
    import { fade, fly } from "svelte/transition";
    import type { PageData } from './$types';
    import { createPortalTicket, sendTicketMessage, getPortalTickets } from '$lib/api/portal';
    import VideoCallModal from '$lib/components/video/VideoCallModal.svelte';

    let { data } = $props<{ data: PageData }>();

    // State
    let tickets = $state(data.tickets);
    // svelte-ignore state_referenced_locally
    let totalTickets = $state(data.total || 0);
    let showVideoModal = $state(false);

    // Sync state when data props change
    $effect(() => {
        tickets = data.tickets;
        totalTickets = data.total || 0;
    });

    const publicSettings = $derived(data.publicSettings);
    const botUsername = $derived(publicSettings?.client_bot_username || "OmniWispBot");
    
    // Pagination
    let currentPage = $state(1);
    let currentLimit = $state(10);
    let isFetchingPage = $state(false);

    let totalPages = $derived(Math.ceil(totalTickets / currentLimit) || 1);

    async function loadPage(page: number, limit: number) {
        if (page < 1) page = 1;
        try {
            isFetchingPage = true;
            const offset = (page - 1) * limit;
            const res = await getPortalTickets(limit, offset);
            tickets = res.items;
            totalTickets = res.total;
            currentPage = page;
            currentLimit = limit;
        } catch (e) {
            console.error('Error fetching tickets', e);
        } finally {
            isFetchingPage = false;
        }
    }

    // Filter state
    let statusFilter = $state('Todos');

    const filteredTickets = $derived(
        statusFilter === 'Todos' ? tickets : tickets.filter((t: any) => t.estado === statusFilter)
    );

    // Form state
    let isCreating = $state(false);
    let errorMsg = $state('');
    let showModal = $state(false);
    let formData = $state({
        asunto: '',
        descripcion: '',
        prioridad: 'normal'
    });

    // Detail Modal State
    let showDetailModal = $state(false);
    let selectedTicket = $state<any>(null);
    let replyMsg = $state('');
    let isReplying = $state(false);

    function openTicketDetail(ticket: any) {
        selectedTicket = ticket;
        showDetailModal = true;
    }

    async function handleReply() {
        if (!replyMsg.trim() || !selectedTicket) return;
        try {
            isReplying = true;
            const newMsg = await sendTicketMessage(selectedTicket.id, replyMsg);
            
            // Update local ticket messages
            const tIndex = tickets.findIndex((t: any) => t.id === selectedTicket.id);
            if (tIndex !== -1) {
                const updatedTickets = [...tickets];
                updatedTickets[tIndex].messages = [...updatedTickets[tIndex].messages, newMsg];
                tickets = updatedTickets;
                selectedTicket = updatedTickets[tIndex]; 
            }
            replyMsg = '';
        } catch(e) {
            console.error(e);
            alert("Error al enviar mensaje");
        } finally {
            isReplying = false;
        }
    }

    function getStatusClass(status: string) {
        switch (status) {
            case 'open': return 'badge-success';
            case 'pending': return 'badge-info';
            case 'resolved': return 'badge-warning';
            case 'closed': return 'badge-ghost opacity-50';
            default: return 'badge-neutral';
        }
    }

    async function handleSubmit() {
        if (!formData.asunto || !formData.descripcion) {
            errorMsg = "Por favor, completa todos los campos requeridos.";
            return;
        }

        try {
            isCreating = true;
            errorMsg = '';
            
            const newTicket = await createPortalTicket({
                asunto: formData.asunto,
                descripcion: formData.descripcion,
                prioridad: formData.prioridad
            });
            
            tickets = [newTicket, ...tickets];
            totalTickets++;
            
            // Cierra el modal y limpia el form
            showModal = false;
            formData = { asunto: '', descripcion: '', prioridad: 'normal' };
        } catch (err: any) {
            console.error(err);
            errorMsg = err.response?.data?.detail || "Ocurrió un error al crear el ticket.";
        } finally {
            isCreating = false;
        }
    }
</script>

<svelte:head>
	<title>Soporte Técnico | Portal de Clientes — OmniWISP</title>
</svelte:head>

<div class="space-y-8" in:fade={{ duration: 400 }}>
    <section class="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-base-300 pb-6">
        <div>
            <h1 class="text-4xl font-black tracking-tight mb-2">Soporte <span class="bg-gradient-to-r from-warning to-error bg-clip-text text-transparent">Técnico</span></h1>
            <p class="opacity-60 text-lg">Estamos aquí para ayudarte. Revisa tus solicitudes o abre una nueva.</p>
        </div>
        <button onclick={() => showModal = true} class="btn btn-warning rounded-xl shadow-lg shadow-warning/20 gap-2">
            <span class="text-xl">➕</span> Nuevo Ticket
        </button>
    </section>

    <!-- Filtros Rápidos -->
    <div class="flex justify-end pb-2">
        <select bind:value={statusFilter} class="select select-bordered select-sm w-full max-w-xs">
            <option value="Todos">Mostrar Todos</option>
            <option value="open">Abiertos</option>
            <option value="pending">En Proceso</option>
            <option value="resolved">Resueltos</option>
            <option value="closed">Cerrados</option>
        </select>
    </div>

    <!-- Lista de Tickets y Paginación -->
    <div class="relative bg-base-100/20 rounded-box p-1">
        {#if isFetchingPage}
            <div class="absolute inset-0 z-20 flex items-center justify-center bg-base-100/60 backdrop-blur-sm rounded-box">
                <span class="loading loading-spinner loading-lg text-primary"></span>
            </div>
        {/if}
        <!-- Contenedor con scroll para los tickets -->
        <div class="max-h-[450px] overflow-y-auto pr-2 custom-scrollbar">
            <div class="grid grid-cols-1 gap-4">
                {#each filteredTickets as ticket, i}
            <button 
                class="card bg-base-100 shadow-md border border-base-200 hover:border-primary/30 transition-all cursor-pointer group w-full text-left"
                in:fly={{ x: -20, delay: 100 * i }}
                onclick={() => openTicketDetail(ticket)}
            >
                <div class="p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 w-full">
                    <div class="flex items-start gap-4">
                        <div class="w-12 h-12 bg-base-200 rounded-2xl flex items-center justify-center text-2xl group-hover:bg-primary/10 transition-colors shrink-0">
                            {ticket.estado === 'closed' ? '✅' : '⏳'}
                        </div>
                        <div>
                            <div class="flex items-center gap-2 mb-1">
                                <span class="text-[10px] font-mono font-bold opacity-40">{ticket.id.slice(0,8)}</span>
                                <span class="badge {getStatusClass(ticket.estado)} badge-xs uppercase font-bold tracking-tighter">{ticket.estado}</span>
                            </div>
                            <h3 class="font-bold text-lg leading-tight group-hover:text-primary transition-colors">{ticket.asunto}</h3>
                        </div>
                    </div>
                    
                    <div class="flex items-center justify-end gap-3 shrink-0">
                        <div class="hidden md:block text-right">
                            <p class="text-[10px] uppercase font-bold opacity-30">Creado el</p>
                            <p class="text-xs font-medium">{new Date(ticket.fecha_creacion).toLocaleDateString()}</p>
                        </div>
                    </div>
                </div>
            </button>
                {/each}
            </div>
        </div>

        <!-- Controles de Paginación -->
        <div class="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 mt-2 bg-base-200/50 rounded-xl border border-base-300">
            <div class="flex items-center gap-2 text-sm font-medium opacity-80">
                <span>Mostrando</span>
                <select class="select select-bordered select-sm w-20" bind:value={currentLimit} onchange={() => loadPage(1, currentLimit)}>
                    <option value={10}>10</option>
                    <option value={20}>20</option>
                    <option value={50}>50</option>
                </select>
                <span>por pág.</span>
            </div>
            
            <div class="flex items-center gap-4">
                <span class="text-sm font-medium opacity-80">
                    Página {currentPage} de {totalPages} <span class="opacity-50 text-xs ml-1">({totalTickets} total)</span>
                </span>
                <div class="join shadow-sm border border-base-300">
                    <button class="join-item btn btn-sm bg-base-100 border-none hover:bg-base-300" disabled={currentPage === 1} onclick={() => loadPage(currentPage - 1, currentLimit)}>« Ant</button>
                    <button class="join-item btn btn-sm bg-base-100 border-none hover:bg-base-300" disabled={currentPage === totalPages} onclick={() => loadPage(currentPage + 1, currentLimit)}>Sig »</button>
                </div>
            </div>
        </div>
    </div>

    <!-- Ayuda Directa -->
    <div class="card bg-primary text-primary-content border-none overflow-hidden relative shadow-2xl shadow-primary/20" in:fade={{ delay: 500 }}>
        <!-- Decoración de fondo -->
        <div class="absolute -right-20 -top-20 w-64 h-64 bg-white/10 rounded-full blur-3xl"></div>
        <div class="absolute -left-20 -bottom-20 w-64 h-64 bg-black/10 rounded-full blur-3xl"></div>

        <div class="p-8 relative z-10 flex flex-col md:flex-row items-center gap-8">
            <div class="text-center md:text-left flex-1">
                <h2 class="text-3xl font-black mb-2">¿Problemas con tu conexión?</h2>
                <p class="text-primary-content/80 text-lg">Nuestro bot de Telegram está disponible 24/7 para pruebas de velocidad y reinicios remotos.</p>
            </div>
            <div class="flex flex-col sm:flex-row gap-4 w-full md:w-auto">
                <a href="https://t.me/{botUsername.replace('@','')}" target="_blank" class="btn btn-neutral rounded-xl px-8 gap-2 border-none">
                    <svg class="w-5 h-5 fill-current" viewBox="0 0 24 24"><path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.894 8.221l-1.97 9.28c-.145.658-.537.818-1.084.508l-3-2.21-1.446 1.394c-.14.14-.26.26-.54.26l.213-3.054 5.56-5.022c.24-.213-.053-.334-.374-.12l-6.873 4.33-2.955-.924c-.642-.204-.654-.642.134-.95l11.535-4.45c.533-.204 1 .116.84.808z"/></svg>
                    Abrir Telegram
                </a>
                <button 
                    class="btn btn-white bg-white text-primary hover:bg-white/90 border-none rounded-xl px-8 gap-2"
                    onclick={() => showVideoModal = true}
                >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
                    </svg>
                    📹 Llamar a Soporte
                </button>
            </div>
        </div>
    </div>
</div>

<!-- Modal para Nuevo Ticket -->
<dialog class="modal modal-bottom sm:modal-middle" class:modal-open={showModal}>
    <div class="modal-box p-0 overflow-hidden">
        <div class="bg-warning/10 p-6 border-b border-warning/20">
            <h3 class="font-black text-2xl flex items-center gap-2">
                <span class="text-warning">➕</span> Nuevo Ticket de Soporte
            </h3>
            <p class="text-sm opacity-60 mt-1">Describe tu problema y nuestro equipo te ayudará a la brevedad.</p>
        </div>
        
        <div class="p-6">
            {#if errorMsg}
                <div class="alert alert-error text-sm mb-4 py-2">
                    <span class="text-lg">❌</span>
                    <span>{errorMsg}</span>
                </div>
            {/if}

            <form onsubmit={(e) => { e.preventDefault(); handleSubmit(); }} class="space-y-4">
                <div class="flex flex-col gap-2 w-full">
                    <label for="asunto-select" class="font-bold text-sm ml-1 text-base-content/80">
                        Asunto *
                    </label>
                    <select 
                        id="asunto-select"
                        bind:value={formData.asunto}
                        class="select select-bordered w-full" 
                        required 
                        disabled={isCreating}
                    >
                        <option value="" disabled selected>Seleccione un asunto...</option>
                        <option value="Reportar falla">Reportar falla</option>
                        <option value="Soporte técnico">Soporte técnico</option>
                        <option value="Solicitar agente técnico">Solicitar agente técnico</option>
                        <option value="Cambio de password">Cambio de password</option>
                        <option value="Otro">Otro...</option>
                    </select>
                </div>
                
                <div class="flex flex-col gap-2 w-full mt-2">
                    <label for="descripcion-input" class="font-bold text-sm ml-1 text-base-content/80">
                        Descripción *
                    </label>
                    <textarea 
                        id="descripcion-input"
                        bind:value={formData.descripcion}
                        class="textarea textarea-bordered h-28 w-full block" 
                        placeholder="Por favor, detalla tu problema..."
                        required
                        disabled={isCreating}
                    ></textarea>
                </div>
                
                <div class="modal-action mt-6 gap-2">
                    <button type="button" class="btn btn-ghost" onclick={() => showModal = false} disabled={isCreating}>
                        Cancelar
                    </button>
                    <button type="submit" class="btn btn-warning gap-2" disabled={isCreating}>
                        {#if isCreating}
                            <span class="loading loading-spinner loading-sm"></span>
                            Creando...
                        {:else}
                            <span class="text-lg">📨</span> Enviar Ticket
                        {/if}
                    </button>
                </div>
            </form>
        </div>
    </div>
    <form method="dialog" class="modal-backdrop">
        <button onclick={() => showModal = false} disabled={isCreating}>close</button>
    </form>
</dialog>

<!-- Modal de Detalles del Ticket -->
<dialog class="modal modal-bottom sm:modal-middle" class:modal-open={showDetailModal}>
    <div class="modal-box p-0 overflow-hidden max-w-2xl flex flex-col h-[80vh]">
        {#if selectedTicket}
        <div class="bg-base-200 p-6 border-b border-base-300">
            <h3 class="font-black text-2xl mb-1">{selectedTicket.asunto}</h3>
            <div class="flex items-center gap-2 text-sm opacity-70">
                <span class="font-mono">#{selectedTicket.id.slice(0,8)}</span>
                <span>&bull;</span>
                <span>Creado el {new Date(selectedTicket.fecha_creacion).toLocaleDateString()}</span>
            </div>
            
            <div class="mt-6">
                <!-- Barra de progreso -->
                <ul class="steps w-full">
                    <li class="step step-primary">Abierto</li>
                    <li class="step {selectedTicket.estado === 'pending' || selectedTicket.estado === 'resolved' || selectedTicket.estado === 'closed' ? 'step-primary' : ''}">En Proceso</li>
                    <li class="step {selectedTicket.estado === 'closed' || selectedTicket.estado === 'resolved' ? 'step-primary' : ''}">Cerrado</li>
                </ul>
            </div>
            
            {#if selectedTicket.assigned_tech_name}
            <div class="mt-4 flex items-center gap-2 bg-info/10 text-info p-3 rounded-lg text-sm">
                <span>👨‍🔧</span>
                <span class="font-medium">Técnico asignado: <strong>{selectedTicket.assigned_tech_name}</strong></span>
            </div>
            {/if}
        </div>
        
        <div class="flex-1 overflow-y-auto p-6 space-y-6">
            <!-- Mensaje Inicial (Descripción del Ticket) -->
            <div class="chat chat-start">
                <div class="chat-header opacity-50 text-xs mb-1">
                    Tú
                    <time class="text-xs opacity-50 ml-1">{new Date(selectedTicket.fecha_creacion).toLocaleDateString()}</time>
                </div>
                <div class="chat-bubble chat-bubble-primary">{selectedTicket.descripcion}</div>
            </div>
            
            <!-- Resto de Mensajes -->
            {#each selectedTicket.messages || [] as msg}
                <div class="chat {msg.sender_type === 'client' ? 'chat-start' : 'chat-end'}">
                    <div class="chat-header opacity-50 text-xs mb-1">
                        {msg.sender_type === 'client' ? 'Tú' : (selectedTicket.assigned_tech_name || 'Soporte')}
                        <time class="text-xs opacity-50 ml-1">{new Date(msg.created_at).toLocaleDateString()}</time>
                    </div>
                    <div class="chat-bubble {msg.sender_type === 'client' ? 'chat-bubble-primary' : 'chat-bubble-info'}">
                        {msg.content}
                    </div>
                </div>
            {/each}
        </div>
        
        <div class="p-4 bg-base-200 border-t border-base-300">
            <form class="flex gap-2" onsubmit={(e) => { e.preventDefault(); handleReply(); }}>
                <input 
                    type="text" 
                    bind:value={replyMsg} 
                    placeholder="Escribe tu mensaje..." 
                    class="input input-bordered flex-1"
                    disabled={isReplying || selectedTicket.estado === 'closed'}
                />
                <button 
                    type="submit" 
                    class="btn btn-primary"
                    disabled={isReplying || !replyMsg.trim() || selectedTicket.estado === 'closed'}
                >
                    {#if isReplying}
                        <span class="loading loading-spinner loading-sm"></span>
                    {:else}
                        Enviar
                    {/if}
                </button>
            </form>
        </div>
        {/if}
    </div>
    <form method="dialog" class="modal-backdrop">
        <button onclick={() => showDetailModal = false}>close</button>
    </form>
</dialog>

<!-- Modal de Videollamada -->
<VideoCallModal bind:isOpen={showVideoModal} />

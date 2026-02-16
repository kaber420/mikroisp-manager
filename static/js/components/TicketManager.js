/**
 * Ticket Manager Component - Alpine.js
 * 
 * Manages the support ticket interface.
 * Handles listing, filtering, detail view, and replying.
 */
document.addEventListener('alpine:init', () => {
    Alpine.data('ticketManager', (config = {}) => ({
        // --- State ---
        tickets: [],
        loading: true,
        error: null,

        // Filters
        filterStatus: 'todos', // open, pending, resolved, closed, todos
        filterType: 'support', // support, installation
        searchQuery: '', // Added search query state

        // Pagination
        page: 0,
        pageSize: 20,
        totalTickets: 0,

        // Detailed View
        selectedTicket: null,
        showDetailModal: false,
        replyContent: '',
        sendingReply: false,

        // Creation
        showCreateModal: false,
        newTicket: {
            client_id: '',
            subject: '',
            description: '',
            priority: 'normal',
            ticket_type: 'support',
            scheduled_at: '',
            coordinates: '',
            address_notes: ''
        },
        searchClientQuery: '',
        clientSearchResults: [],
        creatingTicket: false,

        // Status Update
        updatingStatus: false,

        // Stats Modal
        showStatsModal: false,
        statsLoading: false,
        stats: {},
        _typeChart: null,
        _statusChart: null,

        // User Context
        currentUserId: null,
        currentUserName: null,

        // --- Lifecycle ---
        async init() {
            console.log('TicketManager initialized');

            // Watch for search query changes
            this.$watch('searchQuery', () => {
                this.page = 0;
                this.loadTickets();
            });

            // Watch for client search in create modal
            this.$watch('searchClientQuery', (value) => {
                if (value && value.length >= 2) {
                    this.searchClients(value);
                } else {
                    this.clientSearchResults = [];
                }
            });

            // 1. Initialize User from injected config
            if (config.currentUserId) {
                this.currentUserId = config.currentUserId;
                this.currentUserName = config.currentUserName;
                console.log('TicketManager: Initialized with User', this.currentUserId);
            } else {
                console.warn('TicketManager: No user ID provided in config');
            }

            await this.loadTickets();

            // Auto-refresh every 30s
            setInterval(() => {
                if (!this.showDetailModal) {
                    this.loadTickets(true); // Silent refresh
                }
            }, 30000);
            // 2. Listen for WebSocket updates (via ws-client.js)
            const self = this;
            window.addEventListener('data-refresh-needed', (e) => {
                const data = e.detail || {};
                console.log('🎫 TicketManager received data-refresh-needed event:', data);

                // Delay to ensure DB consistency across processes (bot -> web)
                setTimeout(() => {
                    if (self.showDetailModal && self.selectedTicket) {
                        // Strip dashes for robust UUID comparison (some clients send without dashes)
                        const currentId = String(self.selectedTicket.id).toLowerCase().replace(/-/g, '');
                        const incomingId = data.ticket_id ? String(data.ticket_id).toLowerCase().replace(/-/g, '') : null;

                        console.log('🎫 Comparing ticket IDs:', { currentId, incomingId, match: (!incomingId || incomingId === currentId) });

                        // If no ticket_id is provided, or it matches the active one, refresh chat
                        if (!incomingId || incomingId === currentId) {
                            console.log('🎫 Refreshing chat for matching ticket');
                            self.openTicket(self.selectedTicket);
                        } else {
                            // Different ticket updated, refresh background list
                            console.log('🎫 Different ticket updated, refreshing list only');
                            self.loadTickets(true);
                        }
                    } else {
                        console.log('🎫 No modal open, refreshing ticket list');
                        self.loadTickets(true);
                    }
                }, 1000);  // Increased delay for DB sync
            });

        },

        // --- Creation ---
        openCreateModal(type = 'support') {
            this.newTicket = {
                client_id: '',
                subject: '',
                description: '',
                priority: 'normal',
                ticket_type: type,
                scheduled_at: '',
                coordinates: '',
                address_notes: ''
            };
            this.searchClientQuery = '';
            this.clientSearchResults = [];
            this.showCreateModal = true;
        },

        closeCreateModal() {
            this.showCreateModal = false;
        },

        async searchClients(query) {
            try {
                // Assuming an endpoint for client search exists or using general search
                // Current `clients` endpoint usually supports search
                const response = await ApiService.fetchJSON(`/api/clients/?search=${query}&limit=5`);
                this.clientSearchResults = response.items || [];
            } catch (e) {
                console.error('Client search error', e);
            }
        },

        selectClient(client) {
            this.newTicket.client_id = client.id;
            this.searchClientQuery = client.name;
            this.clientSearchResults = []; // Hide dropdown
            // Auto-fill coordinates if available
            if (client.coordinates) {
                this.newTicket.coordinates = client.coordinates;
            }
        },

        async createTicket() {
            if (!this.newTicket.client_id || !this.newTicket.subject || !this.newTicket.description) {
                showToast('Please fill in all required fields', 'warning');
                return;
            }

            this.creatingTicket = true;
            try {
                // Clean empty strings to null for optional fields
                const payload = { ...this.newTicket };
                if (!payload.scheduled_at) payload.scheduled_at = null;
                if (!payload.coordinates) payload.coordinates = null;
                if (!payload.address_notes) payload.address_notes = null;

                await ApiService.fetchJSON('/api/tickets/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                showToast('Ticket created successfully', 'success');
                this.closeCreateModal();
                this.loadTickets(); // Refresh list
            } catch (e) {
                showToast(`Error creating ticket: ${e.message}`, 'danger');
            } finally {
                this.creatingTicket = false;
            }
        },

        // --- Data Loading ---
        async loadTickets(silent = false) {
            if (!silent) this.loading = true;
            try {
                const params = new URLSearchParams({
                    status_filter: this.filterStatus,
                    ticket_type: this.filterType,
                    limit: this.pageSize,
                    offset: this.page * this.pageSize,
                });

                if (this.searchQuery) {
                    params.append('search', this.searchQuery);
                }

                const response = await ApiService.fetchJSON(`/api/tickets/?${params}`);
                this.tickets = response.items || [];
                this.totalTickets = response.total || 0;
            } catch (e) {
                console.error('Error loading tickets:', e);
                this.error = e.message;
                if (!silent) showToast(`Error loading tickets: ${e.message}`, 'danger');
            } finally {
                if (!silent) this.loading = false;
            }
        },

        async refresh() {
            this.page = 0;
            await this.loadTickets();
        },

        nextPage() {
            if ((this.page + 1) * this.pageSize < this.totalTickets) {
                this.page++;
                this.loadTickets();
            }
        },

        prevPage() {
            if (this.page > 0) {
                this.page--;
                this.loadTickets();
            }
        },

        changePageSize(newSize) {
            this.pageSize = parseInt(newSize);
            this.page = 0; // Reset to first page
            this.loadTickets();
        },

        get totalPages() {
            return Math.ceil(this.totalTickets / this.pageSize);
        },

        get paginationInfo() {
            const start = this.page * this.pageSize + 1;
            const end = Math.min((this.page + 1) * this.pageSize, this.totalTickets);
            if (this.totalTickets === 0) return '0 - 0 of 0';
            return `${start} - ${end} of ${this.totalTickets}`;
        },

        setFilter(status) {
            this.filterStatus = status;
            this.refresh();
        },

        getFilterActiveClass(status) {
            switch (status) {
                case 'todos': return 'bg-primary text-white shadow-lg shadow-primary/20';
                case 'open': return 'bg-success text-white shadow-lg shadow-success/20';
                case 'pending': return 'bg-warning text-white shadow-lg shadow-warning/20';
                case 'resolved': return 'bg-primary text-white shadow-lg shadow-primary/20';
                case 'closed': return 'bg-surface-3 text-white border-white/20';
                default: return 'bg-primary text-white';
            }
        },

        // --- Ticket Detail ---
        async openTicket(ticket) {
            try {
                // Add cache-buster to ensure we get the latest messages immediately
                const fullTicket = await ApiService.fetchJSON(`/api/tickets/${ticket.id}?_t=${Date.now()}`);
                this.selectedTicket = fullTicket;
                this.showDetailModal = true;

                // Scroll to bottom of chat
                this.$nextTick(() => {
                    console.log('TicketManager: Scrolling to bottom');
                    this.scrollToBottom();
                });
            } catch (e) {
                showToast(`Error opening ticket: ${e.message}`, 'danger');
            }
        },

        closeTicket() {
            this.showDetailModal = false;
            this.selectedTicket = null;
            this.replyContent = '';
            // Refresh list to show read status or updates
            this.loadTickets(true);
        },

        // --- Actions ---

        async sendReply() {
            if (!this.replyContent.trim()) return;

            this.sendingReply = true;
            try {
                await ApiService.fetchJSON(`/api/tickets/${this.selectedTicket.id}/reply`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ content: this.replyContent })
                });

                this.replyContent = '';
                // Refresh detail
                await this.openTicket(this.selectedTicket); // Re-fetch
                showToast('Reply sent', 'success');
            } catch (e) {
                showToast(`Error sending reply: ${e.message}`, 'danger');
            } finally {
                this.sendingReply = false;
            }
        },

        async changeStatus(newStatus) {
            this.updatingStatus = true;
            try {
                await ApiService.fetchJSON(`/api/tickets/${this.selectedTicket.id}/status`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ status: newStatus })
                });

                this.selectedTicket.status = newStatus;

                // Update local ownership state based on status change
                if (newStatus === 'open') {
                    this.selectedTicket.assigned_tech_id = null;
                    this.selectedTicket.assigned_tech_username = null;
                } else if (!this.selectedTicket.assigned_tech_id && this.currentUserId) {
                    // Auto-claimed
                    this.selectedTicket.assigned_tech_id = this.currentUserId;
                    // We might want to set username too but we might not have it fully (email vs username loop)
                    // A Reload is safer
                    await this.openTicket(this.selectedTicket);
                    showToast(`Status updated to ${newStatus} (Auto-claimed)`, 'success');
                    return;
                }

                showToast(`Status updated to ${newStatus}`, 'success');
                // Optional: Close modal if resolved/closed?
                // this.closeTicket();
            } catch (e) {
                showToast(`Error updating status: ${e.message}`, 'danger');
            } finally {
                this.updatingStatus = false;
            }
        },

        async claimTicket() {
            // Claiming is essentially just assigning (or setting status to pending which triggers auto-claim)
            // Let's use status update to 'pending' as the "Take" action
            await this.changeStatus('pending');
        },

        // --- Computed/Helpers for UI ---

        isOwner() {
            if (!this.selectedTicket || !this.currentUserId) return false;
            return this.selectedTicket.assigned_tech_id === this.currentUserId;
        },

        isAssignedToOther() {
            if (!this.selectedTicket || !this.selectedTicket.assigned_tech_id) return false;
            return this.selectedTicket.assigned_tech_id !== this.currentUserId;
        },

        canReply() {
            // Can reply if I own it OR if it's unassigned (will auto-claim)
            if (!this.selectedTicket) return false;
            if (this.isAssignedToOther()) return false;
            return true;
        },

        canModifyStatus() {
            // Can modify if I own it OR if unassigned
            if (!this.selectedTicket) return false;
            if (this.isAssignedToOther()) return false;
            return true;
        },

        // --- Helpers ---
        formatDate(dateStr) {
            if (!dateStr) return '';
            return new Date(dateStr).toLocaleString();
        },

        getStatusColor(status) {
            switch (status) {
                case 'open': return 'bg-success/20 text-success border-success/30';
                case 'pending': return 'bg-warning/20 text-warning border-warning/30';
                case 'resolved': return 'bg-primary/20 text-primary border-primary/30';
                case 'closed': return 'bg-surface-2 text-text-secondary border-white/10';
                default: return 'bg-surface-2';
            }
        },

        scrollToBottom() {
            const container = document.getElementById('messages-container');
            if (container) {
                container.scrollTop = container.scrollHeight;
            }
        },

        getDisplayId(ticket) {
            if (!ticket) return '';
            if (ticket.ticket_id && ticket.ticket_id > 0) return '#' + ticket.ticket_id;
            return '#' + (ticket.id ? ticket.id.slice(-6) : '??????');
        },

        // --- Stats ---
        async openStatsModal() {
            this.showStatsModal = true;
            await this.loadStats();
        },

        async loadStats() {
            this.statsLoading = true;
            try {
                const data = await ApiService.fetchJSON('/api/stats/tickets');
                this.stats = data;
                // Wait for DOM to update, then render charts
                this.$nextTick(() => {
                    this.renderTypeChart(data);
                    this.renderStatusChart(data);
                });
            } catch (e) {
                console.error('Error loading stats:', e);
                showToast('Error loading stats', 'danger');
            } finally {
                this.statsLoading = false;
            }
        },

        renderTypeChart(data) {
            const canvas = document.getElementById('statsChartTypes');
            if (!canvas) return;
            const ctx = canvas.getContext('2d');
            if (this._typeChart) this._typeChart.destroy();
            this._typeChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['Support', 'Installation'],
                    datasets: [{
                        data: [data.support_tickets || 0, data.installation_tickets || 0],
                        backgroundColor: [
                            'rgba(59, 130, 246, 0.8)',
                            'rgba(16, 185, 129, 0.8)'
                        ],
                        borderColor: 'rgba(255, 255, 255, 0.1)',
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: { color: '#9ca3af', font: { family: 'Inter' } }
                        }
                    }
                }
            });
        },

        renderStatusChart(data) {
            const canvas = document.getElementById('statsChartStatus');
            if (!canvas) return;
            const ctx = canvas.getContext('2d');
            if (this._statusChart) this._statusChart.destroy();
            this._statusChart = new Chart(ctx, {
                type: 'pie',
                data: {
                    labels: ['Open', 'Pending', 'Resolved'],
                    datasets: [{
                        data: [data.open_tickets || 0, data.pending_tickets || 0, data.resolved_tickets || 0],
                        backgroundColor: [
                            'rgba(16, 185, 129, 0.8)',
                            'rgba(245, 158, 11, 0.8)',
                            'rgba(59, 130, 246, 0.8)'
                        ],
                        borderColor: 'rgba(255, 255, 255, 0.1)',
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: { color: '#9ca3af', font: { family: 'Inter' } }
                        }
                    }
                }
            });
        }
    }));
});

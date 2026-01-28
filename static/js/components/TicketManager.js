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
        filterStatus: 'open', // open, pending, resolved, closed, todos
        searchQuery: '', // Added search query state
        page: 0,
        hasMore: true,

        // Detailed View
        selectedTicket: null,
        showDetailModal: false,
        replyContent: '',
        sendingReply: false,

        // Status Update
        updatingStatus: false,

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
        },

        // --- Data Loading ---
        async loadTickets(silent = false) {
            if (!silent) this.loading = true;
            try {
                const params = new URLSearchParams({
                    status_filter: this.filterStatus,
                    limit: 50,
                    offset: this.page * 50
                });

                if (this.searchQuery) {
                    params.append('search', this.searchQuery);
                }

                const response = await ApiService.fetchJSON(`/api/tickets/?${params}`);
                this.tickets = response || [];
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
                // Fetch full details (messages might be loaded lazily or we just refresh)
                const fullTicket = await ApiService.fetchJSON(`/api/tickets/${ticket.id}`);
                this.selectedTicket = fullTicket;
                this.showDetailModal = true;

                // Scroll to bottom of chat
                this.$nextTick(() => {
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
            // If ticket_id is present and not 0, use it (though backend sends 0 mostly)
            if (ticket.ticket_id && ticket.ticket_id > 0) return '#' + ticket.ticket_id;
            // Otherwise use last 6 of UUID
            return '#' + (ticket.id ? ticket.id.slice(-6) : '??????');
        }
    }));
});

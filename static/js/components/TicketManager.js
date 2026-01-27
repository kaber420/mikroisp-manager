/**
 * Ticket Manager Component - Alpine.js
 * 
 * Manages the support ticket interface.
 * Handles listing, filtering, detail view, and replying.
 */
document.addEventListener('alpine:init', () => {
    Alpine.data('ticketManager', () => ({
        // --- State ---
        tickets: [],
        loading: true,
        error: null,

        // Filters
        filterStatus: 'open', // open, pending, resolved, closed, todos
        page: 0,
        hasMore: true,

        // Detailed View
        selectedTicket: null,
        showDetailModal: false,
        replyContent: '',
        sendingReply: false,

        // Status Update
        updatingStatus: false,

        // --- Lifecycle ---
        async init() {
            console.log('TicketManager initialized');
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
                showToast(`Status updated to ${newStatus}`, 'success');
                // Optional: Close modal if resolved/closed?
                // this.closeTicket();
            } catch (e) {
                showToast(`Error updating status: ${e.message}`, 'danger');
            } finally {
                this.updatingStatus = false;
            }
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

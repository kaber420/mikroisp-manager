/**
 * AuditLogs.js
 * Alpine.js component for audit logs table with pagination and filtering
 */

document.addEventListener('alpine:init', () => {
    Alpine.data('auditLogs', () => ({
        // State
        logs: [],
        isLoading: false,
        page: 1,
        pageSize: 20,
        totalPages: 1,
        totalRecords: 0,
        actionFilter: 'all',
        userFilter: 'all',
        actions: [],
        usernames: [],
        initialized: false,

        // Computed properties
        get paginationInfo() {
            if (this.totalRecords === 0) return 'Sin resultados';
            const start = (this.page - 1) * this.pageSize + 1;
            const end = Math.min(start + this.pageSize - 1, this.totalRecords);
            return `Mostrando ${start}-${end} de ${this.totalRecords}`;
        },

        get prevDisabled() {
            return this.page <= 1;
        },

        get nextDisabled() {
            return this.page >= this.totalPages;
        },

        // Initialize component (called when tab is activated)
        async init() {
            if (!this.initialized) {
                await this.loadFilters();
                await this.loadLogs();
                this.initialized = true;
            }
        },

        // Load filter options
        async loadFilters() {
            try {
                const res = await fetch(`${window.location.origin}/api/settings/audit-logs/filters`);
                if (!res.ok) return;

                const filters = await res.json();
                this.actions = filters.actions || [];
                this.usernames = filters.usernames || [];
            } catch (e) {
                console.error('Error loading audit filters:', e);
            }
        },

        // Load current page of logs
        async loadLogs() {
            this.isLoading = true;

            try {
                let url = `${window.location.origin}/api/settings/audit-logs?page=${this.page}&page_size=${this.pageSize}`;
                if (this.actionFilter !== 'all') url += `&action=${encodeURIComponent(this.actionFilter)}`;
                if (this.userFilter !== 'all') url += `&username=${encodeURIComponent(this.userFilter)}`;

                const res = await fetch(url);
                if (!res.ok) {
                    throw new Error('Failed to load audit logs');
                }

                const data = await res.json();
                this.logs = data.items || [];
                this.totalPages = data.total_pages || 1;
                this.totalRecords = data.total || 0;

            } catch (error) {
                console.error('Error loading audit logs:', error);
                this.logs = [];
            } finally {
                this.isLoading = false;
            }
        },

        // Apply filters (reset to page 1)
        async applyFilters() {
            this.page = 1;
            await this.loadLogs();
        },

        // Change page size
        async changePageSize(size) {
            this.pageSize = parseInt(size);
            this.page = 1;
            await this.loadLogs();
        },

        // Navigate pages
        async changePage(direction) {
            const newPage = this.page + direction;
            if (newPage > 0 && newPage <= this.totalPages) {
                this.page = newPage;
                await this.loadLogs();
            }
        },

        // Refresh current page
        async refresh() {
            await this.loadLogs();
        },

        // Format timestamp
        formatTime(timestamp) {
            const dateObj = new Date(timestamp);
            return dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        },

        formatDate(timestamp) {
            const dateObj = new Date(timestamp);
            return dateObj.toLocaleDateString();
        },

        // Get action badge color
        getActionColor(action) {
            const actionColors = {
                'DELETE': 'text-danger bg-danger/10 border-danger/20',
                'CREATE': 'text-success bg-success/10 border-success/20',
                'UPDATE': 'text-warning bg-warning/10 border-warning/20',
                'LOGIN': 'text-primary bg-primary/10 border-primary/20',
            };
            return actionColors[action] || 'text-text-secondary bg-surface-2 border-white/10';
        }
    }));
});

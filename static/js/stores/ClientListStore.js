/**
 * Client List Store - Alpine.js Global Store
 * Manages the client list state and filtering.
 */
document.addEventListener('alpine:init', () => {
    Alpine.store('clientList', {
        // --- State ---
        clients: [],
        isLoading: true,
        filters: {
            search: '',
            status: 'all'
        },
        pagination: {
            page: 1,
            pageSize: 10,
            total: 0,
            totalPages: 1
        },

        // --- Computed ---
        get filteredClients() {
            // Filtering is now done server-side
            return this.clients;
        },

        // --- Actions ---
        async loadClients() {
            this.isLoading = true;
            try {
                const params = new URLSearchParams({
                    page: this.pagination.page,
                    page_size: this.pagination.pageSize
                });

                if (this.filters.search) {
                    params.append('search', this.filters.search);
                }
                if (this.filters.status && this.filters.status !== 'all') {
                    params.append('status', this.filters.status);
                }

                const response = await fetch(`/api/clients?${params.toString()}`);
                if (!response.ok) throw new Error('Network response was not ok');

                const data = await response.json();
                this.clients = data.items;
                this.pagination.total = data.total;
                this.pagination.totalPages = data.total_pages;

            } catch (error) {
                console.error('Failed to load clients', error);
                if (window.showToast) window.showToast('Error: Could not load clients.', 'danger');
            } finally {
                this.isLoading = false;
            }
        },

        setPage(page) {
            if (page < 1 || page > this.pagination.totalPages) return;
            this.pagination.page = page;
            this.loadClients();
        },

        setPageSize(size) {
            this.pagination.pageSize = size;
            this.pagination.page = 1; // Reset to first page
            this.loadClients();
        },

        removeClient(id) {
            // Reload to keep pagination sync or just remove locally? 
            // Better to just remove locally for responsiveness, but count will be off. 
            // For now, simple remove locally is fine as per original code.
            this.clients = this.clients.filter(c => c.id !== id);
        },

        updateClient(updatedClient) {
            const index = this.clients.findIndex(c => c.id === updatedClient.id);
            if (index !== -1) {
                this.clients[index] = updatedClient;
            } else {
                this.clients.unshift(updatedClient);
            }
        }
    });
});

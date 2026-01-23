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

        // --- Computed ---
        get filteredClients() {
            return this.clients.filter(client => {
                const term = this.filters.search.toLowerCase();
                const statusMatch = this.filters.status === 'all' || client.service_status === this.filters.status;
                const searchMatch = !term ||
                    client.name.toLowerCase().includes(term) ||
                    (client.address && client.address.toLowerCase().includes(term)) ||
                    (client.phone_number && client.phone_number.includes(term));
                return statusMatch && searchMatch;
            });
        },

        // --- Actions ---
        async loadClients() {
            this.isLoading = true;
            try {
                this.clients = await (await fetch('/api/clients')).json();
            } catch (error) {
                console.error('Failed to load clients', error);
                if (window.showToast) window.showToast('Error: Could not load clients.', 'danger');
            } finally {
                this.isLoading = false;
            }
        },

        removeClient(id) {
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

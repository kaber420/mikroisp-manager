document.addEventListener('alpine:init', () => {
    Alpine.data('clientList', () => ({
        // --- Getters to access Store ---
        get clients() { return Alpine.store('clientList').filteredClients; },
        get isLoading() { return Alpine.store('clientList').isLoading; },

        // --- Filters binding ---
        get searchQuery() { return Alpine.store('clientList').filters.search; },
        set searchQuery(val) {
            Alpine.store('clientList').filters.search = val;

            // Only search if empty (reset) or >= 3 chars
            if (val.length === 0 || val.length >= 3) {
                Alpine.store('clientList').pagination.page = 1;
                Alpine.store('clientList').loadClients();
            }
        },

        get statusFilter() { return Alpine.store('clientList').filters.status; },
        set statusFilter(val) {
            Alpine.store('clientList').filters.status = val;
            Alpine.store('clientList').pagination.page = 1;
            Alpine.store('clientList').loadClients();
        },

        // --- Pagination ---
        get pagination() { return Alpine.store('clientList').pagination; },
        setPage(page) { Alpine.store('clientList').setPage(page); },
        setPageSize(size) { Alpine.store('clientList').setPageSize(size); },

        init() {
            Alpine.store('clientList').loadClients();

            // Listen for refreshes
            window.addEventListener('data-refresh-needed', () => {
                console.log("⚡ Clients: Reloading list...");
                Alpine.store('clientList').loadClients();
            });
        },

        getStatusBadgeClass(status) {
            return {
                'active': 'bg-success/20 text-success',
                'pendiente': 'bg-warning/20 text-warning',
                'suspended': 'bg-danger/20 text-danger',
                'cancelled': 'bg-surface-2 text-text-secondary'
            }[status] || 'bg-surface-2 text-text-secondary';
        },

        async deleteClient(clientId, clientName) {
            const confirmed = await window.ModalUtils.showConfirmModal({
                title: 'Delete Client',
                message: `Are you sure you want to delete client "<strong>${clientName}</strong>"?`,
                confirmText: 'Delete Client',
                confirmIcon: 'delete',
                type: 'danger',
            });

            if (!confirmed) return;

            try {
                const response = await fetch(`/api/clients/${clientId}`, { method: 'DELETE' });
                if (!response.ok) throw new Error((await response.json()).detail);

                Alpine.store('clientList').removeClient(clientId);
                if (window.showToast) window.showToast('Client deleted successfully', 'success');
            } catch (error) {
                if (window.showToast) window.showToast(`Error: ${error.message}`, 'danger');
            }
        }
    }));
});

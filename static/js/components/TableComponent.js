export class TableComponent {
    /**
     * @param {Object} config Configuration object for the table
     * @param {string[]} config.columns Array of column definitions
     * @param {Function} config.renderRow Function to render a single row (returns HTML string)
     * @param {string} [config.emptyMessage] Message to show when no data is present
     * @param {string} [config.tableClass] Custom class for the table element
     */
    constructor(config) {
        this.columns = config.columns || [];
        this.renderRow = config.renderRow;
        this.emptyMessage = config.emptyMessage || 'No data available';
        this.tableClass = config.tableClass || 'std-table';
        this.onAction = config.onAction || (() => { }); // Callback for actions
    }

    /**
     * Renders the table with the given data
     * @param {Array} data Array of data items
     * @param {HTMLElement} container Container element to render the table into
     */
    render(data, container) {
        if (!container) {
            console.error('TableComponent: Container not provided');
            return;
        }

        container.innerHTML = '';

        if (!data || data.length === 0) {
            container.innerHTML = this._buildEmptyState();
            return;
        }

        const table = document.createElement('table');
        table.className = this.tableClass;

        // Header
        const thead = document.createElement('thead');
        thead.innerHTML = `
            <tr>
                ${this.columns.map(col => `<th class="std-th">${col}</th>`).join('')}
            </tr>
        `;
        table.appendChild(thead);

        // Body
        const tbody = document.createElement('tbody');
        tbody.innerHTML = data.map(item => this.renderRow(item)).join('');
        table.appendChild(tbody);

        container.appendChild(table);

        // Attach event listeners for actions
        this._attachEventListeners(tbody);
    }

    _buildEmptyState() {
        return `
            <div class="p-8 text-center text-text-secondary bg-surface-2/30 rounded-lg border border-dashed border-border-color">
                <p>${this.emptyMessage}</p>
            </div>
        `;
    }

    _attachEventListeners(tbody) {
        tbody.addEventListener('click', (e) => {
            const btn = e.target.closest('button[data-action]');
            if (!btn) return;

            e.preventDefault();
            const action = btn.dataset.action;
            const id = btn.dataset.id;
            // Collect all data attributes
            const payload = { ...btn.dataset };

            this.onAction(action, payload);
        });
    }
}

/**
 * Toast Notification System
 * Uses Alpine.js store for reactive toast management.
 */

document.addEventListener('alpine:init', () => {
    Alpine.store('toasts', {
        items: [],
        
        /**
         * Show a toast notification
         * @param {string} message - The message to display
         * @param {string} type - 'success', 'danger', 'warning', or 'primary'
         * @param {number} duration - Duration in ms (default 3500)
         */
        show(message, type = 'primary', duration = 3500) {
            const id = Date.now();
            this.items.push({ id, message, type });
            
            setTimeout(() => {
                this.remove(id);
            }, duration);
        },
        
        remove(id) {
            this.items = this.items.filter(t => t.id !== id);
        }
    });
});

/**
 * Global helper function to show a toast from anywhere in the app.
 * @param {string} message - The message to display
 * @param {string} type - 'success', 'danger', 'warning', or 'primary'
 * @param {number} duration - Duration in ms (default 3500)
 */
window.showToast = function(message, type = 'primary', duration = 3500) {
    // Ensure Alpine is loaded
    if (typeof Alpine !== 'undefined' && Alpine.store('toasts')) {
        Alpine.store('toasts').show(message, type, duration);
    } else {
        // Fallback if Alpine isn't ready yet
        console.warn('Toast system not ready, using console:', message);
    }
};

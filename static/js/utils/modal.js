// static/js/utils/modal.js

/**
 * Shared Modal Utilities
 * Provides reusable modal functions for consistent UI across the application
 * Styled to match the router_details aesthetic (backdrop blur, surface colors, animations)
 */
window.ModalUtils = {
    /**
     * Show a confirmation modal with customizable options
     * @param {Object} options - Modal configuration
     * @param {string} options.title - Modal title (default: 'Confirmar Acción')
     * @param {string} options.message - Message to display
     * @param {string} options.confirmText - Confirm button text (default: 'Confirmar')
     * @param {string} options.cancelText - Cancel button text (default: 'Cancelar')
     * @param {string} options.confirmIcon - Material icon for confirm button (default: 'check')
     * @param {string} options.type - Modal type: 'danger', 'warning', 'info' (default: 'danger')
     * @returns {Promise<boolean>} - true if confirmed, false if cancelled
     */
    showConfirmModal(options = {}) {
        return new Promise((resolve) => {
            const {
                title = 'Confirmar Acción',
                message = '¿Estás seguro?',
                confirmText = 'Confirmar',
                cancelText = 'Cancelar',
                confirmIcon = 'check',
                type = 'danger'
            } = options;

            // Remove existing modal if present
            const existingModal = document.getElementById('confirm-modal');
            if (existingModal) existingModal.remove();

            // Type-based styling
            const typeStyles = {
                danger: {
                    icon: 'warning',
                    iconColor: 'text-danger',
                    btnBg: 'bg-danger/10',
                    btnText: 'text-danger',
                    btnHoverBg: 'hover:bg-danger',
                    btnHoverText: 'hover:text-white'
                },
                warning: {
                    icon: 'warning',
                    iconColor: 'text-warning',
                    btnBg: 'bg-warning/10',
                    btnText: 'text-warning',
                    btnHoverBg: 'hover:bg-warning',
                    btnHoverText: 'hover:text-white'
                },
                info: {
                    icon: 'info',
                    iconColor: 'text-primary',
                    btnBg: 'bg-primary/10',
                    btnText: 'text-primary',
                    btnHoverBg: 'hover:bg-primary',
                    btnHoverText: 'hover:text-white'
                }
            };

            const style = typeStyles[type] || typeStyles.danger;

            const modalHtml = `
            <div id="confirm-modal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
                <div class="bg-surface-1 rounded-xl shadow-2xl max-w-md w-full border border-border overflow-hidden animate-in fade-in zoom-in duration-200">
                    <!-- Header -->
                    <div class="p-4 border-b border-border flex justify-between items-center bg-surface-2">
                        <h3 class="text-lg font-semibold text-text-primary flex items-center gap-2">
                            <span class="material-symbols-outlined ${style.iconColor}">${style.icon}</span>
                            ${title}
                        </h3>
                        <button id="confirm-modal-close-x" class="text-text-secondary hover:text-text-primary transition-colors">
                            <span class="material-symbols-outlined">close</span>
                        </button>
                    </div>
                    
                    <!-- Body -->
                    <div class="p-6">
                        <p class="text-text-secondary">${message}</p>
                    </div>
                    
                    <!-- Footer -->
                    <div class="p-4 border-t border-border bg-surface-2 flex justify-end gap-3">
                        <button id="confirm-modal-cancel" class="modal-btn modal-btn-cancel">
                            ${cancelText}
                        </button>
                        <button id="confirm-modal-confirm" class="modal-btn ${type === 'danger' ? 'modal-btn-danger' : type === 'warning' ? 'modal-btn-danger' : 'modal-btn-secondary'}">
                            <span class="material-symbols-outlined text-sm">${confirmIcon}</span>
                            ${confirmText}
                        </button>
                    </div>
                </div>
            </div>
            `;

            document.body.insertAdjacentHTML('beforeend', modalHtml);

            const modal = document.getElementById('confirm-modal');

            const cleanup = (result) => {
                modal.remove();
                resolve(result);
            };

            // Event listeners
            document.getElementById('confirm-modal-cancel').onclick = () => cleanup(false);
            document.getElementById('confirm-modal-close-x').onclick = () => cleanup(false);
            document.getElementById('confirm-modal-confirm').onclick = () => cleanup(true);

            // Close on backdrop click
            modal.addEventListener('click', (e) => {
                if (e.target === modal) cleanup(false);
            });

            // Close on Escape key
            const handleEscape = (e) => {
                if (e.key === 'Escape') {
                    document.removeEventListener('keydown', handleEscape);
                    cleanup(false);
                }
            };
            document.addEventListener('keydown', handleEscape);

            // Focus confirm button for accessibility
            document.getElementById('confirm-modal-confirm').focus();
        });
    },

    /**
     * Show a custom modal with custom content
     * @param {Object} options - Modal configuration
     * @param {string} options.title - Modal title
     * @param {string|HTMLElement} options.content - HTML content or element to display in modal body
     * @param {Array<Object>} options.actions - Array of action buttons { text, icon, handler, primary, danger, className }
     * @param {string} options.size - Modal size: 'sm', 'md', 'lg', 'xl' (default: 'md')
     * @param {string} options.modalId - Custom modal ID (default: 'custom-modal')
     * @returns {Object} - { close: function } to manually close the modal
     */
    showCustomModal(options = {}) {
        const {
            title = 'Modal',
            content = '',
            actions = [],
            size = 'md',
            modalId = 'custom-modal'
        } = options;

        // Remove existing modal if present
        const existingModal = document.getElementById(modalId);
        if (existingModal) existingModal.remove();

        // Size mapping
        const sizeClasses = {
            sm: 'max-w-md',
            md: 'max-w-lg',
            lg: 'max-w-2xl',
            xl: 'max-w-4xl'
        };

        const sizeClass = sizeClasses[size] || sizeClasses.md;

        // Build actions HTML
        let actionsHtml = '';
        if (actions.length > 0) {
            const actionButtons = actions.map((action, index) => {
                const buttonClass = action.className ||
                    (action.primary ? 'modal-btn modal-btn-primary' :
                        action.danger ? 'modal-btn modal-btn-danger' :
                            'modal-btn modal-btn-cancel');

                const icon = action.icon ? `<span class="material-symbols-outlined text-lg">${action.icon}</span>` : '';

                return `<button id="${modalId}-action-${index}" class="${buttonClass}">
                    ${icon}
                    ${action.text}
                </button>`;
            }).join('');

            actionsHtml = `
                <div class="p-4 border-t border-border flex justify-end gap-3 bg-surface-2">
                    ${actionButtons}
                </div>
            `;
        }

        const modalHtml = `
        <div id="${modalId}" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
            <div class="bg-surface-1 rounded-xl shadow-2xl w-full ${sizeClass} border border-border flex flex-col max-h-[90vh] overflow-hidden animate-in fade-in zoom-in duration-200">
                <div class="p-4 border-b border-border flex justify-between items-center bg-surface-2">
                    <h3 class="text-lg font-bold text-text-primary">${title}</h3>
                    <button id="${modalId}-close" class="text-text-secondary hover:text-text-primary transition-colors">
                        <span class="material-symbols-outlined">close</span>
                    </button>
                </div>
                <div class="flex-1 overflow-auto" id="${modalId}-content">
                    ${typeof content === 'string' ? content : ''}
                </div>
                ${actionsHtml}
            </div>
        </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHtml);

        const modal = document.getElementById(modalId);
        const contentContainer = document.getElementById(`${modalId}-content`);

        // If content is an HTMLElement, append it
        if (content instanceof HTMLElement) {
            contentContainer.innerHTML = '';
            contentContainer.appendChild(content);
        }

        const cleanup = () => {
            modal.remove();
        };

        // Close button
        document.getElementById(`${modalId}-close`).onclick = cleanup;

        // Action handlers
        actions.forEach((action, index) => {
            const button = document.getElementById(`${modalId}-action-${index}`);
            if (button && action.handler) {
                button.onclick = () => {
                    action.handler();
                    if (action.closeOnClick !== false) {
                        cleanup();
                    }
                };
            }
        });

        // Close on backdrop click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) cleanup();
        });

        // Close on Escape key
        const handleEscape = (e) => {
            if (e.key === 'Escape') {
                document.removeEventListener('keydown', handleEscape);
                cleanup();
            }
        };
        document.addEventListener('keydown', handleEscape);

        return { close: cleanup };
    },

    /**
     * Show a conflict modal for file duplication scenarios
     * @param {string} filename - Name of the conflicting file
     * @param {string} type - Type of file (backup, export, etc.)
     * @param {Function} callback - (action) => void. action can be 'overwrite', 'copy'
     */
    showConflictModal(filename, type, callback) {
        const existingModal = document.getElementById('conflict-modal');
        if (existingModal) existingModal.remove();

        const modalHtml = `
        <div id="conflict-modal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
            <div class="bg-surface-1 rounded-xl shadow-2xl max-w-md w-full border border-border overflow-hidden animate-in fade-in zoom-in duration-200">
                <!-- Header -->
                <div class="p-4 border-b border-border flex justify-between items-center bg-surface-2">
                    <h3 class="text-lg font-semibold text-text-primary flex items-center gap-2">
                        <span class="material-symbols-outlined text-warning">warning</span>
                        Archivo Existente
                    </h3>
                    <button id="btn-cancel-x" class="text-text-secondary hover:text-text-primary transition-colors">
                        <span class="material-symbols-outlined">close</span>
                    </button>
                </div>
                
                <!-- Body -->
                <div class="p-6">
                    <p class="text-text-secondary mb-4">
                        El archivo <span class="font-bold text-text-primary">"${filename}"</span> ya existe en el router.
                    </p>
                    <p class="text-sm text-text-tertiary">
                        ¿Deseas sobrescribirlo o crear una copia con un nuevo nombre?
                    </p>
                </div>
                
                <!-- Footer -->
                <div class="p-4 border-t border-border bg-surface-2 flex justify-end gap-3">
                    <button id="btn-cancel" class="modal-btn modal-btn-cancel">
                        Cancelar
                    </button>
                    <button id="btn-copy" class="modal-btn modal-btn-secondary">
                        <span class="material-symbols-outlined text-sm">filter_none</span>
                        Crear Copia
                    </button>
                    <button id="btn-overwrite" class="modal-btn modal-btn-danger">
                        <span class="material-symbols-outlined text-sm">save_as</span>
                        Sobrescribir
                    </button>
                </div>
            </div>
        </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHtml);

        const modal = document.getElementById('conflict-modal');
        const cleanup = () => modal.remove();

        document.getElementById('btn-cancel').onclick = cleanup;
        document.getElementById('btn-cancel-x').onclick = cleanup;

        document.getElementById('btn-copy').onclick = () => {
            callback('copy');
            cleanup();
        };

        document.getElementById('btn-overwrite').onclick = () => {
            callback('overwrite');
            cleanup();
        };

        // Close on backdrop click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) cleanup();
        });

        // Close on Escape key
        const handleEscape = (e) => {
            if (e.key === 'Escape') {
                document.removeEventListener('keydown', handleEscape);
                cleanup();
            }
        };
        document.addEventListener('keydown', handleEscape);
    }
};

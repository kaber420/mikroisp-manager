/**
 * Unified SSL Security Badge & Provisioning Component
 * 
 * Handles:
 * 1. Displaying SSL status (Badge)
 * 2. Creating/Injecting the Configuration Modal
 * 3. Handling Provisioning Logic for Routers, APs, and Switches
 */

export class SslBadge {
    constructor(config) {
        this.elementId = config.elementId || 'ssl-security-badge';
        this.deviceType = config.deviceType; // 'routers', 'aps', 'switches'
        this.host = config.host;
        this.element = document.getElementById(this.elementId);

        // Ensure modal exists
        this.modalId = 'ssl-modal-shared';
        this.injectModal();

        // Bind methods
        this.openModal = this.openModal.bind(this);
        this.closeModal = this.closeModal.bind(this);
        this.handleProvision = this.handleProvision.bind(this);
    }

    async init() {
        if (!this.element) {
            console.warn(`SslBadge: Element #${this.elementId} not found`);
            return;
        }

        // Add click listener to badge
        this.element.addEventListener('click', this.openModal);

        this.setLoading();
        await this.refresh();
    }

    setLoading() {
        if (!this.element) return;
        this.element.classList.remove('hidden');
        this.element.innerHTML = '<span class="animate-pulse">...</span>';
        this.element.className = 'text-xs font-semibold px-2 py-1 rounded-full bg-gray-600 text-white cursor-wait';
        this.element.title = 'Cargando estado SSL...';
    }

    async refresh() {
        try {
            const response = await fetch(`/api/${this.deviceType}/${this.host}/ssl/status`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const status = await response.json();
            this.render(status);
        } catch (e) {
            console.error('SslBadge: Error fetching status', e);
            this.renderError();
        }
    }

    render(status) {
        if (!this.element) return;
        this.element.classList.remove('hidden');

        if (!status || status.status === 'not_applicable') {
            // Hide if not applicable
            this.element.classList.add('hidden');
            return;
        }

        if (!status.ssl_enabled) {
            this.element.textContent = '🔴 INSEGURO';
            this.element.className = 'text-xs font-semibold px-2 py-1 rounded-full bg-red-600 text-white cursor-pointer hover:bg-red-700 shadow-sm';
            this.element.title = 'SSL no habilitado. Click para configurar.';
        } else if (status.is_trusted) {
            this.element.textContent = '🟢 SEGURO';
            this.element.className = 'text-xs font-semibold px-2 py-1 rounded-full bg-green-600 text-white cursor-pointer hover:bg-green-700 shadow-sm';
            this.element.title = `SSL Activo y Confiable (${status.certificate_name})`;
        } else {
            this.element.textContent = '🟡 AUTO-FIRMADO';
            this.element.className = 'text-xs font-semibold px-2 py-1 rounded-full bg-yellow-600 text-white cursor-pointer hover:bg-yellow-700 shadow-sm';
            this.element.title = 'SSL Auto-firmado. Click para corregir.';
        }
    }

    renderError() {
        if (!this.element) return;
        this.element.textContent = '⚠️ Error SSL';
        this.element.className = 'text-xs font-semibold px-2 py-1 rounded-full bg-gray-500 text-white cursor-pointer';
    }

    // --- Modal Logic ---

    injectModal() {
        if (document.getElementById(this.modalId)) return; // Already injected

        const modalHtml = `
        <div id="${this.modalId}" class="fixed inset-0 bg-black bg-opacity-50 z-50 hidden items-center justify-center">
            <div class="bg-surface-1 rounded-lg shadow-xl w-full max-w-md mx-4">
                <div class="p-6 border-b border-border-color flex justify-between items-center">
                    <h4 class="text-xl font-bold">Configurar SSL/TLS</h4>
                    <button type="button" class="close-modal-btn text-text-secondary hover:text-text-primary text-2xl">&times;</button>
                </div>
                <div class="p-6">
                    <form id="ssl-provision-form-shared">
                        <div class="mb-4">
                            <label class="block text-sm font-medium mb-2">Método de Generación</label>
                            <select name="method" class="w-full bg-background border border-border-color rounded-md p-2">
                                <option value="router-side">🔒 Router-Side (Recomendado)</option>
                                <option value="server-side">🖥️ Server-Side (Fallback)</option>
                            </select>
                            <p class="text-xs text-text-secondary mt-1">
                                Router-Side: La clave privada nunca sale del dispositivo.
                            </p>
                        </div>
                        <div class="mb-4">
                            <label class="flex items-center gap-2 cursor-pointer">
                                <input type="checkbox" name="install_ca" checked class="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary">
                                <span class="text-sm">Instalar CA en el dispositivo</span>
                            </label>
                        </div>
                        <div id="ssl-status-details-shared" class="mb-4 p-3 rounded-md bg-surface-2 text-sm hidden"></div>
                        <div class="flex justify-end gap-4">
                            <button type="button" class="cancel-modal-btn px-4 py-2 rounded-md text-sm font-semibold">Cancelar</button>
                            <button type="submit" id="provision-ssl-btn-shared" class="px-4 py-2 rounded-md text-sm font-semibold text-white bg-primary hover:bg-primary-hover">
                                Provisionar SSL
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>`;

        document.body.insertAdjacentHTML('beforeend', modalHtml);

        // Global Event Delegation for this modal (simplifies lifecycle)
        const modal = document.getElementById(this.modalId);
        modal.addEventListener('click', (e) => {
            if (e.target === modal || e.target.closest('.close-modal-btn') || e.target.closest('.cancel-modal-btn')) {
                this.closeModal();
            }
        });

        const form = document.getElementById('ssl-provision-form-shared');
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleProvision(new FormData(form));
        });
    }

    async openModal() {
        // Update CURRENT instance config to the modal context if we supported multiple badges per page,
        // but here we just use 'this' instance context.
        this.activeInstance = this;

        const modal = document.getElementById(this.modalId);
        if (!modal) return;

        modal.classList.remove('hidden');
        modal.classList.add('flex');

        // Update context details
        const detailsEl = document.getElementById('ssl-status-details-shared');
        if (detailsEl) {
            detailsEl.innerHTML = '<span class="animate-pulse">Cargando detalles...</span>';
            detailsEl.classList.remove('hidden');

            try {
                const response = await fetch(`/api/${this.deviceType}/${this.host}/ssl/status`);
                const status = await response.json();

                let html = '';
                if (status.ssl_enabled) {
                    const color = status.is_trusted ? 'text-green-400' : 'text-yellow-400';
                    html = `<div class="font-bold ${color}">${status.is_trusted ? 'Certificado Confiable' : 'Certificado Auto-firmado'}</div>
                            <div class="text-xs mt-1">Nombre: ${status.certificate_name}</div>`;
                } else {
                    html = `<div class="font-bold text-red-400">SSL Deshabilitado</div>`;
                }
                detailsEl.innerHTML = html;
            } catch (e) {
                detailsEl.textContent = 'Error informático.';
            }
        }
    }

    closeModal() {
        const modal = document.getElementById(this.modalId);
        if (modal) {
            modal.classList.add('hidden');
            modal.classList.remove('flex');
        }
    }

    async handleProvision(formData) {
        // Use 'this' instance context
        const btn = document.getElementById('provision-ssl-btn-shared');
        const originalText = btn.textContent;
        btn.disabled = true;
        btn.textContent = 'Procesando...';

        try {
            let url, payload;
            const method = formData.get('method');
            const installCa = formData.get('install_ca') === 'on';

            if (this.deviceType === 'routers') {
                // Router Specific Endpoint
                url = `/api/routers/${this.host}/ssl/provision`;
                payload = { method, install_ca: installCa };
            } else {
                // AP/Switch Endpoint
                url = `/api/${this.deviceType}/${this.host}/provision`;
                payload = {
                    new_api_user: "umanager_api",
                    new_api_password: this.generatePassword(),
                    method: method
                };
            }

            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || response.statusText);
            }

            const resData = await response.json();
            this.showToast(`Éxito: ${resData.message || 'Provisionado'}`, 'success');
            this.closeModal();
            await this.refresh(); // Refresh badge
        } catch (e) {
            console.error(e);
            this.showToast(`Error: ${e.message}`, 'danger');
        } finally {
            btn.disabled = false;
            btn.textContent = originalText;
        }
    }

    generatePassword() {
        return Math.random().toString(36).slice(-10) + Math.random().toString(36).slice(-10);
    }

    showToast(msg, type) {
        if (window.showToast) window.showToast(msg, type);
        else alert(msg);
    }
}

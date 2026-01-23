document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = window.location.origin;
    let allCPEs = [];
    let searchTerm = '';
    let refreshIntervalId = null;

    // --- REFERENCIAS A ELEMENTOS DEL DOM ---
    const searchInput = document.getElementById('search-input');
    const tableBody = document.getElementById('cpe-table-body');

    /**
     * Deshabilita un CPE en la base de datos.
     * @param {string} mac - La dirección MAC del CPE a deshabilitar.
     */
    async function disableCPE(mac) {
        window.ModalUtils.showConfirmModal({
            title: 'Deshabilitar CPE',
            message: `¿Estás seguro de que deseas deshabilitar el CPE con MAC <strong>${mac}</strong>?<br><br>Podrás eliminarlo permanentemente después.`,
            confirmText: 'Deshabilitar',
            confirmIcon: 'block',
            type: 'warning',
        }).then(async (confirmed) => {
            if (confirmed) {
                try {
                    const response = await fetch(`${API_BASE_URL}/api/cpes/${encodeURIComponent(mac)}/disable`, {
                        method: 'POST',
                    });
                    if (!response.ok) {
                        const errorData = await response.json().catch(() => ({ detail: 'Error desconocido' }));
                        throw new Error(errorData.detail || 'Failed to disable CPE');
                    }
                    // Refresh the table after successful disable
                    loadAllCPEs();
                } catch (error) {
                    console.error("Error disabling CPE:", error);
                    alert(`Error al deshabilitar CPE: ${error.message}`);
                }
            }
        });
    }
    // Make disableCPE globally accessible for onclick handlers
    window.disableCPE = disableCPE;

    /**
     * Elimina permanentemente un CPE de la base de datos.
     * Solo funciona si el CPE ya está deshabilitado.
     * @param {string} mac - La dirección MAC del CPE a eliminar.
     */
    async function deleteCPE(mac) {
        window.ModalUtils.showConfirmModal({
            title: 'Eliminar CPE Permanentemente',
            message: `¿Estás seguro de que deseas eliminar permanentemente el CPE con MAC <strong>${mac}</strong>?<br><br>Esta acción es irreversible y no se puede deshacer.`,
            confirmText: 'Eliminar Permanentemente',
            confirmIcon: 'delete',
            type: 'danger',
        }).then(async (confirmed) => {
            if (confirmed) {
                try {
                    const response = await fetch(`${API_BASE_URL}/api/cpes/${encodeURIComponent(mac)}`, {
                        method: 'DELETE',
                    });
                    if (!response.ok) {
                        const errorData = await response.json().catch(() => ({ detail: 'Error desconocido' }));
                        throw new Error(errorData.detail || 'Failed to delete CPE');
                    }
                    // Refresh the table after successful deletion
                    loadAllCPEs();
                } catch (error) {
                    console.error("Error deleting CPE:", error);
                    alert(`Error al eliminar CPE: ${error.message}`);
                }
            }
        });
    }
    // Make deleteCPE globally accessible for onclick handlers
    window.deleteCPE = deleteCPE;

    /**
     * Updates a CPE property via the API.
     * @param {string} mac - CPE MAC address
     * @param {object} updateData - Object with fields to update
     */
    async function updateCPE(mac, updateData) {
        try {
            const response = await fetch(`${API_BASE_URL}/api/cpes/${encodeURIComponent(mac)}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updateData)
            });
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: 'Error desconocido' }));
                throw new Error(errorData.detail || 'Failed to update CPE');
            }
            loadAllCPEs();
            return true;
        } catch (error) {
            console.error("Error updating CPE:", error);
            alert(`Error al actualizar CPE: ${error.message}`);
            return false;
        }
    }

    /**
     * Opens a custom modal to edit the CPE IP address.
     * @param {string} mac - CPE MAC address
     * @param {string} currentIp - Current IP address (or empty)
     */
    function editCpeIp(mac, currentIp) {
        const inputId = `cpe-ip-input-${mac.replace(/:/g, '')}`;

        const content = `
            <div class="flex flex-col gap-4">
                <p class="text-text-secondary">Introduzca la nueva dirección IP para el CPE <strong>${mac}</strong>.</p>
                <div class="flex flex-col gap-2">
                    <label for="${inputId}" class="text-sm font-medium text-text-primary">Dirección IP</label>
                    <input type="text" id="${inputId}" value="${currentIp || ''}" 
                        class="w-full px-3 py-2 bg-surface-1 border border-border rounded-lg focus:outline-none focus:border-primary text-text-primary font-mono"
                        placeholder="Ej. 192.168.1.50">
                    <p class="text-xs text-text-tertiary">Deje en blanco para "No IP".</p>
                </div>
            </div>
        `;

        const { close } = window.ModalUtils.showCustomModal({
            title: 'Editar Dirección IP',
            content: content,
            size: 'sm',
            actions: [
                {
                    text: 'Cancelar',
                    closeOnClick: true
                },
                {
                    text: 'Guardar IP',
                    icon: 'save',
                    primary: true,
                    closeOnClick: false,
                    handler: async () => {
                        const input = document.getElementById(inputId);
                        const newIp = input.value.trim();

                        // Validation
                        if (newIp !== '') {
                            const ipRegex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
                            if (!ipRegex.test(newIp)) {
                                // Try to use showToast if available, otherwise alert
                                if (typeof showToast === 'function') {
                                    showToast('IP inválida. Formato esperado: xxx.xxx.xxx.xxx', 'danger');
                                } else {
                                    alert('IP inválida. Formato esperado: xxx.xxx.xxx.xxx');
                                }
                                return;
                            }
                        }

                        // Update
                        const success = await updateCPE(mac, { ip_address: newIp });
                        if (success) {
                            if (typeof showToast === 'function') {
                                showToast('IP actualizada correctamente', 'success');
                            }
                            close();
                        }
                    }
                }
            ]
        });

        // Focus the input
        setTimeout(() => {
            const input = document.getElementById(inputId);
            if (input) input.focus();
        }, 100);
    }
    window.editCpeIp = editCpeIp;

    // --- Manual CPE Name Editing (Modal) ---
    const editCPEModal = document.getElementById('edit-cpe-modal');
    const editCPEForm = document.getElementById('edit-cpe-form');
    const editCPECancelBtn = document.getElementById('edit-cpe-cancel-button');

    function openEditCPEModal(mac, currentHostname) {
        if (!editCPEModal) return;
        document.getElementById('edit-cpe-mac').value = mac;
        document.getElementById('edit-cpe-mac-display').value = mac;
        document.getElementById('edit-cpe-hostname').value = currentHostname;
        editCPEModal.classList.remove('hidden');
        editCPEModal.classList.add('flex');
    }

    function closeEditCPEModal() {
        if (!editCPEModal) return;
        editCPEModal.classList.add('hidden');
        editCPEModal.classList.remove('flex');
        // Optional: editCPEForm.reset();
    }

    if (editCPECancelBtn) {
        editCPECancelBtn.addEventListener('click', closeEditCPEModal);
    }

    if (editCPEModal) {
        editCPEModal.addEventListener('click', (e) => {
            if (e.target === editCPEModal) closeEditCPEModal();
        });
    }

    if (editCPEForm) {
        editCPEForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const mac = document.getElementById('edit-cpe-mac').value;
            const hostname = document.getElementById('edit-cpe-hostname').value.trim();

            const success = await updateCPE(mac, { hostname: hostname });
            if (success) {
                if (typeof showToast === 'function') showToast('Hostname updated', 'success');
                closeEditCPEModal();
            }
        });
    }

    /**
     * Devuelve la clase y el texto para un badge de estado basado en la señal.
     * @param {number|null} signal - El nivel de señal del CPE en dBm.
     * @returns {{badgeClass: string, text: string}}
     */
    function getStatusFromSignal(signal) {
        if (signal == null) {
            return { badgeClass: 'bg-text-secondary/20 text-text-secondary', text: 'Unknown' };
        }
        if (signal > -65) {
            return { badgeClass: 'bg-success/20 text-success', text: 'Excellent' };
        }
        if (signal > -75) {
            return { badgeClass: 'bg-primary/20 text-primary', text: 'Good' };
        }
        if (signal > -85) {
            return { badgeClass: 'bg-warning/20 text-warning', text: 'Weak' };
        }
        return { badgeClass: 'bg-danger/20 text-danger', text: 'Poor' };
    }

    /**
     * Filtra y renderiza la lista de CPEs en la tabla.
     */
    function renderCPEs() {
        if (!tableBody) return;

        const filteredCPEs = allCPEs.filter(cpe => {
            const term = searchTerm.toLowerCase();
            return !term ||
                (cpe.cpe_hostname && cpe.cpe_hostname.toLowerCase().includes(term)) ||
                (cpe.ap_hostname && cpe.ap_hostname.toLowerCase().includes(term)) ||
                cpe.cpe_mac.toLowerCase().includes(term) ||
                (cpe.ip_address && cpe.ip_address.toLowerCase().includes(term));
        });

        // Ordenamos los CPEs por señal, de más débil a más fuerte
        filteredCPEs.sort((a, b) => (a.signal || -100) - (b.signal || -100));

        tableBody.innerHTML = '';

        if (filteredCPEs.length === 0) {
            const emptyRow = document.createElement('tr');
            emptyRow.innerHTML = `<td colspan="9" class="text-center p-8 text-text-secondary">No CPEs match the current filter.</td>`;
            tableBody.appendChild(emptyRow);
        } else {
            filteredCPEs.forEach(cpe => {
                const row = document.createElement('tr');
                row.className = "hover:bg-surface-2 transition-colors duration-200";

                const status = getStatusFromSignal(cpe.signal);
                const signalStrength = cpe.signal != null ? `${cpe.signal} dBm` : 'N/A';

                const apLink = cpe.ap_host ? `<a href="/ap/${cpe.ap_host}" class="text-primary hover:underline">${cpe.ap_hostname || cpe.ap_host}</a>` : 'N/A';

                const ipDisplay = cpe.ip_address || "No IP";
                const ipClass = cpe.ip_address ? "text-text-secondary" : "text-warning";

                // Conditional buttons based on is_enabled status
                const isEnabled = cpe.is_enabled !== false; // Default to true if undefined
                const actionButtons = isEnabled
                    ? `<button data-action="edit-ip" data-mac="${cpe.cpe_mac}" data-ip="${cpe.ip_address || ''}" class="text-text-secondary hover:text-primary transition-colors mr-2" title="Editar IP">
                            <span class="material-symbols-outlined">edit</span>
                        </button>
                        <button data-action="disable" data-mac="${cpe.cpe_mac}" class="text-warning hover:text-yellow-400 transition-colors" title="Deshabilitar CPE">
                            <span class="material-symbols-outlined">block</span>
                        </button>`
                    : `<button data-action="delete" data-mac="${cpe.cpe_mac}" class="text-danger hover:text-red-400 transition-colors" title="Eliminar CPE Permanentemente">
                            <span class="material-symbols-outlined">delete</span>
                        </button>`;

                row.innerHTML = `
                    <td class="px-6 py-4 whitespace-nowrap">
                        <span class="text-xs font-semibold px-2 py-1 rounded-full ${status.badgeClass}">${status.text}</span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap font-semibold text-text-primary">
                        <div class="flex items-center gap-2">
                            <span>${cpe.cpe_hostname || "Unnamed Device"}</span>
                            <button data-action="edit-hostname" data-mac="${cpe.cpe_mac}" data-hostname="${cpe.cpe_hostname ? cpe.cpe_hostname.replace(/"/g, '&quot;') : ''}" 
                                class="text-text-secondary hover:text-primary transition-colors opacity-50 hover:opacity-100" title="Edit Hostname">
                                <span class="material-symbols-outlined text-sm">edit</span>
                            </button>
                        </div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-text-secondary">${apLink}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-text-secondary">${cpe.ssid || "N/A"}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-text-secondary">${cpe.band || "N/A"}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-text-primary font-semibold">${signalStrength}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-text-secondary font-mono">${cpe.cpe_mac}</td>
                    <td class="px-6 py-4 whitespace-nowrap ${ipClass} font-mono cursor-pointer hover:text-primary ip-cell" 
                        data-mac="${cpe.cpe_mac}" data-ip="${cpe.ip_address || ''}" title="Click para editar IP">
                        ${ipDisplay} <span class="material-symbols-outlined text-xs align-middle opacity-50">edit</span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        ${actionButtons}
                    </td>
                `;
                tableBody.appendChild(row);
            });
        }
    }

    /**
     * Event delegation for button clicks
     */
    if (tableBody) {
        tableBody.addEventListener('click', (e) => {
            const button = e.target.closest('button[data-action]');
            const ipCell = e.target.closest('.ip-cell');

            if (button) {
                const action = button.dataset.action;
                const mac = button.dataset.mac;
                const ip = button.dataset.ip;

                switch (action) {
                    case 'edit-hostname':
                        openEditCPEModal(mac, button.dataset.hostname);
                        break;
                    case 'edit-ip':
                        editCpeIp(mac, ip);
                        break;
                    case 'disable':
                        disableCPE(mac);
                        break;
                    case 'delete':
                        deleteCPE(mac);
                        break;
                }
            } else if (ipCell) {
                const mac = ipCell.dataset.mac;
                const ip = ipCell.dataset.ip;
                editCpeIp(mac, ip);
            }
        });
    }

    /**
 * Carga todos los datos de los CPEs desde la API y los renderiza.
 */
    function loadAllCPEs() {
        if (!tableBody) return;

        tableBody.style.filter = 'blur(4px)';
        tableBody.style.opacity = '0.6';

        if (allCPEs.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="9" class="text-center p-8 text-text-secondary">Loading CPE data...</td></tr>';
        }

        setTimeout(async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/api/cpes/all`);
                if (!response.ok) {
                    throw new Error('Failed to load CPEs');
                }
                allCPEs = await response.json();
                renderCPEs();
            } catch (error) {
                console.error("Error loading CPE data:", error);
                tableBody.innerHTML = `<tr><td colspan="9" class="text-center p-8 text-danger">Failed to load network data. Please check the API.</td></tr>`;
            } finally {
                setTimeout(() => {
                    if (tableBody) {
                        tableBody.style.filter = 'blur(0px)';
                        tableBody.style.opacity = '1';
                    }
                }, 50);
            }
        }, 300);
    }

    // --- ESCUCHA REACTIVA: Actualizar solo cuando el monitor guarda nuevos datos ---
    window.addEventListener('data-refresh-needed', () => {
        console.log("⚡ CPEs: Recargando lista por actualización en vivo.");
        loadAllCPEs();
    });

    // --- INICIALIZACIÓN ---
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            searchTerm = e.target.value;
            renderCPEs();
        });
    }

    loadAllCPEs();
});
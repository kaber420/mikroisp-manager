document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = window.location.origin;
    let allCPEs = [];
    let searchTerm = '';
    let refreshIntervalId = null;

    // --- REFERENCIAS A ELEMENTOS DEL DOM ---
    const searchInput = document.getElementById('search-input');
    const tableBody = document.getElementById('cpe-table-body');

    /**
     * Elimina un CPE de la base de datos.
     * @param {string} mac - La dirección MAC del CPE a eliminar.
     */
    async function deleteCPE(mac) {
        window.ModalUtils.showConfirmModal({
            title: 'Eliminar CPE',
            message: `¿Estás seguro de que deseas eliminar el CPE con MAC <strong>${mac}</strong>?<br><br>Esta acción es irreversible.`,
            confirmText: 'Eliminar',
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
     * Opens a prompt to edit the CPE IP address.
     * @param {string} mac - CPE MAC address
     * @param {string} currentIp - Current IP address (or empty)
     */
    async function editCpeIp(mac, currentIp) {
        const newIp = prompt('Introduce la dirección IP para este CPE:', currentIp || '');
        if (newIp === null) return; // Cancelled
        if (newIp === '') {
            alert('La IP no puede estar vacía. Usa "No IP" para indicar sin IP.');
            return;
        }
        // Basic IP validation
        const ipRegex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
        if (!ipRegex.test(newIp)) {
            alert('IP inválida. Formato esperado: xxx.xxx.xxx.xxx');
            return;
        }
        await updateCPE(mac, { ip_address: newIp });
    }
    window.editCpeIp = editCpeIp;

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

                row.innerHTML = `
                    <td class="px-6 py-4 whitespace-nowrap">
                        <span class="text-xs font-semibold px-2 py-1 rounded-full ${status.badgeClass}">${status.text}</span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap font-semibold text-text-primary">${cpe.cpe_hostname || "Unnamed Device"}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-text-secondary">${apLink}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-text-secondary">${cpe.ssid || "N/A"}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-text-secondary">${cpe.band || "N/A"}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-text-primary font-semibold">${signalStrength}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-text-secondary font-mono">${cpe.cpe_mac}</td>
                    <td class="px-6 py-4 whitespace-nowrap ${ipClass} font-mono cursor-pointer hover:text-primary" 
                        onclick="editCpeIp('${cpe.cpe_mac}', '${cpe.ip_address || ''}')" title="Click para editar IP">
                        ${ipDisplay} <span class="material-symbols-outlined text-xs align-middle opacity-50">edit</span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <button onclick="editCpeIp('${cpe.cpe_mac}', '${cpe.ip_address || ''}')" class="text-text-secondary hover:text-primary transition-colors mr-2" title="Editar IP">
                            <span class="material-symbols-outlined">edit</span>
                        </button>
                        <button onclick="deleteCPE('${cpe.cpe_mac}')" class="text-danger hover:text-red-400 transition-colors" title="Eliminar CPE">
                            <span class="material-symbols-outlined">delete</span>
                        </button>
                    </td>
                `;
                tableBody.appendChild(row);
            });
        }
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
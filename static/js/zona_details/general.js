/**
 * General information module for Zone Details
 * Handles basic zone info form and rendering
 */

function renderGeneralInfo(zonaData) {
    if (!zonaData) return;
    document.getElementById('main-zonaname').textContent = zonaData.nombre;
    document.getElementById('zona-nombre').value = zonaData.nombre;
    document.getElementById('zona-coordenadas').value = zonaData.coordenadas_gps || '';
    document.getElementById('zona-direccion').value = zonaData.direccion || '';
}

function initGeneralInfo() {
    const API_BASE_URL = window.location.origin;
    const zonaId = window.location.pathname.split('/').pop();

    document.getElementById('form-general').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const data = Object.fromEntries(formData.entries());

        try {
            await fetch(`${API_BASE_URL}/api/zonas/${zonaId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            showToast('General info saved!', 'success');
            window.loadAllDetails();
        } catch (error) {
            showToast(`Error saving: ${error.message}`, 'danger');
        }
    });
}

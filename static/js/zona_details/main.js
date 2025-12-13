/**
 * Main entry point for Zone Details page
 * Orchestrates all modules and handles tab switching
 */

document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = window.location.origin;
    const zonaId = window.location.pathname.split('/').pop();
    let zonaData = null;

    // --- Element Cache ---
    const mainZoneName = document.getElementById('main-zonaname');
    const refreshInfraBtn = document.getElementById('refresh-infra-btn');

    // --- Tab Switching Logic ---
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabPanels = document.querySelectorAll('.tab-panel');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            tabButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            const tabName = button.getAttribute('data-tab');
            tabPanels.forEach(panel => {
                if (panel.id === `tab-${tabName}`) {
                    panel.classList.add('active');
                } else {
                    panel.classList.remove('active');
                }
            });
            // Load infrastructure when tab is clicked
            if (tabName === 'infra') {
                loadInfrastructure(zonaId);
            }
        });
    });

    // --- Data Loading & Rendering ---
    async function loadAllDetails() {
        try {
            const response = await fetch(`${API_BASE_URL}/api/zonas/${zonaId}/details`);
            if (!response.ok) throw new Error('Zone not found');
            zonaData = await response.json();

            renderGeneralInfo(zonaData);
            renderDocuments(zonaData);
            renderNotes(zonaData);
        } catch (error) {
            mainZoneName.textContent = 'Error';
            showToast(`Failed to load zone details: ${error.message}`, 'danger');
        }
    }

    // Expose globally so modules can call it
    window.loadAllDetails = loadAllDetails;

    // Refresh button handler
    if (refreshInfraBtn) {
        refreshInfraBtn.addEventListener('click', () => loadInfrastructure(zonaId));
    }

    // Initialize modules
    initGeneralInfo();
    initDocuments();
    initNotes(zonaData);

    // Initial Load
    loadAllDetails();
});

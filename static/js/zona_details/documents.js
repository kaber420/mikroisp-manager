/**
 * Documents management module for Zone Details
 * Handles document gallery, uploads, and deletions
 */

function renderDocuments(zonaData) {
    const gallery = document.getElementById('document-gallery');
    gallery.innerHTML = '';
    if (!zonaData || zonaData.documentos.length === 0) {
        gallery.innerHTML = '<p class="text-text-secondary">No documents uploaded for this zone.</p>';
        return;
    }

    const grid = document.createElement('div');
    grid.className = 'grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4';

    zonaData.documentos.forEach(doc => {
        const isImage = doc.tipo === 'image';
        const fileUrl = `/uploads/zonas/${doc.zona_id}/${doc.nombre_guardado}`;

        const card = document.createElement('div');
        card.className = 'bg-surface-2 rounded-lg p-3 text-center space-y-2';
        card.innerHTML = `
            <div class="flex items-center justify-center h-24 bg-background rounded-md">
                ${isImage ?
                `<img src="${fileUrl}" alt="${doc.descripcion || 'Image'}" class="max-h-full max-w-full object-contain">` :
                `<span class="material-symbols-outlined text-5xl text-text-secondary">description</span>`
            }
            </div>
            <p class="text-sm font-medium truncate" title="${doc.nombre_original}">${doc.nombre_original}</p>
            <div class="flex justify-center gap-2">
                <a href="${fileUrl}" target="_blank" class="text-primary hover:underline text-xs">View</a>
                <a href="${fileUrl}" download="${doc.nombre_original}" class="text-primary hover:underline text-xs">Download</a>
                <button data-doc-id="${doc.id}" class="delete-doc-btn text-danger hover:underline text-xs">Delete</button>
            </div>
        `;
        grid.appendChild(card);
    });
    gallery.appendChild(grid);
}

function initDocuments() {
    const API_BASE_URL = window.location.origin;
    const zonaId = window.location.pathname.split('/').pop();

    // Upload form handler
    document.getElementById('form-docs').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);

        try {
            const response = await fetch(`${API_BASE_URL}/api/zonas/${zonaId}/documentos`, {
                method: 'POST',
                body: formData
            });
            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Failed to upload');
            }
            e.target.reset();
            showToast('File uploaded successfully!', 'success');
            window.loadAllDetails();
        } catch (error) {
            showToast(`Error uploading file: ${error.message}`, 'danger');
        }
    });

    // Delete handler (event delegation)
    document.getElementById('document-gallery').addEventListener('click', async (e) => {
        if (e.target.classList.contains('delete-doc-btn')) {
            const docId = e.target.getAttribute('data-doc-id');
            if (confirm('Are you sure you want to delete this document?')) {
                try {
                    await fetch(`${API_BASE_URL}/api/documentos/${docId}`, { method: 'DELETE' });
                    showToast('Document deleted.', 'success');
                    window.loadAllDetails();
                } catch (error) {
                    showToast(`Error deleting document: ${error.message}`, 'danger');
                }
            }
        }
    });
}

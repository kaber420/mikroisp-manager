/**
 * Zone Details Alpine.js Application
 * Unified component for zona details page
 * Note: infra.js remains in Vanilla JS due to complex SVG rendering
 */

document.addEventListener('alpine:init', () => {
    Alpine.data('zonaDetails', () => ({
        // State
        zonaId: window.location.pathname.split('/').pop(),
        activeTab: 'general',
        loading: true,

        // Zone data
        zona: {
            nombre: '',
            coordenadas_gps: '',
            direccion: '',
            documentos: [],
            notes: []
        },

        // Notes modal state
        noteModal: {
            open: false,
            isEdit: false,
            id: null,
            title: '',
            content: '',
            is_encrypted: false
        },

        // Computed property for markdown preview
        get notePreview() {
            if (typeof marked !== 'undefined' && this.noteModal.content) {
                return marked.parse(this.noteModal.content);
            }
            return '<p class="text-text-secondary">Markdown preview</p>';
        },

        // Initialize
        async init() {
            await this.loadZonaDetails();

            // Setup infra refresh button (for vanilla infra.js)
            const refreshBtn = document.getElementById('refresh-infra-btn');
            if (refreshBtn) {
                refreshBtn.addEventListener('click', () => this.loadInfra());
            }

            // Expose reload function globally for infra.js compatibility
            window.loadAllDetails = () => this.loadZonaDetails();
        },

        // Tab switching
        switchTab(tab) {
            this.activeTab = tab;
            if (tab === 'infra') {
                this.loadInfra();
            }
        },

        isActiveTab(tab) {
            return this.activeTab === tab;
        },

        // Load zone details
        async loadZonaDetails() {
            this.loading = true;
            try {
                const response = await fetch(`/api/zonas/${this.zonaId}/details`);
                if (!response.ok) throw new Error('Zone not found');
                const data = await response.json();

                this.zona = {
                    nombre: data.nombre || '',
                    coordenadas_gps: data.coordenadas_gps || '',
                    direccion: data.direccion || '',
                    documentos: data.documentos || [],
                    notes: data.notes || []
                };
            } catch (error) {
                showToast(`Failed to load zone details: ${error.message}`, 'danger');
            } finally {
                this.loading = false;
            }
        },

        // Load infrastructure (calls vanilla infra.js)
        loadInfra() {
            if (typeof loadInfrastructure === 'function') {
                loadInfrastructure(this.zonaId);
            }
        },

        // === GENERAL INFO ===
        async saveGeneralInfo() {
            try {
                const response = await fetch(`/api/zonas/${this.zonaId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        nombre: this.zona.nombre,
                        coordenadas_gps: this.zona.coordenadas_gps,
                        direccion: this.zona.direccion
                    })
                });
                if (!response.ok) throw new Error('Failed to save');
                showToast('General info saved!', 'success');
                await this.loadZonaDetails();
            } catch (error) {
                showToast(`Error saving: ${error.message}`, 'danger');
            }
        },

        // === DOCUMENTS ===
        async uploadDocument(event) {
            const form = event.target;
            const formData = new FormData(form);

            try {
                const response = await fetch(`/api/zonas/${this.zonaId}/documentos`, {
                    method: 'POST',
                    body: formData
                });
                if (!response.ok) {
                    const err = await response.json();
                    throw new Error(err.detail || 'Failed to upload');
                }
                form.reset();
                showToast('File uploaded successfully!', 'success');
                await this.loadZonaDetails();
            } catch (error) {
                showToast(`Error uploading file: ${error.message}`, 'danger');
            }
        },

        async deleteDocument(docId) {
            if (!confirm('Are you sure you want to delete this document?')) return;

            try {
                const response = await fetch(`/api/documentos/${docId}`, { method: 'DELETE' });
                if (!response.ok) throw new Error('Failed to delete');
                showToast('Document deleted.', 'success');
                await this.loadZonaDetails();
            } catch (error) {
                showToast(`Error deleting document: ${error.message}`, 'danger');
            }
        },

        getDocumentUrl(doc) {
            return `/uploads/zonas/${doc.zona_id}/${doc.nombre_guardado}`;
        },

        // === NOTES ===
        openNewNote() {
            this.noteModal = {
                open: true,
                isEdit: false,
                id: null,
                title: '',
                content: '',
                is_encrypted: false
            };
        },

        openEditNote(note) {
            this.noteModal = {
                open: true,
                isEdit: true,
                id: note.id,
                title: note.title,
                content: note.content,
                is_encrypted: note.is_encrypted
            };
        },

        closeNoteModal() {
            this.noteModal.open = false;
        },

        async saveNote() {
            const url = this.noteModal.isEdit
                ? `/api/zonas/notes/${this.noteModal.id}`
                : `/api/zonas/${this.zonaId}/notes`;
            const method = this.noteModal.isEdit ? 'PUT' : 'POST';

            try {
                const response = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        title: this.noteModal.title,
                        content: this.noteModal.content,
                        is_encrypted: this.noteModal.is_encrypted
                    })
                });
                if (!response.ok) {
                    const err = await response.json();
                    throw new Error(err.detail || 'Failed to save note');
                }
                this.closeNoteModal();
                showToast('Note saved successfully!', 'success');
                await this.loadZonaDetails();
            } catch (error) {
                showToast(`Error saving note: ${error.message}`, 'danger');
            }
        },

        async deleteNote(noteId) {
            if (!confirm('Are you sure you want to delete this note?')) return;

            try {
                const response = await fetch(`/api/zonas/notes/${noteId}`, { method: 'DELETE' });
                if (!response.ok) {
                    const err = await response.json();
                    throw new Error(err.detail || 'Failed to delete note');
                }
                showToast('Note deleted successfully!', 'success');
                await this.loadZonaDetails();
            } catch (error) {
                showToast(`Error deleting note: ${error.message}`, 'danger');
            }
        },

        getNotePreviewHtml(note) {
            if (note.is_encrypted) {
                return '<p class="text-text-secondary italic">This note is encrypted.</p>';
            }
            if (typeof marked !== 'undefined') {
                const preview = note.content.substring(0, 200) + (note.content.length > 200 ? '...' : '');
                return marked.parse(preview);
            }
            return note.content.substring(0, 200);
        }
    }));
});

// static/js/zona_details/components.js

document.addEventListener('alpine:init', () => {

    // Shared Store for Zone Data
    Alpine.store('currentZone', {
        loading: true,
        data: {
            id: window.location.pathname.split('/').pop(),
            nombre: '',
            coordenadas_gps: '',
            direccion: '',
            documentos: [],
            notes: []
        },

        async load() {
            this.loading = true;
            try {
                const response = await fetch(`/api/zonas/${this.data.id}/details`);
                if (!response.ok) throw new Error('Zone not found');
                const result = await response.json();

                // Update data preserving the id
                this.data = { ...this.data, ...result };
            } catch (error) {
                showToast(`Failed to load zone details: ${error.message}`, 'danger');
            } finally {
                this.loading = false;
            }
        },

        updateGeneralInfo(info) {
            this.data = { ...this.data, ...info };
        },

        addDocument(doc) {
            this.data.documentos.push(doc);
        },

        removeDocument(docId) {
            this.data.documentos = this.data.documentos.filter(d => d.id !== docId);
        },

        addNote(note) {
            this.data.notes.unshift(note);
        },

        updateNote(note) {
            const index = this.data.notes.findIndex(n => n.id === note.id);
            if (index !== -1) {
                this.data.notes[index] = note;
            }
        },

        removeNote(noteId) {
            this.data.notes = this.data.notes.filter(n => n.id !== noteId);
        }
    });

    // Main Manager Component (mostly for initialization and generic info)
    Alpine.data('zoneManager', () => ({
        get zona() { return this.$store.currentZone.data; },
        get loading() { return this.$store.currentZone.loading; },

        init() {
            this.$store.currentZone.load();

            // Expose for external scripts (infra.js)
            window.loadAllDetails = () => this.$store.currentZone.load();
        },

        async saveGeneralInfo() {
            try {
                const response = await fetch(`/api/zonas/${this.zona.id}`, {
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
            } catch (error) {
                showToast(`Error saving: ${error.message}`, 'danger');
            }
        }
    }));

    // Tabs Component
    Alpine.data('zoneTabs', () => ({
        activeTab: 'general',

        init() {
            const hash = window.location.hash.replace('#', '');
            if (hash && ['general', 'infra', 'docs', 'notes'].includes(hash)) {
                this.activeTab = hash;
            }
        },

        switchTab(tab) {
            this.activeTab = tab;
            window.location.hash = tab;
            if (tab === 'infra') {
                this.loadInfra();
            }
        },

        isActiveTab(tab) {
            return this.activeTab === tab;
        },

        loadInfra() {
            // Interop with legacy infra.js
            const zonaId = this.$store.currentZone.data.id;
            if (typeof initInfrastructure === 'function') {
                initInfrastructure(zonaId);
            } else if (typeof loadInfrastructure === 'function') {
                loadInfrastructure(zonaId);
            }
        }
    }));

    // Documents Component
    Alpine.data('zoneDocuments', () => ({
        get docs() { return this.$store.currentZone.data.documentos; },
        get zonaId() { return this.$store.currentZone.data.id; },

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
                const newDoc = await response.json();
                this.$store.currentZone.addDocument(newDoc);
                form.reset();
                showToast('File uploaded successfully!', 'success');
            } catch (error) {
                showToast(`Error uploading file: ${error.message}`, 'danger');
            }
        },

        async deleteDocument(docId) {
            const confirmed = await ModalUtils.showConfirmModal({
                title: 'Eliminar Documento',
                message: '¿Estás seguro de que deseas eliminar este documento? Esta acción no se puede deshacer.',
                confirmText: 'Eliminar',
                confirmIcon: 'delete',
                type: 'danger'
            });

            if (!confirmed) return;

            try {
                const response = await fetch(`/api/documentos/${docId}`, { method: 'DELETE' });
                if (!response.ok) throw new Error('Failed to delete');
                this.$store.currentZone.removeDocument(docId);
                showToast('Document deleted.', 'success');
            } catch (error) {
                showToast(`Error deleting document: ${error.message}`, 'danger');
            }
        },

        getDocumentUrl(doc) {
            return `/uploads/zonas/${doc.zona_id}/${doc.nombre_guardado}`;
        },

        async viewDocument(doc) {
            const url = this.getDocumentUrl(doc);
            let content = '';
            let size = 'lg';

            if (doc.tipo === 'image') {
                content = `<div class="flex justify-center bg-black/5 rounded-lg overflow-hidden">
                    <img src="${url}" alt="${doc.nombre_original}" class="max-w-full max-h-[70vh] object-contain">
                </div>`;
                size = 'xl';
            } else {
                // Must be text/code/config
                try {
                    const response = await fetch(url);
                    if (!response.ok) throw new Error('Failed to load file content');
                    const text = await response.text();
                    content = `<pre class="bg-black/90 text-gray-200 p-4 rounded-lg overflow-auto max-h-[70vh] text-sm font-mono whitespace-pre-wrap">${this.escapeHtml(text)}</pre>`;
                    size = 'xl';
                } catch (e) {
                    showToast(`Could not load document preview: ${e.message}`, 'danger');
                    return;
                }
            }

            ModalUtils.showCustomModal({
                title: doc.nombre_original,
                content: content,
                size: size,
                actions: [
                    {
                        text: 'Download',
                        icon: 'download',
                        className: 'modal-btn modal-btn-primary',
                        handler: () => {
                            const link = document.createElement('a');
                            link.href = url;
                            link.download = doc.nombre_original;
                            document.body.appendChild(link);
                            link.click();
                            document.body.removeChild(link);
                        },
                        closeOnClick: false
                    },
                    {
                        text: 'Close',
                        className: 'modal-btn modal-btn-cancel',
                        handler: () => { }
                    }
                ]
            });
        },

        escapeHtml(text) {
            const map = {
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#039;'
            };
            return text.replace(/[&<>"']/g, function (m) { return map[m]; });
        }
    }));

    // Notes Component
    Alpine.data('zoneNotes', () => ({
        get notes() { return this.$store.currentZone.data.notes; },
        get zonaId() { return this.$store.currentZone.data.id; },

        noteModal: {
            open: false,
            isEdit: false,
            id: null,
            title: '',
            content: '',
            is_encrypted: false
        },

        get notePreview() {
            if (typeof marked !== 'undefined' && this.noteModal.content) {
                return marked.parse(this.noteModal.content);
            }
            return '<p class="text-text-secondary">Markdown preview</p>';
        },

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
                const savedNote = await response.json();

                if (this.noteModal.isEdit) {
                    this.$store.currentZone.updateNote(savedNote);
                } else {
                    this.$store.currentZone.addNote(savedNote);
                }

                this.closeNoteModal();
                showToast('Note saved successfully!', 'success');
            } catch (error) {
                showToast(`Error saving note: ${error.message}`, 'danger');
            }
        },

        async deleteNote(noteId) {
            const confirmed = await ModalUtils.showConfirmModal({
                title: 'Eliminar Nota',
                message: '¿Estás seguro de que deseas eliminar esta nota? Esta acción no se puede deshacer.',
                confirmText: 'Eliminar',
                confirmIcon: 'delete',
                type: 'danger'
            });

            if (!confirmed) return;

            try {
                const response = await fetch(`/api/zonas/notes/${noteId}`, { method: 'DELETE' });
                if (!response.ok) {
                    const err = await response.json();
                    throw new Error(err.detail || 'Failed to delete note');
                }
                this.$store.currentZone.removeNote(noteId);
                showToast('Note deleted successfully!', 'success');
            } catch (error) {
                showToast(`Error deleting note: ${error.message}`, 'danger');
            }
        },

        getNotePreviewHtml(note) {
            if (typeof marked !== 'undefined') {
                const preview = note.content.substring(0, 200) + (note.content.length > 200 ? '...' : '');
                return marked.parse(preview);
            }
            return note.content.substring(0, 200);
        }
    }));
});

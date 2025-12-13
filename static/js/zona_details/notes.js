/**
 * Notes management module for Zone Details
 * Handles CRUD operations for notes and modal interactions
 */

let zonaNotesData = null;

function initNotes(zonaData) {
    zonaNotesData = zonaData;

    const noteModal = document.getElementById('note-modal');
    const noteForm = document.getElementById('note-form');
    const noteEditor = document.getElementById('note-editor');
    const notePreview = document.getElementById('note-preview');
    const notesListContainer = document.getElementById('notes-list');

    // Event Listeners
    document.getElementById('new-note-btn').addEventListener('click', () => openNoteModal());
    document.getElementById('cancel-note-btn').addEventListener('click', closeNoteModal);
    document.getElementById('close-note-modal-btn').addEventListener('click', closeNoteModal);

    noteEditor.addEventListener('input', () => {
        notePreview.innerHTML = marked.parse(noteEditor.value);
    });

    notesListContainer.addEventListener('click', (e) => {
        if (e.target.classList.contains('edit-note-btn')) {
            const noteId = parseInt(e.target.getAttribute('data-note-id'));
            const noteToEdit = zonaNotesData.notes.find(n => n.id === noteId);
            openNoteModal(noteToEdit);
        }
        if (e.target.classList.contains('delete-note-btn')) {
            const noteId = parseInt(e.target.getAttribute('data-note-id'));
            if (confirm('Are you sure you want to delete this note?')) {
                deleteNote(noteId);
            }
        }
    });

    noteForm.addEventListener('submit', handleNoteSubmit);
}

function renderNotes(zonaData) {
    zonaNotesData = zonaData;
    const notesListContainer = document.getElementById('notes-list');
    if (!zonaData || !zonaData.notes) return;
    notesListContainer.innerHTML = '';

    if (zonaData.notes.length === 0) {
        notesListContainer.innerHTML = '<p class="text-text-secondary">No notes for this zone yet.</p>';
        return;
    }

    zonaData.notes.forEach(note => {
        const card = document.createElement('div');
        card.className = 'bg-surface-1 rounded-lg border border-border-color p-4 flex justify-between items-start';

        const contentPreview = note.is_encrypted
            ? '<p class="text-text-secondary italic">This note is encrypted.</p>'
            : marked.parse(note.content.substring(0, 200) + (note.content.length > 200 ? '...' : ''));

        card.innerHTML = `
            <div class="prose prose-invert max-w-none">
                <h4 class="font-bold text-lg mb-2 flex items-center gap-2">
                    ${note.is_encrypted ? '<span class="material-symbols-outlined text-base">lock</span>' : ''}
                    ${note.title}
                </h4>
                <div class="text-sm text-text-secondary">${contentPreview}</div>
            </div>
            <div class="flex-shrink-0 ml-4">
                <button data-note-id="${note.id}" class="edit-note-btn text-primary hover:underline text-sm">Edit</button>
                <button data-note-id="${note.id}" class="delete-note-btn text-danger hover:underline text-sm ml-2">Delete</button>
            </div>
        `;
        notesListContainer.appendChild(card);
    });
}

function openNoteModal(note = null) {
    const noteModal = document.getElementById('note-modal');
    const noteModalTitle = document.getElementById('note-modal-title');
    const noteForm = document.getElementById('note-form');
    const noteIdInput = document.getElementById('note-id');
    const noteTitleInput = document.getElementById('note-title');
    const noteEditor = document.getElementById('note-editor');
    const notePreview = document.getElementById('note-preview');
    const noteIsEncryptedInput = document.getElementById('note-is-encrypted');

    noteForm.reset();
    if (note) {
        noteModalTitle.textContent = 'Edit Note';
        noteIdInput.value = note.id;
        noteTitleInput.value = note.title;
        noteEditor.value = note.content;
        noteIsEncryptedInput.checked = note.is_encrypted;
    } else {
        noteModalTitle.textContent = 'New Note';
        noteIdInput.value = '';
    }
    notePreview.innerHTML = marked.parse(noteEditor.value);
    noteModal.classList.remove('hidden');
    noteModal.classList.add('flex');
}

function closeNoteModal() {
    const noteModal = document.getElementById('note-modal');
    noteModal.classList.add('hidden');
    noteModal.classList.remove('flex');
}

async function handleNoteSubmit(e) {
    e.preventDefault();
    const API_BASE_URL = window.location.origin;
    const zonaId = window.location.pathname.split('/').pop();
    const noteIdInput = document.getElementById('note-id');
    const noteTitleInput = document.getElementById('note-title');
    const noteEditor = document.getElementById('note-editor');
    const noteIsEncryptedInput = document.getElementById('note-is-encrypted');

    const noteId = noteIdInput.value;
    const data = {
        title: noteTitleInput.value,
        content: noteEditor.value,
        is_encrypted: noteIsEncryptedInput.checked,
    };

    const url = noteId
        ? `${API_BASE_URL}/api/zonas/notes/${noteId}`
        : `${API_BASE_URL}/api/zonas/${zonaId}/notes`;
    const method = noteId ? 'PUT' : 'POST';

    try {
        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to save note');
        }

        closeNoteModal();
        await window.loadAllDetails(); // Call global reload function
        showToast('Note saved successfully!', 'success');

    } catch (error) {
        showToast(`Error saving note: ${error.message}`, 'danger');
    }
}

async function deleteNote(noteId) {
    const API_BASE_URL = window.location.origin;
    try {
        const response = await fetch(`${API_BASE_URL}/api/zonas/notes/${noteId}`, {
            method: 'DELETE',
        });
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to delete note');
        }
        await window.loadAllDetails();
        showToast('Note deleted successfully!', 'success');
    } catch (error) {
        showToast(`Error deleting note: ${error.message}`, 'danger');
    }
}

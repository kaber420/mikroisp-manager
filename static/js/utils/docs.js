/**
 * Documentation System Utility
 * Handles fetching, rendering, and navigation for the Markdown-based help system
 * Implements architectural mimicry by using Alpine.js (similar to toast.js)
 */

class DocsFetcher {
    constructor() {
        this.index = null;
        this.basePath = '/static/docs';
        this.cache = new Map();
    }

    async loadIndex() {
        if (this.index) return this.index;
        try {
            const response = await fetch(`${this.basePath}/index.json`);
            if (!response.ok) throw new Error('Failed to load documentation index');
            this.index = await response.json();
            return this.index;
        } catch (error) {
            console.error('Error loading docs index:', error);
            throw error;
        }
    }

    async loadArticle(filePath) {
        if (this.cache.has(filePath)) return this.cache.get(filePath);

        try {
            const response = await fetch(`${this.basePath}/${filePath}`);
            if (!response.ok) throw new Error(`Failed to load article: ${filePath}`);
            const markdown = await response.text();

            // Use marked.js to parse markdown
            // Using unsafe-eval compliant configuration if possible, 
            // but marked.js is generally safe if not using specialized extensions
            const html = marked.parse(markdown);

            this.cache.set(filePath, html);
            return html;
        } catch (error) {
            console.error('Error loading article:', error);
            throw error;
        }
    }

    findArticleById(articleId) {
        if (!this.index) return null;
        for (const section of this.index.sections) {
            for (const item of section.items) {
                if (item.id === articleId) return item;
            }
        }
        return null;
    }
}

// Global fetcher instance (internal)
const docsFetcher = new DocsFetcher();
window.docsFetcher = docsFetcher;

document.addEventListener('alpine:init', () => {
    Alpine.store('docs', {
        isOpen: false,
        isLoading: false,
        currentHtml: '',
        currentTitle: '',
        index: null,

        async init() {
            // Preload index silently
            try {
                this.index = await docsFetcher.loadIndex();
            } catch (e) {
                console.warn('Docs index preload failed');
            }
        },

        async open(articleId = null) {
            this.isOpen = true;
            this.isLoading = true;

            try {
                if (!this.index) {
                    this.index = await docsFetcher.loadIndex();
                }

                // Default to intro if no ID
                const targetId = articleId || 'intro';
                const article = docsFetcher.findArticleById(targetId) || docsFetcher.findArticleById('intro');

                if (article) {
                    this.currentTitle = article.title;
                    this.currentHtml = await docsFetcher.loadArticle(article.file);
                } else {
                    this.currentTitle = 'Error';
                    this.currentHtml = '<p class="text-text-secondary">Documento no encontrado.</p>';
                }
            } catch (error) {
                this.currentTitle = 'Error';
                this.currentHtml = '<p class="text-danger">No se pudo cargar la documentación.</p>';
            } finally {
                this.isLoading = false;
            }
        },

        close() {
            this.isOpen = false;
        },

        toggle() {
            this.isOpen = !this.isOpen;
            if (this.isOpen) this.open();
        }
    });
});

// Expose a global helper for non-Alpine contexts if needed (legacy mimicry)
window.openHelp = (articleId) => {
    if (window.Alpine) {
        Alpine.store('docs').open(articleId);
    }
};


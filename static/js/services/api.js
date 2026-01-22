/**
 * ApiService - Centralized API Fetch Helper
 *
 * This module provides a shared `fetchJSON` utility for all Alpine.js components.
 * It handles:
 * - Cache-busting for GET requests
 * - JSON response parsing
 * - Error handling with detail extraction
 * - 204 No Content responses
 *
 * Usage:
 *   const data = await ApiService.fetchJSON('/api/clients/1');
 *   const result = await ApiService.fetchJSON('/api/clients', { method: 'POST', body: JSON.stringify(payload) });
 */
const ApiService = {
    API_BASE_URL: window.location.origin,

    /**
     * Fetch JSON from an API endpoint.
     * @param {string} url - The API endpoint (relative or absolute).
     * @param {RequestInit} options - Fetch options (method, body, headers, etc.).
     * @returns {Promise<any>} - Parsed JSON response or null for 204.
     * @throws {Error} - Throws an error with the detail message if the request fails.
     */
    async fetchJSON(url, options = {}) {
        const getUrl = new URL(url, this.API_BASE_URL);

        // Add cache-busting for GET requests
        if (!options.method || options.method === 'GET') {
            getUrl.searchParams.append('_', Date.now());
        }

        const response = await fetch(getUrl.toString(), options);

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(errorData.detail || 'API Request Failed');
        }

        return response.status === 204 ? null : response.json();
    }
};

// Expose globally for use in Alpine components
window.ApiService = ApiService;

console.log('[Service] ApiService initialized');

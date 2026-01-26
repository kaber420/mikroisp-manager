/**
 * API Utilities - Global Fetch Interceptor & Helper Class
 * 
 * 1. Intercepts all fetch requests (401 Redirect, 403 Logging).
 * 2. Exposes global 'ApiService' for standardized JSON requests.
 */

(function () {
    'use strict';

    // --- 1. Fetch Interceptor ---
    const originalFetch = window.fetch;

    function isOnAuthPage() {
        const path = window.location.pathname;
        return path === '/login' || path === '/logout';
    }

    window.fetch = async function (...args) {
        try {
            const response = await originalFetch.apply(this, args);
            const url = args[0]?.url || args[0];
            const isApiCall = typeof url === 'string' && url.includes('/api/');

            if (isApiCall) {
                if (response.status === 401 && !isOnAuthPage()) {
                    console.warn('[API] 401 Unauthorized - Session expired, redirecting to login');
                    window.location.href = '/login';
                    return new Promise(() => { }); // Never resolve
                }
                if (response.status === 403) {
                    console.warn('[API] 403 Forbidden - Permission denied for:', url);
                }
            }
            return response;
        } catch (error) {
            throw error;
        }
    };
})();

// --- 2. ApiService Helper ---
class ApiService {
    /**
     * Helper to fetch JSON data.
     * Throws error if response is not OK.
     */
    static async fetchJSON(url, options = {}) {
        const defaultHeaders = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        };

        const config = {
            ...options,
            headers: { ...defaultHeaders, ...options.headers }
        };

        try {
            const response = await fetch(url, config);

            // Parse JSON if possible
            let data;
            try {
                data = await response.json();
            } catch (e) {
                data = null;
            }

            if (!response.ok) {
                const errorMessage = data?.detail || data?.message || `HTTP Error ${response.status}`;
                throw new Error(errorMessage);
            }

            return data;
        } catch (error) {
            console.error(`[ApiService] Error fetching ${url}:`, error);
            throw error;
        }
    }
}

// Expose globally
window.ApiService = ApiService;
console.log('[API] ApiService initialized');

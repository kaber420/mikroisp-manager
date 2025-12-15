/**
 * API Utilities - Global Fetch Interceptor
 * 
 * This module intercepts all fetch requests and handles common HTTP errors:
 * - 401 Unauthorized: Redirects to login page
 * - 403 Forbidden: Does NOT auto-redirect (to prevent loops)
 * 
 * The 403 errors are passed through so each page can handle them appropriately.
 * For 403 on direct page navigation, the server-side handler in main.py will
 * render the 403.html template.
 * 
 * Usage: Include this script BEFORE any other JS files that use fetch.
 */

(function () {
    'use strict';

    // Store the original fetch
    const originalFetch = window.fetch;

    /**
     * Check if we're on an auth-related page
     */
    function isOnAuthPage() {
        const path = window.location.pathname;
        return path === '/login' || path === '/logout';
    }

    // Override global fetch
    window.fetch = async function (...args) {
        try {
            const response = await originalFetch.apply(this, args);

            // Only intercept API calls (not static assets, etc.)
            const url = args[0]?.url || args[0];
            const isApiCall = typeof url === 'string' && url.includes('/api/');

            if (isApiCall) {
                // Handle 401 - Redirect to login (session expired)
                if (response.status === 401 && !isOnAuthPage()) {
                    console.warn('[API] 401 Unauthorized - Session expired, redirecting to login');
                    window.location.href = '/login';
                    return new Promise(() => { });
                }

                // Handle 403 - Log but don't redirect
                // Let each page handle the error gracefully
                if (response.status === 403) {
                    console.warn('[API] 403 Forbidden - Permission denied for:', url);
                    // Return the response so the page can handle it
                    // (show error message, hide section, etc.)
                }
            }

            return response;
        } catch (error) {
            throw error;
        }
    };

    console.log('[API] Fetch interceptor initialized (401 redirect, 403 passthrough)');
})();

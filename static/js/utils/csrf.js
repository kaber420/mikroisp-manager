/**
 * CSRF Protection Utilities
 * Provides helper functions for CSRF token handling in AJAX requests.
 */

/**
 * Get the CSRF token from cookies
 * @returns {string|null} The CSRF token or null if not found
 */
function getCsrfToken() {
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'fastapi-csrf-token') {
            return decodeURIComponent(value);
        }
    }
    return null;
}

/**
 * Get default headers for API requests including CSRF token
 * @param {Object} additionalHeaders - Additional headers to include
 * @returns {Object} Headers object with Content-Type and CSRF token
 */
function getApiHeaders(additionalHeaders = {}) {
    const headers = {
        'Content-Type': 'application/json',
        ...additionalHeaders
    };

    const csrfToken = getCsrfToken();
    if (csrfToken) {
        headers['X-CSRF-Token'] = csrfToken;
    }

    return headers;
}

/**
 * Wrapper for fetch that automatically includes CSRF token
 * Use this for all POST, PUT, DELETE requests
 * @param {string} url - The URL to fetch
 * @param {Object} options - Fetch options
 * @returns {Promise} The fetch promise
 */
async function csrfFetch(url, options = {}) {
    const method = (options.method || 'GET').toUpperCase();

    // Only add CSRF token for mutating requests
    if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(method)) {
        options.headers = {
            ...options.headers,
            ...getApiHeaders()
        };
    }

    // Always include credentials for cookie-based auth
    options.credentials = options.credentials || 'include';

    return fetch(url, options);
}

// Export for module systems, also available globally
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { getCsrfToken, getApiHeaders, csrfFetch };
}

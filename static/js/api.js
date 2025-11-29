/**
 * API Service Layer (Task 73: API Integration Layer)
 * Centralized API calls with error handling, retry logic, and token management
 */

const API_BASE = window.API_BASE || 'http://localhost:8000/api';

// Token management
let authToken = localStorage.getItem('auth_token');
let refreshToken = localStorage.getItem('refresh_token');

/**
 * Set authentication tokens
 */
function setAuthTokens(accessToken, refresh, userInfo = null) {
    authToken = accessToken;
    refreshToken = refresh;
    if (accessToken) {
        localStorage.setItem('auth_token', accessToken);
    }
    if (refresh) {
        localStorage.setItem('refresh_token', refresh);
    }
    // Store user info (including role) for quick access
    if (userInfo) {
        localStorage.setItem('user_info', JSON.stringify(userInfo));
    }
}

/**
 * Clear authentication tokens
 */
function clearAuthTokens() {
    authToken = null;
    refreshToken = null;
    localStorage.removeItem('auth_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user_info');
}

/**
 * Get authentication token
 */
function getAuthToken() {
    return authToken || localStorage.getItem('auth_token');
}

/**
 * Get stored user info
 */
function getUserInfo() {
    const userInfoStr = localStorage.getItem('user_info');
    if (userInfoStr) {
        try {
            return JSON.parse(userInfoStr);
        } catch (e) {
            console.error('Error parsing user info:', e);
            return null;
        }
    }
    return null;
}

/**
 * API request with automatic token refresh and error handling
 */
async function apiRequest(endpoint, options = {}) {
    // Normalize endpoint - remove leading slash if present
    const normalizedEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint;
    
    // Normalize API_BASE - ensure it ends with exactly one slash
    let normalizedBase = API_BASE.trim();
    if (!normalizedBase.endsWith('/')) {
        normalizedBase += '/';
    }
    
    // Construct URL - normalizedEndpoint should not have leading slash
    const url = `${normalizedBase}${normalizedEndpoint}`;
    
    // Check if this is an auth endpoint (login/register) - don't include token
    const isAuthEndpoint = normalizedEndpoint.includes('/auth/login') || 
                          normalizedEndpoint.includes('/auth/register');
    
    const token = isAuthEndpoint ? null : getAuthToken();
    
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
    };
    
    if (token) {
        defaultOptions.headers['Authorization'] = `Bearer ${token}`;
    }
    
    const config = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...(options.headers || {}),
        },
    };
    
    try {
        const response = await fetch(url, config);
        
        // Handle 401 - try to refresh token (but skip for auth endpoints)
        const isAuthEndpoint = normalizedEndpoint.includes('/auth/login') || 
                              normalizedEndpoint.includes('/auth/register') ||
                              normalizedEndpoint.includes('/auth/refresh');
        
        if (response.status === 401 && token && refreshToken && !isAuthEndpoint) {
            const refreshed = await refreshAuthToken();
            if (refreshed) {
                // Retry original request with new token
                config.headers['Authorization'] = `Bearer ${getAuthToken()}`;
                const retryResponse = await fetch(url, config);
                return handleResponse(retryResponse);
            } else {
                // Refresh failed, redirect to login
                clearAuthTokens();
                window.location.href = 'login.html';
                throw new Error('Authentication failed');
            }
        }
        
        return handleResponse(response);
    } catch (error) {
        console.error('API request failed:', error);
        
        // Handle network errors
        if (error.message && (error.message.includes('Failed to fetch') || error.message.includes('Network'))) {
            if (window.errorHandler) {
                window.errorHandler.handleApiError({
                    message: 'Network error. Please check your connection.'
                }, 'API request');
            }
        }
        
        throw error;
    }
}

/**
 * Handle API response
 */
async function handleResponse(response) {
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
        // For 401 errors on auth endpoints, provide user-friendly message
        if (response.status === 401) {
            throw new Error(`HTTP ${response.status}`);
        }
        throw new Error(error.detail || `HTTP ${response.status}`);
    }
    return response.json();
}

/**
 * Refresh authentication token
 */
async function refreshAuthToken() {
    try {
        const response = await fetch(`${API_BASE}/auth/refresh`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ refresh_token: refreshToken }),
        });
        
        if (response.ok) {
            const data = await response.json();
            setAuthTokens(data.access_token, data.refresh_token || refreshToken);
            return true;
        }
        return false;
    } catch (error) {
        console.error('Token refresh failed:', error);
        return false;
    }
}

/**
 * GET request
 */
async function apiGet(endpoint, params = {}) {
    // Normalize endpoint first (remove leading slash)
    const normalizedEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint;
    
    // Build query string
    const queryString = new URLSearchParams(params).toString();
    const url = queryString ? `${normalizedEndpoint}?${queryString}` : normalizedEndpoint;
    
    return apiRequest(url, { method: 'GET' });
}

/**
 * POST request
 */
async function apiPost(endpoint, data = {}) {
    const normalizedEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint;
    const isAuthEndpoint = normalizedEndpoint.includes('/auth/login') || 
                          normalizedEndpoint.includes('/auth/register');
    
    // For auth endpoints, don't include Authorization header even if token exists
    const options = {
        method: 'POST',
        body: JSON.stringify(data),
    };
    
    // Remove Authorization header for login/register requests
    if (isAuthEndpoint) {
        options.headers = {
            'Content-Type': 'application/json',
        };
    }
    
    return apiRequest(endpoint, options);
}

/**
 * PUT request
 */
async function apiPut(endpoint, data = {}) {
    return apiRequest(endpoint, {
        method: 'PUT',
        body: JSON.stringify(data),
    });
}

/**
 * PATCH request
 */
async function apiPatch(endpoint, data = {}) {
    return apiRequest(endpoint, {
        method: 'PATCH',
        body: JSON.stringify(data),
    });
}

/**
 * DELETE request
 */
async function apiDelete(endpoint) {
    return apiRequest(endpoint, { method: 'DELETE' });
}

// Export for use in other modules
window.api = {
    get: apiGet,
    post: apiPost,
    put: apiPut,
    patch: apiPatch,
    delete: apiDelete,
    setAuthTokens,
    clearAuthTokens,
    getAuthToken,
    getUserInfo,
    request: apiRequest
};


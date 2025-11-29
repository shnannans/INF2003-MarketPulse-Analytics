/**
 * Authentication Module (Task 48: User Authentication & Authorization System)
 * Handles login, registration, password reset, and authentication state
 */

// Authentication state
let currentUser = null;
let userRole = null;

/**
 * Initialize authentication state
 */
async function initAuth() {
    const token = window.api.getAuthToken();
    if (token) {
        // Try to get user info from token or API - await to ensure it completes
        await loadUserInfo();
    }
    checkAuthState();
}

/**
 * Load user information
 */
async function loadUserInfo() {
    try {
        const token = window.api.getAuthToken();
        if (token) {
            // Try to get user info from localStorage first (stored during login)
            const storedUserInfo = window.api.getUserInfo();
            if (storedUserInfo) {
                currentUser = storedUserInfo;
                userRole = currentUser.role || 'user';
                updateUIForAuth();
                return;
            }
            
            // Fallback: Try to decode as JWT (for backward compatibility)
            try {
                // Check if token is a valid JWT format (has 3 parts separated by dots)
                const parts = token.split('.');
                if (parts.length === 3) {
                    // Decode the payload (second part)
                    const payloadBase64 = parts[1];
                    // Add padding if needed for base64 decoding
                    const padded = payloadBase64 + '='.repeat((4 - payloadBase64.length % 4) % 4);
                    const payload = JSON.parse(atob(padded));
                    
                    currentUser = {
                        id: payload.sub || payload.user_id,
                        username: payload.username || payload.email?.split('@')[0] || 'User',
                        email: payload.email,
                        role: payload.role || 'user',
                    };
                    userRole = currentUser.role;
                    updateUIForAuth();
                    return;
                }
            } catch (e) {
                // Token is not JWT format, which is expected for this API
                // Try to get user info from API endpoint
                console.log('Token is not JWT format, attempting to fetch user info from API');
            }
            
            // If we have a token but no user info, try to fetch from API
            // Note: This would require a /auth/me endpoint, which may not exist
            // For now, we'll just use the stored info or default to 'user'
            if (!currentUser) {
                console.warn('No user info available. User may need to log in again.');
            }
        }
    } catch (error) {
        console.error('Error loading user info:', error);
    }
}

/**
 * Check authentication state and redirect if needed
 */
function checkAuthState() {
    const token = window.api.getAuthToken();
    const currentPage = window.location.pathname;
    
    // Normalize pathname - remove leading slash and handle different formats
    const normalizedPath = currentPage.replace(/^\/+/, '').toLowerCase();
    
    // Pages that require authentication
    const protectedPages = ['admin', 'profile', 'index.html'];
    
    // Pages that should redirect if already authenticated
    const authPages = ['login.html', 'register.html'];
    
    // Check if current page is a protected page
    const isProtectedPage = protectedPages.some(page => normalizedPath.includes(page));
    const isAuthPage = authPages.some(page => normalizedPath.includes(page));
    
    // Redirect to login if accessing protected page without token
    if (!token && isProtectedPage) {
        window.location.href = 'login.html';
        return;
    }
    
    // Redirect based on role if accessing auth pages with valid token
    if (token && isAuthPage) {
        // Check if token is valid by trying to decode it
        try {
            const parts = token.split('.');
            if (parts.length === 3) {
                // Try to decode the payload to verify it's a valid JWT
                const payloadBase64 = parts[1];
                const padded = payloadBase64 + '='.repeat((4 - payloadBase64.length % 4) % 4);
                const payload = JSON.parse(atob(padded));
                
                // Check if payload has required fields (basic validation)
                if (payload && (payload.sub || payload.user_id || payload.email)) {
                    // Token appears valid, redirect based on role
                    const role = payload.role || 'user';
                    if (role === 'admin') {
                        window.location.href = 'admin.html';
                    } else {
                        window.location.href = 'index.html';
                    }
                    return;
                }
            }
        } catch (e) {
            // Invalid token, allow access to auth pages
            console.log('Invalid token, allowing access to auth page');
        }
    }
}

/**
 * Update UI based on authentication state
 */
function updateUIForAuth() {
    const token = window.api.getAuthToken();
    const loginLinks = document.querySelectorAll('.login-link');
    const logoutLinks = document.querySelectorAll('.logout-link');
    const adminLinks = document.querySelectorAll('.admin-only');
    const userLinks = document.querySelectorAll('.user-only');
    const welcomeMessage = document.getElementById('welcomeMessage');
    const usernameDisplay = document.getElementById('usernameDisplay');
    const profileIcon = document.getElementById('profileIcon');
    
    if (token) {
        // User is logged in - hide login/signup, show logout and user/admin links
        loginLinks.forEach(link => link.style.display = 'none');
        logoutLinks.forEach(link => link.style.display = 'inline-block');
        
        // Show welcome message with username
        if (welcomeMessage) {
            welcomeMessage.style.display = 'inline-block';
        }
        if (usernameDisplay && currentUser) {
            // Get username from currentUser, fallback to email or email prefix
            const username = currentUser.username || currentUser.email?.split('@')[0] || 'User';
            usernameDisplay.textContent = username;
        }
        if (profileIcon) {
            profileIcon.style.display = 'inline-block';
        }
        
        // Show/hide based on role
        if (userRole === 'admin') {
            adminLinks.forEach(link => link.style.display = 'inline-block');
        } else {
            adminLinks.forEach(link => link.style.display = 'none');
        }
        
        userLinks.forEach(link => link.style.display = 'inline-block');
    } else {
        // User is not logged in - show login/signup, hide user-specific links
        loginLinks.forEach(link => link.style.display = 'inline-block');
        logoutLinks.forEach(link => link.style.display = 'none');
        adminLinks.forEach(link => link.style.display = 'none');
        userLinks.forEach(link => link.style.display = 'none');
        
        if (welcomeMessage) {
            welcomeMessage.style.display = 'none';
        }
        if (profileIcon) {
            profileIcon.style.display = 'none';
        }
    }
}

/**
 * Login user
 */
async function login(email, password) {
    try {
        const response = await window.api.post('/auth/login', {
            email: email,
            password: password,
        });
        
        if (response.access_token) {
            // API returns user object with username, email, role, etc.
            currentUser = response.user || {
                id: response.user?.id,
                email: email,
                username: response.user?.username || response.username || email.split('@')[0] || 'User',
                role: response.user?.role || response.role || 'user',
            };
            userRole = currentUser.role;
            
            // Store tokens and user info (including role) in localStorage
            window.api.setAuthTokens(
                response.access_token,
                response.refresh_token,
                currentUser  // Store user info for quick access
            );
            
            updateUIForAuth();
            
            // Return user info including username for display
            return { 
                success: true, 
                user: currentUser,
                role: userRole
            };
        }
        
        return { success: false, error: 'Invalid response from server' };
    } catch (error) {
        // Check for 401 Unauthorized error (wrong email/password)
        if (error.message && (error.message.includes('401') || error.message.includes('Unauthorized'))) {
            return { success: false, error: 'Wrong Email or Password. Try Again...' };
        }
        return { success: false, error: error.message || 'Login failed' };
    }
}

/**
 * Register new user
 */
async function register(userData) {
    try {
        const response = await window.api.post('/users', {
            username: userData.username,
            email: userData.email,
            password: userData.password,
            role: 'user', // Default role
        });
        
        if (response.status === 'success') {
            // Auto-login after registration
            return await login(userData.email, userData.password);
        }
        
        return { success: false, error: response.message || 'Registration failed' };
    } catch (error) {
        return { success: false, error: error.message || 'Registration failed' };
    }
}

/**
 * Logout user
 */
function logout() {
    window.api.clearAuthTokens();
    currentUser = null;
    userRole = null;
    updateUIForAuth();
    window.location.href = 'login.html';
}

/**
 * Check if user is authenticated
 */
function isAuthenticated() {
    return !!window.api.getAuthToken();
}

/**
 * Check if user is admin
 */
function isAdmin() {
    return userRole === 'admin';
}

/**
 * Get current user
 */
function getCurrentUser() {
    return currentUser;
}

/**
 * Get user role
 */
function getUserRole() {
    return userRole;
}

// Export for use in other modules
window.auth = {
    init: initAuth,
    login,
    register,
    logout,
    isAuthenticated,
    isAdmin,
    getCurrentUser,
    getUserRole,
    checkAuthState,
    updateUIForAuth,
    loadUserInfo,  // Export loadUserInfo so admin.js can call it
};

// Initialize on page load (async, but don't block)
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        initAuth().catch(err => console.error('Error initializing auth:', err));
    });
} else {
    initAuth().catch(err => console.error('Error initializing auth:', err));
}


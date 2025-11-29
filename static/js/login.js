/**
 * Login Page Handler (Task 48: User Authentication & Authorization System)
 */

document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('loginForm');
    const loginButton = document.getElementById('loginButton');
    const errorAlert = document.getElementById('errorAlert');
    const successAlert = document.getElementById('successAlert');
    const spinner = loginButton.querySelector('.loading-spinner');
    
    // Check if already logged in (with valid token)
    const token = window.api && window.api.getAuthToken ? window.api.getAuthToken() : null;
    if (token) {
        // Verify token is valid before redirecting
        try {
            const parts = token.split('.');
            if (parts.length === 3) {
                const payloadBase64 = parts[1];
                const padded = payloadBase64 + '='.repeat((4 - payloadBase64.length % 4) % 4);
                const payload = JSON.parse(atob(padded));
                if (payload && (payload.sub || payload.user_id || payload.email)) {
                    // Valid token, redirect to index
                    window.location.href = 'index.html';
                    return;
                }
            }
        } catch (e) {
            // Invalid token, allow login
            console.log('Invalid token, allowing login');
        }
    }
    
    loginForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Hide previous alerts
        errorAlert.style.display = 'none';
        successAlert.style.display = 'none';
        
        // Get form data
        const email = document.getElementById('email').value.trim();
        const password = document.getElementById('password').value;
        const rememberMe = document.getElementById('rememberMe').checked;
        
        // Validate
        if (!email || !password) {
            showError('Please enter both email and password');
            return;
        }
        
        // Show loading state
        setLoadingState(true);
        
        try {
            // Attempt login
            const result = await window.auth.login(email, password);
            
            if (result.success) {
                showSuccess('Login successful! Redirecting...');
                
                // Store remember me preference
                if (rememberMe) {
                    localStorage.setItem('remember_me', 'true');
                }
                
                // Redirect based on user role
                setTimeout(() => {
                    const role = result.role || result.user?.role || 'user';
                    if (role === 'admin') {
                        window.location.href = 'admin.html';
                    } else {
                        window.location.href = 'index.html';
                    }
                }, 1000);
            } else {
                showError(result.error || 'Login failed. Please check your credentials.');
                setLoadingState(false);
            }
        } catch (error) {
            // Check for 401 Unauthorized error (wrong email/password)
            if (error.message && (error.message.includes('401') || error.message.includes('Unauthorized'))) {
                showError('Wrong Email or Password. Try Again...');
            } else {
                showError(error.message || 'An error occurred during login. Please try again.');
            }
            setLoadingState(false);
        }
    });
    
    function setLoadingState(loading) {
        loginButton.disabled = loading;
        if (loading) {
            spinner.classList.add('active');
            loginButton.querySelector('span:not(.loading-spinner)')?.remove();
        } else {
            spinner.classList.remove('active');
        }
    }
    
    function showError(message) {
        errorAlert.textContent = message;
        errorAlert.style.display = 'block';
        errorAlert.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    
    function showSuccess(message) {
        successAlert.textContent = message;
        successAlert.style.display = 'block';
    }
    
    // Auto-focus email field
    document.getElementById('email').focus();
});


/**
 * Registration Page Handler (Task 48: User Authentication & Authorization System)
 */

document.addEventListener('DOMContentLoaded', function() {
    const registerForm = document.getElementById('registerForm');
    const registerButton = document.getElementById('registerButton');
    const errorAlert = document.getElementById('errorAlert');
    const successAlert = document.getElementById('successAlert');
    const spinner = registerButton.querySelector('.loading-spinner');
    
    const usernameInput = document.getElementById('username');
    const emailInput = document.getElementById('email');
    const passwordInput = document.getElementById('password');
    const confirmPasswordInput = document.getElementById('confirmPassword');
    const termsCheckbox = document.getElementById('terms');
    
    const passwordStrengthText = document.getElementById('passwordStrengthText');
    const passwordStrengthFill = document.getElementById('passwordStrengthFill');
    
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
            // Invalid token, allow registration
            console.log('Invalid token, allowing registration');
        }
    }
    
    // Username validation
    usernameInput.addEventListener('input', function() {
        validateUsername();
    });
    
    // Email validation
    emailInput.addEventListener('input', function() {
        validateEmail();
    });
    
    // Password strength check
    passwordInput.addEventListener('input', function() {
        checkPasswordStrength();
        validatePasswordMatch();
    });
    
    // Confirm password validation
    confirmPasswordInput.addEventListener('input', function() {
        validatePasswordMatch();
    });
    
    // Form submission
    registerForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Hide previous alerts
        errorAlert.style.display = 'none';
        successAlert.style.display = 'none';
        
        // Validate all fields
        const isUsernameValid = validateUsername();
        const isEmailValid = validateEmail();
        const isPasswordValid = validatePassword();
        const isPasswordMatchValid = validatePasswordMatch();
        const isTermsValid = validateTerms();
        
        if (!isUsernameValid || !isEmailValid || !isPasswordValid || !isPasswordMatchValid || !isTermsValid) {
            showError('Please fix the errors in the form');
            return;
        }
        
        // Show loading state
        setLoadingState(true);
        
        try {
            // Attempt registration
            const result = await window.auth.register({
                username: usernameInput.value.trim(),
                email: emailInput.value.trim(),
                password: passwordInput.value,
            });
            
            if (result.success) {
                showSuccess('Account created successfully! Redirecting...');
                
                // Redirect back to login page after registration
                setTimeout(() => {
                    window.location.href = 'login.html';
                }, 1500);
            } else {
                showError(result.error || 'Registration failed. Please try again.');
                setLoadingState(false);
            }
        } catch (error) {
            showError(error.message || 'An error occurred during registration. Please try again.');
            setLoadingState(false);
        }
    });
    
    function validateUsername() {
        const username = usernameInput.value.trim();
        const pattern = /^[a-zA-Z0-9_]{3,20}$/;
        
        if (!username) {
            setFieldError(usernameInput, 'Username is required');
            return false;
        }
        
        if (!pattern.test(username)) {
            setFieldError(usernameInput, 'Username must be 3-20 characters (letters, numbers, underscores only)');
            return false;
        }
        
        setFieldValid(usernameInput);
        return true;
    }
    
    function validateEmail() {
        const email = emailInput.value.trim();
        const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        
        if (!email) {
            setFieldError(emailInput, 'Email is required');
            return false;
        }
        
        if (!pattern.test(email)) {
            setFieldError(emailInput, 'Please enter a valid email address');
            return false;
        }
        
        setFieldValid(emailInput);
        return true;
    }
    
    function validatePassword() {
        const password = passwordInput.value;
        
        if (!password) {
            setFieldError(passwordInput, 'Password is required');
            return false;
        }
        
        if (password.length < 8) {
            setFieldError(passwordInput, 'Password must be at least 8 characters');
            return false;
        }
        
        setFieldValid(passwordInput);
        return true;
    }
    
    function validatePasswordMatch() {
        const password = passwordInput.value;
        const confirmPassword = confirmPasswordInput.value;
        
        if (!confirmPassword) {
            setFieldError(confirmPasswordInput, 'Please confirm your password');
            return false;
        }
        
        if (password !== confirmPassword) {
            setFieldError(confirmPasswordInput, 'Passwords do not match');
            return false;
        }
        
        setFieldValid(confirmPasswordInput);
        return true;
    }
    
    function validateTerms() {
        if (!termsCheckbox.checked) {
            termsCheckbox.classList.add('is-invalid');
            return false;
        }
        
        termsCheckbox.classList.remove('is-invalid');
        return true;
    }
    
    function checkPasswordStrength() {
        const password = passwordInput.value;
        
        if (!password) {
            passwordStrengthText.textContent = '';
            passwordStrengthFill.className = 'password-strength-fill';
            passwordStrengthFill.style.width = '0%';
            return;
        }
        
        // Check password strength
        let strength = 0;
        let strengthText = '';
        let strengthClass = '';
        
        if (password.length >= 8) strength++;
        if (password.length >= 12) strength++;
        if (/[a-z]/.test(password)) strength++;
        if (/[A-Z]/.test(password)) strength++;
        if (/[0-9]/.test(password)) strength++;
        if (/[^a-zA-Z0-9]/.test(password)) strength++;
        
        if (strength <= 2) {
            strengthText = 'Weak';
            strengthClass = 'weak';
        } else if (strength <= 4) {
            strengthText = 'Medium';
            strengthClass = 'medium';
        } else {
            strengthText = 'Strong';
            strengthClass = 'strong';
        }
        
        passwordStrengthText.textContent = `Password strength: ${strengthText}`;
        passwordStrengthFill.className = `password-strength-fill ${strengthClass}`;
    }
    
    function setFieldError(field, message) {
        field.classList.remove('is-valid');
        field.classList.add('is-invalid');
        const feedback = field.nextElementSibling;
        if (feedback && feedback.classList.contains('invalid-feedback')) {
            feedback.textContent = message;
        }
    }
    
    function setFieldValid(field) {
        field.classList.remove('is-invalid');
        field.classList.add('is-valid');
    }
    
    function setLoadingState(loading) {
        registerButton.disabled = loading;
        if (loading) {
            spinner.classList.add('active');
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
    
    // Auto-focus username field
    usernameInput.focus();
});


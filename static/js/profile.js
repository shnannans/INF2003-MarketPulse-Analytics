/**
 * Profile Page Handler (Task 49: User Management Interface - Profile Page)
 */

let currentUserId = null;

document.addEventListener('DOMContentLoaded', async function() {
    // Check authentication
    if (!window.auth || !window.auth.isAuthenticated()) {
                window.location.href = 'login.html';
        return;
    }
    
    // Get current user
    const user = window.auth.getCurrentUser();
    if (!user || !user.id) {
        // Try to load user info
        await loadUserProfile();
    } else {
        currentUserId = user.id;
        await loadUserProfile();
    }
    
    // Setup form handlers
    setupProfileForm();
    setupPasswordForm();
});

async function loadUserProfile() {
    try {
        const user = window.auth.getCurrentUser();
        
        if (!user || !user.id) {
            // Try to get user from API
            const token = window.api.getAuthToken();
            if (!token) {
                window.location.href = 'login.html';
                return;
            }
            
            // For now, we'll use a placeholder - in production, you'd have a /api/users/me endpoint
            showError('Unable to load user profile. Please log in again.');
            return;
        }
        
        currentUserId = user.id;
        
        // Load user details from API
        const response = await window.api.get(`/users/${currentUserId}`);
        
        if (response.status === 'success' && response.user) {
            const userData = response.user;
            
            // Update UI
            document.getElementById('userName').textContent = userData.username || 'User';
            document.getElementById('userEmail').textContent = userData.email || '';
            document.getElementById('userRole').textContent = userData.role || 'user';
            document.getElementById('userRole').className = `badge ${userData.role === 'admin' ? 'bg-danger' : 'bg-primary'} mt-2`;
            
            // Update avatar
            const avatar = document.getElementById('userAvatar');
            avatar.textContent = (userData.username || 'U').charAt(0).toUpperCase();
            
            // Update form fields
            document.getElementById('username').value = userData.username || '';
            document.getElementById('email').value = userData.email || '';
            document.getElementById('role').value = userData.role || 'user';
            document.getElementById('status').value = userData.is_active ? 'Active' : 'Inactive';
            document.getElementById('createdAt').value = userData.created_at ? new Date(userData.created_at).toLocaleDateString() : 'N/A';
            document.getElementById('updatedAt').value = userData.updated_at ? new Date(userData.updated_at).toLocaleDateString() : 'N/A';
        }
    } catch (error) {
        console.error('Error loading profile:', error);
        showError('Failed to load profile. Please try again.');
    }
}

function setupProfileForm() {
    const form = document.getElementById('profileForm');
    const saveButton = document.getElementById('saveProfileButton');
    
    // Password strength check
    const newPasswordInput = document.getElementById('newPassword');
    if (newPasswordInput) {
        newPasswordInput.addEventListener('input', checkPasswordStrength);
    }
    
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const email = document.getElementById('email').value.trim();
        
        if (!email) {
            showError('Email is required');
            return;
        }
        
        saveButton.disabled = true;
        // Spinner removed - button disabled state used instead
        
        try {
            const response = await window.api.patch(`/users/${currentUserId}`, {
                email: email
            });
            
            if (response.status === 'success') {
                showSuccess('Profile updated successfully!');
                await loadUserProfile(); // Reload to get updated data
            } else {
                showError(response.message || 'Failed to update profile');
            }
        } catch (error) {
            showError(error.message || 'Failed to update profile. Please try again.');
        } finally {
            saveButton.disabled = false;
            // Spinner removed - button re-enabled
        }
    });
}

function setupPasswordForm() {
    const form = document.getElementById('passwordForm');
    const changeButton = document.getElementById('changePasswordButton');
    
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const currentPassword = document.getElementById('currentPassword').value;
        const newPassword = document.getElementById('newPassword').value;
        const confirmPassword = document.getElementById('confirmNewPassword').value;
        
        // Validate
        if (!currentPassword || !newPassword || !confirmPassword) {
            showError('All password fields are required');
            return;
        }
        
        if (newPassword.length < 8) {
            showError('New password must be at least 8 characters');
            return;
        }
        
        if (newPassword !== confirmPassword) {
            showError('New passwords do not match');
            return;
        }
        
        changeButton.disabled = true;
        // Spinner removed - button disabled state used instead
        
        try {
            const response = await window.api.patch(`/users/${currentUserId}/password`, {
                current_password: currentPassword,
                new_password: newPassword
            });
            
            if (response.status === 'success') {
                showSuccess('Password changed successfully!');
                form.reset();
                document.getElementById('passwordStrengthText').textContent = '';
                document.getElementById('passwordStrengthFill').style.width = '0%';
            } else {
                showError(response.message || 'Failed to change password');
            }
        } catch (error) {
            showError(error.message || 'Failed to change password. Please check your current password.');
        } finally {
            changeButton.disabled = false;
            // Spinner removed - button re-enabled
        }
    });
}

function checkPasswordStrength() {
    const password = document.getElementById('newPassword').value;
    const strengthText = document.getElementById('passwordStrengthText');
    const strengthFill = document.getElementById('passwordStrengthFill');
    
    if (!password) {
        strengthText.textContent = '';
        strengthFill.style.width = '0%';
        strengthFill.className = 'progress-bar';
        return;
    }
    
    let strength = 0;
    let strengthLabel = '';
    let strengthClass = '';
    
    if (password.length >= 8) strength++;
    if (password.length >= 12) strength++;
    if (/[a-z]/.test(password)) strength++;
    if (/[A-Z]/.test(password)) strength++;
    if (/[0-9]/.test(password)) strength++;
    if (/[^a-zA-Z0-9]/.test(password)) strength++;
    
    if (strength <= 2) {
        strengthLabel = 'Weak';
        strengthClass = 'bg-danger';
        strengthFill.style.width = '33%';
    } else if (strength <= 4) {
        strengthLabel = 'Medium';
        strengthClass = 'bg-warning';
        strengthFill.style.width = '66%';
    } else {
        strengthLabel = 'Strong';
        strengthClass = 'bg-success';
        strengthFill.style.width = '100%';
    }
    
    strengthText.textContent = `Password strength: ${strengthLabel}`;
    strengthFill.className = `progress-bar ${strengthClass}`;
}

function showError(message) {
    // Auto-hide loading overlay when error appears
    if (window.utils && window.utils.hideLoadingOverlay) {
        setTimeout(() => {
            window.utils.hideLoadingOverlay();
        }, 300);
    }
    
    const alert = document.getElementById('errorAlert');
    alert.textContent = message;
    alert.style.display = 'block';
    alert.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    
    // Hide after 5 seconds
    setTimeout(() => {
        alert.style.display = 'none';
    }, 5000);
}

function showSuccess(message) {
    // Auto-hide loading overlay when success appears
    if (window.utils && window.utils.hideLoadingOverlay) {
        setTimeout(() => {
            window.utils.hideLoadingOverlay();
        }, 300);
    }
    
    const alert = document.getElementById('successAlert');
    alert.textContent = message;
    alert.style.display = 'block';
    alert.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    
    // Hide after 5 seconds
    setTimeout(() => {
        alert.style.display = 'none';
    }, 5000);
}


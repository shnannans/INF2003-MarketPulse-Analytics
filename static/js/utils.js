/**
 * Utility Functions for Frontend
 * Common helper functions used across the application
 */

/**
 * Show toast notification (Task 74: Notification System)
 */
function showToast(message, type = 'info', duration = 5000) {
    // Loading overlay removed - no longer auto-hiding overlay
    
    // Create toast container if it doesn't exist
    let toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toastContainer';
        toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
        toastContainer.style.zIndex = '9999';
        document.body.appendChild(toastContainer);
    }
    
    // Create toast element
    const toastId = `toast-${Date.now()}`;
    const bgClass = {
        'success': 'bg-success',
        'error': 'bg-danger',
        'warning': 'bg-warning',
        'info': 'bg-info'
    }[type] || 'bg-info';
    
    const icon = {
        'success': 'bi-check-circle',
        'error': 'bi-x-circle',
        'warning': 'bi-exclamation-triangle',
        'info': 'bi-info-circle'
    }[type] || 'bi-info-circle';
    
    const toastHTML = `
        <div id="${toastId}" class="toast ${bgClass} text-white" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header ${bgClass} text-white">
                <i class="bi ${icon} me-2"></i>
                <strong class="me-auto">${type.charAt(0).toUpperCase() + type.slice(1)}</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">
                ${escapeHtml(message)}
            </div>
        </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', toastHTML);
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, {
        autohide: true,
        delay: duration
    });
    toast.show();
    
    // Remove element after it's hidden
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}

// Loading overlay removed - functions are no-ops
let loadingOverlayTimeout = null;

/**
 * Show loading spinner overlay (removed - no-op)
 */
function showLoadingOverlay(message = 'Loading...') {
    // Loading overlay removed - do nothing
    // This function is kept for backward compatibility but does nothing
}

/**
 * Hide loading spinner overlay (removed - no-op)
 */
function hideLoadingOverlay() {
    // Loading overlay removed - do nothing
    // This function is kept for backward compatibility but does nothing
    // Remove any existing overlay from DOM if it exists
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.remove();
    }
    // Clear timeout if it exists
    if (loadingOverlayTimeout) {
        clearTimeout(loadingOverlayTimeout);
        loadingOverlayTimeout = null;
    }
}

/**
 * Show error page (Task 62: Error Handling & User Feedback - Error States)
 */
function showErrorPage(errorType, message, details = null) {
    const errorPages = {
        404: {
            title: 'Page Not Found',
            message: 'The page you are looking for does not exist.',
            icon: 'bi-exclamation-triangle'
        },
        403: {
            title: 'Access Forbidden',
            message: 'You do not have permission to access this resource.',
            icon: 'bi-shield-x'
        },
        500: {
            title: 'Server Error',
            message: 'An error occurred on the server. Please try again later.',
            icon: 'bi-server'
        },
        network: {
            title: 'Network Error',
            message: 'Unable to connect to the server. Please check your internet connection.',
            icon: 'bi-wifi-off'
        }
    };
    
    const errorInfo = errorPages[errorType] || {
        title: 'Error',
        message: message || 'An unexpected error occurred.',
        icon: 'bi-exclamation-circle'
    };
    
    document.body.innerHTML = `
        <div class="container d-flex align-items-center justify-content-center" style="min-height: 100vh;">
            <div class="text-center">
                <i class="bi ${errorInfo.icon}" style="font-size: 5rem; color: #dc3545;"></i>
                <h1 class="mt-4">${errorInfo.title}</h1>
                <p class="text-muted">${errorInfo.message}</p>
                ${details ? `<p class="text-muted small">${escapeHtml(details)}</p>` : ''}
                <div class="mt-4">
                    <a href="index.html" class="btn btn-primary me-2">Go to Dashboard</a>
                    <button class="btn btn-outline-secondary" onclick="window.location.reload()">Retry</button>
                </div>
            </div>
        </div>
    `;
}

/**
 * Format number with commas
 */
function formatNumber(num) {
    if (num === null || num === undefined) return 'N/A';
    return num.toLocaleString();
}

/**
 * Format currency
 */
function formatCurrency(amount) {
    if (amount === null || amount === undefined) return 'N/A';
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(amount);
}

/**
 * Format percentage
 */
function formatPercentage(value, decimals = 2) {
    if (value === null || value === undefined) return 'N/A';
    return `${value >= 0 ? '+' : ''}${value.toFixed(decimals)}%`;
}

/**
 * Format date
 */
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

/**
 * Format datetime
 */
function formatDateTime(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Debounce function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Check if element is in viewport
 */
function isInViewport(element) {
    const rect = element.getBoundingClientRect();
    return (
        rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
        rect.right <= (window.innerWidth || document.documentElement.clientWidth)
    );
}

/**
 * Lazy load images
 */
function lazyLoadImages() {
    const images = document.querySelectorAll('img[data-src]');
    images.forEach(img => {
        if (isInViewport(img)) {
            img.src = img.dataset.src;
            img.removeAttribute('data-src');
        }
    });
}

// Export for use in other modules
window.utils = {
    showToast,
    showLoadingOverlay,
    hideLoadingOverlay,
    showErrorPage,
    formatNumber,
    formatCurrency,
    formatPercentage,
    formatDate,
    formatDateTime,
    escapeHtml,
    debounce,
    isInViewport,
    lazyLoadImages
};


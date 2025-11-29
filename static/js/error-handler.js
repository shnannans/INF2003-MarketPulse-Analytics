/**
 * Error Handler (Task 62: Error Handling & User Feedback - Error States)
 */

// Global error handler
window.addEventListener('error', function(event) {
    console.error('Global error:', event.error);
    handleError(event.error);
});

// Unhandled promise rejection handler
window.addEventListener('unhandledrejection', function(event) {
    console.error('Unhandled promise rejection:', event.reason);
    handleError(event.reason);
});

// Network error handler
window.addEventListener('online', function() {
    if (window.utils) {
        window.utils.showToast('Connection restored', 'success');
    }
});

window.addEventListener('offline', function() {
    if (window.utils) {
        window.utils.showToast('No internet connection', 'warning');
    }
});

function handleError(error) {
    // Don't show error page for minor errors
    if (error && error.message && error.message.includes('favicon')) {
        return;
    }
    
    // Show user-friendly error message
    if (window.utils) {
        const message = error?.message || 'An unexpected error occurred';
        window.utils.showToast(message, 'error', 7000);
    }
}

/**
 * Handle API errors
 */
function handleApiError(error, context = 'operation') {
    if (!error) return;
    
    let errorMessage = 'An error occurred';
    let errorType = 'generic';
    
    if (error.message) {
        errorMessage = error.message;
        
        // Categorize error types
        if (errorMessage.includes('401') || errorMessage.includes('Unauthorized')) {
            errorType = 'auth';
            errorMessage = 'Authentication required. Please log in.';
        } else if (errorMessage.includes('403') || errorMessage.includes('Forbidden')) {
            errorType = 'permission';
            errorMessage = 'You do not have permission to perform this action.';
        } else if (errorMessage.includes('404') || errorMessage.includes('Not Found')) {
            errorType = 'notfound';
            errorMessage = 'The requested resource was not found.';
        } else if (errorMessage.includes('500') || errorMessage.includes('Server Error')) {
            errorType = 'server';
            errorMessage = 'Server error. Please try again later.';
        } else if (errorMessage.includes('Network') || errorMessage.includes('Failed to fetch')) {
            errorType = 'network';
            errorMessage = 'Network error. Please check your connection.';
        }
    }
    
    // Show appropriate error UI
    if (errorType === 'auth') {
        // Redirect to login
        setTimeout(() => {
            window.location.href = 'login.html?redirect=' + encodeURIComponent(window.location.pathname);
        }, 2000);
    }
    
    if (window.utils) {
        window.utils.showToast(`${context}: ${errorMessage}`, 'error', 7000);
    } else {
        alert(`${context}: ${errorMessage}`);
    }
    
    return {
        type: errorType,
        message: errorMessage
    };
}

/**
 * Retry function with exponential backoff
 */
async function retryWithBackoff(fn, maxRetries = 3, initialDelay = 1000) {
    let delay = initialDelay;
    
    for (let i = 0; i < maxRetries; i++) {
        try {
            return await fn();
        } catch (error) {
            if (i === maxRetries - 1) {
                throw error;
            }
            
            // Wait before retrying
            await new Promise(resolve => setTimeout(resolve, delay));
            delay *= 2; // Exponential backoff
        }
    }
}

// Export for use in other modules
window.errorHandler = {
    handleError,
    handleApiError,
    retryWithBackoff
};


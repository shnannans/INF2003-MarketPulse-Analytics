/**
 * Loading States Manager (Task 63: Error Handling & User Feedback - Loading States)
 */

const loadingStates = new Map();

/**
 * Create a loading state
 */
function createLoadingState(operationId, message = 'Loading...') {
    loadingStates.set(operationId, {
        id: operationId,
        message: message,
        startTime: Date.now(),
        isComplete: false
    });
    
    // Show loading indicator
    showLoadingIndicator(operationId, message);
}

/**
 * Update loading state
 */
function updateLoadingState(operationId, progress, message = null) {
    const state = loadingStates.get(operationId);
    if (!state) return;
    
    if (message) {
        state.message = message;
    }
    
    updateLoadingIndicator(operationId, progress, state.message);
}

/**
 * Complete loading state
 */
function completeLoadingState(operationId) {
    const state = loadingStates.get(operationId);
    if (!state) return;
    
    state.isComplete = true;
    state.duration = Date.now() - state.startTime;
    
    hideLoadingIndicator(operationId);
    loadingStates.delete(operationId);
}

/**
 * Cancel loading state
 */
function cancelLoadingState(operationId) {
    const state = loadingStates.get(operationId);
    if (!state) return;
    
    hideLoadingIndicator(operationId);
    loadingStates.delete(operationId);
}

/**
 * Show loading indicator
 */
function showLoadingIndicator(operationId, message) {
    // Create or update loading indicator
    let indicator = document.getElementById(`loading-${operationId}`);
    
    if (!indicator) {
        indicator = document.createElement('div');
        indicator.id = `loading-${operationId}`;
        indicator.className = 'loading-indicator position-fixed bottom-0 end-0 m-3';
        indicator.style.zIndex = '9999';
        document.body.appendChild(indicator);
    }
    
    indicator.innerHTML = `
        <div class="card shadow">
            <div class="card-body d-flex align-items-center">
                <div class="text-primary me-3" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <div>
                    <div class="fw-bold">${escapeHtml(message)}</div>
                    <div class="progress mt-2" style="height: 4px; width: 200px;">
                        <div class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" style="width: 100%"></div>
                    </div>
                </div>
            </div>
        </div>
    `;
    indicator.style.display = 'block';
}

/**
 * Update loading indicator
 */
function updateLoadingIndicator(operationId, progress, message) {
    const indicator = document.getElementById(`loading-${operationId}`);
    if (!indicator) return;
    
    const messageEl = indicator.querySelector('.fw-bold');
    const progressBar = indicator.querySelector('.progress-bar');
    
    if (messageEl && message) {
        messageEl.textContent = message;
    }
    
    if (progressBar && typeof progress === 'number') {
        progressBar.style.width = `${Math.min(100, Math.max(0, progress))}%`;
    }
}

/**
 * Hide loading indicator
 */
function hideLoadingIndicator(operationId) {
    const indicator = document.getElementById(`loading-${operationId}`);
    if (indicator) {
        indicator.style.display = 'none';
        // Remove after animation
        setTimeout(() => {
            if (indicator.parentNode) {
                indicator.remove();
            }
        }, 300);
    }
}

/**
 * Show skeleton loader
 */
function showSkeletonLoader(containerId, count = 3) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    container.innerHTML = Array(count).fill(0).map(() => `
        <div class="skeleton mb-3" style="height: 60px; border-radius: 8px;"></div>
    `).join('');
}

/**
 * Show progress bar
 */
function showProgressBar(containerId, label = 'Loading...') {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    container.innerHTML = `
        <div class="progress" style="height: 25px;">
            <div class="progress-bar progress-bar-striped progress-bar-animated" 
                 role="progressbar" 
                 style="width: 0%" 
                 aria-valuenow="0" 
                 aria-valuemin="0" 
                 aria-valuemax="100">
                ${escapeHtml(label)}
            </div>
        </div>
    `;
    
    return {
        update: (progress) => {
            const bar = container.querySelector('.progress-bar');
            if (bar) {
                bar.style.width = `${progress}%`;
                bar.setAttribute('aria-valuenow', progress);
            }
        },
        complete: () => {
            const bar = container.querySelector('.progress-bar');
            if (bar) {
                bar.classList.remove('progress-bar-animated');
                bar.style.width = '100%';
            }
        }
    };
}

/**
 * Disable form during submission
 */
function disableForm(formId, disabled = true) {
    const form = document.getElementById(formId);
    if (!form) return;
    
    const inputs = form.querySelectorAll('input, button, select, textarea');
    inputs.forEach(input => {
        input.disabled = disabled;
    });
}

// Export for use in other modules
window.loadingStates = {
    create: createLoadingState,
    update: updateLoadingState,
    complete: completeLoadingState,
    cancel: cancelLoadingState,
    showSkeleton: showSkeletonLoader,
    showProgress: showProgressBar,
    disableForm
};


/**
 * Real-Time Updates Handler (Task 65: Data Visualization Enhancements - Real-Time Updates)
 */

let autoRefreshInterval = null;
let autoRefreshEnabled = false;
let lastUpdateTimes = {};

document.addEventListener('DOMContentLoaded', function() {
    // Initialize real-time updates
    initRealTimeUpdates();
    
    // Setup connection status indicator
    setupConnectionStatus();
});

function initRealTimeUpdates() {
    // Load real-time configuration
    loadRealTimeConfig();
    
    // Setup auto-refresh toggle
    setupAutoRefreshToggle();
    
    // Update last update timestamps
    updateLastUpdateTimestamps();
}

async function loadRealTimeConfig() {
    try {
        // Check if we're accessing via file:// protocol
        if (window.location.protocol === 'file:') {
            console.warn('Accessing via file:// protocol. Please use http://localhost:8080 for full functionality.');
            return;
        }
        
        const response = await window.api.get('realtime/auto-refresh-config');
        if (response.status === 'success' && response.config) {
            autoRefreshEnabled = response.config.enabled || false;
            const interval = response.config.interval_seconds || 300; // 5 minutes default
            
            if (autoRefreshEnabled) {
                startAutoRefresh(interval * 1000);
            }
        }
    } catch (error) {
        // Silently fail if endpoint doesn't exist or server isn't running
        if (error.message && error.message.includes('404')) {
            console.debug('Real-time config endpoint not available');
        } else {
        console.error('Error loading real-time config:', error);
        }
    }
}

function setupAutoRefreshToggle() {
    // Auto-refresh toggle removed from topbar per user request
    // Auto-refresh still works in background but UI controls removed
}

function startAutoRefresh(intervalMs) {
    stopAutoRefresh(); // Clear any existing interval
    
    autoRefreshInterval = setInterval(async () => {
        if (document.visibilityState === 'visible') {
            await refreshDashboard();
        }
    }, intervalMs);
    
    // Show "Live" badge
    showLiveBadge();
}

function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }
    hideLiveBadge();
}

async function refreshDashboard() {
    try {
        // Refresh dashboard data
        if (typeof loadDashboard === 'function') {
            await loadDashboard();
        }
        
        // Refresh advanced analytics if available
        if (window.dashboardEnhanced) {
            await window.dashboardEnhanced.loadAdvancedAnalytics();
        }
        
        // Update last update timestamp
        updateLastUpdateTimestamps();
    } catch (error) {
        console.error('Error refreshing dashboard:', error);
    }
}

// Live badge removed per user request
function showLiveBadge() {
    // Removed - no longer showing live badge
}

function hideLiveBadge() {
    // Removed - no longer showing live badge
}

function setupConnectionStatus() {
    // Check if we're accessing via file:// protocol
    if (window.location.protocol === 'file:') {
        console.warn('Accessing via file:// protocol. Connection status check disabled.');
        return;
    }
    
    // Check connection status periodically
    setInterval(async () => {
        try {
            const response = await window.api.get('realtime/status');
            if (response.status === 'success') {
                updateConnectionStatus(response.connection_status?.connected || false);
            }
        } catch (error) {
            // Silently fail if endpoint doesn't exist
            if (error.message && !error.message.includes('404')) {
                console.debug('Connection status check failed:', error);
            }
            updateConnectionStatus(false);
        }
    }, 30000); // Check every 30 seconds
}

function updateConnectionStatus(connected) {
    const statusEl = document.getElementById('apiStatus');
    if (statusEl) {
        if (connected) {
            statusEl.textContent = 'Online';
            statusEl.className = 'api-status online';
        } else {
            statusEl.textContent = 'Offline';
            statusEl.className = 'api-status offline';
        }
    }
}

async function updateLastUpdateTimestamps() {
    try {
        // Check if we're accessing via file:// protocol
        if (window.location.protocol === 'file:') {
            console.warn('Accessing via file:// protocol. Please use http://localhost:8080 for full functionality.');
            return;
        }
        
        const response = await window.api.get('realtime/last-updates');
        if (response.status === 'success' && response.last_updates) {
            lastUpdateTimes = response.last_updates;
            
            // Update UI with last update times
            Object.keys(lastUpdateTimes).forEach(key => {
                const element = document.getElementById(`lastUpdate-${key}`);
                if (element && lastUpdateTimes[key]) {
                    const date = new Date(lastUpdateTimes[key]);
                    const now = new Date();
                    const diffMs = now - date;
                    const diffMins = Math.floor(diffMs / 60000);
                    
                    if (diffMins < 1) {
                        element.textContent = 'Just now';
                    } else if (diffMins < 60) {
                        element.textContent = `${diffMins}m ago`;
                    } else {
                        element.textContent = window.utils?.formatDateTime(lastUpdateTimes[key]) || 'N/A';
                    }
                }
            });
        }
    } catch (error) {
        // Silently fail if endpoint doesn't exist or server isn't running
        if (error.message && error.message.includes('404')) {
            console.debug('Last updates endpoint not available');
        } else {
        console.error('Error updating last update timestamps:', error);
        }
    }
}

// Manual refresh function
async function manualRefresh() {
    if (window.utils && window.utils.showLoadingOverlay) {
        window.utils.showLoadingOverlay('Refreshing data...');
    }
    try {
        await refreshDashboard();
        window.utils?.showToast('Data refreshed successfully', 'success');
    } catch (error) {
        window.errorHandler?.handleApiError(error, 'Refreshing data');
    } finally {
        window.utils?.hideLoadingOverlay();
    }
}

// Export for use in other modules
window.realtimeUpdates = {
    startAutoRefresh,
    stopAutoRefresh,
    refreshDashboard: manualRefresh,
    updateLastUpdateTimestamps
};

// Add CSS for pulse animation
if (!document.getElementById('realtimeStyles')) {
    const style = document.createElement('style');
    style.id = 'realtimeStyles';
    style.textContent = `
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        #liveBadge {
            animation: pulse 2s infinite;
        }
    `;
    document.head.appendChild(style);
}


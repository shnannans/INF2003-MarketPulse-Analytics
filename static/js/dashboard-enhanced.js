/**
 * Enhanced Dashboard Handler (Tasks 55-56: Dashboard Enhancements - Advanced Analytics & Materialized Views)
 */

let analyticsCharts = {
    sectorPerformance: null,
    rollingAggregations: null
};

document.addEventListener('DOMContentLoaded', async function() {
    // Check authentication
    if (!window.auth || !window.auth.isAuthenticated()) {
        // Allow viewing dashboard without auth, but show login prompt
        showLoginPrompt();
    }
    
    // Load enhanced dashboard features
    await loadAdvancedAnalytics();
    await loadMaterializedViews();
    
    // Setup auto-refresh
    setupAutoRefresh();
});

function showLoginPrompt() {
    // Show a subtle prompt to login for full features
    const prompt = document.createElement('div');
    prompt.className = 'alert alert-info alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3';
    prompt.style.zIndex = '9999';
    prompt.innerHTML = `
        <i class="bi bi-info-circle me-2"></i>
        <a href="login.html" class="alert-link">Login</a> for full dashboard features
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(prompt);
    
    setTimeout(() => {
        prompt.remove();
    }, 5000);
}

async function loadAdvancedAnalytics() {
    const containers = ['windowFunctionsContainer', 'sectorPerformanceContainer', 'rollingAggregationsContainer'];
    
    try {
        // Load window functions data
        const windowFunctions = await window.api.get('analytics/window-functions', { limit: 50 });
        if (windowFunctions.status === 'success' && windowFunctions.data) {
            renderWindowFunctions(windowFunctions.data);
        } else {
            console.warn('Window functions: No data or failed', windowFunctions);
            const container = document.getElementById('windowFunctionsContainer');
            if (container) {
                container.innerHTML = '<div class="alert alert-info">No window functions data available</div>';
            }
        }
        
        // Load sector performance
        const sectorPerformance = await window.api.get('analytics/sector-performance');
        if (sectorPerformance.status === 'success') {
            // Sector performance returns 'sectors' not 'data'
            const sectors = sectorPerformance.sectors || sectorPerformance.data || [];
            renderSectorPerformance(sectors);
        } else {
            console.warn('Sector performance: No data or failed', sectorPerformance);
            const container = document.getElementById('sectorPerformanceContainer');
            if (container) {
                container.innerHTML = '<div class="alert alert-info">No sector performance data available</div>';
            }
        }
        
        // Price trends chart removed per user request
        
        // Load rolling aggregations
        const rollingAgg = await window.api.get('analytics/rolling-aggregations');
        if (rollingAgg.status === 'success' && rollingAgg.data) {
            renderRollingAggregations(rollingAgg.data);
        } else {
            console.warn('Rolling aggregations: No data or failed', rollingAgg);
            const container = document.getElementById('rollingAggregationsContainer');
            if (container) {
                container.innerHTML = '<div class="alert alert-info">No rolling aggregations data available</div>';
            }
        }
        
        // Price-sentiment correlation removed - Combined Analytics already shows this
    } catch (error) {
        console.error('Error loading advanced analytics:', error);
        // Show error message in containers and clear any spinners
        containers.forEach(id => {
            const container = document.getElementById(id);
            if (container) {
                // Clear spinner if present
                if (container.innerHTML.includes('spinner-border')) {
                    container.innerHTML = `<div class="alert alert-warning">Failed to load data: ${error.message}</div>`;
                } else {
                    // Only update if container is empty or has spinner
                    const currentHTML = container.innerHTML.trim();
                    if (!currentHTML || currentHTML.includes('spinner-border') || currentHTML.includes('Loading')) {
                        container.innerHTML = `<div class="alert alert-warning">Failed to load data: ${error.message}</div>`;
                    }
                }
            }
        });
    } finally {
        // Always hide overlay if it was shown
        if (window.utils && window.utils.hideLoadingOverlay) {
            window.utils.hideLoadingOverlay();
        }
    }
}

async function loadMaterializedViews() {
    const container = document.getElementById('materializedViewsContent') || document.getElementById('materializedViewContainer');
    try {
        // Load materialized view data
        const mvData = await window.api.get('warehouse/materialized-view/sector-performance');
        if (mvData.status === 'success' && mvData.data) {
            renderMaterializedView(mvData.data);
        } else {
            console.warn('Materialized views: No data or failed', mvData);
            if (container) {
                // Clear spinner if present
                if (container.innerHTML.includes('spinner-border')) {
                    container.innerHTML = '<div class="alert alert-info">No materialized view data available</div>';
                } else {
                    container.innerHTML = '<div class="alert alert-info">No materialized view data available</div>';
                }
            }
        }
    } catch (error) {
        console.error('Error loading materialized views:', error);
        if (container) {
            // Clear spinner if present
            if (container.innerHTML.includes('spinner-border')) {
                container.innerHTML = `<div class="alert alert-warning">Failed to load materialized views: ${error.message}</div>`;
            } else {
                container.innerHTML = `<div class="alert alert-warning">Failed to load materialized views: ${error.message}</div>`;
            }
        }
    } finally {
        // Always hide overlay if it was shown
        if (window.utils && window.utils.hideLoadingOverlay) {
            window.utils.hideLoadingOverlay();
        }
    }
}

function renderWindowFunctions(data) {
    // Render window functions data in a table or chart
    const container = document.getElementById('windowFunctionsContainer');
    if (!container) return;
    
    if (data && data.length > 0) {
        container.innerHTML = `
            <div class="table-responsive">
                <table class="table table-sm">
                    <thead>
                        <tr>
                            <th>Ticker</th>
                            <th>Date</th>
                            <th>Price</th>
                            <th>MA 30</th>
                            <th>Momentum</th>
                            <th>Rank</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.slice(0, 20).map(item => `
                            <tr>
                                <td>${item.ticker}</td>
                                <td>${window.utils.formatDate(item.date)}</td>
                                <td>${window.utils.formatCurrency(item.close_price)}</td>
                                <td>${window.utils.formatCurrency(item.ma_30)}</td>
                                <td>${item.momentum_pct !== null && item.momentum_pct !== undefined ? window.utils.formatPercentage(item.momentum_pct) : (item.momentum_30d_pct !== null && item.momentum_30d_pct !== undefined ? window.utils.formatPercentage(item.momentum_30d_pct) : 'N/A')}</td>
                                <td>${item.price_rank_today || 'N/A'}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }
}

function renderSectorPerformance(data) {
    // Render sector performance with all metrics
    const container = document.getElementById('sectorPerformanceContainer');
    if (!container) return;
    
    if (!data || data.length === 0) {
        container.innerHTML = '<div class="alert alert-info">No sector performance data available</div>';
        return;
    }
    
    // Create a comprehensive table showing all metrics
    let html = `
        <div class="card">
            <div class="card-header">
                <h5 class="mb-0"><i class="bi bi-bar-chart"></i> Sector Performance Analysis</h5>
                <small class="text-muted">Comprehensive metrics across all sectors</small>
            </div>
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-hover table-striped">
                        <thead class="table-dark">
                            <tr>
                                <th>Sector</th>
                                <th class="text-end">Avg Price</th>
                                <th class="text-end">Avg Volume</th>
                                <th class="text-end">Price Volatility</th>
                                <th class="text-end">Price Range</th>
                                <th class="text-end">Volatility %</th>
                                <th class="text-center">Companies</th>
                            </tr>
                        </thead>
                        <tbody>
    `;
    
    data.forEach(sector => {
        const volatilityPct = sector.volatility_pct !== null && sector.volatility_pct !== undefined 
            ? sector.volatility_pct 
            : (sector.price_volatility && sector.avg_price && sector.avg_price > 0 
                ? (sector.price_volatility / sector.avg_price * 100) 
                : null);
        
        const volatilityBadgeClass = volatilityPct !== null 
            ? (volatilityPct > 20 ? 'bg-danger' : volatilityPct > 10 ? 'bg-warning' : 'bg-info')
            : '';
        
        html += `
            <tr>
                <td><strong>${escapeHtml(sector.sector || 'Unknown')}</strong></td>
                <td class="text-end">$${sector.avg_price ? sector.avg_price.toFixed(2) : 'N/A'}</td>
                <td class="text-end">${sector.avg_volume ? Math.round(sector.avg_volume).toLocaleString() : 'N/A'}</td>
                <td class="text-end">${sector.price_volatility !== null && sector.price_volatility !== undefined ? sector.price_volatility.toFixed(2) : 'N/A'}</td>
                <td class="text-end">$${sector.price_range !== null && sector.price_range !== undefined ? sector.price_range.toFixed(2) : 'N/A'}</td>
                <td class="text-end">
                    ${volatilityPct !== null ? `
                        <span class="badge ${volatilityBadgeClass}">${volatilityPct.toFixed(2)}%</span>
                    ` : 'N/A'}
                </td>
                <td class="text-center">
                    <span class="badge bg-secondary">${sector.company_count || 0}</span>
                </td>
            </tr>
        `;
    });
    
    html += `
                        </tbody>
                    </table>
                </div>
                
                <!-- Summary Statistics -->
                <div class="row mt-4">
                    <div class="col-md-3">
                        <div class="card bg-primary text-white">
                            <div class="card-body text-center">
                                <h6 class="card-title">Total Sectors</h6>
                                <h3>${data.length}</h3>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card bg-success text-white">
                            <div class="card-body text-center">
                                <h6 class="card-title">Total Companies</h6>
                                <h3>${data.reduce((sum, s) => sum + (s.company_count || 0), 0)}</h3>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card bg-info text-white">
                            <div class="card-body text-center">
                                <h6 class="card-title">Avg Price (All)</h6>
                                <h3>$${data.length > 0 ? (data.reduce((sum, s) => sum + (s.avg_price || 0), 0) / data.length).toFixed(2) : '0.00'}</h3>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card bg-warning text-white">
                            <div class="card-body text-center">
                                <h6 class="card-title">Avg Volatility</h6>
                                <h3>${data.filter(s => s.volatility_pct !== null).length > 0 
                                    ? (data.reduce((sum, s) => sum + (s.volatility_pct || 0), 0) / data.filter(s => s.volatility_pct !== null).length).toFixed(2) 
                                    : 'N/A'}%</h3>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    container.innerHTML = html;
    
    // Also create a chart for visual comparison (optional - can be toggled)
    // Keep the chart creation but make it optional
    const chartContainer = document.createElement('div');
    chartContainer.className = 'mt-3';
    chartContainer.innerHTML = `
        <div class="card">
            <div class="card-header">
                <h6 class="mb-0"><i class="bi bi-graph-up"></i> Average Price by Sector</h6>
            </div>
            <div class="card-body">
                <canvas id="sectorPriceChart" style="max-height: 300px;"></canvas>
            </div>
        </div>
    `;
    container.appendChild(chartContainer);
    
    if (typeof Chart !== 'undefined') {
        const ctx = document.getElementById('sectorPriceChart');
        if (ctx) {
            // Destroy existing chart if it exists
            if (analyticsCharts.sectorPerformance) {
                analyticsCharts.sectorPerformance.destroy();
            }
            
            analyticsCharts.sectorPerformance = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.map(d => d.sector || 'Unknown'),
                    datasets: [{
                        label: 'Average Price ($)',
                        data: data.map(d => d.avg_price || 0),
                        backgroundColor: data.map((d, i) => {
                            const colors = [
                                'rgba(102, 126, 234, 0.8)',
                                'rgba(40, 167, 69, 0.8)',
                                'rgba(220, 53, 69, 0.8)',
                                'rgba(255, 193, 7, 0.8)',
                                'rgba(23, 162, 184, 0.8)',
                                'rgba(108, 117, 125, 0.8)'
                            ];
                            return colors[i % colors.length];
                        }),
                        borderColor: data.map((d, i) => {
                            const colors = [
                                'rgba(102, 126, 234, 1)',
                                'rgba(40, 167, 69, 1)',
                                'rgba(220, 53, 69, 1)',
                                'rgba(255, 193, 7, 1)',
                                'rgba(23, 162, 184, 1)',
                                'rgba(108, 117, 125, 1)'
                            ];
                            return colors[i % colors.length];
                        }),
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Average Price by Sector',
                            font: {
                                size: 16
                            }
                        },
                        legend: {
                            display: false
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return `$${context.parsed.y.toFixed(2)}`;
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Average Price ($)'
                            },
                            ticks: {
                                callback: function(value) {
                                    return '$' + value.toFixed(0);
                                }
                            }
                        },
                        x: {
                            title: {
                                display: true,
                                text: 'Sector'
                            }
                        }
                    }
                }
            });
        }
    }
}

// Helper function to escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Price trends render function removed per user request

function renderRollingAggregations(data) {
    // Render rolling aggregations
    const container = document.getElementById('rollingAggregationsContainer');
    if (!container) return;
    
    if (data && data.length > 0) {
        // Group by ticker and get latest record for each
        const tickerMap = new Map();
        data.forEach(item => {
            if (!tickerMap.has(item.ticker) || new Date(item.date) > new Date(tickerMap.get(item.ticker).date)) {
                tickerMap.set(item.ticker, item);
            }
        });
        
        const latestData = Array.from(tickerMap.values()).slice(0, 6);
        
        container.innerHTML = `
            <div class="row">
                ${latestData.map(item => `
                    <div class="col-md-4 mb-3">
                        <div class="card">
                            <div class="card-body">
                                <h6 class="card-title">${item.ticker}</h6>
                                <p class="card-text small">
                                    <strong>7-Day Volume Sum:</strong> ${window.utils.formatNumber(item.volume_7day_sum) || 'N/A'}<br>
                                    <strong>20-Day MA:</strong> ${window.utils.formatCurrency(item.ma_20) || 'N/A'}<br>
                                    <strong>20-Day High:</strong> ${window.utils.formatCurrency(item.high_20d) || 'N/A'}<br>
                                    <strong>20-Day Low:</strong> ${window.utils.formatCurrency(item.low_20d) || 'N/A'}<br>
                                    <strong>Stochastic Oscillator:</strong> ${item.stoch_oscillator ? item.stoch_oscillator.toFixed(2) + '%' : 'N/A'}
                                </p>
                            </div>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    } else {
        container.innerHTML = '<div class="alert alert-info">No rolling aggregation data available</div>';
    }
}

// Price-Sentiment Correlation render function removed - Combined Analytics already shows this

function renderMaterializedView(data) {
    // Render materialized view data
    const container = document.getElementById('materializedViewsContent') || document.getElementById('materializedViewContainer');
    if (!container) return;
    
    if (data && data.length > 0) {
        container.innerHTML = `
            <div class="table-responsive">
                <table class="table table-sm">
                    <thead>
                        <tr>
                            <th>Sector</th>
                            <th>Date</th>
                            <th>Avg Price</th>
                            <th>Total Volume</th>
                            <th>Company Count</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.slice(0, 20).map(item => `
                            <tr>
                                <td>${item.sector}</td>
                                <td>${window.utils.formatDate(item.date)}</td>
                                <td>${window.utils.formatCurrency(item.avg_price)}</td>
                                <td>${window.utils.formatNumber(item.total_volume)}</td>
                                <td>${item.company_count}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }
}

function setupAutoRefresh() {
    // Auto-refresh every 5 minutes (only if page is visible)
    setInterval(async () => {
        if (document.visibilityState === 'visible') {
            try {
                await loadAdvancedAnalytics();
                await loadMaterializedViews();
            } catch (error) {
                console.error('Error in auto-refresh:', error);
            }
        }
    }, 5 * 60 * 1000);
}

// Global refresh functions for buttons
window.refreshAnalytics = async function() {
    const containers = ['windowFunctionsContainer', 'sectorPerformanceContainer', 'rollingAggregationsContainer'];
    
    // Show loading overlay
    if (window.utils && window.utils.showLoadingOverlay) {
        window.utils.showLoadingOverlay('Refreshing analytics...');
    }
    
    // Show spinners in containers
    containers.forEach(id => {
        const container = document.getElementById(id);
        if (container) {
            container.innerHTML = '<div class="text-center text-muted py-4"><p class="mt-2">Loading...</p></div>';
        }
    });
    
    try {
        await loadAdvancedAnalytics();
        // Show success notification
        if (window.utils && window.utils.showToast) {
            window.utils.showToast('Advanced Analytics refreshed successfully', 'success');
        } else if (window.showNotification) {
            window.showNotification('Advanced Analytics refreshed successfully', 'success');
        }
    } catch (error) {
        console.error('Error refreshing analytics:', error);
        if (window.utils && window.utils.showToast) {
            window.utils.showToast('Failed to refresh analytics', 'error');
        } else if (window.showNotification) {
            window.showNotification('Failed to refresh analytics', 'error');
        }
        // Clear loading state on error
        containers.forEach(id => {
            const container = document.getElementById(id);
            if (container && container.innerHTML.includes('spinner-border')) {
                container.innerHTML = '<div class="alert alert-warning">Failed to load data</div>';
            }
        });
    } finally {
        // Always hide overlay
        if (window.utils && window.utils.hideLoadingOverlay) {
            window.utils.hideLoadingOverlay();
        }
    }
};

window.refreshMaterializedView = async function() {
    const container = document.getElementById('materializedViewsContent') || document.getElementById('materializedViewContainer');
    
    // Show loading overlay
    if (window.utils && window.utils.showLoadingOverlay) {
        window.utils.showLoadingOverlay('Refreshing materialized views...');
    }
    
    // Show spinner in container
    if (container) {
        container.innerHTML = '<div class="text-center text-muted py-4"><p class="mt-2">Refreshing materialized views...</p></div>';
    }
    
    try {
        // Call the refresh endpoint first
        await window.api.post('warehouse/materialized-view/refresh');
        
        // Then reload the data
        await loadMaterializedViews();
        
        if (window.utils && window.utils.showToast) {
            window.utils.showToast('Materialized views refreshed successfully', 'success');
        } else {
            console.log('Materialized views refreshed successfully');
        }
    } catch (error) {
        console.error('Error refreshing materialized views:', error);
        if (window.utils && window.utils.showToast) {
            window.utils.showToast('Failed to refresh materialized views', 'error');
        }
        if (window.errorHandler && window.errorHandler.handleApiError) {
            window.errorHandler.handleApiError(error, 'Refreshing materialized views');
        }
        if (container) {
            // Clear spinner and show error
            if (container.innerHTML.includes('spinner-border')) {
                container.innerHTML = '<div class="alert alert-warning">Failed to refresh materialized views</div>';
            }
        }
    } finally {
        // Always hide loading overlay, even on error
        if (window.utils && window.utils.hideLoadingOverlay) {
            window.utils.hideLoadingOverlay();
        }
    }
};

// Export for use in other modules
window.dashboardEnhanced = {
    loadAdvancedAnalytics,
    loadMaterializedViews
};


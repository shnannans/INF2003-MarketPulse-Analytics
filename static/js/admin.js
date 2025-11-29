/**
 * Admin Dashboard Handler (Tasks 50-51: User Management Interface - Admin Dashboard & Admin Management)
 */

let allUsers = [];
let allAdmins = [];

document.addEventListener('DOMContentLoaded', async function() {
    // Wait for auth to initialize and load user info
    // Give it a moment to load user info from localStorage
    if (window.auth && window.auth.init) {
        await window.auth.init();
    }
    
    // Small delay to ensure user info is loaded
    await new Promise(resolve => setTimeout(resolve, 100));
    
    // Check authentication and admin role
    if (!window.auth || !window.auth.isAuthenticated()) {
        window.location.href = 'login.html';
        return;
    }
    
    // Double-check: try loading user info again if role is not set
    if (!window.auth.getUserRole()) {
        await window.auth.loadUserInfo();
        // Wait a bit more
        await new Promise(resolve => setTimeout(resolve, 100));
    }
    
    // Final check for admin role
    const userRole = window.auth.getUserRole();
    console.log('Current user role:', userRole); // Debug log
    
    if (!window.auth.isAdmin()) {
        console.error('Admin check failed. User role:', userRole);
        showError('Access denied. Admin privileges required.');
        setTimeout(() => {
            window.location.href = 'index.html';
        }, 2000);
        return;
    }
    
    // Load initial data
    await loadStats();
    await loadUsers();
    await loadAdmins();
    
    // Setup search
    document.getElementById('userSearch').addEventListener('input', filterUsers);
    
    // Setup tab switching
    const tabs = document.querySelectorAll('#adminTabs button[data-bs-toggle="tab"]');
    tabs.forEach(tab => {
        tab.addEventListener('shown.bs.tab', function(event) {
            const target = event.target.getAttribute('data-bs-target');
            if (target === '#users') {
                loadUsers();
            } else if (target === '#admins') {
                loadAdmins();
            } else if (target === '#warehouse') {
                loadETLStatus();
            } else if (target === '#database') {
                loadIsolationLevel();
                loadTableSizes();
            }
        });
    });
    
    // Load users for promote modal
    loadUsersForPromote();
});

async function loadStats() {
    try {
        const usersResponse = await window.api.get('/users');
        if (usersResponse.status === 'success' && usersResponse.users) {
            const users = usersResponse.users;
            const activeUsers = users.filter(u => u.is_active).length;
            const admins = users.filter(u => u.role === 'admin').length;
            
            document.getElementById('totalUsers').textContent = usersResponse.total || users.length;
            document.getElementById('activeUsers').textContent = activeUsers;
            document.getElementById('totalAdmins').textContent = admins;
            document.getElementById('inactiveUsers').textContent = users.length - activeUsers;
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

async function loadUsers() {
    try {
        const response = await window.api.get('/users', { limit: 100 });
        
        if (response.status === 'success' && response.users) {
            allUsers = response.users;
            renderUsersTable(allUsers);
        }
    } catch (error) {
        console.error('Error loading users:', error);
        showError('Failed to load users. Please try again.');
        document.getElementById('usersTableBody').innerHTML = 
            '<tr><td colspan="7" class="text-center text-danger">Error loading users</td></tr>';
    }
}

async function loadAdmins() {
    const tbody = document.getElementById('adminsTableBody');
    try {
        const response = await window.api.get('admins');
        
        if (response.status === 'success' && response.admins) {
            allAdmins = response.admins;
            renderAdminsTable(allAdmins);
        } else {
            // Clear spinner even if response format is unexpected
            if (tbody) {
                tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No admins found</td></tr>';
            }
        }
    } catch (error) {
        console.error('Error loading admins:', error);
        showError('Failed to load admins. Please try again.');
        // Always clear spinner on error
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger">Error loading admins</td></tr>';
        }
    }
}

function renderUsersTable(users) {
    const tbody = document.getElementById('usersTableBody');
    if (!tbody) return;
    
    // Always clear spinner first - replace entire tbody content
    if (users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">No users found</td></tr>';
        return;
    }
    
    // Replace spinner with actual data
    tbody.innerHTML = users.map(user => `
        <tr>
            <td>${user.id}</td>
            <td>${escapeHtml(user.username)}</td>
            <td>${escapeHtml(user.email)}</td>
            <td><span class="badge ${user.role === 'admin' ? 'bg-danger' : 'bg-primary'}">${user.role}</span></td>
            <td><span class="badge ${user.is_active ? 'bg-success' : 'bg-secondary'}">${user.is_active ? 'Active' : 'Inactive'}</span></td>
            <td>${user.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}</td>
            <td>
                <button class="btn btn-sm btn-outline-primary" onclick="editUser(${user.id})" title="Edit">
                    <i class="bi bi-pencil"></i>
                </button>
                ${user.role !== 'admin' ? `
                    <button class="btn btn-sm btn-outline-success" onclick="promoteUserById(${user.id})" title="Promote to Admin">
                        <i class="bi bi-shield-plus"></i>
                    </button>
                ` : ''}
                <button class="btn btn-sm btn-outline-danger" onclick="deleteUser(${user.id})" title="Delete">
                    <i class="bi bi-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

function renderAdminsTable(admins) {
    const tbody = document.getElementById('adminsTableBody');
    
    if (admins.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No admins found</td></tr>';
        return;
    }
    
    tbody.innerHTML = admins.map(admin => `
        <tr>
            <td>${admin.id}</td>
            <td>${escapeHtml(admin.username)}</td>
            <td>${escapeHtml(admin.email)}</td>
            <td><span class="badge ${admin.is_active ? 'bg-success' : 'bg-secondary'}">${admin.is_active ? 'Active' : 'Inactive'}</span></td>
            <td>
                <button class="btn btn-sm btn-outline-warning" onclick="demoteAdmin(${admin.id})" title="Demote to User">
                    <i class="bi bi-shield-x"></i> Demote
                </button>
            </td>
        </tr>
    `).join('');
}

function filterUsers() {
    const searchTerm = document.getElementById('userSearch').value.toLowerCase();
    const filtered = allUsers.filter(user => 
        user.username.toLowerCase().includes(searchTerm) ||
        user.email.toLowerCase().includes(searchTerm)
    );
    renderUsersTable(filtered);
}

async function createUser() {
    const username = document.getElementById('newUsername').value.trim();
    const email = document.getElementById('newEmail').value.trim();
    const password = document.getElementById('newPassword').value;
    const role = document.getElementById('newRole').value;
    
    if (!username || !email || !password) {
        showError('Please fill in all fields');
        return;
    }
    
    try {
        const response = await window.api.post('/users', {
            username,
            email,
            password,
            role
        });
        
        if (response.status === 'success') {
            showSuccess('User created successfully!');
            bootstrap.Modal.getInstance(document.getElementById('createUserModal')).hide();
            document.getElementById('createUserForm').reset();
            await loadUsers();
            await loadStats();
        } else {
            showError(response.message || 'Failed to create user');
        }
    } catch (error) {
        showError(error.message || 'Failed to create user. Please try again.');
    }
}

async function editUser(userId) {
    const user = allUsers.find(u => u.id === userId);
    if (!user) return;
    
    // Simple edit - in production, use a modal
    const newEmail = prompt('Enter new email:', user.email);
    if (!newEmail || newEmail === user.email) return;
    
    try {
        const response = await window.api.patch(`/users/${userId}`, {
            email: newEmail
        });
        
        if (response.status === 'success') {
            showSuccess('User updated successfully!');
            await loadUsers();
        } else {
            showError(response.message || 'Failed to update user');
        }
    } catch (error) {
        showError(error.message || 'Failed to update user. Please try again.');
    }
}

async function deleteUser(userId) {
    if (!confirm('Are you sure you want to delete this user? This action can be undone.')) {
        return;
    }
    
    try {
        const response = await window.api.delete(`/users/${userId}`);
        
        if (response.status === 'success') {
            showSuccess('User deleted successfully!');
            await loadUsers();
            await loadStats();
        } else {
            showError(response.message || 'Failed to delete user');
        }
    } catch (error) {
        showError(error.message || 'Failed to delete user. Please try again.');
    }
}

async function promoteUserById(userId) {
    try {
        const response = await window.api.patch(`/users/${userId}/role`, {
            role: 'admin'
        });
        
        if (response.status === 'success') {
            showSuccess('User promoted to admin successfully!');
            await loadUsers();
            await loadAdmins();
            await loadStats();
        } else {
            showError(response.message || 'Failed to promote user');
        }
    } catch (error) {
        showError(error.message || 'Failed to promote user. Please try again.');
    }
}

async function promoteUser() {
    const userId = parseInt(document.getElementById('promoteUserId').value);
    if (!userId) {
        showError('Please select a user');
        return;
    }
    
    await promoteUserById(userId);
    bootstrap.Modal.getInstance(document.getElementById('promoteUserModal')).hide();
}

async function demoteAdmin(adminId) {
    if (!confirm('Are you sure you want to demote this admin to a regular user?')) {
        return;
    }
    
    try {
        const response = await window.api.patch(`/admins/${adminId}/demote`);
        
        if (response.status === 'success') {
            showSuccess('Admin demoted successfully!');
            await loadUsers();
            await loadAdmins();
            await loadStats();
        } else {
            showError(response.message || 'Failed to demote admin');
        }
    } catch (error) {
        showError(error.message || 'Failed to demote admin. Please try again.');
    }
}

async function loadUsersForPromote() {
    try {
        const response = await window.api.get('/users', { role: 'user', limit: 100 });
        const select = document.getElementById('promoteUserId');
        
        if (response.status === 'success' && response.users) {
            select.innerHTML = '<option value="">Select a user...</option>' +
                response.users.map(user => 
                    `<option value="${user.id}">${escapeHtml(user.username)} (${escapeHtml(user.email)})</option>`
                ).join('');
        }
    } catch (error) {
        console.error('Error loading users for promote:', error);
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
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
    
    // Also show toast
    window.utils?.showToast(message, 'error', 5000);
    
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
    
    setTimeout(() => {
        alert.style.display = 'none';
    }, 5000);
}

// ==================== Data Warehouse Functions ====================

async function loadETLStatus() {
    try {
        const result = await window.api.get('warehouse/etl/status');
        if (result.status === 'success' && result.etl_status) {
            const status = result.etl_status;
            const statusBadge = document.getElementById('etlStatus');
            const statusText = status.status || 'unknown';
            
            statusBadge.textContent = statusText.toUpperCase();
            statusBadge.className = `badge ${getETLStatusClass(statusText)}`;
            
            document.getElementById('etlLastRun').textContent = 
                status.last_run ? new Date(status.last_run).toLocaleString() : 'Never';
            document.getElementById('etlRecords').textContent = 
                status.records_processed || 0;
        }
    } catch (error) {
        console.error('Error loading ETL status:', error);
        document.getElementById('etlStatus').textContent = 'ERROR';
        document.getElementById('etlStatus').className = 'badge bg-danger';
    }
}

function getETLStatusClass(status) {
    const statusLower = (status || '').toLowerCase();
    if (statusLower === 'completed' || statusLower === 'success') return 'bg-success';
    if (statusLower === 'running' || statusLower === 'in_progress') return 'bg-warning';
    if (statusLower === 'failed' || statusLower === 'error') return 'bg-danger';
    return 'bg-secondary';
}

async function runETLPipeline() {
    if (!confirm('Run ETL pipeline? This may take several minutes.')) return;
    
    try {
        if (window.utils && window.utils.showLoadingOverlay) {
            window.utils.showLoadingOverlay('Running ETL pipeline...');
        }
        
        const result = await window.api.post('warehouse/etl/run');
        
        if (result.status === 'success') {
            showSuccess('ETL pipeline completed successfully');
            await loadETLStatus();
        } else {
            showError('ETL pipeline failed: ' + (result.message || 'Unknown error'));
        }
    } catch (error) {
        showError('Error running ETL pipeline: ' + (error.message || 'Unknown error'));
    } finally {
        if (window.utils && window.utils.hideLoadingOverlay) {
            window.utils.hideLoadingOverlay();
        }
    }
}

async function refreshAllMaterializedViews() {
    const statusDiv = document.getElementById('mvRefreshStatus');
    try {
        if (statusDiv) {
            statusDiv.innerHTML = '<span class="text-muted">Refreshing...</span>';
        }
        
        // Also show overlay for consistency
        if (window.utils && window.utils.showLoadingOverlay) {
            window.utils.showLoadingOverlay('Refreshing materialized views...');
        }
        
        const result = await window.api.post('warehouse/materialized-view/refresh');
        
        if (result.status === 'success') {
            if (statusDiv) {
                statusDiv.innerHTML = '<span class="text-success">✓ Refreshed successfully</span>';
            }
            showSuccess('Materialized views refreshed');
        } else {
            if (statusDiv) {
                statusDiv.innerHTML = '<span class="text-danger">✗ Refresh failed</span>';
            }
            showError('Failed to refresh materialized views');
        }
    } catch (error) {
        if (statusDiv) {
            statusDiv.innerHTML = '<span class="text-danger">✗ Refresh failed: ' + (error.message || 'Unknown error') + '</span>';
        }
        showError('Error refreshing materialized views: ' + (error.message || 'Unknown error'));
    } finally {
        // Always hide overlay and clear spinner
        if (window.utils && window.utils.hideLoadingOverlay) {
            window.utils.hideLoadingOverlay();
        }
    }
}

async function loadOLAPAnalysis() {
    const analysisType = document.getElementById('olapAnalysisType').value;
    const endpoint = analysisType === 'sector-time' 
        ? 'warehouse/olap/sector-time-analysis'
        : 'warehouse/olap/trend-analysis';
    
    const container = document.getElementById('olapResults');
    
    try {
        if (window.utils && window.utils.showLoadingOverlay) {
            window.utils.showLoadingOverlay('Loading OLAP analysis...');
        }
        
        const result = await window.api.get(endpoint);
        
        // Hide overlay IMMEDIATELY after API call completes, before rendering
        if (window.utils && window.utils.hideLoadingOverlay) {
            window.utils.hideLoadingOverlay();
        }
        
        if (result.status === 'success' && result.data) {
            renderOLAPResults(result.data, analysisType);
        } else {
            if (container) {
                container.innerHTML = '<div class="alert alert-warning">No data available</div>';
            }
        }
    } catch (error) {
        // Hide overlay on error too
        if (window.utils && window.utils.hideLoadingOverlay) {
            window.utils.hideLoadingOverlay();
        }
        
        if (container) {
            container.innerHTML = '<div class="alert alert-danger">Error loading OLAP analysis: ' + (error.message || 'Unknown error') + '</div>';
        }
        showError('Error loading OLAP analysis');
    }
}

function renderOLAPResults(data, type) {
    const container = document.getElementById('olapResults');
    
    if (!data || data.length === 0) {
        container.innerHTML = '<div class="alert alert-info">No data available for this analysis</div>';
        return;
    }
    
    let html = '<div class="table-responsive"><table class="table table-sm table-bordered">';
    
    if (type === 'sector-time') {
        html += '<thead><tr><th>Year</th><th>Quarter</th><th>Sector</th><th>Companies</th><th>Avg Price</th><th>Total Volume</th><th>Avg Change %</th></tr></thead><tbody>';
        data.forEach(row => {
            html += `<tr>
                <td>${row.year || 'N/A'}</td>
                <td>${row.quarter || 'N/A'}</td>
                <td>${row.sector || 'N/A'}</td>
                <td>${row.company_count || 0}</td>
                <td>$${row.avg_price ? row.avg_price.toFixed(2) : 'N/A'}</td>
                <td>${row.total_volume ? row.total_volume.toLocaleString() : 'N/A'}</td>
                <td>${row.avg_change_pct ? row.avg_change_pct.toFixed(2) + '%' : 'N/A'}</td>
            </tr>`;
        });
    } else {
        html += '<thead><tr><th>Year</th><th>Sector</th><th>Companies</th><th>Avg Price</th><th>Total Volume</th><th>Avg Change %</th><th>Max Price</th><th>Min Price</th></tr></thead><tbody>';
        data.forEach(row => {
            html += `<tr>
                <td>${row.year || 'N/A'}</td>
                <td>${row.sector || 'N/A'}</td>
                <td>${row.company_count || 0}</td>
                <td>$${row.avg_price ? row.avg_price.toFixed(2) : 'N/A'}</td>
                <td>${row.total_volume ? row.total_volume.toLocaleString() : 'N/A'}</td>
                <td>${row.avg_change_pct ? row.avg_change_pct.toFixed(2) + '%' : 'N/A'}</td>
                <td>$${row.max_price ? row.max_price.toFixed(2) : 'N/A'}</td>
                <td>$${row.min_price ? row.min_price.toFixed(2) : 'N/A'}</td>
            </tr>`;
        });
    }
    
    html += '</tbody></table></div>';
    html += `<p class="text-muted mt-2"><small>Showing ${data.length} result(s)</small></p>`;
    container.innerHTML = html;
}

// ==================== Transaction & Concurrency Functions ====================

async function loadIsolationLevel() {
    try {
        const result = await window.api.get('transaction/isolation-level');
        if (result.status === 'success' && result.isolation_level) {
            const level = result.isolation_level;
            const badge = document.getElementById('currentIsolationLevel');
            badge.textContent = level;
            badge.className = `badge ${getIsolationBadgeClass(level)}`;
            document.getElementById('isolationLevelSelect').value = level;
            updateIsolationInfo(level);
        }
    } catch (error) {
        console.error('Error loading isolation level:', error);
        document.getElementById('currentIsolationLevel').textContent = 'ERROR';
        document.getElementById('currentIsolationLevel').className = 'badge bg-danger';
    }
}

async function setIsolationLevel() {
    const level = document.getElementById('isolationLevelSelect').value;
    
    try {
        const result = await window.api.post('transaction/set-isolation-level', {}, {
            params: { level: level }
        });
        
        if (result.status === 'success') {
            showSuccess(`Isolation level set to ${level}`);
            await loadIsolationLevel();
        } else {
            showError('Failed to set isolation level');
        }
    } catch (error) {
        showError('Error setting isolation level: ' + (error.message || 'Unknown error'));
    }
}

function getIsolationBadgeClass(level) {
    const classes = {
        'READ_UNCOMMITTED': 'bg-danger',
        'READ_COMMITTED': 'bg-info',
        'REPEATABLE_READ': 'bg-warning',
        'SERIALIZABLE': 'bg-success'
    };
    return classes[level] || 'bg-secondary';
}

function updateIsolationInfo(level) {
    const info = {
        'READ_UNCOMMITTED': 'Lowest isolation. Allows dirty reads. Not recommended for production.',
        'READ_COMMITTED': 'Default level. Prevents dirty reads but allows non-repeatable reads. Good for most cases.',
        'REPEATABLE_READ': 'Higher consistency. Prevents non-repeatable reads. Good for financial calculations.',
        'SERIALIZABLE': 'Highest isolation. Maximum consistency but can cause deadlocks. Use with caution.'
    };
    
    const infoDiv = document.getElementById('isolationLevelInfo');
    if (infoDiv) {
        infoDiv.innerHTML = `<strong>${level}:</strong> ${info[level] || ''}`;
    }
}

// ==================== Indexing & Performance Functions ====================

async function analyzeQuery() {
    const query = document.getElementById('queryToAnalyze').value.trim();
    
    if (!query) {
        showError('Please enter a query to analyze');
        return;
    }
    
    try {
        if (window.utils && window.utils.showLoadingOverlay) {
            window.utils.showLoadingOverlay('Analyzing query...');
        }
        
        // The API expects query as a query parameter in the URL (even though it's POST)
        const encodedQuery = encodeURIComponent(query);
        const url = `performance/analyze-query?query=${encodedQuery}`;
        const result = await window.api.post(url, {});
        
        const resultsDiv = document.getElementById('queryAnalysisResults');
        
        if (result.status === 'success' && result.analysis) {
            renderExecutionPlan(result.analysis);
            renderPerformanceMetrics(result.analysis);
            resultsDiv.style.display = 'block';
        } else {
            resultsDiv.innerHTML = '<div class="alert alert-warning">No analysis available</div>';
            resultsDiv.style.display = 'block';
        }
    } catch (error) {
        document.getElementById('queryAnalysisResults').innerHTML = 
            '<div class="alert alert-danger">Error analyzing query: ' + (error.message || 'Unknown error') + '</div>';
        document.getElementById('queryAnalysisResults').style.display = 'block';
        showError('Error analyzing query');
    } finally {
        if (window.utils && window.utils.hideLoadingOverlay) {
            window.utils.hideLoadingOverlay();
        }
    }
}

function renderExecutionPlan(analysis) {
    const table = document.getElementById('executionPlanTable');
    
    if (analysis.execution_plan && analysis.execution_plan.length > 0) {
        let html = '<h6>Execution Plan</h6><div class="table-responsive"><table class="table table-sm table-bordered"><thead><tr>';
        html += '<th>Table</th><th>Type</th><th>Possible Keys</th><th>Key Used</th><th>Rows</th><th>Extra</th></tr></thead><tbody>';
        
        analysis.execution_plan.forEach(row => {
            html += `<tr>
                <td>${row.table || '-'}</td>
                <td><span class="badge ${getTypeBadgeClass(row.type)}">${row.type || '-'}</span></td>
                <td>${row.possible_keys || '-'}</td>
                <td>${row.key || '-'}</td>
                <td>${row.rows || '-'}</td>
                <td>${row.extra || '-'}</td>
            </tr>`;
        });
        
        html += '</tbody></table></div>';
        table.innerHTML = html;
    } else {
        table.innerHTML = '<p class="text-muted">No execution plan available</p>';
    }
}

function renderPerformanceMetrics(analysis) {
    const container = document.getElementById('performanceMetrics');
    
    const metrics = analysis.metrics || {};
    container.innerHTML = `
        <h6>Performance Metrics</h6>
        <div class="row">
            <div class="col-md-4">
                <div class="card bg-light">
                    <div class="card-body">
                        <h6>Estimated Cost</h6>
                        <p class="h4">${metrics.estimated_cost || 'N/A'}</p>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card bg-light">
                    <div class="card-body">
                        <h6>Total Rows</h6>
                        <p class="h4">${metrics.total_rows || 'N/A'}</p>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card bg-light">
                    <div class="card-body">
                        <h6>Indexes Used</h6>
                        <p class="h4">${metrics.indexes_used || 0}</p>
                    </div>
                </div>
            </div>
        </div>
        ${analysis.recommendations ? `
            <div class="alert alert-info mt-3">
                <strong>Recommendations:</strong>
                <ul class="mb-0">
                    ${analysis.recommendations.map(rec => `<li>${rec}</li>`).join('')}
                </ul>
            </div>
        ` : ''}
    `;
}

function getTypeBadgeClass(type) {
    const classes = {
        'ALL': 'bg-danger',
        'index': 'bg-success',
        'ref': 'bg-warning',
        'eq_ref': 'bg-info'
    };
    return classes[type] || 'bg-secondary';
}

async function loadTableSizes() {
    try {
        const result = await window.api.get('maintenance/table-sizes');
        const container = document.getElementById('tableSizesContainer');
        
        if (result.status === 'success' && result.tables) {
            const sorted = result.tables.sort((a, b) => b.size_mb - a.size_mb);
            
            container.innerHTML = `
                <div class="table-responsive">
                    <table class="table table-sm">
                        <thead>
                            <tr>
                                <th>Table Name</th>
                                <th>Size (MB)</th>
                                <th>Rows</th>
                                <th>Data Size (MB)</th>
                                <th>Index Size (MB)</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${sorted.map(table => `
                                <tr>
                                    <td><strong>${table.table_name}</strong></td>
                                    <td>${table.size_mb.toFixed(2)}</td>
                                    <td>${table.table_rows ? table.table_rows.toLocaleString() : 'N/A'}</td>
                                    <td>${table.data_mb ? table.data_mb.toFixed(2) : 'N/A'}</td>
                                    <td>${table.index_mb ? table.index_mb.toFixed(2) : 'N/A'}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                        <tfoot>
                            <tr class="table-info">
                                <td><strong>Total</strong></td>
                                <td><strong>${result.total_size_mb.toFixed(2)}</strong></td>
                                <td colspan="3"></td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            `;
        }
    } catch (error) {
        document.getElementById('tableSizesContainer').innerHTML = 
            '<div class="alert alert-danger">Error loading table sizes: ' + (error.message || 'Unknown error') + '</div>';
    }
}

async function analyzeTable() {
    const tableName = document.getElementById('tableToAnalyze').value;
    if (!tableName) {
        showError('Please select a table');
        return;
    }
    
    try {
        if (window.utils && window.utils.showLoadingOverlay) {
            window.utils.showLoadingOverlay(`Analyzing table ${tableName}...`);
        }
        
        const result = await window.api.post('maintenance/analyze-table', {}, {
            params: { table_name: tableName }
        });
        
        if (result.status === 'success') {
            showSuccess(`Table ${tableName} analyzed successfully`);
        } else {
            showError('Failed to analyze table');
        }
    } catch (error) {
        showError('Error analyzing table: ' + (error.message || 'Unknown error'));
    } finally {
        if (window.utils && window.utils.hideLoadingOverlay) {
            window.utils.hideLoadingOverlay();
        }
    }
}

async function optimizeTable() {
    const tableName = document.getElementById('tableToOptimize').value;
    if (!tableName) {
        showError('Please select a table');
        return;
    }
    
    if (!confirm(`Optimize table ${tableName}? This may take several minutes.`)) {
        return;
    }
    
    try {
        if (window.utils && window.utils.showLoadingOverlay) {
            window.utils.showLoadingOverlay(`Optimizing table ${tableName}... This may take a while.`);
        }
        
        const result = await window.api.post('maintenance/optimize-table', {}, {
            params: { table_name: tableName }
        });
        
        if (result.status === 'success') {
            showSuccess(`Table ${tableName} optimized successfully`);
        } else {
            showError('Failed to optimize table');
        }
    } catch (error) {
        showError('Error optimizing table: ' + (error.message || 'Unknown error'));
    } finally {
        if (window.utils && window.utils.hideLoadingOverlay) {
            window.utils.hideLoadingOverlay();
        }
    }
}

async function analyzeAllTables() {
    if (!confirm('Analyze all tables? This may take several minutes.')) return;
    
    try {
        if (window.utils && window.utils.showLoadingOverlay) {
            window.utils.showLoadingOverlay('Analyzing all tables...');
        }
        
        const result = await window.api.post('maintenance/analyze-all');
        
        if (result.status === 'success') {
            const count = result.result?.tables_analyzed?.length || 0;
            showSuccess(`Analyzed ${count} tables`);
        } else {
            showError('Failed to analyze all tables');
        }
    } catch (error) {
        showError('Error analyzing all tables: ' + (error.message || 'Unknown error'));
    } finally {
        if (window.utils && window.utils.hideLoadingOverlay) {
            window.utils.hideLoadingOverlay();
        }
    }
}

async function optimizeAllTables() {
    if (!confirm('Optimize all tables? This may take 10+ minutes for large databases.')) return;
    
    try {
        if (window.utils && window.utils.showLoadingOverlay) {
            window.utils.showLoadingOverlay('Optimizing all tables... This will take a while.');
        }
        
        const result = await window.api.post('maintenance/optimize-all');
        
        if (result.status === 'success') {
            const count = result.result?.tables_optimized?.length || 0;
            showSuccess(`Optimized ${count} tables`);
        } else {
            showError('Failed to optimize all tables');
        }
    } catch (error) {
        showError('Error optimizing all tables: ' + (error.message || 'Unknown error'));
    } finally {
        if (window.utils && window.utils.hideLoadingOverlay) {
            window.utils.hideLoadingOverlay();
        }
    }
}

// Export functions for onclick handlers
window.createUser = createUser;
window.promoteUser = promoteUser;
window.editUser = editUser;
window.deleteUser = deleteUser;
window.promoteUserById = promoteUserById;
window.demoteAdmin = demoteAdmin;
window.loadETLStatus = loadETLStatus;
window.runETLPipeline = runETLPipeline;
window.refreshAllMaterializedViews = refreshAllMaterializedViews;
window.loadOLAPAnalysis = loadOLAPAnalysis;
window.loadIsolationLevel = loadIsolationLevel;
window.setIsolationLevel = setIsolationLevel;
window.analyzeQuery = analyzeQuery;
window.loadTableSizes = loadTableSizes;
window.analyzeTable = analyzeTable;
window.optimizeTable = optimizeTable;
window.analyzeAllTables = analyzeAllTables;
window.optimizeAllTables = optimizeAllTables;


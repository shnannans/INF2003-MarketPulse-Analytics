/**
 * Company Management Handler (Tasks 52-53: Company Management Interface - CRUD Operations & Soft Delete Management)
 */

let allCompanies = [];
let showDeleted = false;

document.addEventListener('DOMContentLoaded', async function() {
    // Check authentication and admin role
    if (!window.auth || !window.auth.isAuthenticated()) {
        window.location.href = 'login.html';
        return;
    }
    
    if (!window.auth.isAdmin()) {
        showError('Access denied. Admin privileges required.');
        setTimeout(() => {
            window.location.href = 'index.html';
        }, 2000);
        return;
    }
    
    // Load companies
    await loadCompanies();
    
    // Setup search
    document.getElementById('companySearch').addEventListener('input', filterCompanies);
    
    // Setup ticker uppercase
    document.getElementById('ticker')?.addEventListener('input', function(e) {
        e.target.value = e.target.value.toUpperCase();
    });
});

async function loadCompanies() {
    try {
        const response = await window.api.get('/companies', { limit: 200 });
        
        if (response.status === 'success' && response.companies) {
            allCompanies = response.companies;
            renderCompaniesTable(allCompanies.filter(c => !c.deleted_at));
        }
    } catch (error) {
        console.error('Error loading companies:', error);
        showError('Failed to load companies. Please try again.');
        document.getElementById('companiesTableBody').innerHTML = 
            '<tr><td colspan="5" class="text-center text-danger">Error loading companies</td></tr>';
    }
}

async function loadDeletedCompanies() {
    showDeleted = !showDeleted;
    const button = event.target;
    
    try {
        const response = await window.api.get('/companies', { include_deleted: true, limit: 200 });
        
        if (response.status === 'success' && response.companies) {
            allCompanies = response.companies;
            if (showDeleted) {
                renderCompaniesTable(allCompanies.filter(c => c.deleted_at), true);
                button.innerHTML = '<i class="bi bi-eye"></i> View Active';
            } else {
                renderCompaniesTable(allCompanies.filter(c => !c.deleted_at), false);
                button.innerHTML = '<i class="bi bi-trash"></i> View Deleted';
            }
        }
    } catch (error) {
        console.error('Error loading companies:', error);
        showError('Failed to load companies. Please try again.');
    }
}

function renderCompaniesTable(companies, showDeletedFlag = false) {
    const tbody = document.getElementById('companiesTableBody');
    
    if (companies.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted">No companies found</td></tr>`;
        return;
    }
    
    tbody.innerHTML = companies.map(company => {
        const rowClass = company.deleted_at ? 'deleted-row' : '';
        return `
            <tr class="${rowClass}">
                <td><strong>${escapeHtml(company.ticker)}</strong></td>
                <td>${escapeHtml(company.company_name || 'N/A')}</td>
                <td>${escapeHtml(company.sector || 'N/A')}</td>
                <td>${company.market_cap ? formatMarketCap(company.market_cap) : 'N/A'}</td>
                <td>
                    ${company.deleted_at ? `
                        <button class="btn btn-sm btn-outline-success" onclick="restoreCompany('${company.ticker}')" title="Restore">
                            <i class="bi bi-arrow-counterclockwise"></i> Restore
                        </button>
                    ` : `
                        <button class="btn btn-sm btn-outline-primary" onclick="editCompany('${company.ticker}')" title="Edit">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteCompany('${company.ticker}')" title="Delete">
                            <i class="bi bi-trash"></i>
                        </button>
                    `}
                </td>
            </tr>
        `;
    }).join('');
}

function filterCompanies() {
    const searchTerm = document.getElementById('companySearch').value.toLowerCase();
    const filtered = allCompanies.filter(company => 
        company.ticker.toLowerCase().includes(searchTerm) ||
        (company.company_name && company.company_name.toLowerCase().includes(searchTerm))
    );
    renderCompaniesTable(filtered.filter(c => showDeleted ? c.deleted_at : !c.deleted_at), showDeleted);
}

async function createCompany() {
    const ticker = document.getElementById('ticker').value.trim().toUpperCase();
    const companyName = document.getElementById('companyName').value.trim();
    const sector = document.getElementById('sector').value.trim();
    const marketCap = document.getElementById('marketCap').value ? parseInt(document.getElementById('marketCap').value) : null;
    const fetchData = document.getElementById('fetchData').checked;
    
    if (!ticker || !companyName) {
        showError('Ticker and company name are required');
        return;
    }
    
    const spinner = document.getElementById('createSpinner');
    const button = spinner.parentElement;
    button.disabled = true;
    spinner.classList.remove('d-none');
    
    try {
        const companyData = {
            ticker: ticker,
            company_name: companyName,
            sector: sector || null,
            market_cap: marketCap
        };
        
        const response = await window.api.post('/companies', companyData);
        
        if (response.status === 'success') {
            showSuccess('Company created successfully!');
            bootstrap.Modal.getInstance(document.getElementById('createCompanyModal')).hide();
            document.getElementById('createCompanyForm').reset();
            
            // If fetch data is enabled, trigger data fetch (this would be handled by backend)
            if (fetchData) {
                showSuccess('Company created. Historical data will be fetched automatically.');
            }
            
            await loadCompanies();
        } else {
            showError(response.message || 'Failed to create company');
        }
    } catch (error) {
        showError(error.message || 'Failed to create company. Please try again.');
    } finally {
        button.disabled = false;
        spinner.classList.add('d-none');
    }
}

async function editCompany(ticker) {
    try {
        const response = await window.api.get(`/companies/${ticker}`);
        
        if (response.status === 'success' && response.company) {
            const company = response.company;
            
            document.getElementById('editTicker').value = ticker;
            document.getElementById('editTickerDisplay').value = ticker;
            document.getElementById('editCompanyName').value = company.company_name || '';
            document.getElementById('editSector').value = company.sector || '';
            document.getElementById('editMarketCap').value = company.market_cap || '';
            
            // Optimistic Locking (Priority 2): Store version for conflict detection
            const version = company.version || 0;
            document.getElementById('editVersion').value = version;
            document.getElementById('editVersionDisplay').textContent = version;
            
            const modal = new bootstrap.Modal(document.getElementById('editCompanyModal'));
            modal.show();
        }
    } catch (error) {
        showError('Failed to load company details. Please try again.');
    }
}

async function updateCompany() {
    const ticker = document.getElementById('editTicker').value;
    const companyName = document.getElementById('editCompanyName').value.trim();
    const sector = document.getElementById('editSector').value.trim();
    const marketCap = document.getElementById('editMarketCap').value ? parseInt(document.getElementById('editMarketCap').value) : null;
    const expectedVersion = parseInt(document.getElementById('editVersion').value) || 0;
    
    if (!companyName) {
        showError('Company name is required');
        return;
    }
    
    const spinner = document.getElementById('updateSpinner');
    const button = spinner.parentElement;
    button.disabled = true;
    spinner.classList.remove('d-none');
    
    try {
        // Try optimistic locking endpoint first (Priority 2)
        let response;
        try {
            response = await window.api.patch(`/companies/${ticker}/optimistic`, {
                company_name: companyName,
                sector: sector || null,
                market_cap: marketCap
            }, {
                params: { expected_version: expectedVersion }
            });
        } catch (optimisticError) {
            // If optimistic locking fails (409 conflict or endpoint not available), fallback to regular update
            if (optimisticError.message && optimisticError.message.includes('409')) {
                // Version conflict - reload company data
                const updatedCompany = await window.api.get(`/companies/${ticker}`);
                if (updatedCompany.status === 'success' && updatedCompany.company) {
                    const company = updatedCompany.company;
                    document.getElementById('editCompanyName').value = company.company_name || '';
                    document.getElementById('editSector').value = company.sector || '';
                    document.getElementById('editMarketCap').value = company.market_cap || '';
                    const newVersion = company.version || 0;
                    document.getElementById('editVersion').value = newVersion;
                    document.getElementById('editVersionDisplay').textContent = `${newVersion} (Updated - please review changes)`;
                    document.getElementById('editVersionDisplay').parentElement.className = 'alert alert-warning mb-0';
                    showError('Update failed: Record was modified by another user. Please review the changes and try again.');
                    return;
                }
            }
            // Fallback to regular update endpoint
            response = await window.api.put(`/companies/${ticker}`, {
                company_name: companyName,
                sector: sector || null,
                market_cap: marketCap
            });
        }
        
        if (response.status === 'success') {
            showSuccess('Company updated successfully!');
            bootstrap.Modal.getInstance(document.getElementById('editCompanyModal')).hide();
            await loadCompanies();
        } else {
            showError(response.message || 'Failed to update company');
        }
    } catch (error) {
        showError(error.message || 'Failed to update company. Please try again.');
    } finally {
        button.disabled = false;
        spinner.classList.add('d-none');
    }
}

async function deleteCompany(ticker) {
    if (!confirm(`Are you sure you want to delete company ${ticker}? This action can be undone.`)) {
        return;
    }
    
    try {
        const response = await window.api.delete(`/companies/${ticker}`);
        
        if (response.status === 'success') {
            showSuccess('Company deleted successfully!');
            await loadCompanies();
        } else {
            showError(response.message || 'Failed to delete company');
        }
    } catch (error) {
        showError(error.message || 'Failed to delete company. Please try again.');
    }
}

async function restoreCompany(ticker) {
    try {
        const response = await window.api.patch(`/companies/${ticker}/restore`);
        
        if (response.status === 'success') {
            showSuccess('Company restored successfully!');
            await loadCompanies();
        } else {
            showError(response.message || 'Failed to restore company');
        }
    } catch (error) {
        showError(error.message || 'Failed to restore company. Please try again.');
    }
}

async function exportCompanies() {
    try {
        const response = await window.api.get('/export/companies', { format: 'json' });
        
        if (response.status === 'success') {
            // Download as JSON file
            const dataStr = JSON.stringify(response.data, null, 2);
            const dataBlob = new Blob([dataStr], { type: 'application/json' });
            const url = URL.createObjectURL(dataBlob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `companies_${new Date().toISOString().split('T')[0]}.json`;
            link.click();
            URL.revokeObjectURL(url);
            
            showSuccess('Companies exported successfully!');
        }
    } catch (error) {
        showError('Failed to export companies. Please try again.');
    }
}

function formatMarketCap(value) {
    if (value >= 1e12) return `$${(value / 1e12).toFixed(2)}T`;
    if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
    if (value >= 1e6) return `$${(value / 1e6).toFixed(2)}M`;
    return `$${value.toLocaleString()}`;
}

function escapeHtml(text) {
    if (!text) return '';
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

// Export functions for onclick handlers
window.createCompany = createCompany;
window.updateCompany = updateCompany;
window.editCompany = editCompany;
window.deleteCompany = deleteCompany;
window.restoreCompany = restoreCompany;
window.exportCompanies = exportCompanies;


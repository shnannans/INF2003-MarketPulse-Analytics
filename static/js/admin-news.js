/**
 * News Management Handler (Task 54: News Management Interface)
 */

let allNews = [];

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
    
    // Load news
    await loadNews();
    
    // Setup search
    document.getElementById('newsSearch').addEventListener('input', filterNews);
    
    // Setup ticker uppercase
    document.getElementById('newsTicker')?.addEventListener('input', function(e) {
        e.target.value = e.target.value.toUpperCase();
    });
});

async function loadNews() {
    try {
        const response = await window.api.get('/news', { limit: 100, live: false });
        
        if (response.status === 'success' && response.articles) {
            allNews = response.articles;
            renderNewsTable(allNews);
        }
    } catch (error) {
        console.error('Error loading news:', error);
        showError('Failed to load news articles. Please try again.');
        document.getElementById('newsTableBody').innerHTML = 
            '<tr><td colspan="6" class="text-center text-danger">Error loading news</td></tr>';
    }
}

function renderNewsTable(articles) {
    const tbody = document.getElementById('newsTableBody');
    
    if (articles.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No news articles found</td></tr>';
        return;
    }
    
    tbody.innerHTML = articles.map(article => {
        const sentiment = article.sentiment_analysis?.overall_sentiment || 'neutral';
        const sentimentClass = `sentiment-${sentiment}`;
        const sentimentScore = article.sentiment_analysis?.overall_score || 0;
        
        return `
            <tr>
                <td class="article-preview" title="${escapeHtml(article.title || '')}">
                    ${escapeHtml((article.title || 'No title').substring(0, 60))}${(article.title || '').length > 60 ? '...' : ''}
                </td>
                <td><span class="badge bg-secondary">${escapeHtml(article.ticker || 'N/A')}</span></td>
                <td>${escapeHtml(article.source || 'N/A')}</td>
                <td>${article.published_date ? new Date(article.published_date).toLocaleDateString() : 'N/A'}</td>
                <td>
                    <span class="sentiment-badge ${sentimentClass}">
                        ${sentiment.charAt(0).toUpperCase() + sentiment.slice(1)} 
                        (${sentimentScore > 0 ? '+' : ''}${sentimentScore.toFixed(2)})
                    </span>
                </td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="viewArticle('${article.article_id || article.id}')" title="View">
                        <i class="bi bi-eye"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-secondary" onclick="editArticle('${article.article_id || article.id}')" title="Edit">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteArticle('${article.article_id || article.id}')" title="Delete">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

function filterNews() {
    const searchTerm = document.getElementById('newsSearch').value.toLowerCase();
    const filtered = allNews.filter(article => 
        (article.title && article.title.toLowerCase().includes(searchTerm)) ||
        (article.ticker && article.ticker.toLowerCase().includes(searchTerm)) ||
        (article.source && article.source.toLowerCase().includes(searchTerm))
    );
    renderNewsTable(filtered);
}

function applyFilters() {
    const sentiment = document.getElementById('sentimentFilter').value;
    const date = document.getElementById('dateFilter').value;
    const searchTerm = document.getElementById('newsSearch').value.toLowerCase();
    
    let filtered = allNews;
    
    if (searchTerm) {
        filtered = filtered.filter(article => 
            (article.title && article.title.toLowerCase().includes(searchTerm)) ||
            (article.ticker && article.ticker.toLowerCase().includes(searchTerm)) ||
            (article.source && article.source.toLowerCase().includes(searchTerm))
        );
    }
    
    if (sentiment) {
        filtered = filtered.filter(article => 
            (article.sentiment_analysis?.overall_sentiment || 'neutral') === sentiment
        );
    }
    
    if (date) {
        filtered = filtered.filter(article => {
            if (!article.published_date) return false;
            const articleDate = new Date(article.published_date).toISOString().split('T')[0];
            return articleDate === date;
        });
    }
    
    renderNewsTable(filtered);
}

async function ingestNews() {
    const title = document.getElementById('newsTitle').value.trim();
    const content = document.getElementById('newsContent').value.trim();
    const ticker = document.getElementById('newsTicker').value.trim().toUpperCase();
    const source = document.getElementById('newsSource').value.trim();
    const url = document.getElementById('newsUrl').value.trim();
    const publishedDate = document.getElementById('newsDate').value;
    const autoSentiment = document.getElementById('autoSentiment').checked;
    
    if (!title || !content) {
        showError('Title and content are required');
        return;
    }
    
    const spinner = document.getElementById('ingestSpinner');
    const button = spinner.parentElement;
    button.disabled = true;
    spinner.classList.remove('d-none');
    
    try {
        const articleData = {
            title: title,
            content: content,
            ticker: ticker || null,
            source: source || null,
            url: url || null,
            published_date: publishedDate || new Date().toISOString()
        };
        
        if (!autoSentiment) {
            // If auto sentiment is disabled, we'd need to provide sentiment_analysis
            // For now, we'll always compute it
        }
        
        const response = await window.api.post('/news/ingest', articleData);
        
        if (response.status === 'success') {
            showSuccess('News article ingested successfully!');
            bootstrap.Modal.getInstance(document.getElementById('ingestNewsModal')).hide();
            document.getElementById('ingestNewsForm').reset();
            await loadNews();
        } else {
            showError(response.message || 'Failed to ingest news article');
        }
    } catch (error) {
        showError(error.message || 'Failed to ingest news article. Please try again.');
    } finally {
        button.disabled = false;
        spinner.classList.add('d-none');
    }
}

async function bulkIngest() {
    const fileInput = document.getElementById('bulkFile');
    const file = fileInput.files[0];
    
    if (!file) {
        showError('Please select a JSON file');
        return;
    }
    
    const spinner = document.getElementById('bulkSpinner');
    const button = spinner.parentElement;
    button.disabled = true;
    spinner.classList.remove('d-none');
    
    try {
        const fileContent = await file.text();
        const data = JSON.parse(fileContent);
        
        if (!data.articles || !Array.isArray(data.articles)) {
            showError('Invalid file format. Expected { "articles": [...] }');
            return;
        }
        
        const response = await window.api.post('/news/ingest', {
            articles: data.articles
        });
        
        if (response.status === 'success') {
            const successCount = response.results?.filter(r => r.status === 'ingested').length || 0;
            const errorCount = response.errors?.length || 0;
            
            showSuccess(`Bulk ingest completed! ${successCount} articles ingested, ${errorCount} errors.`);
            bootstrap.Modal.getInstance(document.getElementById('bulkIngestModal')).hide();
            fileInput.value = '';
            await loadNews();
        } else {
            showError(response.message || 'Failed to bulk ingest articles');
        }
    } catch (error) {
        if (error instanceof SyntaxError) {
            showError('Invalid JSON file. Please check the file format.');
        } else {
            showError(error.message || 'Failed to bulk ingest articles. Please try again.');
        }
    } finally {
        button.disabled = false;
        spinner.classList.add('d-none');
    }
}

async function viewArticle(articleId) {
    try {
        const response = await window.api.get(`/news/${articleId}`);
        
        if (response.status === 'success' && response.article) {
            const article = response.article;
            
            // Show article in modal or new page
            alert(`Title: ${article.title}\n\nContent: ${(article.content || '').substring(0, 200)}...\n\nSentiment: ${article.sentiment_analysis?.overall_sentiment || 'N/A'}`);
        }
    } catch (error) {
        showError('Failed to load article. Please try again.');
    }
}

async function editArticle(articleId) {
    try {
        const response = await window.api.get(`/news/${articleId}`);
        
        if (response.status === 'success' && response.article) {
            const article = response.article;
            
            // Simple edit - in production, use a modal
            const newTitle = prompt('Enter new title:', article.title);
            if (!newTitle || newTitle === article.title) return;
            
            const updateResponse = await window.api.patch(`/news/${articleId}`, {
                title: newTitle
            });
            
            if (updateResponse.status === 'success') {
                showSuccess('Article updated successfully!');
                await loadNews();
            } else {
                showError(updateResponse.message || 'Failed to update article');
            }
        }
    } catch (error) {
        showError('Failed to load article. Please try again.');
    }
}

async function deleteArticle(articleId) {
    if (!confirm('Are you sure you want to delete this article? This action can be undone.')) {
        return;
    }
    
    try {
        const response = await window.api.delete(`/news/${articleId}`);
        
        if (response.status === 'success') {
            showSuccess('Article deleted successfully!');
            await loadNews();
        } else {
            showError(response.message || 'Failed to delete article');
        }
    } catch (error) {
        showError(error.message || 'Failed to delete article. Please try again.');
    }
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
window.ingestNews = ingestNews;
window.bulkIngest = bulkIngest;
window.viewArticle = viewArticle;
window.editArticle = editArticle;
window.deleteArticle = deleteArticle;
window.applyFilters = applyFilters;


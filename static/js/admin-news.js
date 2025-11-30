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
        console.log('Loading news articles...');
        
        // Load ONLY from Firestore (live: false)
        // Use a large days value (365) to get all articles from Firestore, not just recent ones
        let response = await window.api.get('/news', { limit: 100, live: false, days: 365 });
        console.log('Firestore response:', response);
        console.log('Articles count:', response.articles ? response.articles.length : 0);
        
        if (response && response.status === 'success') {
            allNews = response.articles || [];
            console.log(`Loaded ${allNews.length} articles`);
            console.log('First article sample:', allNews[0] ? JSON.stringify(allNews[0], null, 2) : 'No articles');
            
            if (allNews.length === 0) {
                document.getElementById('newsTableBody').innerHTML = 
                    '<tr><td colspan="6" class="text-center text-muted">' +
                    '<p>No news articles found.</p>' +
                    '<p><small>Click "Ingest News" to manually add articles.</small></p>' +
                    '<button class="btn btn-sm btn-primary mt-2" onclick="loadNews()">Refresh</button>' +
                    '</td></tr>';
            } else {
                renderNewsTable(allNews);
            }
        } else {
            console.error('Invalid response format:', response);
            document.getElementById('newsTableBody').innerHTML = 
                '<tr><td colspan="6" class="text-center text-muted">No news articles found. Click "Ingest News" to add articles.</td></tr>';
        }
    } catch (error) {
        console.error('Error loading news:', error);
        showError('Failed to load news articles: ' + (error.message || 'Unknown error'));
        document.getElementById('newsTableBody').innerHTML = 
            '<tr><td colspan="6" class="text-center text-danger">' +
            '<p>Error loading news. Please try again.</p>' +
            '<button class="btn btn-sm btn-primary mt-2" onclick="loadNews()">Retry</button>' +
            '</td></tr>';
    }
}

function renderNewsTable(articles) {
    const tbody = document.getElementById('newsTableBody');
    if (!tbody) {
        console.error('newsTableBody element not found');
        return;
    }
    
    if (!articles || articles.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No news articles found</td></tr>';
        return;
    }
    
    console.log(`Rendering ${articles.length} articles to table`);
    
    try {
        tbody.innerHTML = articles.map(article => {
            // Get sentiment info
            const sentimentData = article.sentiment_analysis || {};
            const sentiment = sentimentData.overall_sentiment || 'neutral';
            const sentimentScore = sentimentData.overall_score || sentimentData.polarity || 0;
            const sentimentClass = `sentiment-${sentiment}`;
            
            // Get article ID - could be article_id or id (from Firestore document ID)
            const articleId = article.article_id || article.id || '';
            
            // Handle source - could be string or object
            let sourceText = 'N/A';
            if (article.source) {
                if (typeof article.source === 'string') {
                    sourceText = article.source;
                } else if (article.source.name) {
                    sourceText = article.source.name;
                } else if (article.source.url) {
                    sourceText = article.source.url;
                }
            }
            
            return `
                <tr>
                    <td class="article-preview" title="${escapeHtml(article.title || '')}">
                        ${escapeHtml((article.title || 'No title').substring(0, 60))}${(article.title || '').length > 60 ? '...' : ''}
                    </td>
                    <td><span class="badge bg-secondary">${escapeHtml(article.ticker || 'N/A')}</span></td>
                    <td>${escapeHtml(sourceText)}</td>
                    <td>${article.published_date ? new Date(article.published_date).toLocaleDateString() : 'N/A'}</td>
                    <td>
                        <span class="sentiment-badge ${sentimentClass}">
                            ${sentiment.charAt(0).toUpperCase() + sentiment.slice(1)} 
                            (${sentimentScore > 0 ? '+' : ''}${sentimentScore.toFixed(2)})
                        </span>
                    </td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary" onclick="viewArticle('${escapeHtml(articleId)}')" title="View">
                            <i class="bi bi-eye"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-secondary" onclick="editArticle('${escapeHtml(articleId)}')" title="Edit">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteArticle('${escapeHtml(articleId)}')" title="Delete">
                            <i class="bi bi-trash"></i>
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
        console.log(`Successfully rendered ${articles.length} articles`);
    } catch (error) {
        console.error('Error rendering articles:', error);
        console.error('Article sample:', articles[0]);
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-danger">Error rendering articles. Check console for details.</td></tr>';
    }
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
            const sentiment = article.sentiment_analysis?.overall_sentiment || 'neutral';
            const sentimentScore = article.sentiment_analysis?.overall_score || 0;
            const sentimentClass = `sentiment-${sentiment}`;
            
            // Populate view modal
            document.getElementById('viewArticleTitle').textContent = article.title || 'No Title';
            document.getElementById('viewArticleBody').innerHTML = `
                <div class="mb-3">
                    <strong>Content:</strong>
                    <p class="mt-2">${escapeHtml(article.content || 'No content available')}</p>
                </div>
                <div class="row mb-3">
                    <div class="col-md-6">
                        <strong>Ticker:</strong> <span class="badge bg-secondary">${escapeHtml(article.ticker || 'N/A')}</span>
                    </div>
                    <div class="col-md-6">
                        <strong>Source:</strong> ${escapeHtml(article.source || 'N/A')}
                    </div>
                </div>
                <div class="row mb-3">
                    <div class="col-md-6">
                        <strong>Published Date:</strong> ${article.published_date ? new Date(article.published_date).toLocaleString() : 'N/A'}
                    </div>
                    <div class="col-md-6">
                        <strong>Sentiment:</strong> 
                        <span class="sentiment-badge ${sentimentClass}">
                            ${sentiment.charAt(0).toUpperCase() + sentiment.slice(1)} 
                            (${sentimentScore > 0 ? '+' : ''}${sentimentScore.toFixed(2)})
                        </span>
                    </div>
                </div>
                ${article.url ? `<div class="mb-3"><strong>URL:</strong> <a href="${escapeHtml(article.url)}" target="_blank">${escapeHtml(article.url)}</a></div>` : ''}
                ${article.article_id ? `<div class="mb-3"><small class="text-muted">Article ID: ${escapeHtml(article.article_id)}</small></div>` : ''}
            `;
            
            // Show modal
            const modal = new bootstrap.Modal(document.getElementById('viewArticleModal'));
            modal.show();
        } else {
            showError('Article not found');
        }
    } catch (error) {
        console.error('Error viewing article:', error);
        showError('Failed to load article: ' + (error.message || 'Unknown error'));
    }
}

let currentEditArticleId = null;

async function editArticle(articleId) {
    try {
        const response = await window.api.get(`/news/${articleId}`);
        
        if (response.status === 'success' && response.article) {
            const article = response.article;
            currentEditArticleId = articleId;
            
            // Populate edit form
            document.getElementById('editArticleId').value = articleId;
            document.getElementById('editTitle').value = article.title || '';
            document.getElementById('editContent').value = article.content || '';
            document.getElementById('editTicker').value = article.ticker || '';
            document.getElementById('editSource').value = article.source || '';
            document.getElementById('editUrl').value = article.url || '';
            
            // Convert published_date to datetime-local format
            if (article.published_date) {
                const date = new Date(article.published_date);
                const year = date.getFullYear();
                const month = String(date.getMonth() + 1).padStart(2, '0');
                const day = String(date.getDate()).padStart(2, '0');
                const hours = String(date.getHours()).padStart(2, '0');
                const minutes = String(date.getMinutes()).padStart(2, '0');
                document.getElementById('editPublishedDate').value = `${year}-${month}-${day}T${hours}:${minutes}`;
            }
            
            // Setup ticker uppercase
            document.getElementById('editTicker').addEventListener('input', function(e) {
                e.target.value = e.target.value.toUpperCase();
            });
            
            // Show modal
            const modal = new bootstrap.Modal(document.getElementById('editArticleModal'));
            modal.show();
        } else {
            showError('Article not found');
        }
    } catch (error) {
        console.error('Error loading article for edit:', error);
        showError('Failed to load article: ' + (error.message || 'Unknown error'));
    }
}

async function saveArticleEdit() {
    if (!currentEditArticleId) {
        showError('No article selected for editing');
        return;
    }
    
    const title = document.getElementById('editTitle').value.trim();
    const content = document.getElementById('editContent').value.trim();
    const ticker = document.getElementById('editTicker').value.trim().toUpperCase();
    const source = document.getElementById('editSource').value.trim();
    const url = document.getElementById('editUrl').value.trim();
    const publishedDate = document.getElementById('editPublishedDate').value;
    
    if (!title || !content) {
        showError('Title and content are required');
        return;
    }
    
    const spinner = document.getElementById('editSpinner');
    const button = spinner.parentElement;
    button.disabled = true;
    spinner.classList.remove('d-none');
    
    try {
        const updateData = {
            title: title,
            content: content,
            ticker: ticker || null,
            source: source || null,
            url: url || null,
            published_date: publishedDate ? new Date(publishedDate).toISOString() : null
        };
        
        const response = await window.api.patch(`/news/${currentEditArticleId}`, updateData);
        
        if (response.status === 'success') {
            showSuccess('Article updated successfully!');
            bootstrap.Modal.getInstance(document.getElementById('editArticleModal')).hide();
            await loadNews();
        } else {
            showError(response.message || 'Failed to update article');
        }
    } catch (error) {
        console.error('Error updating article:', error);
        showError('Failed to update article: ' + (error.message || 'Unknown error'));
    } finally {
        button.disabled = false;
        spinner.classList.add('d-none');
        currentEditArticleId = null;
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

async function fetchFromNewsAPI() {
    try {
        showSuccess('Fetching articles from NewsAPI... This may take a moment.');
        
        // Fetch from NewsAPI with live mode
        const response = await window.api.get('/news', { limit: 50, live: true, days: 30 });
        
        if (response.status === 'success') {
            const count = response.articles ? response.articles.length : 0;
            if (count > 0) {
                showSuccess(`Successfully fetched ${count} articles from NewsAPI!`);
                await loadNews(); // Reload to show new articles
            } else {
                showError('No articles were fetched. NewsAPI may be rate-limited or no articles found.');
            }
        } else {
            showError('Failed to fetch articles from NewsAPI');
        }
    } catch (error) {
        console.error('Error fetching from NewsAPI:', error);
        showError('Failed to fetch articles: ' + (error.message || 'Unknown error'));
    }
}

// Export functions for onclick handlers
window.ingestNews = ingestNews;
window.bulkIngest = bulkIngest;
window.viewArticle = viewArticle;
window.editArticle = editArticle;
window.deleteArticle = deleteArticle;
window.saveArticleEdit = saveArticleEdit;
window.applyFilters = applyFilters;
window.fetchFromNewsAPI = fetchFromNewsAPI;
window.loadNews = loadNews;


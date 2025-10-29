// js/main.js
document.addEventListener("DOMContentLoaded", () => {
  setupEventHandlers();
  loadDashboard(); // initial load
});

let priceChart = null;
let sentimentTrendChart = null;
let indicesChart = null;
let overlayChart = null;

// Helper function for safe element access
function safeGetElement(id, context = 'general') {
  const element = document.getElementById(id);
  if (!element) {
    console.warn(`Element with id '${id}' not found (${context})`);
  }
  return element;
}

// Helper function for safe element text update
function safeUpdateText(id, value, context = 'general') {
  const element = safeGetElement(id, context);
  if (element) {
    element.innerText = value;
    return true;
  }
  return false;
}

// Helper function for safe element HTML update
function safeUpdateHTML(id, value, context = 'general') {
  const element = safeGetElement(id, context);
  if (element) {
    element.innerHTML = value;
    return true;
  }
  return false;
}

function setupEventHandlers() {
  const applySearchBtn = safeGetElement("applySearch", "event handlers");
  if (applySearchBtn) {
    applySearchBtn.addEventListener("click", () => {
      loadDashboard();
    });
  }

  const applyFiltersBtn = safeGetElement("applyFilters", "event handlers");
  if (applyFiltersBtn) {
    applyFiltersBtn.addEventListener("click", () => {
      loadDashboard();
    });
  }

  const exportCSVBtn = safeGetElement("btnExportCSV", "event handlers");
  if (exportCSVBtn) {
    exportCSVBtn.addEventListener("click", exportCurrentViewCSV);
  }

  const runAlertsBtn = safeGetElement("btnRunAlerts", "event handlers");
  if (runAlertsBtn) {
    runAlertsBtn.addEventListener("click", runAlerts);
  }

  const wordcloudBtn = safeGetElement("btnWordcloud", "event handlers");
  if (wordcloudBtn) {
    wordcloudBtn.addEventListener("click", generateWordCloud);
  }
}

async function loadDashboard() {
  const tickerElement = safeGetElement("tickerSearch", "dashboard load");
  const daysElement = safeGetElement("dateRange", "dashboard load");
  const tickersFilterElement = safeGetElement("filterTickers", "dashboard load");
  const sentimentTypeElement = safeGetElement("sentimentType", "dashboard load");
  const keywordElement = safeGetElement("keywordFilter", "dashboard load");
  const sourceElement = safeGetElement("sourceSelect", "dashboard load");

  const ticker = tickerElement ? tickerElement.value.trim() : "";
  const days = daysElement ? parseInt(daysElement.value) : 7;
  const tickersFilter = tickersFilterElement ? tickersFilterElement.value.trim() : "";
  const sentimentType = sentimentTypeElement ? sentimentTypeElement.value : "";
  const keyword = keywordElement ? keywordElement.value.trim() : "";
  const source = sourceElement ? sourceElement.value : "";

  // Load KPIs
  try {
    const response = await fetch(`${window.API_BASE}dashboard?days=${days}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const summary = await response.json();
    console.log("Dashboard summary response:", summary); // Debug logging

    safeUpdateText("totalCompanies", summary.total_companies ?? "—", "dashboard KPI");

    // Load additional market summary data
    await loadMarketSummary();
  } catch (err) {
    console.error("Error fetching summary", err);
    showApiError("Failed to load dashboard summary");
  }

  // Stock price & moving averages
  loadStockPrices(ticker || (tickersFilter.split(",")[0] || "AAPL"), days, tickersFilter);

  // Indices overview
  loadIndices(days);

  // Sentiment trends & news
  loadSentimentTrend(ticker, days, sentimentType, keyword, source); // Filter by ticker for specific data

  // Combined overlay of price vs sentiment
  loadPriceSentimentOverlay(ticker || "AAPL", days);
  loadNewsFeed(ticker, days, sentimentType, keyword, source); // Filter by ticker for specific data

  // Sector heatmap + timeline (optional)
  loadSectorHeatmap(days);
  loadTimeline(days);
}

// ---------- Stock Prices (API: stock_analysis.py) ----------
async function loadStockPrices(ticker = "AAPL", days = 7, tickersFilter = "") {
  try {
    const resp = await fetch(`${window.API_BASE}stock_analysis?ticker=${encodeURIComponent(ticker)}&days=${days}`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const json = await resp.json();
    console.log("Stock analysis response:", json); // Debug logging
    const data = json.analysis || [];

    // Chart labels: date ascending
    const labels = data.slice().reverse().map(d => d.date);
    const close = data.slice().reverse().map(d => parseFloat(d.close_price));
    
    // Fix: Use correct column names from your database
    const ma5 = data.slice().reverse().map(d => d.ma_5 ? parseFloat(d.ma_5) : null);
    const ma20 = data.slice().reverse().map(d => d.ma_20 ? parseFloat(d.ma_20) : null);
    const ma50 = data.slice().reverse().map(d => d.ma_50 ? parseFloat(d.ma_50) : null);

    const chartElement = safeGetElement("priceChart", "stock prices chart");
    if (!chartElement) {
      console.warn("Price chart element not found, skipping chart creation");
      return;
    }
    const ctx = chartElement.getContext("2d");
    if (priceChart) priceChart.destroy();

    priceChart = new Chart(ctx, {
      type: "line",
      data: {
        labels,
        datasets: [
          { label: `${ticker} Close`, data: close, borderColor: "rgb(34,139,34)", tension:0.1, pointRadius: 2 },
          { label: "MA 5", data: ma5, borderColor: "rgb(30,144,255)", borderDash: [5,5], tension:0.1, pointRadius: 0 },
          { label: "MA 20", data: ma20, borderColor: "rgb(255,165,0)", borderDash: [5,5], tension:0.1, pointRadius: 0 },
          { label: "MA 50", data: ma50, borderColor: "rgb(255,99,132)", borderDash: [5,5], tension:0.1, pointRadius: 0 }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        scales: { x: { display: true }, y: { display: true } },
        plugins: {
          tooltip: {
            callbacks: {
              label: (ctx) => `${ctx.dataset.label}: ${ctx.formattedValue}`
            }
          }
        }
      }
    });

    // Update volume and market summary
    const last = data[0];
    if (last) {
      safeUpdateText("lastVolume", last.volume ?? "—", "stock prices");
      safeUpdateText("dailyVolume", last.volume ?? "—", "market summary");

      // Calculate price change
      if (data.length >= 2) {
        const prev = data[1];
        const change = ((last.close_price - prev.close_price) / prev.close_price) * 100;
        const changeText = `${change >= 0 ? '+' : ''}${change.toFixed(2)}%`;
        const changeElement = safeGetElement("priceChange", "market summary");
        if (changeElement) {
          changeElement.innerText = changeText;
          changeElement.className = `mb-0 h6 ${change >= 0 ? 'text-success' : 'text-danger'}`;
        }
      }
    }
  } catch (err) {
    console.error("Error loading stock prices", err);
    showApiError(`Failed to load stock data for ${ticker}`);
  }
}

// ---------- Market Indices (API: indices.py) ----------
async function loadIndices(days = 7) {
  try {
    const resp = await fetch(`${window.API_BASE}indices?days=${days}`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const json = await resp.json();
    console.log("Indices response:", json); // Debug logging
    const labels = json.trend.map(d => d.date);
    const datasets = json.indices.map(idx => ({
      label: idx.name, data: idx.values, tension:0.1
    }));

    const chartElement = safeGetElement("indicesChart", "indices chart");
    if (!chartElement) {
      console.warn("Indices chart element not found, skipping chart creation");
      return;
    }
    const ctx = chartElement.getContext("2d");
    if (indicesChart) indicesChart.destroy();
    indicesChart = new Chart(ctx, {
      type: "line",
      data: { labels, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: 'bottom' } }
      }
    });

    // index cards
    const container = safeGetElement("indexCards", "indices summary");
    if (container) {
      container.innerHTML = "";
      json.summary.forEach(s => {
        const col = document.createElement("div");
        col.className = "card p-2 me-2";
        col.style.minWidth = "150px";
        col.innerHTML = `<small>${s.name}</small><h6 class="${s.change_percent >=0 ? 'text-success' : 'text-danger'}">${s.change_percent}%</h6>`;
        container.appendChild(col);
      });
    }
  } catch (err) {
    console.error("Error loading indices", err);
    showApiError("Failed to load market indices");
  }
}

// ---------- Sentiment Trend & Wordcloud (API: sentiment.py) ----------
async function loadSentimentTrend(ticker="", days=7, sentiment="", keyword="", source="") {
  try {
    const q = new URLSearchParams({ ticker, days, sentiment, keyword, source, live: true });
    const resp = await fetch(`${window.API_BASE}sentiment?${q.toString()}`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const json = await resp.json();
    console.log("Sentiment API response:", json); // Debug logging

    const trends = json.trends || [];
    const labels = trends.map(t => t._id ? t._id.date : t.date || '');
    const values = trends.map(t => {
      const val = parseFloat(t.avg_sentiment);
      return isNaN(val) ? 0 : val;
    });

    console.log("Sentiment chart data:", { labels, values }); // Debug logging

    const chartElement = safeGetElement("sentimentTrendChart", "sentiment trend chart");
    if (!chartElement) {
      console.warn("Sentiment trend chart element not found, skipping chart creation");
      return;
    }
    const ctx = chartElement.getContext("2d");
    if (sentimentTrendChart) sentimentTrendChart.destroy();

    // Only create chart if we have valid data points
    if (labels.length > 0 && values.some(v => v !== 0)) {
      sentimentTrendChart = new Chart(ctx, {
        type: "bar",
        data: {
          labels,
          datasets: [
            {
              label: "Daily Sentiment",
              data: values,
              backgroundColor: values.map(v => v > 0.1 ? 'rgba(40, 167, 69, 0.8)' : v < -0.1 ? 'rgba(220, 53, 69, 0.8)' : 'rgba(108, 117, 125, 0.8)'),
              borderColor: values.map(v => v > 0.1 ? 'rgb(40, 167, 69)' : v < -0.1 ? 'rgb(220, 53, 69)' : 'rgb(108, 117, 125)'),
              borderWidth: 2,
              borderRadius: 4,
              borderSkipped: false
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: true,
              position: 'top',
              labels: {
                font: {
                  size: 12,
                  weight: 'bold'
                }
              }
            },
            tooltip: {
              callbacks: {
                title: (context) => `Date: ${context[0].label}`,
                label: (context) => {
                  const value = context.parsed.y;
                  const sentiment = value > 0.1 ? 'Positive' : value < -0.1 ? 'Negative' : 'Neutral';
                  return `${sentiment}: ${value >= 0 ? '+' : ''}${value.toFixed(3)}`;
                }
              },
              backgroundColor: 'rgba(0,0,0,0.8)',
              titleColor: 'white',
              bodyColor: 'white',
              borderColor: 'rgba(255,255,255,0.2)',
              borderWidth: 1
            }
          },
          scales: {
            x: {
              title: {
                display: true,
                text: 'Date',
                font: {
                  weight: 'bold'
                }
              },
              grid: {
                display: true,
                color: 'rgba(0,0,0,0.1)'
              }
            },
            y: {
              beginAtZero: true,
              min: -1,
              max: 1,
              title: {
                display: true,
                text: 'Sentiment Score',
                font: {
                  weight: 'bold'
                }
              },
              grid: {
                display: true,
                color: 'rgba(0,0,0,0.1)'
              },
              ticks: {
                callback: function(value) {
                  return value >= 0 ? '+' + value.toFixed(2) : value.toFixed(2);
                }
              }
            }
          },
          animation: {
            duration: 800,
            easing: 'easeInOutQuart'
          }
        }
      });

      // Add a horizontal line at zero for reference
      const chart = sentimentTrendChart;
      const originalDraw = chart.draw;
      chart.draw = function() {
        originalDraw.apply(this, arguments);

        const ctx = this.ctx;
        const yScale = this.scales.y;
        const zeroY = yScale.getPixelForValue(0);

        ctx.save();
        ctx.strokeStyle = 'rgba(0,0,0,0.3)';
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 5]);
        ctx.beginPath();
        ctx.moveTo(yScale.left, zeroY);
        ctx.lineTo(yScale.right, zeroY);
        ctx.stroke();
        ctx.restore();
      };

    } else {
      // Enhanced no data message
      ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);

      // Background
      ctx.fillStyle = "rgba(248, 249, 250, 0.8)";
      ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height);

      // Icon and text
      ctx.textAlign = "center";
      ctx.fillStyle = "#6c757d";

      // Large chart icon
      ctx.font = "48px Arial";
      ctx.fillText("📊", ctx.canvas.width / 2, ctx.canvas.height / 2 - 20);

      // Message
      ctx.font = "16px Arial";
      ctx.fillText("No sentiment data available", ctx.canvas.width / 2, ctx.canvas.height / 2 + 20);
      ctx.font = "14px Arial";
      ctx.fillStyle = "#adb5bd";
      ctx.fillText("Try adjusting filters or check data source", ctx.canvas.width / 2, ctx.canvas.height / 2 + 40);
    }

    // topics / highlights (simple listing)
    const topics = json.topics || [];
    const th = safeGetElement("topicHighlights", "topic highlights");
    if (th) {
      th.innerHTML = topics.map(t => `<span class="badge bg-light text-dark me-1 mb-1">${t.word} (${t.count})</span>`).join("");
    }
    // update KPIs
    safeUpdateText("totalArticles", json.statistics?.total_articles ?? "—", "sentiment KPI");
    safeUpdateText("avgSent", (json.statistics?.avg_sentiment ?? 0).toFixed(2), "sentiment KPI");
  } catch (err) {
    console.error("Error loading sentiment trend", err);
    showApiError("Failed to load sentiment data");
  }
}

// ---------- News Feed (API: news.py) ----------
async function loadNewsFeed(ticker = "", days = 7, sentiment="", keyword="", source="") {
  try {
    const q = new URLSearchParams({ ticker, days, sentiment, keyword, source, limit: 30, live: true });
    const resp = await fetch(`${window.API_BASE}news?${q.toString()}`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const json = await resp.json();
    console.log("News API response:", json); // Debug logging

    const feed = safeGetElement("newsFeed", "news feed");
    if (!feed) {
      console.warn("News feed element not found, skipping news display");
      return;
    }

    feed.innerHTML = "";

    if (!json.articles || json.articles.length === 0) {
      // Show proper message from API or default message
      const message = json.message || "No news articles available";
      feed.innerHTML = `
        <div class="text-center text-muted p-3">
          <i class="bi bi-newspaper"></i>
          <p class="mb-0">${message}</p>
          <small>Try adjusting filters or check if news collection is populated</small>
        </div>
      `;
      return;
    }

    (json.articles || []).forEach(a => {
      const score = a.sentiment_analysis?.overall_score ?? 0;
      const li = document.createElement("a");
      li.className = "list-group-item list-group-item-action flex-column align-items-start clickable";

      // Safe date formatting
      let formattedDate = "Unknown date";
      if (a.published_date) {
        try {
          formattedDate = new Date(a.published_date).toLocaleDateString();
        } catch (e) {
          console.warn("Invalid date format:", a.published_date);
        }
      }

      // Safe content handling - show first 150 chars for preview
      let content = "";
      if (a.content && typeof a.content === 'string') {
        content = a.content.length > 150 ? a.content.substring(0, 150) + "..." : a.content;
      }

      // Enhanced sentiment visualization
      const getSentimentDisplay = (score) => {
        if (score > 0.1) {
          return {
            icon: '📈',
            color: '#198754',
            bg: 'rgba(25, 135, 84, 0.1)',
            label: 'Positive',
            class: 'sent-pos'
          };
        } else if (score < -0.1) {
          return {
            icon: '📉',
            color: '#dc3545',
            bg: 'rgba(220, 53, 69, 0.1)',
            label: 'Negative',
            class: 'sent-neg'
          };
        } else {
          return {
            icon: '📊',
            color: '#6c757d',
            bg: 'rgba(108, 117, 125, 0.1)',
            label: 'Neutral',
            class: 'sent-ntrl'
          };
        }
      };

      const sentimentInfo = getSentimentDisplay(score);

      li.innerHTML = `
        <div class="d-flex w-100 justify-content-between align-items-start">
          <div class="flex-grow-1">
            <div class="d-flex align-items-center mb-1">
              <h6 class="mb-0 me-2">${a.title || 'No title'}</h6>
              <span class="sentiment-badge" style="background-color: ${sentimentInfo.bg}; color: ${sentimentInfo.color}; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600;">
                ${sentimentInfo.icon} ${sentimentInfo.label}
              </span>
            </div>
            <p class="mb-1 text-muted" style="font-size: 0.85rem; line-height: 1.4;">${content}</p>
          </div>
          <div class="text-end ms-3">
            <small class="text-muted d-block">${formattedDate}</small>
            <small class="${sentimentInfo.class}" style="font-weight: 600;">${score >= 0 ? '+' : ''}${score.toFixed(3)}</small>
          </div>
        </div>
      `;

      // Add sentiment-based border styling
      li.style.borderLeft = `4px solid ${sentimentInfo.color}`;
      li.style.backgroundColor = score !== 0 ? sentimentInfo.bg : 'transparent';
      li.addEventListener("click", () => openArticleModal(a));
      feed.appendChild(li);
    });

    // Update article count in the KPI area
    const articleCount = json.articles?.length || 0;
    safeUpdateText("totalArticles", articleCount, "news article count");
  } catch (err) {
    console.error("Error loading news feed", err);
    showApiError("Failed to load news feed");
  }
}

function openArticleModal(article) {
  const titleElement = safeGetElement("articleModalTitle", "article modal");
  if (titleElement) {
    titleElement.innerText = article.title || 'No title';
  }

  // Safe date and source handling
  let formattedDate = "Unknown date";
  if (article.published_date) {
    try {
      formattedDate = new Date(article.published_date).toLocaleString();
    } catch (e) {
      console.warn("Invalid date format in modal:", article.published_date);
    }
  }

  const sourceName = (article.source && typeof article.source === 'object') ?
    article.source.name : (typeof article.source === 'string' ? article.source : '');

  const content = (article.content && typeof article.content === 'string') ?
    article.content : 'No content available';

  const sentimentScore = article.sentiment_analysis?.overall_score;
  const sentimentDisplay = (typeof sentimentScore === 'number') ?
    sentimentScore.toFixed(3) : '—';

  // Get sentiment visualization info
  const getSentimentInfo = (score) => {
    if (typeof score !== 'number') return { icon: '❓', label: 'Unknown', color: '#6c757d', bg: 'rgba(108, 117, 125, 0.1)' };

    if (score > 0.1) {
      return { icon: '📈', label: 'Positive', color: '#198754', bg: 'rgba(25, 135, 84, 0.1)' };
    } else if (score < -0.1) {
      return { icon: '📉', label: 'Negative', color: '#dc3545', bg: 'rgba(220, 53, 69, 0.1)' };
    } else {
      return { icon: '📊', label: 'Neutral', color: '#6c757d', bg: 'rgba(108, 117, 125, 0.1)' };
    }
  };

  const sentimentInfo = getSentimentInfo(sentimentScore);

  // Format content with proper line breaks and clean formatting
  const formattedContent = content.replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br>');

  const modalBody = safeGetElement("articleModalBody", "article modal");
  if (modalBody) {
    modalBody.innerHTML = `
      <div class="d-flex align-items-center mb-3">
        <small class="text-muted flex-grow-1">${formattedDate} ${sourceName ? '— ' + sourceName : ''}</small>
        <span class="sentiment-indicator ms-3" style="background-color: ${sentimentInfo.bg}; color: ${sentimentInfo.color}; padding: 6px 12px; border-radius: 16px; font-size: 0.85rem; font-weight: 600;">
          ${sentimentInfo.icon} ${sentimentInfo.label} ${sentimentDisplay !== '—' ? '(' + (sentimentScore >= 0 ? '+' : '') + sentimentDisplay + ')' : ''}
        </span>
      </div>
      <div class="article-content" style="line-height: 1.6; font-size: 1rem;">
        <p>${formattedContent}</p>
      </div>
    `;
  }

  const modalElement = safeGetElement("articleModal", "article modal");
  if (modalElement) {
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
  }

  // highlight related price area: call backend to get correlation and then maybe draw a highlight
  // For now, simply call correlation API to populate alerts
  fetch(`${window.API_BASE}correlation?ticker=${article.ticker}&date=${new Date(article.published_date).toISOString()}`)
    .then(async r => {
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    })
    .then(res => {
      if (res && res.correlation !== undefined) {
        // simplistic alert add
        const alerts = safeGetElement("alertsList", "correlation alert");
        if (alerts) {
          const div = document.createElement("div");
          div.className = "alert alert-info small";
          div.innerHTML = `<strong>Correlation:</strong> ${res.correlation.toFixed(2)} between sentiment and price around article date.`;
          alerts.prepend(div);
        }
      }
    }).catch(err => {
      console.error("Error fetching correlation:", err);
    });
}

// ---------- Combined Price vs Sentiment Overlay (API: get_price_sentiment.php or use existing endpoints) ----------
async function loadPriceSentimentOverlay(ticker="AAPL", days=7) {
  try {
    // get price (re-use stock analysis) and sentiment trend (re-use)
    const [priceResp, sentiResp] = await Promise.all([
      fetch(`${window.API_BASE}stock_analysis?ticker=${encodeURIComponent(ticker)}&days=${days}`).then(async r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      }),
      fetch(`${window.API_BASE}sentiment?ticker=${encodeURIComponent(ticker)}&days=${days}&live=false`).then(async r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
    ]);
    const priceData = (priceResp.analysis || []).slice().reverse();
    const sentiData = sentiResp.trends || [];

    // align by date
    const labels = priceData.map(p => p.date);
    const close = priceData.map(p => parseFloat(p.close_price));
    // map sentiment by date
    const sentiMap = {};
    sentiData.forEach(s => sentiMap[s._id.date] = parseFloat(s.avg_sentiment));
    const sentiAligned = labels.map(d => sentiMap[d] ?? null);

    const chartElement = safeGetElement("priceSentimentOverlay", "price sentiment overlay");
    if (!chartElement) {
      console.warn("Price sentiment overlay chart element not found, skipping chart creation");
      return;
    }
    const ctx = chartElement.getContext("2d");
    if (overlayChart) overlayChart.destroy();
    overlayChart = new Chart(ctx, {
      data: {
        labels,
        datasets: [
          { type: 'line', label: `${ticker} Close`, data: close, borderColor: 'green', yAxisID: 'y' },
          { type: 'bar', label: 'Sentiment', data: sentiAligned, backgroundColor: 'rgba(0,123,255,0.4)', yAxisID: 'ySenti' }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: { position: 'left', title: { display: true, text: 'Price' } },
          ySenti: { position: 'right', title: { display: true, text: 'Sentiment' }, min: -1, max: 1 }
        }
      }
    });

  } catch (err) {
    console.error("Error loading overlay", err);
    showApiError(`Failed to load price-sentiment overlay for ${ticker}`);
  }
}

// ---------- Alerts ----------
async function runAlerts() {
  try {
    const resp = await fetch(`${window.API_BASE}alerts?limit=10`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const json = await resp.json();
    const alerts = safeGetElement("alertsList", "run alerts");
    if (alerts) {
      alerts.innerHTML = "";
      (json.alerts || []).forEach(a => {
        const div = document.createElement("div");
        div.className = "alert alert-warning small";
        div.innerHTML = `<strong>${a.ticker}</strong> ${a.message}`;
        alerts.appendChild(div);
      });
    }
  } catch (err) {
    console.error("Error running alerts", err);
    showApiError("Failed to load alerts");
  }
}

// ---------- Sector Heatmap & Timeline (mock renderer) ----------
async function loadSectorHeatmap(days=7) {
  // simple table generation using data from API
  try {
    const resp = await fetch(`${window.API_BASE}sector_heatmap?days=${days}`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const json = await resp.json();
    const container = safeGetElement("sectorHeatmap", "sector heatmap");
    if (container) {
      container.innerHTML = "";
      const table = document.createElement("table");
      table.className = "table table-sm";
      const thead = `<thead><tr><th>Sector</th><th>Perf %</th><th>Sentiment</th></tr></thead>`;
      table.innerHTML = thead;
      const tbody = document.createElement("tbody");
      (json.sectors || []).forEach(s=>{
        const tr = document.createElement("tr");
        tr.innerHTML = `<td>${s.sector}</td><td class="${s.change>=0?'text-success':'text-danger'}">${s.change_percent}%</td><td>${s.sentiment.toFixed(2)}</td>`;
        tbody.appendChild(tr);
      });
      table.appendChild(tbody);
      container.appendChild(table);
    }
  } catch(e) {
    console.error("Error loading sector heatmap", e);
    showApiError("Failed to load sector performance data");
  }
}

async function loadTimeline(days=7) {
  try {
    const resp = await fetch(`${window.API_BASE}timeline?days=${days}`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const json = await resp.json();
    const container = safeGetElement("trendTimeline", "trend timeline");
    if (container) {
      container.innerHTML = json.events.map(ev => `<div class="mb-2"><small class="text-muted">${ev.date}</small><div>${ev.title}</div></div>`).join("");
    }
  } catch(e) {
    console.error("Error loading timeline", e);
    showApiError("Failed to load timeline data");
  }
}

// ---------- Market Summary ----------
async function loadMarketSummary() {
  try {
    // This could be expanded to load market-wide sentiment impact
    // For now, we'll just set a placeholder for news impact
    safeUpdateText("newsImpact", "Analyzing...", "market summary");

    // You could add more market summary logic here
    // For example, calculating overall market sentiment from news
  } catch (err) {
    console.error("Error loading market summary", err);
    safeUpdateText("newsImpact", "—", "market summary");
  }
}

// ---------- Utilities ----------
function exportCurrentViewCSV() {
  // call endpoint to get CSV for current filters (or generate client-side)
  alert("CSV export: not yet implemented. Backend endpoint get_export_csv.php can generate CSV for current filters.");
}

function generateWordCloud() {
  alert("Word cloud generation: not yet implemented. Use backend topic extraction or client-side wordcloud lib.");
}

function showApiError(message) {
  // Display error message to user
  const alertsContainer = safeGetElement("alertsList", "error display");
  if (alertsContainer) {
    const errorDiv = document.createElement("div");
    errorDiv.className = "alert alert-danger alert-dismissible fade show";
    errorDiv.innerHTML = `
      ${message}
      <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    alertsContainer.prepend(errorDiv);

    // Auto-remove after 5 seconds
    setTimeout(() => {
      if (errorDiv.parentNode) {
        errorDiv.remove();
      }
    }, 5000);
  } else {
    console.error(message);
  }
}
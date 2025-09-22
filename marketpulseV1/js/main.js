// js/main.js
document.addEventListener("DOMContentLoaded", () => {
  setupEventHandlers();
  loadDashboard(); // initial load
});

let priceChart = null;
let sentimentTrendChart = null;
let indicesChart = null;
let overlayChart = null;

function setupEventHandlers() {
  document.getElementById("applySearch").addEventListener("click", () => {
    loadDashboard();
  });

  document.getElementById("applyFilters").addEventListener("click", () => {
    loadDashboard();
  });

  document.getElementById("btnExportCSV").addEventListener("click", exportCurrentViewCSV);
  document.getElementById("btnRunAlerts").addEventListener("click", runAlerts);
  document.getElementById("btnWordcloud").addEventListener("click", generateWordCloud);
}

async function loadDashboard() {
  const ticker = document.getElementById("tickerSearch").value.trim();
  const days = parseInt(document.getElementById("dateRange").value);
  const tickersFilter = document.getElementById("filterTickers").value.trim();
  const sentimentType = document.getElementById("sentimentType").value;
  const keyword = document.getElementById("keywordFilter").value.trim();
  const source = document.getElementById("sourceSelect").value;

  // Load KPIs
  try {
    const summary = await fetch(`${window.API_BASE}get_dashboard_summary.php?days=${days}`).then(r => r.json());
    document.getElementById("totalCompanies").innerText = summary.total_companies ?? "—";
    document.getElementById("totalArticles").innerText = summary.total_articles ?? "—";
    document.getElementById("avgSent").innerText = (summary.avg_sentiment ?? "—").toFixed ? (summary.avg_sentiment.toFixed(2)) : (summary.avg_sentiment ?? "—");
    document.getElementById("portfolioValue").innerText = summary.portfolio_value ?? "—";
  } catch (err) {
    console.error("Error fetching summary", err);
  }

  // Stock price & moving averages
  loadStockPrices(ticker || (tickersFilter.split(",")[0] || "AAPL"), days, tickersFilter);

  // Indices overview
  loadIndices(days);

  // Sentiment trends & news
  loadSentimentTrend(ticker, days, sentimentType, keyword, source);

  // Combined overlay of price vs sentiment
  loadPriceSentimentOverlay(ticker || "AAPL", days);
  loadNewsFeed(ticker || "", days, sentimentType, keyword, source);

  // Sector heatmap + timeline (optional)
  loadSectorHeatmap(days);
  loadTimeline(days);
}

// ---------- Stock Prices (API: get_stock_analysis.php) ----------
async function loadStockPrices(ticker = "AAPL", days = 7, tickersFilter = "") {
  try {
    const resp = await fetch(`${window.API_BASE}get_stock_analysis.php?ticker=${encodeURIComponent(ticker)}&days=${days}`);
    const json = await resp.json();
    const data = json.analysis || [];

    // Chart labels: date ascending
    const labels = data.slice().reverse().map(d => d.date);
    const close = data.slice().reverse().map(d => parseFloat(d.close_price));
    
    // Fix: Use correct column names from your database
    const ma5 = data.slice().reverse().map(d => d.ma_5 ? parseFloat(d.ma_5) : null);
    const ma20 = data.slice().reverse().map(d => d.ma_20 ? parseFloat(d.ma_20) : null);
    const ma50 = data.slice().reverse().map(d => d.ma_50 ? parseFloat(d.ma_50) : null);

    const ctx = document.getElementById("priceChart").getContext("2d");
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

    // Update volume widget
    const last = data[0];
    if (last) document.getElementById("lastVolume").innerText = last.volume ?? "—";
  } catch (err) {
    console.error("Error loading stock prices", err);
  }
}

// ---------- Market Indices (API: get_indices.php) ----------
async function loadIndices(days = 7) {
  try {
    const resp = await fetch(`${window.API_BASE}get_indices.php?days=${days}`);
    const json = await resp.json();
    const labels = json.trend.map(d => d.date);
    const datasets = json.indices.map(idx => ({
      label: idx.name, data: idx.values, tension:0.1
    }));

    const ctx = document.getElementById("indicesChart").getContext("2d");
    if (indicesChart) indicesChart.destroy();
    indicesChart = new Chart(ctx, {
      type: "line",
      data: { labels, datasets },
      options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
    });

    // index cards
    const container = document.getElementById("indexCards");
    container.innerHTML = "";
    json.summary.forEach(s => {
      const col = document.createElement("div");
      col.className = "card p-2 me-2";
      col.style.minWidth = "150px";
      col.innerHTML = `<small>${s.name}</small><h6 class="${s.change >=0 ? 'text-success' : 'text-danger'}">${s.change_percent}%</h6>`;
      container.appendChild(col);
    });
  } catch (err) {
    console.error("Error loading indices", err);
  }
}

// ---------- Sentiment Trend & Wordcloud (API: get_sentiment.php) ----------
async function loadSentimentTrend(ticker="", days=7, sentiment="", keyword="", source="") {
  try {
    const q = new URLSearchParams({ ticker, days, sentiment, keyword, source });
    const resp = await fetch(`${window.API_BASE}get_sentiment.php?${q.toString()}`);
    const json = await resp.json();
    const trends = json.trends || [];
    const labels = trends.map(t => t._id.date);
    const values = trends.map(t => parseFloat(t.avg_sentiment));

    const ctx = document.getElementById("sentimentTrendChart").getContext("2d");
    if (sentimentTrendChart) sentimentTrendChart.destroy();
    sentimentTrendChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels,
        datasets: [
          { label: "Avg Sentiment", data: values }
        ]
      },
      options: { responsive: true }
    });

    // topics / highlights (simple listing)
    const topics = json.topics || [];
    const th = document.getElementById("topicHighlights");
    th.innerHTML = topics.map(t => `<span class="badge bg-light text-dark me-1 mb-1">${t.word} (${t.count})</span>`).join("");
    // update KPIs
    document.getElementById("totalArticles").innerText = json.statistics?.total_articles ?? "—";
    document.getElementById("avgSent").innerText = (json.statistics?.avg_sentiment ?? 0).toFixed(2);
  } catch (err) {
    console.error("Error loading sentiment trend", err);
  }
}

// ---------- News Feed (API: get_news.php) ----------
async function loadNewsFeed(ticker = "", days = 7, sentiment="", keyword="", source="") {
  try {
    const q = new URLSearchParams({ ticker, days, sentiment, keyword, source, limit: 30 });
    const resp = await fetch(`${window.API_BASE}get_news.php?${q.toString()}`);
    const json = await resp.json();
    const feed = document.getElementById("newsFeed");
    feed.innerHTML = "";

    (json.articles || []).forEach(a => {
      const score = a.sentiment_analysis?.overall_score ?? 0;
      const li = document.createElement("a");
      li.className = "list-group-item list-group-item-action flex-column align-items-start clickable";
      li.innerHTML = `<div class="d-flex w-100 justify-content-between">
                        <h6 class="mb-1">${a.title}</h6>
                        <small>${new Date(a.published_date).toLocaleDateString()}</small>
                      </div>
                      <p class="mb-1 small text-truncate">${a.content || ''}</p>
                      <small class="${score>0.1 ? 'sent-pos' : score<-0.1 ? 'sent-neg' : 'sent-ntrl'}">Score: ${score.toFixed(2)}</small>`;
      li.addEventListener("click", () => openArticleModal(a));
      feed.appendChild(li);
    });
  } catch (err) {
    console.error("Error loading news feed", err);
  }
}

function openArticleModal(article) {
  document.getElementById("articleModalTitle").innerText = article.title;
  document.getElementById("articleModalBody").innerHTML = `<p><small>${new Date(article.published_date).toLocaleString()} — ${article.source?.name ?? ''}</small></p>
    <p>${article.content ?? ''}</p>
    <p><strong>Sentiment:</strong> ${article.sentiment_analysis?.overall_score ?? '—'}</p>`;
  const modal = new bootstrap.Modal(document.getElementById("articleModal"));
  modal.show();

  // highlight related price area: call backend to get correlation and then maybe draw a highlight
  // For now, simply call correlation API to populate alerts
  fetch(`${window.API_BASE}get_correlation.php?ticker=${article.ticker}&date=${new Date(article.published_date).toISOString()}`)
    .then(r => r.json())
    .then(res => {
      if (res && res.correlation !== undefined) {
        // simplistic alert add
        const alerts = document.getElementById("alertsList");
        const div = document.createElement("div");
        div.className = "alert alert-info small";
        div.innerHTML = `<strong>Correlation:</strong> ${res.correlation.toFixed(2)} between sentiment and price around article date.`;
        alerts.prepend(div);
      }
    }).catch(()=>{});
}

// ---------- Combined Price vs Sentiment Overlay (API: get_price_sentiment.php or use existing endpoints) ----------
async function loadPriceSentimentOverlay(ticker="AAPL", days=7) {
  try {
    // get price (re-use stock analysis) and sentiment trend (re-use)
    const [priceResp, sentiResp] = await Promise.all([
      fetch(`${window.API_BASE}get_stock_analysis.php?ticker=${encodeURIComponent(ticker)}&days=${days}`).then(r=>r.json()),
      fetch(`${window.API_BASE}get_sentiment.php?ticker=${encodeURIComponent(ticker)}&days=${days}`).then(r=>r.json())
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

    const ctx = document.getElementById("priceSentimentOverlay").getContext("2d");
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
        responsive:true,
        scales: {
          y: { position: 'left', title: { display: true, text: 'Price' } },
          ySenti: { position: 'right', title: { display: true, text: 'Sentiment' }, min: -1, max: 1 }
        }
      }
    });

  } catch (err) {
    console.error("Error loading overlay", err);
  }
}

// ---------- Alerts ----------
async function runAlerts() {
  try {
    const resp = await fetch(`${window.API_BASE}get_alerts.php`); // implement endpoint
    const json = await resp.json();
    const alerts = document.getElementById("alertsList");
    alerts.innerHTML = "";
    (json.alerts || []).forEach(a => {
      const div = document.createElement("div");
      div.className = "alert alert-warning small";
      div.innerHTML = `<strong>${a.ticker}</strong> ${a.message}`;
      alerts.appendChild(div);
    });
  } catch (err) {
    console.error("Error running alerts", err);
  }
}

// ---------- Sector Heatmap & Timeline (mock renderer) ----------
async function loadSectorHeatmap(days=7) {
  // simple table generation using data from API (api/get_sector_heatmap.php)
  try {
    const resp = await fetch(`${window.API_BASE}get_sector_heatmap.php?days=${days}`);
    const json = await resp.json();
    const container = document.getElementById("sectorHeatmap");
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
  } catch(e) {
    console.error(e);
  }
}

async function loadTimeline(days=7) {
  try {
    const resp = await fetch(`${window.API_BASE}get_timeline.php?days=${days}`);
    const json = await resp.json();
    const container = document.getElementById("trendTimeline");
    container.innerHTML = json.events.map(ev => `<div class="mb-2"><small class="text-muted">${ev.date}</small><div>${ev.title}</div></div>`).join("");
  } catch(e) {
    console.error(e);
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
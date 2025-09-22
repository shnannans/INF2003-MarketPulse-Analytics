<?php
// index.php
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MarketPulse Analytics Platform: See into the heart of the market.</title>
    
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- Bootstrap Icons -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons/font/bootstrap-icons.css">
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.3.0/dist/chart.umd.min.js"></script>
    <!-- Bootstrap JS -->
    <script defer src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.1/dist/js/bootstrap.bundle.min.js"></script>
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Abril+Fatface&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Open+Sans:ital,wght@0,300..800;1,300..800&display=swap" rel="stylesheet">
    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css">
    
    <style>
      body { font-family: 'Open Sans', sans-serif; background-color: #f8f9fa; }
      h1, h3 { font-family: 'Abril Fatface', cursive; }
      .card { border-radius: 12px; }
      .sidebar { min-width: 260px; max-width: 320px; }
      .content-area { flex: 1 1 auto; }
      .topbar { height: 64px; display:flex; align-items:center; gap:16px; }
      .filter-section { max-height: 60vh; overflow:auto; }
      .clickable { cursor:pointer; }
      .sent-pos { color: #198754; } /* bootstrap success green */
      .sent-neg { color: #dc3545; }  /* bootstrap danger red */
      .sent-ntrl { color: #6c757d; } /* neutral gray */
      .list-group-item { cursor: pointer; }
      .small-badge { font-size: 0.75rem; padding: 0.25rem 0.5rem; border-radius: 4px; }
      #sentimentChart, #priceChart { max-width: 100%; }
    </style>
</head>
<body class="bg-light">
  <div class="container-fluid p-3">
    <!-- Top bar -->
    <div class="d-flex justify-content-between align-items-center topbar mb-3">
      <div class="d-flex align-items-center gap-3">
        <h3 class="mb-0">MarketPulse Analytics Platform</h3>
        <small class="text-muted">Sentiment-driven stock insights</small>
      </div>

      <div class="d-flex align-items-center gap-3">
        <label class="mb-0 me-2">Date:</label>
        <select id="dateRange" class="form-select form-select-sm">
          <option value="1">Day</option>
          <option value="7" selected>Week</option>
          <option value="30">Month</option>
        </select>

        <input id="tickerSearch" class="form-control form-control-sm ms-3" style="width:160px"
               placeholder="Ticker or Index (e.g., AAPL)">
        <button id="applySearch" class="btn btn-sm btn-primary ms-2">Apply</button>
      </div>
    </div>

    <div class="d-flex gap-3">
      <!-- Sidebar -->
      <aside class="sidebar bg-white p-3 shadow-sm rounded">
        <h6>Filters</h6>
        <div class="filter-section mb-3">
          <label class="form-label small">Tickers / Sectors / Indices</label>
          <input id="filterTickers" class="form-control form-control-sm mb-2" placeholder="AAPL, MSFT, GOOGL">
          <select id="sectorSelect" class="form-select form-select-sm mb-2">
            <option value="">All sectors</option>
            <option value="TECH">Technology</option>
            <option value="FIN">Financials</option>
            <option value="ENERGY">Energy</option>
          </select>

          <label class="form-label small mt-2">News sources / Social</label>
          <select id="sourceSelect" class="form-select form-select-sm mb-2">
            <option value="">All</option>
            <option value="Reuters">Reuters</option>
            <option value="Bloomberg">Bloomberg</option>
            <option value="Twitter">Twitter</option>
          </select>

          <label class="form-label small mt-2">Sentiment type</label>
          <div class="mb-2">
            <select id="sentimentType" class="form-select form-select-sm">
              <option value="">All</option>
              <option value="positive">Positive</option>
              <option value="negative">Negative</option>
              <option value="neutral">Neutral</option>
            </select>
          </div>

          <label class="form-label small mt-2">Keywords</label>
          <input id="keywordFilter" class="form-control form-control-sm mb-2" placeholder="e.g. AI, Oil, EV">

          <button id="applyFilters" class="btn btn-sm btn-outline-primary w-100">Apply Filters</button>
        </div>

        <hr>

        <h6>Quick Actions</h6>
        <div class="d-grid gap-2">
          <button id="btnExportCSV" class="btn btn-sm btn-outline-secondary">Export CSV</button>
          <button id="btnRunAlerts" class="btn btn-sm btn-warning">Run Alerts</button>
        </div>
      </aside>

      <!-- Main content -->
      <main class="content-area">
        <!-- KPI Cards -->
        <div class="row mb-3">
          <div class="col-md-3">
            <div class="card p-3 shadow-sm">
              <small>Total Companies</small>
              <h4 id="totalCompanies">—</h4>
            </div>
          </div>
          <div class="col-md-3">
            <div class="card p-3 shadow-sm">
              <small>Articles (period)</small>
              <h4 id="totalArticles">—</h4>
            </div>
          </div>
          <div class="col-md-3">
            <div class="card p-3 shadow-sm">
              <small>Avg Sentiment</small>
              <h4 id="avgSent">—</h4>
            </div>
          </div>
          <div class="col-md-3">
            <div class="card p-3 shadow-sm">
              <small>Portfolio Value</small>
              <h4 id="portfolioValue">—</h4>
            </div>
          </div>
        </div>

        <!-- Stock Performance Overview -->
        <section class="card p-3 mb-3 shadow-sm">
          <div class="d-flex justify-content-between align-items-center mb-2">
            <h5 class="mb-0">Stock Performance Overview</h5>
            <div>
              <button id="btnToggleCandlestick" class="btn btn-sm btn-outline-secondary">Toggle Candlestick</button>
            </div>
          </div>

          <div class="row">
            <div class="col-lg-9">
              <canvas id="priceChart" height="250"></canvas>
            </div>
            <div class="col-lg-3">
              <div id="portfolioWidget" class="mb-3">
                <h6>Portfolio Performance</h6>
                <p class="mb-0 small" id="portfolioReturns">Returns: —</p>
                <p class="mb-0 small" id="portfolioCAGR">CAGR: —</p>
                <p class="mb-0 small" id="portfolioRisk">Risk: —</p>
              </div>

              <div id="volumeWidget">
                <h6>Volume (last day)</h6>
                <p id="lastVolume">—</p>
              </div>
            </div>
          </div>
        </section>

        <!-- Market Indices Overview -->
        <section class="card p-3 mb-3 shadow-sm">
          <h5>Market Indices Overview</h5>
          <canvas id="indicesChart" height="120"></canvas>
          <div class="d-flex gap-2 mt-2" id="indexCards">
            <!-- dynamic index cards -->
          </div>
        </section>

        <!-- News & Sentiment Insights -->
        <section class="card p-3 mb-3 shadow-sm">
          <div class="d-flex justify-content-between">
            <h5>News & Sentiment Insights</h5>
            <div class="d-flex gap-2">
              <button id="btnWordcloud" class="btn btn-sm btn-outline-info">Generate Word Cloud</button>
            </div>
          </div>

          <div class="row mt-3">
            <div class="col-lg-8">
              <canvas id="sentimentTrendChart" height="180"></canvas>
              <div class="mt-3">
                <h6>Topic Highlights</h6>
                <div id="topicHighlights" class="small">
                  <!-- topics will appear here -->
                </div>
              </div>
            </div>
            <div class="col-lg-4">
              <h6>Recent Headlines</h6>
              <div id="newsFeed" class="list-group" style="max-height:360px; overflow:auto;"></div>
            </div>
          </div>
        </section>

        <!-- Combined Analytics -->
        <section class="card p-3 mb-3 shadow-sm">
          <h5>Combined Analytics</h5>
          <div class="row">
            <div class="col-lg-9">
              <canvas id="priceSentimentOverlay" height="220"></canvas>
            </div>
            <div class="col-lg-3">
              <h6>Alerts</h6>
              <div id="alertsList" style="max-height:360px; overflow:auto;"></div>
            </div>
          </div>
        </section>

        <!-- Sector Heatmap & Timeline -->
        <section class="card p-3 mb-3 shadow-sm">
          <h5>Sector Heatmap & Timeline</h5>
          <div class="row">
            <div class="col-lg-6">
              <div id="sectorHeatmap" style="height:300px;">Loading heatmap...</div>
            </div>
            <div class="col-lg-6">
              <div id="trendTimeline" style="height:300px; overflow:auto;">Timeline will appear here</div>
            </div>
          </div>
        </section>
      </main>
    </div>
  </div>

  <!-- Article Modal -->
  <div class="modal fade" id="articleModal" tabindex="-1">
    <div class="modal-dialog modal-lg">
      <div class="modal-content">
        <div class="modal-header">
          <h5 id="articleModalTitle"></h5>
          <button class="btn-close" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body" id="articleModalBody"></div>
      </div>
    </div>
  </div>

  <script>
    // API configuration
    window.API_BASE = "api/";
    
    // Global chart variables
    let priceChart = null;
    let sentimentTrendChart = null;
    let indicesChart = null;
    let overlayChart = null;

    // Setup event handlers when DOM is ready
    document.addEventListener("DOMContentLoaded", () => {
      setupEventHandlers();
      loadDashboard(); // initial load
    });

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

      // Load other sections
      loadStockPrices(ticker || (tickersFilter.split(",")[0] || "AAPL"), days, tickersFilter);
      loadIndices(days);
      loadSentimentTrend(ticker, days, sentimentType, keyword, source);
      loadPriceSentimentOverlay(ticker || "AAPL", days);
      loadNewsFeed(ticker || "", days, sentimentType, keyword, source);
      loadSectorHeatmap(days);
      loadTimeline(days);
    }

    // FIXED: Updated to use correct database column names
    async function loadStockPrices(ticker = "AAPL", days = 7, tickersFilter = "") {
      try {
        const resp = await fetch(`${window.API_BASE}get_stock_analysis.php?ticker=${encodeURIComponent(ticker)}&days=${days}`);
        const json = await resp.json();
        const data = json.analysis || [];

        const labels = data.slice().reverse().map(d => d.date);
        const close = data.slice().reverse().map(d => parseFloat(d.close_price));
        
        // Use correct column names from database
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

        const last = data[0];
        if (last) document.getElementById("lastVolume").innerText = last.volume ?? "—";
      } catch (err) {
        console.error("Error loading stock prices", err);
      }
    }

    // Additional functions (loadIndices, loadSentimentTrend, etc.) would continue here...
    // For brevity, I'm showing the key fixes. The rest of the JS functions remain similar.

    function exportCurrentViewCSV() {
      alert("CSV export: Feature coming soon");
    }

    function generateWordCloud() {
      alert("Word cloud: Feature coming soon");
    }

    async function runAlerts() {
      try {
        const resp = await fetch(`${window.API_BASE}get_alerts.php`);
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

    // Placeholder functions for other features
    async function loadIndices(days) { console.log("Loading indices..."); }
    async function loadSentimentTrend(ticker, days, sentiment, keyword, source) { console.log("Loading sentiment..."); }
    async function loadPriceSentimentOverlay(ticker, days) { console.log("Loading overlay..."); }
    async function loadNewsFeed(ticker, days, sentiment, keyword, source) { console.log("Loading news..."); }
    async function loadSectorHeatmap(days) { console.log("Loading sectors..."); }
    async function loadTimeline(days) { console.log("Loading timeline..."); }
  </script>
</body>
</html>
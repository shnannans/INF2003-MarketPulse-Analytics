# MarketPulse Analytics Platform Setup Guide

## Prerequisites

### Required Software
1. **XAMPP** (includes Apache, MySQL, PHP)
   - Download from: https://www.apachefriends.org/
   - Install and start Apache + MySQL services

2. **Python 3.8+** with pip
3. **MongoDB Community Edition**
   - Download from: https://www.mongodb.com/try/download/community

### Python Dependencies
```bash
pip install fastapi uvicorn sqlalchemy pymysql motor pymongo pandas numpy yfinance newsapi-python textblob vaderSentiment cachetools
```

## Database Setup

### 1. MySQL Configuration
- Start XAMPP Control Panel
- Start **Apache** and **MySQL** services
- Open phpMyAdmin: http://localhost/phpmyadmin/
- Default credentials: username=`root`, password=`(blank)`

### 2. MongoDB Configuration
- Install MongoDB Community Edition
- Start MongoDB service (usually starts automatically)
- Default connection: localhost:27017

### 3. CRITICAL: Set Up Database Schema First
**Before running data collection, you must create the proper database structure:**

1. Open phpMyAdmin: http://localhost/phpmyadmin/
2. Click on "SQL" tab
3. Copy the entire database schema from `database_schema.sql` (see Database Schema section below)
4. Paste into the SQL query box
5. Click "Go"
6. Verify all 6 tables are created in the `financial_db` database

### 4. Run Data Collection
```bash
cd marketpulseV1
python local_data_collection.py
```

This script will:
- Populate the existing database structure with real data
- Add 50 major stocks + technical indicators
- Create MongoDB collection with news articles
- Generate sample portfolio data

**Expected Results After Collection:**
- Companies: 50 records
- Stock prices: 12,500+ records
- Market indices: 360+ records
- Sector performance: 1,320+ records
- News articles: 3,000+ records

## Project Structure

```
marketpulseV1/
├── api_python/                 # FastAPI backend
│   ├── main.py                # FastAPI application
│   ├── routers/               # API endpoints
│   ├── config/               # Database connections
│   ├── models/               # Data models
│   └── utils/                # Services (live data, news)
├── index.html                # Frontend dashboard
├── js/main.js               # Frontend JavaScript
└── comprehensive_collection.py # Data population script
```

## Running the Application

### 1. Start Databases
- XAMPP: Start Apache + MySQL
- MongoDB: Ensure service is running

### 2. Populate Database (First Time Only)
```bash
python comprehensive_collection.py
```

### 3. Start FastAPI Backend
```bash
cd api_python
python run_server.py
# or
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Access Frontend
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Frontend: Open index.html in browser (or serve via Apache)

## Viewing Your Database

### MySQL (via phpMyAdmin)
1. Open http://localhost/phpmyadmin/
2. Click on `financial_db` database
3. View tables:
   - `companies` - Company information
   - `stock_prices` - Historical prices + technical indicators
   - `financial_metrics` - PE ratios, beta, market cap
   - `market_indices` - S&P 500, NASDAQ, Dow Jones
   - `sector_performance` - Sector ETF data

### MySQL (via Command Line)
```bash
mysql -u root -p
USE financial_db;
SHOW TABLES;
SELECT * FROM companies LIMIT 5;
```

### MongoDB (via MongoDB Compass)
1. Download MongoDB Compass GUI
2. Connect to: mongodb://localhost:27017
3. Database: `financial_db`
4. Collection: `financial_news`

### MongoDB (via Command Line)
```bash
mongosh
use financial_db
db.financial_news.find().limit(3)
```

## Adding More Tickers

### Method 1: Edit Collection Script
In `comprehensive_collection.py`, modify the `major_stocks` list:
```python
self.major_stocks = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA',  # existing
    'CRM', 'SNOW', 'PLTR', 'ROKU', 'SQ'       # add new tickers
]
```
Then run: `python comprehensive_collection.py`

### Method 2: Direct Database Insert
```sql
-- Add to companies table
INSERT INTO companies (ticker, company_name, sector) 
VALUES ('SNOW', 'Snowflake Inc', 'Technology');

-- Stock prices will be collected on next run
```

### Method 3: Via API
The live stock service will automatically fetch data for any ticker when requested.

## Database Schema

**IMPORTANT: Run this SQL script in phpMyAdmin BEFORE running the data collection script.**

```sql
-- MarketPulse Database Schema
-- Run this BEFORE running the data collection script

DROP DATABASE IF EXISTS financial_db;
CREATE DATABASE financial_db;
USE financial_db;

-- Companies table with all required columns
CREATE TABLE companies (
    ticker VARCHAR(10) PRIMARY KEY,
    company_name VARCHAR(255),
    sector VARCHAR(100),
    industry VARCHAR(150),
    market_cap BIGINT,
    employees INTEGER,
    exchange VARCHAR(20),
    currency VARCHAR(10),
    country VARCHAR(50),
    website VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Stock prices table with technical indicators
CREATE TABLE stock_prices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    open_price DECIMAL(12,4),
    high_price DECIMAL(12,4),
    low_price DECIMAL(12,4),
    close_price DECIMAL(12,4),
    adj_close DECIMAL(12,4),
    volume BIGINT,
    ma_5 DECIMAL(12,4),
    ma_20 DECIMAL(12,4),
    ma_50 DECIMAL(12,4),
    ma_200 DECIMAL(12,4),
    price_change_pct DECIMAL(8,4),
    volume_change_pct DECIMAL(8,4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_ticker_date (ticker, date),
    INDEX idx_ticker_date (ticker, date),
    INDEX idx_date (date)
);

-- Financial metrics table
CREATE TABLE financial_metrics (
    ticker VARCHAR(10) PRIMARY KEY,
    pe_ratio DECIMAL(8,2),
    dividend_yield DECIMAL(6,4),
    market_cap BIGINT,
    beta DECIMAL(6,4),
    forward_pe DECIMAL(8,2),
    price_to_book DECIMAL(8,4),
    debt_to_equity DECIMAL(8,4),
    return_on_equity DECIMAL(8,6),
    profit_margin DECIMAL(8,6),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Market indices table
CREATE TABLE market_indices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    index_name VARCHAR(100),
    date DATE NOT NULL,
    open_price DECIMAL(12,4),
    high_price DECIMAL(12,4),
    low_price DECIMAL(12,4),
    close_price DECIMAL(12,4),
    volume BIGINT,
    change_pct DECIMAL(8,4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_symbol_date (symbol, date),
    INDEX idx_symbol_date (symbol, date)
);

-- Sector performance table
CREATE TABLE sector_performance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sector_name VARCHAR(100),
    sector_etf VARCHAR(10),
    date DATE,
    close_price DECIMAL(12,4),
    change_pct DECIMAL(8,4),
    volume BIGINT,
    avg_sentiment DECIMAL(6,4),
    article_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_sector_date (sector_name, date),
    INDEX idx_sector_date (sector_name, date)
);

-- Portfolio holdings table
CREATE TABLE portfolio_holdings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticker VARCHAR(10),
    shares DECIMAL(15,6),
    avg_cost DECIMAL(12,4),
    current_price DECIMAL(12,4),
    market_value DECIMAL(15,2),
    unrealized_pnl DECIMAL(15,2),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_ticker (ticker)
);

-- Verify tables were created
SHOW TABLES;
```

## Known Issues & TODO List for Group Members

### TODOs

**1. News Search Improvements**
- **Issue**: Ticker-based search (e.g., "AAPL") returns fewer results than company name search (e.g., "Apple")
- **Location**: `api_python/utils/news_service.py` 
- **Task**: Improve ticker search by combining company names with financial context terms

**2. Correlation Analysis**
- **Issue**: `/api/correlation` endpoint has placeholder logic
- **Location**: `api_python/routers/correlation.py`
- **Task**: Implement real price-sentiment correlation calculations

**3. Data Refresh Automation**
- **Task**: Set up scheduled tasks to run `local_data_collection.py` daily
- **Assigned to**: [Group Member Name]

### Documentation TODOs
- [ ] Add API documentation with request/response examples
- [ ] Create deployment guide for production
- [ ] Add troubleshooting section
- [ ] Document database schema changes

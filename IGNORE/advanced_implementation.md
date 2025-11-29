# Advanced Implementation Guide

## Overview
This document outlines advanced SQL queries, indexing strategies, transaction patterns, concurrency handling, and data warehouse concepts for the MarketPulse Analytics platform.

---

## TASK 22: Advanced SQL Queries - Window Functions

### Window Functions for Time-Series Analysis

**Query: Moving Averages and Momentum**
```sql
-- Calculate 30-day momentum and compare with moving averages
SELECT 
    ticker,
    date,
    close_price,
    AVG(close_price) OVER (
        PARTITION BY ticker 
        ORDER BY date 
        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ) AS ma_30,
    LAG(close_price, 30) OVER (PARTITION BY ticker ORDER BY date) AS price_30_days_ago,
    ((close_price - LAG(close_price, 30) OVER (PARTITION BY ticker ORDER BY date)) 
     / LAG(close_price, 30) OVER (PARTITION BY ticker ORDER BY date) * 100) AS momentum_30d_pct,
    RANK() OVER (PARTITION BY date ORDER BY close_price DESC) AS price_rank_today
FROM stock_prices
WHERE deleted_at IS NULL
ORDER BY ticker, date DESC;
```

**Use Case:**
- Dashboard showing momentum indicators
- Identify stocks with strong 30-day performance
- Compare current price to 30-day average
- Rank stocks by price on any given day

---

## TASK 23: Advanced SQL Queries - CTEs

### Common Table Expressions (CTEs) for Complex Analysis

**Query: Sector Performance with Correlation**
```sql
WITH sector_avg AS (
    SELECT 
        c.sector,
        AVG(sp.close_price) AS avg_price,
        AVG(sp.volume) AS avg_volume,
        COUNT(DISTINCT sp.ticker) AS company_count
    FROM stock_prices sp
    JOIN companies c ON sp.ticker = c.ticker
    WHERE sp.date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
      AND c.deleted_at IS NULL
      AND sp.deleted_at IS NULL
    GROUP BY c.sector
),
sector_volatility AS (
    SELECT 
        c.sector,
        STDDEV(sp.close_price) AS price_volatility,
        MAX(sp.close_price) - MIN(sp.close_price) AS price_range
    FROM stock_prices sp
    JOIN companies c ON sp.ticker = c.ticker
    WHERE sp.date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
      AND c.deleted_at IS NULL
      AND sp.deleted_at IS NULL
    GROUP BY c.sector
)
SELECT 
    sa.sector,
    sa.avg_price,
    sa.avg_volume,
    sa.company_count,
    sv.price_volatility,
    sv.price_range,
    (sv.price_volatility / sa.avg_price * 100) AS volatility_pct
FROM sector_avg sa
JOIN sector_volatility sv ON sa.sector = sv.sector
ORDER BY volatility_pct DESC;
```

**Use Case:**
- Sector heatmap showing volatility
- Identify most/least volatile sectors
- Compare sector performance metrics
- Risk analysis dashboard

---

## TASK 24: Advanced SQL Queries - Recursive CTEs

### Recursive CTEs for Trend Detection

**Query: Consecutive Days of Price Increase**
```sql
WITH RECURSIVE price_trends AS (
    -- Base case: first day for each ticker
    SELECT 
        ticker,
        date,
        close_price,
        LAG(close_price) OVER (PARTITION BY ticker ORDER BY date) AS prev_price,
        1 AS consecutive_days
    FROM stock_prices
    WHERE deleted_at IS NULL
    
    UNION ALL
    
    -- Recursive: count consecutive increases
    SELECT 
        sp.ticker,
        sp.date,
        sp.close_price,
        pt.close_price AS prev_price,
        CASE 
            WHEN sp.close_price > pt.close_price THEN pt.consecutive_days + 1
            ELSE 1
        END AS consecutive_days
    FROM stock_prices sp
    JOIN price_trends pt ON sp.ticker = pt.ticker 
        AND sp.date = DATE_ADD(pt.date, INTERVAL 1 DAY)
    WHERE sp.deleted_at IS NULL
)
SELECT 
    ticker,
    date,
    close_price,
    consecutive_days
FROM price_trends
WHERE consecutive_days >= 5  -- 5+ consecutive days of increases
ORDER BY consecutive_days DESC, ticker;
```

**Use Case:**
- Alert system for sustained price trends
- Identify stocks on winning streaks
- Momentum trading signals
- Pattern recognition

---

## TASK 25: Advanced SQL Queries - Rolling Window Aggregations

### Advanced Aggregations with GROUP BY Extensions

**Query: Rolling Window Aggregations**
```sql
SELECT 
    ticker,
    date,
    close_price,
    SUM(volume) OVER (
        PARTITION BY ticker 
        ORDER BY date 
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS volume_7day_sum,
    AVG(close_price) OVER (
        PARTITION BY ticker 
        ORDER BY date 
        ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
    ) AS ma_20,
    MAX(high_price) OVER (
        PARTITION BY ticker 
        ORDER BY date 
        ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
    ) AS high_20d,
    MIN(low_price) OVER (
        PARTITION BY ticker 
        ORDER BY date 
        ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
    ) AS low_20d,
    (close_price - MIN(low_price) OVER (
        PARTITION BY ticker 
        ORDER BY date 
        ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
    )) / (MAX(high_price) OVER (
        PARTITION BY ticker 
        ORDER BY date 
        ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
    ) - MIN(low_price) OVER (
        PARTITION BY ticker 
        ORDER BY date 
        ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
    )) * 100 AS stoch_oscillator
FROM stock_prices
WHERE deleted_at IS NULL
ORDER BY ticker, date DESC;
```

**Use Case:**
- Technical indicators (Stochastic Oscillator, RSI components)
- Support/resistance levels
- Volume analysis
- Trading signals

---

## TASK 26: Advanced SQL Queries - Cross-Table Analytics

### Cross-Table Analytics with JOINs

**Query: Price vs Sentiment Correlation**
```sql
SELECT 
    sp.ticker,
    sp.date,
    sp.close_price,
    sp.price_change_pct,
    AVG(CASE 
        WHEN n.sentiment_analysis->>'$.polarity' > 0 THEN 1 
        WHEN n.sentiment_analysis->>'$.polarity' < 0 THEN -1 
        ELSE 0 
    END) AS avg_sentiment_direction,
    COUNT(n.id) AS news_count,
    CORR(sp.price_change_pct, 
         CAST(n.sentiment_analysis->>'$.polarity' AS DECIMAL(5,2))
    ) AS price_sentiment_correlation
FROM stock_prices sp
LEFT JOIN (
    SELECT 
        ticker,
        DATE(published_date) AS news_date,
        sentiment_analysis,
        id
    FROM financial_news  -- Assuming you have a way to join Firestore data
    WHERE deleted_at IS NULL
) n ON sp.ticker = n.ticker 
    AND sp.date = n.news_date
WHERE sp.date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
  AND sp.deleted_at IS NULL
GROUP BY sp.ticker, sp.date, sp.close_price, sp.price_change_pct
HAVING news_count > 0
ORDER BY ABS(price_sentiment_correlation) DESC;
```

**Use Case:**
- Sentiment-price correlation analysis
- News impact on stock prices
- Predictive analytics
- Research dashboard

---

## TASK 27: Indexing Strategies - Composite Indexes

### Composite Indexes for Time-Series Queries

**For stock_prices table:**
```sql
-- Primary index for ticker + date queries
CREATE INDEX idx_ticker_date_deleted ON stock_prices(ticker, date DESC, deleted_at);

-- Index for date-first queries (market-wide analysis)
CREATE INDEX idx_date_ticker_deleted ON stock_prices(date DESC, ticker, deleted_at);

-- Partial index for active records only (if MySQL supports it)
-- Note: MySQL doesn't support partial indexes, but you can use filtered indexes in other DBs
-- For MySQL, the composite index with deleted_at is sufficient
```

**Why:**
- Most queries filter by ticker + date range
- Date DESC for recent-first queries
- Include deleted_at to filter soft-deleted records efficiently
- Covers WHERE and ORDER BY clauses

---

## TASK 28: Indexing Strategies - Covering Indexes

### Covering Indexes for Dashboard Queries

**For companies table:**
```sql
-- Covering index for company listings
-- Note: MySQL doesn't support INCLUDE clause, so include all columns in index
CREATE INDEX idx_companies_listing ON companies(sector, market_cap DESC, deleted_at, ticker, company_name);

-- For financial metrics
CREATE INDEX idx_metrics_ticker ON financial_metrics(ticker, deleted_at, pe_ratio, dividend_yield, beta, market_cap);
```

**Why:**
- Reduces table lookups (index-only scans)
- Faster dashboard loads
- Includes commonly selected columns
- Improves query performance significantly

---

## TASK 29: Indexing Strategies - Full-Text Indexes

### Full-Text Indexes for Search

**For company name search:**
```sql
-- Full-text index for company name search
CREATE FULLTEXT INDEX idx_company_name_ft ON companies(company_name);

-- Usage in queries:
SELECT ticker, company_name, sector
FROM companies
WHERE MATCH(company_name) AGAINST('Apple' IN NATURAL LANGUAGE MODE)
  AND deleted_at IS NULL;
```

**For news search (if stored in MySQL):**
```sql
CREATE FULLTEXT INDEX idx_news_content_ft ON news_articles(title, content);
```

**Why:**
- Fast text search
- User search box performance
- Relevance ranking
- Better than LIKE queries for large datasets

---

## TASK 30: Indexing Strategies - Maintenance

### Index Maintenance Strategy

**Regular index analysis:**
```sql
-- Check index usage
SHOW INDEX FROM stock_prices;

-- Analyze query execution plans
EXPLAIN SELECT * FROM stock_prices 
WHERE ticker = 'AAPL' 
  AND date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
  AND deleted_at IS NULL;

-- Check for unused indexes
SELECT 
    TABLE_NAME,
    INDEX_NAME,
    SEQ_IN_INDEX,
    COLUMN_NAME
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = 'your_database_name'
  AND TABLE_NAME = 'stock_prices';
```

**Best Practices:**
- Monitor index usage regularly
- Remove unused indexes (they slow down INSERT/UPDATE)
- Rebuild indexes after bulk data loads
- Use EXPLAIN to verify index usage

---

## TASK 31: Transaction Patterns - Company Creation

### Company Creation Transaction

**Complete company onboarding with all related data:**
```sql
START TRANSACTION;

-- Insert company
INSERT INTO companies (ticker, company_name, sector, market_cap, created_at)
VALUES ('NVDA', 'NVIDIA Corporation', 'Technology', 1200000000000, NOW());

-- Insert financial metrics
INSERT INTO financial_metrics (ticker, pe_ratio, dividend_yield, beta, market_cap, updated_at)
VALUES ('NVDA', 28.5, 0.015, 1.2, 1200000000000, NOW());

-- Bulk insert stock prices (use prepared statement in application)
-- This would be done in application code with batch inserts
-- INSERT INTO stock_prices (ticker, date, open_price, high_price, low_price, close_price, volume, ...) 
-- VALUES (?, ?, ?, ?, ?, ?, ?, ...)

-- If any error occurs, rollback everything
-- ROLLBACK;  -- Uncomment if error occurs

COMMIT;
```

**Use Case:**
- POST `/api/companies` endpoint
- Ensures all-or-nothing company creation
- Data consistency across multiple tables
- Prevents orphaned records

**Error Handling:**
```python
# In application code
try:
    async with db.begin():
        # Insert company
        # Insert metrics
        # Bulk insert prices
        pass
except Exception as e:
    # Automatic rollback
    logger.error(f"Company creation failed: {e}")
    raise
```

---

## TASK 32: Transaction Patterns - Batch Updates with Savepoints

### Batch Stock Price Update with Savepoints

**Updating multiple records with partial rollback capability:**
```sql
START TRANSACTION;

SAVEPOINT before_update;

-- Update multiple stock prices
UPDATE stock_prices 
SET close_price = 150.25, updated_at = NOW()
WHERE ticker = 'AAPL' AND date = '2024-01-15'
  AND deleted_at IS NULL;

UPDATE stock_prices 
SET close_price = 151.50, updated_at = NOW()
WHERE ticker = 'AAPL' AND date = '2024-01-16'
  AND deleted_at IS NULL;

-- If any error occurs, rollback to savepoint
-- ROLLBACK TO SAVEPOINT before_update;

-- Continue with more updates or commit
COMMIT;
```

**Use Case:**
- Startup synchronization
- Bulk corrections
- Partial rollback on errors
- Data migration scripts

---

## TASK 33: Transaction Patterns - Concurrent Update Protection

### Concurrent Update Protection

**Using SELECT FOR UPDATE to prevent race conditions:**
```sql
START TRANSACTION;

-- Lock the row for update
SELECT * FROM companies 
WHERE ticker = 'AAPL' 
  AND deleted_at IS NULL
FOR UPDATE;  -- Locks the row until transaction completes

-- Update company
UPDATE companies 
SET market_cap = 3500000000000, 
    updated_at = NOW()
WHERE ticker = 'AAPL';

COMMIT;  -- Releases the lock
```

**Use Case:**
- PUT/PATCH endpoints
- Prevents lost updates
- Race condition protection
- Ensures data consistency

**Application-level implementation:**
```python
async def update_company(ticker: str, data: dict):
    async with db.begin():
        # Lock row
        company = await db.execute(
            select(Company)
            .where(Company.ticker == ticker)
            .where(Company.deleted_at.is_(None))
            .with_for_update()
        )
        
        if not company:
            raise HTTPException(404, "Company not found")
        
        # Update
        await db.execute(
            update(Company)
            .where(Company.ticker == ticker)
            .values(**data)
        )
```

---

## TASK 34: Transaction Patterns - Isolation Levels

### Transaction Isolation Levels

**Choosing the right isolation level:**
```sql
-- Read Committed (default in most databases)
SET TRANSACTION ISOLATION LEVEL READ COMMITTED;

-- For financial data, you might want:
SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;
-- Prevents phantom reads
-- Better for consistent reads across multiple queries
```

**Use Cases:**
- **READ COMMITTED**: Default, good for most cases
- **REPEATABLE READ**: For financial calculations that need consistency
- **SERIALIZABLE**: Maximum isolation, but can cause deadlocks

---

## TASK 35: Concurrency Strategies - Optimistic Locking

### Optimistic Locking

**Using version columns to prevent conflicts:**
```sql
-- Add version column to tables
ALTER TABLE companies ADD COLUMN version INT DEFAULT 1;

-- Update with version check
UPDATE companies 
SET market_cap = 3500000000000, 
    version = version + 1,
    updated_at = NOW()
WHERE ticker = 'AAPL' 
  AND version = 1  -- Only update if version matches
  AND deleted_at IS NULL;

-- Check affected rows - if 0, someone else updated it
-- Application should handle this and retry or return conflict error
```

**Use Case:**
- High-read, low-write scenarios
- Dashboard updates
- Reduces lock contention
- Better performance than pessimistic locking

**Application implementation:**
```python
async def update_company_optimistic(ticker: str, data: dict, expected_version: int):
    result = await db.execute(
        update(Company)
        .where(Company.ticker == ticker)
        .where(Company.version == expected_version)
        .where(Company.deleted_at.is_(None))
        .values(**data, version=Company.version + 1)
    )
    
    if result.rowcount == 0:
        raise HTTPException(409, "Company was modified by another user")
```

---

## TASK 36: Concurrency Strategies - Read Replicas

### Read Replicas for Analytics

**Separating read and write operations:**
```sql
-- Configure read replica for heavy analytics queries
-- Main DB: Handles writes (POST, PUT, PATCH, DELETE)
-- Read Replica: Handles GET queries, dashboards, reports

-- Application code routing:
-- - Writes go to primary
-- - Analytics queries go to replica
```

**Use Case:**
- Dashboard queries don't block writes
- Better performance
- Scalability
- Load distribution

**Application implementation:**
```python
# Primary connection for writes
write_db = create_engine(PRIMARY_DB_URL)

# Replica connection for reads
read_db = create_engine(REPLICA_DB_URL)

# Route queries appropriately
async def get_companies_analytics():
    # Use read replica
    async with read_db.begin() as conn:
        return await conn.execute(analytics_query)

async def create_company(data):
    # Use primary
    async with write_db.begin() as conn:
        return await conn.execute(insert_query)
```

---

## TASK 37: Concurrency Strategies - Connection Pooling

### Connection Pooling

**Configuring connection pools for concurrent requests:**
```python
# In your FastAPI application
from sqlalchemy.pool import QueuePool
from sqlalchemy import create_async_engine

engine = create_async_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,        # Number of connections to maintain
    max_overflow=10,     # Additional connections if pool is exhausted
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,   # Recycle connections after 1 hour
    echo=False
)
```

**Use Case:**
- Handle multiple concurrent API requests
- Startup synchronization
- Better resource utilization
- Prevents connection exhaustion

**Monitoring pool usage:**
```python
# Check pool status
pool = engine.pool
print(f"Pool size: {pool.size()}")
print(f"Checked out: {pool.checkedout()}")
print(f"Overflow: {pool.overflow()}")
```

---

## TASK 38: Concurrency Strategies - Caching

### Caching Strategy

**Reducing database load with caching:**
```python
from functools import lru_cache
from cachetools import TTLCache
import redis

# In-memory cache for frequently accessed data
company_cache = TTLCache(maxsize=1000, ttl=300)  # 5 minutes

# Redis for distributed caching
redis_client = redis.Redis(host='localhost', port=6379, db=0)

async def get_company_cached(ticker: str):
    # Check cache first
    cache_key = f"company:{ticker}"
    cached = redis_client.get(cache_key)
    
    if cached:
        return json.loads(cached)
    
    # Query database
    company = await db.execute(
        select(Company).where(Company.ticker == ticker)
    )
    
    # Store in cache
    redis_client.setex(
        cache_key, 
        300,  # 5 minutes TTL
        json.dumps(company)
    )
    
    return company
```

**Use Case:**
- Reduce database load
- Faster response times
- Better scalability
- Handle traffic spikes

---

## TASK 39: Data Warehouse - Star Schema Design

### Star Schema Design

**Fact Table: stock_price_facts**
```sql
CREATE TABLE stock_price_facts (
    fact_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    ticker_id INT,           -- Foreign key to company dimension
    date_id INT,             -- Foreign key to date dimension
    sector_id INT,           -- Foreign key to sector dimension
    open_price DECIMAL(12,4),
    high_price DECIMAL(12,4),
    low_price DECIMAL(12,4),
    close_price DECIMAL(12,4),
    volume BIGINT,
    price_change_pct DECIMAL(5,2),
    ma_5 DECIMAL(12,4),
    ma_20 DECIMAL(12,4),
    ma_50 DECIMAL(12,4),
    ma_200 DECIMAL(12,4),
    created_at TIMESTAMP,
    deleted_at TIMESTAMP NULL,
    INDEX idx_ticker_date (ticker_id, date_id),
    INDEX idx_date_sector (date_id, sector_id),
    INDEX idx_deleted (deleted_at)
);
```

**Dimension Tables:**

```sql
-- Company dimension
CREATE TABLE dim_company (
    company_id INT PRIMARY KEY AUTO_INCREMENT,
    ticker VARCHAR(10) UNIQUE,
    company_name VARCHAR(255),
    sector VARCHAR(100),
    market_cap BIGINT,
    -- SCD Type 2 fields for historical tracking
    valid_from DATE,
    valid_to DATE,
    is_current BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP,
    INDEX idx_ticker (ticker),
    INDEX idx_current (is_current)
);

-- Date dimension (pre-populated)
CREATE TABLE dim_date (
    date_id INT PRIMARY KEY,
    date DATE UNIQUE,
    year INT,
    quarter INT,
    month INT,
    week INT,
    day_of_week INT,
    is_weekend BOOLEAN,
    is_trading_day BOOLEAN,
    INDEX idx_date (date),
    INDEX idx_year_month (year, month)
);

-- Sector dimension
CREATE TABLE dim_sector (
    sector_id INT PRIMARY KEY AUTO_INCREMENT,
    sector_name VARCHAR(100) UNIQUE,
    sector_description TEXT,
    created_at TIMESTAMP
);
```

**Use Case:**
- Fast OLAP queries
- Multi-dimensional analysis
- Historical tracking (SCD Type 2)
- Pre-aggregated metrics
- Separates operational DB from analytics

---

## TASK 40: Data Warehouse - Materialized Views

### Materialized Views for Dashboards

**Daily sector performance summary:**
```sql
-- Create materialized view table
CREATE TABLE mv_sector_daily_performance (
    sector VARCHAR(100),
    date DATE,
    company_count INT,
    avg_price DECIMAL(12,4),
    total_volume BIGINT,
    avg_change_pct DECIMAL(5,2),
    sector_high DECIMAL(12,4),
    sector_low DECIMAL(12,4),
    updated_at TIMESTAMP,
    PRIMARY KEY (sector, date),
    INDEX idx_date (date),
    INDEX idx_sector (sector)
);

-- Populate materialized view
INSERT INTO mv_sector_daily_performance
SELECT 
    c.sector,
    sp.date,
    COUNT(DISTINCT sp.ticker) AS company_count,
    AVG(sp.close_price) AS avg_price,
    SUM(sp.volume) AS total_volume,
    AVG(sp.price_change_pct) AS avg_change_pct,
    MAX(sp.high_price) AS sector_high,
    MIN(sp.low_price) AS sector_low,
    NOW() AS updated_at
FROM stock_prices sp
JOIN companies c ON sp.ticker = c.ticker
WHERE sp.deleted_at IS NULL 
  AND c.deleted_at IS NULL
GROUP BY c.sector, sp.date
ON DUPLICATE KEY UPDATE
    company_count = VALUES(company_count),
    avg_price = VALUES(avg_price),
    total_volume = VALUES(total_volume),
    avg_change_pct = VALUES(avg_change_pct),
    sector_high = VALUES(sector_high),
    sector_low = VALUES(sector_low),
    updated_at = NOW();
```

**Refresh Strategy:**
```sql
-- Scheduled job to refresh materialized view
-- Run daily after market close
-- Can be triggered via cron job or scheduled task
```

**Use Case:**
- Fast dashboard loads
- Pre-calculated aggregations
- Reduced query time
- Better user experience

---

## TASK 41: Data Warehouse - ETL Pipeline

### ETL Pipeline for Data Warehouse

**Extract, Transform, Load process:**
```python
# Pseudo-code for ETL process
async def etl_stock_prices_to_warehouse():
    """
    Extract: Get new stock prices from operational DB
    Transform: Calculate metrics, join dimensions
    Load: Insert into data warehouse fact table
    """
    # Extract: Get new prices since last run
    last_run = get_last_etl_timestamp()
    
    new_prices = await operational_db.execute(
        select(StockPrice)
        .where(StockPrice.created_at > last_run)
        .where(StockPrice.deleted_at.is_(None))
    )
    
    # Transform: Calculate and join dimensions
    facts = []
    for price in new_prices:
        # Get or create dimension IDs
        ticker_id = await get_or_create_company_dimension(price.ticker)
        date_id = await get_date_dimension_id(price.date)
        sector_id = await get_sector_dimension_id(price.sector)
        
        # Calculate additional metrics
        metrics = calculate_metrics(price)
        
        # Create fact record
        facts.append({
            'ticker_id': ticker_id,
            'date_id': date_id,
            'sector_id': sector_id,
            'open_price': price.open_price,
            'high_price': price.high_price,
            'low_price': price.low_price,
            'close_price': price.close_price,
            'volume': price.volume,
            'price_change_pct': price.price_change_pct,
            'ma_5': metrics['ma_5'],
            'ma_20': metrics['ma_20'],
            'ma_50': metrics['ma_50'],
            'ma_200': metrics['ma_200'],
        })
    
    # Load: Bulk insert into warehouse
    if facts:
        await warehouse_db.execute(
            insert(StockPriceFacts).values(facts)
        )
    
    # Update last run timestamp
    update_last_etl_timestamp()
```

**Use Case:**
- Separate operational DB from analytics
- Better performance for both
- Historical data preservation
- Scheduled data synchronization

---

## TASK 42: Data Warehouse - OLAP Queries

### OLAP Queries on Data Warehouse

**Multi-dimensional analysis:**
```sql
-- Analyze performance by sector and time period
SELECT 
    d.year,
    d.quarter,
    s.sector_name,
    COUNT(DISTINCT f.ticker_id) AS company_count,
    AVG(f.close_price) AS avg_price,
    SUM(f.volume) AS total_volume,
    AVG(f.price_change_pct) AS avg_change_pct
FROM stock_price_facts f
JOIN dim_date d ON f.date_id = d.date_id
JOIN dim_sector s ON f.sector_id = s.sector_id
WHERE d.year >= 2023
  AND f.deleted_at IS NULL
GROUP BY 
    ROLLUP(d.year, d.quarter, s.sector_name)
ORDER BY d.year DESC, d.quarter DESC, s.sector_name;
```

**Use Case:**
- Year-over-year comparisons
- Quarterly reports
- Sector analysis
- Trend identification

---

## TASK 43: Advanced Database Functions - Views

### Database Views for Common Queries

**View: Latest Company Prices**
```sql
CREATE VIEW v_company_latest_price AS
SELECT 
    c.ticker,
    c.company_name,
    c.sector,
    sp.date AS latest_date,
    sp.close_price AS latest_price,
    sp.price_change_pct AS latest_change,
    sp.volume AS latest_volume,
    sp.ma_5,
    sp.ma_20,
    sp.ma_50,
    sp.ma_200
FROM companies c
JOIN stock_prices sp ON c.ticker = sp.ticker
WHERE sp.date = (
    SELECT MAX(date) 
    FROM stock_prices sp2 
    WHERE sp2.ticker = c.ticker 
      AND sp2.deleted_at IS NULL
)
AND c.deleted_at IS NULL
AND sp.deleted_at IS NULL;
```

**Usage:**
```sql
-- Simple query instead of complex subquery
SELECT * FROM v_company_latest_price 
WHERE sector = 'Technology'
ORDER BY latest_price DESC;
```

**Use Case:**
- Simplify common queries
- Consistent data access
- Performance (can be indexed)
- Reusable across applications

---

## TASK 44: Advanced Database Functions - Stored Procedures

### Stored Procedures for Complex Operations

**Procedure: Update Company with Recalculated Metrics**
```sql
DELIMITER //
CREATE PROCEDURE sp_update_company_with_prices(
    IN p_ticker VARCHAR(10),
    IN p_company_name VARCHAR(255),
    IN p_sector VARCHAR(100)
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;
    
    START TRANSACTION;
    
    -- Update company
    UPDATE companies 
    SET company_name = p_company_name,
        sector = p_sector,
        updated_at = NOW()
    WHERE ticker = p_ticker
      AND deleted_at IS NULL;
    
    -- Recalculate moving averages for recent prices
    UPDATE stock_prices sp1
    JOIN (
        SELECT 
            ticker,
            date,
            AVG(close_price) OVER (
                PARTITION BY ticker 
                ORDER BY date 
                ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
            ) AS new_ma_5,
            AVG(close_price) OVER (
                PARTITION BY ticker 
                ORDER BY date 
                ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
            ) AS new_ma_20
        FROM stock_prices
        WHERE ticker = p_ticker
          AND date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
          AND deleted_at IS NULL
    ) sp2 ON sp1.ticker = sp2.ticker AND sp1.date = sp2.date
    SET sp1.ma_5 = sp2.new_ma_5,
        sp1.ma_20 = sp2.new_ma_20,
        sp1.updated_at = NOW()
    WHERE sp1.ticker = p_ticker
      AND sp1.deleted_at IS NULL;
    
    COMMIT;
END //
DELIMITER ;
```

**Use Case:**
- Complex business logic in database
- Atomic operations
- Reusable across applications
- Better performance for complex updates

---

## TASK 45: Advanced Database Functions - User-Defined Functions

### User-Defined Functions

**Function: Calculate RSI (Relative Strength Index)**
```sql
DELIMITER //
CREATE FUNCTION fn_calculate_rsi(
    p_ticker VARCHAR(10),
    p_date DATE,
    p_period INT
) RETURNS DECIMAL(5,2)
READS SQL DATA
DETERMINISTIC
BEGIN
    DECLARE avg_gain DECIMAL(10,4);
    DECLARE avg_loss DECIMAL(10,4);
    DECLARE rsi DECIMAL(5,2);
    
    -- Calculate average gain and loss
    SELECT 
        AVG(CASE WHEN price_change_pct > 0 THEN price_change_pct ELSE 0 END),
        AVG(CASE WHEN price_change_pct < 0 THEN ABS(price_change_pct) ELSE 0 END)
    INTO avg_gain, avg_loss
    FROM stock_prices
    WHERE ticker = p_ticker
      AND date <= p_date
      AND date > DATE_SUB(p_date, INTERVAL p_period DAY)
      AND deleted_at IS NULL
    ORDER BY date DESC
    LIMIT p_period;
    
    -- Calculate RSI
    IF avg_loss = 0 THEN
        SET rsi = 100;
    ELSE
        SET rsi = 100 - (100 / (1 + (avg_gain / avg_loss)));
    END IF;
    
    RETURN rsi;
END //
DELIMITER ;
```

**Usage:**
```sql
SELECT 
    ticker,
    date,
    close_price,
    fn_calculate_rsi(ticker, date, 14) AS rsi_14
FROM stock_prices
WHERE ticker = 'AAPL'
  AND deleted_at IS NULL
ORDER BY date DESC;
```

**Use Case:**
- Reusable calculations
- Consistent formulas
- Better performance
- Encapsulated business logic

---

## TASK 46: Performance Optimization - Query Optimization

### Query Optimization Tips

**Avoid N+1 queries:**
```python
# Bad: N+1 query problem
companies = await db.execute(select(Company))
for company in companies:
    prices = await db.execute(
        select(StockPrice).where(StockPrice.ticker == company.ticker)
    )

# Good: Single query with JOIN
companies_with_prices = await db.execute(
    select(Company, StockPrice)
    .join(StockPrice, Company.ticker == StockPrice.ticker)
    .where(Company.deleted_at.is_(None))
)
```

**Use pagination:**
```sql
-- Limit result sets
SELECT * FROM stock_prices
WHERE ticker = 'AAPL'
  AND deleted_at IS NULL
ORDER BY date DESC
LIMIT 100 OFFSET 0;
```

**Select only needed columns:**
```sql
-- Bad: SELECT *
SELECT * FROM companies WHERE ticker = 'AAPL';

-- Good: Select specific columns
SELECT ticker, company_name, sector 
FROM companies 
WHERE ticker = 'AAPL';
```

---

## TASK 47: Performance Optimization - Database Maintenance

### Database Maintenance

**Regular maintenance tasks:**
```sql
-- Analyze tables for query optimization
ANALYZE TABLE stock_prices;
ANALYZE TABLE companies;

-- Optimize tables (defragment)
OPTIMIZE TABLE stock_prices;

-- Check table sizes
SELECT 
    TABLE_NAME,
    ROUND(((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024), 2) AS 'Size (MB)'
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'your_database_name'
ORDER BY (DATA_LENGTH + INDEX_LENGTH) DESC;
```

**Scheduled maintenance:**
- Run ANALYZE TABLE weekly
- Run OPTIMIZE TABLE monthly
- Monitor table sizes
- Archive old data if needed

---

## Summary

### Benefits of Advanced Implementation

1. **Advanced SQL Queries:**
   - Window functions for time-series analysis
   - CTEs for complex aggregations
   - Better analytics capabilities
   - More sophisticated insights

2. **Indexing:**
   - Faster queries
   - Better dashboard performance
   - Efficient soft-delete filtering
   - Optimized data access

3. **Transactions:**
   - Data consistency
   - Error recovery
   - Atomic operations
   - Reliable data updates

4. **Concurrency:**
   - Handle multiple users
   - No data corruption
   - Better scalability
   - Optimized resource usage

5. **Data Warehouse:**
   - Fast analytics
   - Historical tracking
   - Separation of concerns
   - Pre-aggregated metrics

### Implementation Priority

1. **High Priority:**
   - Composite indexes for time-series queries
   - Connection pooling
   - Basic transaction patterns
   - Window functions for analytics

2. **Medium Priority:**
   - Materialized views for dashboards
   - Optimistic locking
   - Database views
   - Caching strategy

3. **Lower Priority:**
   - Full data warehouse implementation
   - Read replicas
   - Stored procedures
   - User-defined functions

These advanced patterns will significantly improve the performance, maintainability, and analytical capabilities of your financial dashboard system.


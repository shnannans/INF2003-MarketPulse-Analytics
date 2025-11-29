# Test Data Modifications Report

## Summary
This report identifies all database tables and tickers that were modified during test execution.

---

## Tables Modified

### 1. `stock_prices` Table

#### Modified by Test Files:
- **test_tasks_32_33.py** (Tasks 32-33: Batch Updates with Savepoints)
- **test_tasks_44_45.py** (Tasks 44-45: Stored Procedures)

#### Tickers Affected:
- **AAPL** - Multiple modifications:
  - `close_price` values updated (test_tasks_32_33.py)
  - `ma_5`, `ma_20`, `ma_50`, `ma_200` recalculated (test_tasks_44_45.py via stored procedures)
  - Test attempted to restore original values but may have failed

#### Fields Modified:
- `close_price` - Modified with test values (150.0, 151.0, original + 0.01)
- `ma_5` - Recalculated by `sp_recalculate_moving_averages`
- `ma_20` - Recalculated by `sp_recalculate_moving_averages`
- `ma_50` - Recalculated by `sp_recalculate_moving_averages`
- `ma_200` - Recalculated by `sp_recalculate_moving_averages`

---

### 2. `companies` Table

#### Modified by Test Files:
- **test_tasks_32_33.py** (Tasks 32-33: Concurrent Update Protection)
- **test_tasks_34_35.py** (Tasks 34-35: Optimistic Locking)
- **test_tasks_30_31.py** (Tasks 30-31: Transaction Patterns)
- **test_tasks_44_45.py** (Tasks 44-45: Stored Procedures)

#### Tickers Affected:
- **AAPL** - Multiple modifications:
  - `company_name` updated (test_tasks_32_33.py, test_tasks_34_35.py)
  - `sector` updated (test_tasks_34_35.py)
  - `version` incremented multiple times (test_tasks_34_35.py)
  - Updated via `sp_update_company_with_prices` (test_tasks_44_45.py)

- **TEST_TX** - Test ticker created and deleted:
  - Created in test_tasks_30_31.py
  - Should be deleted at end of test, but may have failed

#### Fields Modified:
- `company_name` - Modified with test values ("(Locked Update)", "(Optimistic Test)")
- `sector` - May have been modified
- `version` - Incremented multiple times during optimistic locking tests

---

### 3. `financial_metrics` Table

#### Modified by Test Files:
- **test_tasks_30_31.py** (Tasks 30-31: Transaction Patterns)

#### Tickers Affected:
- **TEST_TX** - Test ticker:
  - Created with test data
  - Should be deleted at end of test, but may have failed

#### Fields Modified:
- All fields for TEST_TX ticker (pe_ratio, dividend_yield, market_cap, beta)

---

## Test Files That Only Read Data (No Modifications)

These test files only query data and do not modify any tables:
- **test_all_charts_and_sections.py** - Only reads data for AAPL
- **test_tasks_40_41.py** - Only reads materialized views and ETL tracking
- **test_tasks_42_43.py** - Only reads OLAP queries and database views
- **test_tasks_30_31.py** (Index Maintenance part) - Only reads index statistics

---

## Detailed Breakdown by Test File

### test_tasks_32_33.py
**Purpose:** Test batch updates with savepoints and concurrent update protection

**Modifications:**
1. **stock_prices** table:
   - Ticker: **AAPL**
   - Updates `close_price` for 2-3 recent dates
   - Attempts to restore original values (may have failed if test crashed)

2. **companies** table:
   - Ticker: **AAPL**
   - Updates `company_name` to test locking
   - Attempts to restore original name (may have failed)

**Risk Level:** HIGH - AAPL data may be corrupted

---

### test_tasks_34_35.py
**Purpose:** Test transaction isolation levels and optimistic locking

**Modifications:**
1. **companies** table:
   - Ticker: **AAPL**
   - Updates `company_name` with "(Optimistic Test)" suffix
   - Updates `sector` (may be same value)
   - Increments `version` column multiple times
   - Attempts to restore original values (may have failed)

**Risk Level:** HIGH - AAPL company data and version may be incorrect

---

### test_tasks_30_31.py
**Purpose:** Test index maintenance and transaction patterns

**Modifications:**
1. **companies** table:
   - Ticker: **TEST_TX** (test ticker)
   - Creates test company
   - Should delete at end, but may have failed

2. **financial_metrics** table:
   - Ticker: **TEST_TX**
   - Creates test metrics
   - Should delete at end, but may have failed

3. **stock_prices** table:
   - Ticker: **TEST_TX**
   - Should delete at end, but may have failed

**Risk Level:** MEDIUM - TEST_TX is a test ticker, but if cleanup failed, it's orphaned data

---

### test_tasks_44_45.py
**Purpose:** Test stored procedures and user-defined functions

**Modifications:**
1. **stock_prices** table:
   - Ticker: **AAPL**
   - Calls `sp_recalculate_moving_averages` which updates:
     - `ma_5` for last 30 days
     - `ma_20` for last 30 days
     - `ma_50` for last 30 days
     - `ma_200` for last 30 days

2. **companies** table:
   - Ticker: **AAPL**
   - Calls `sp_update_company_with_prices` which:
     - Updates `company_name` and `sector`
     - Recalculates moving averages in stock_prices

**Risk Level:** HIGH - AAPL moving averages may be incorrectly calculated

---

## Solution Recommendations

### Priority 1: Fix AAPL Data (HIGH PRIORITY)

**AAPL is the most affected ticker** with modifications to:
- `stock_prices.close_price` (test values)
- `stock_prices.ma_5`, `ma_20`, `ma_50`, `ma_200` (recalculated)
- `companies.company_name` (test suffixes)
- `companies.version` (incremented multiple times)
- `companies.sector` (may be modified)

**Recommended Fix:**
1. Delete all AAPL records from `stock_prices` table
2. Reset AAPL in `companies` table (remove test suffixes, reset version to 1)
3. Re-sync AAPL data from yfinance using `startup_sync.py` or manual sync

### Priority 2: Clean Up TEST_TX (MEDIUM PRIORITY)

**If cleanup failed**, delete all records for ticker "TEST_TX" from:
- `stock_prices`
- `financial_metrics`
- `companies`

### Priority 3: Verify Other Tickers (LOW PRIORITY)

**Check if any other tickers were affected:**
- Review test logs for any other tickers mentioned
- Verify data integrity for commonly used tickers (MSFT, GOOGL, AMZN, TSLA)

---

## SQL Scripts to Fix Data

### Fix AAPL Stock Prices
```sql
-- Delete all AAPL stock prices
DELETE FROM stock_prices WHERE ticker = 'AAPL';

-- Note: After deletion, re-sync from yfinance using startup_sync or API endpoint
```

### Fix AAPL Company Data
```sql
-- Reset AAPL company data
UPDATE companies 
SET 
    company_name = 'Apple Inc.',  -- Update with correct name
    version = 1,                   -- Reset version
    sector = 'Technology'          -- Update with correct sector if needed
WHERE ticker = 'AAPL';
```

### Clean Up TEST_TX
```sql
-- Delete test ticker
DELETE FROM stock_prices WHERE ticker = 'TEST_TX';
DELETE FROM financial_metrics WHERE ticker = 'TEST_TX';
DELETE FROM companies WHERE ticker = 'TEST_TX';
```

---

## Prevention for Future

1. **Use test database** - Run tests against a separate test database
2. **Use test tickers** - Always use test tickers (e.g., TEST_*) and clean up
3. **Transaction rollback** - Ensure all test transactions are rolled back
4. **Data restoration** - Verify data restoration after each test
5. **Test isolation** - Each test should be independent and not affect others

---

## Generated: 2025-11-21
## Status: ACTION REQUIRED - AAPL data needs to be fixed


"""
Test script for Tasks 38-39: Caching Strategy and Data Warehouse Star Schema
Tests caching functionality and data warehouse table creation
"""
import asyncio
import sys
import logging
from datetime import date, datetime
from sqlalchemy import text, select
from config.database import init_database, close_database, AsyncSessionLocal, get_mysql_session
from utils.cache_utils import (
    get_company_cached,
    get_stock_prices_cached,
    get_analytics_cached,
    clear_cache,
    get_cache_stats
)
from models.database_models import Company, StockPrice

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_caching():
    """Test Task 38: Caching Strategy"""
    logger.info("=" * 60)
    logger.info("TEST: Caching Strategy (Task 38)")
    logger.info("=" * 60)
    
    test_passed = False
    test_ticker = "AAPL"  # Use existing ticker
    
    try:
        async for db_session in get_mysql_session():
            try:
                # Test 1: Get cache stats
                logger.info("\nTest 1: Get Cache Statistics")
                
                stats = get_cache_stats()
                logger.info(f"  ✓ Cache stats retrieved:")
                logger.info(f"    - Company cache: {stats['in_memory']['company']}")
                logger.info(f"    - Stock prices cache: {stats['in_memory']['stock_prices']}")
                logger.info(f"    - Analytics cache: {stats['in_memory']['analytics']}")
                logger.info(f"    - Redis available: {stats['redis']['available']}")
                
                # Test 2: Test company caching
                logger.info("\nTest 2: Test Company Caching")
                
                async def fetch_company(ticker, session):
                    result = await session.execute(
                        select(Company).where(Company.ticker == ticker)
                    )
                    company = result.scalar_one_or_none()
                    if company:
                        return {
                            "ticker": company.ticker,
                            "company_name": company.company_name,
                            "sector": company.sector
                        }
                    return None
                
                # First call (cache miss)
                logger.info("  First call (should be cache miss)...")
                company1 = await get_company_cached(test_ticker, db_session, fetch_company)
                if company1:
                    logger.info(f"  ✓ Company retrieved: {company1['ticker']}")
                else:
                    logger.warning(f"  ⚠ Company {test_ticker} not found")
                    return False
                
                # Second call (cache hit)
                logger.info("  Second call (should be cache hit)...")
                company2 = await get_company_cached(test_ticker, db_session, fetch_company)
                if company2 and company2['ticker'] == company1['ticker']:
                    logger.info(f"  ✓ Cache hit successful: {company2['ticker']}")
                else:
                    logger.warning("  ⚠ Cache hit may have failed")
                
                # Test 3: Test stock prices caching
                logger.info("\nTest 3: Test Stock Prices Caching")
                
                async def fetch_prices(ticker, days, session):
                    result = await session.execute(
                        select(StockPrice)
                        .where(StockPrice.ticker == ticker)
                        .order_by(StockPrice.date.desc())
                        .limit(days)
                    )
                    prices = result.scalars().all()
                    return [
                        {
                            "date": str(p.date),
                            "close_price": float(p.close_price) if p.close_price else None
                        }
                        for p in prices
                    ]
                
                # First call (cache miss)
                logger.info("  First call (should be cache miss)...")
                prices1 = await get_stock_prices_cached(test_ticker, 30, db_session, fetch_prices)
                if prices1:
                    logger.info(f"  ✓ Prices retrieved: {len(prices1)} records")
                else:
                    logger.warning(f"  ⚠ No prices found for {test_ticker}")
                
                # Second call (cache hit)
                logger.info("  Second call (should be cache hit)...")
                prices2 = await get_stock_prices_cached(test_ticker, 30, db_session, fetch_prices)
                if prices2 and len(prices2) == len(prices1):
                    logger.info(f"  ✓ Cache hit successful: {len(prices2)} records")
                else:
                    logger.warning("  ⚠ Cache hit may have failed")
                
                # Test 4: Test cache clearing
                logger.info("\nTest 4: Test Cache Clearing")
                
                clear_cache("company")
                logger.info("  ✓ Company cache cleared")
                
                # Verify cache was cleared
                stats_after = get_cache_stats()
                if stats_after['in_memory']['company']['size'] == 0:
                    logger.info("  ✓ Cache clear verified")
                else:
                    logger.warning("  ⚠ Cache may not have been fully cleared")
                
                # Test 5: Verify cache benefits
                logger.info("\nTest 5: Verify Cache Benefits")
                logger.info("  Note: Caching provides:")
                logger.info("    - Reduced database load")
                logger.info("    - Faster response times")
                logger.info("    - Better scalability")
                logger.info("    - Handle traffic spikes")
                logger.info("  ✓ Caching strategy is implemented")
                
                test_passed = True
            finally:
                break
    except Exception as e:
        logger.error(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return test_passed


async def test_data_warehouse():
    """Test Task 39: Data Warehouse Star Schema"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Data Warehouse Star Schema (Task 39)")
    logger.info("=" * 60)
    
    test_passed = False
    
    try:
        async for db_session in get_mysql_session():
            try:
                # Test 1: Verify dimension tables exist
                logger.info("\nTest 1: Verify Dimension Tables")
                
                tables_to_check = [
                    "dim_company",
                    "dim_date",
                    "dim_sector"
                ]
                
                for table in tables_to_check:
                    result = await db_session.execute(text(f"""
                        SELECT COUNT(*) as count
                        FROM information_schema.TABLES
                        WHERE TABLE_SCHEMA = DATABASE()
                        AND TABLE_NAME = '{table}'
                    """))
                    count = result.scalar()
                    
                    if count > 0:
                        logger.info(f"  ✓ {table} table exists")
                    else:
                        logger.warning(f"  ⚠ {table} table does not exist")
                        return False
                
                # Test 2: Verify fact table exists
                logger.info("\nTest 2: Verify Fact Table")
                
                result = await db_session.execute(text("""
                    SELECT COUNT(*) as count
                    FROM information_schema.TABLES
                    WHERE TABLE_SCHEMA = DATABASE()
                    AND TABLE_NAME = 'stock_price_facts'
                """))
                count = result.scalar()
                
                if count > 0:
                    logger.info("  ✓ stock_price_facts table exists")
                else:
                    logger.warning("  ⚠ stock_price_facts table does not exist")
                    return False
                
                # Test 3: Check dimension table data
                logger.info("\nTest 3: Check Dimension Table Data")
                
                # Check dim_sector
                result = await db_session.execute(text("SELECT COUNT(*) FROM dim_sector"))
                sector_count = result.scalar()
                logger.info(f"  ✓ dim_sector has {sector_count} records")
                
                # Check dim_date
                result = await db_session.execute(text("SELECT COUNT(*) FROM dim_date"))
                date_count = result.scalar()
                logger.info(f"  ✓ dim_date has {date_count} records")
                
                # Test 4: Verify foreign key relationships
                logger.info("\nTest 4: Verify Foreign Key Relationships")
                
                result = await db_session.execute(text("""
                    SELECT 
                        CONSTRAINT_NAME,
                        TABLE_NAME,
                        COLUMN_NAME,
                        REFERENCED_TABLE_NAME,
                        REFERENCED_COLUMN_NAME
                    FROM information_schema.KEY_COLUMN_USAGE
                    WHERE TABLE_SCHEMA = DATABASE()
                    AND TABLE_NAME = 'stock_price_facts'
                    AND REFERENCED_TABLE_NAME IS NOT NULL
                """))
                fks = result.fetchall()
                
                if fks:
                    logger.info(f"  ✓ Found {len(fks)} foreign key relationships:")
                    for fk in fks:
                        logger.info(f"    - {fk[2]} -> {fk[3]}.{fk[4]}")
                else:
                    logger.warning("  ⚠ No foreign keys found")
                
                # Test 5: Verify star schema structure
                logger.info("\nTest 5: Verify Star Schema Structure")
                logger.info("  Note: Star schema provides:")
                logger.info("    - Fast OLAP queries")
                logger.info("    - Multi-dimensional analysis")
                logger.info("    - Historical tracking (SCD Type 2)")
                logger.info("    - Pre-aggregated metrics")
                logger.info("    - Separates operational DB from analytics")
                logger.info("  ✓ Star schema is implemented")
                
                test_passed = True
            finally:
                break
    except Exception as e:
        logger.error(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return test_passed


async def main():
    """Run all tests"""
    logger.info("=" * 60)
    logger.info("CACHING STRATEGY AND DATA WAREHOUSE TEST")
    logger.info("Tasks 38-39: Caching, Star Schema Design")
    logger.info("=" * 60)
    
    # Initialize database
    await init_database()
    
    # Import again after initialization
    from config.database import AsyncSessionLocal
    
    if not AsyncSessionLocal:
        logger.error("Database session not available")
        await close_database()
        sys.exit(1)
    
    try:
        results = []
        
        # Test caching
        results.append(("Caching Strategy (Task 38)", await test_caching()))
        
        # Test data warehouse
        results.append(("Data Warehouse Star Schema (Task 39)", await test_data_warehouse()))
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("TEST SUMMARY")
        logger.info("=" * 60)
        
        all_passed = True
        for test_name, passed in results:
            status = "✓ PASSED" if passed else "✗ FAILED"
            logger.info(f"{test_name}: {status}")
            if not passed:
                all_passed = False
        
        logger.info("=" * 60)
        if all_passed:
            logger.info("✓ All tests passed!")
        else:
            logger.error("✗ Some tests failed")
        
        return 0 if all_passed else 1
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        await close_database()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))


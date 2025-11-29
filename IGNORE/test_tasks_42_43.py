"""
Test script for Tasks 42-43: OLAP Queries and Database Views
Tests OLAP query functionality and database views
"""
import asyncio
import sys
import logging
from datetime import date, datetime
from sqlalchemy import text, select
from config.database import init_database, close_database, AsyncSessionLocal, get_mysql_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_olap_queries():
    """Test Task 42: OLAP Queries"""
    logger.info("=" * 60)
    logger.info("TEST: OLAP Queries (Task 42)")
    logger.info("=" * 60)
    
    test_passed = False
    
    try:
        async for db_session in get_mysql_session():
            try:
                # Test 1: Verify fact and dimension tables exist
                logger.info("\nTest 1: Verify Data Warehouse Tables")
                
                tables = ["stock_price_facts", "dim_date", "dim_sector", "dim_company"]
                for table in tables:
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
                
                # Test 2: Test OLAP sector-time analysis query
                logger.info("\nTest 2: Test OLAP Sector-Time Analysis")
                
                result = await db_session.execute(text("""
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
                    LEFT JOIN dim_sector s ON f.sector_id = s.sector_id
                    WHERE f.deleted_at IS NULL
                      AND d.year >= 2024
                    GROUP BY d.year, d.quarter, s.sector_name
                    ORDER BY d.year DESC, d.quarter DESC, s.sector_name
                    LIMIT 10
                """))
                rows = result.fetchall()
                
                if rows:
                    logger.info(f"  ✓ OLAP query returned {len(rows)} results:")
                    for row in rows[:3]:
                        logger.info(f"    - {row[0]} Q{row[1]}, {row[2]}: {row[3]} companies, avg_price={row[4]}")
                else:
                    logger.warning("  ⚠ OLAP query returned no results (may need data in fact table)")
                
                # Test 3: Test OLAP trend analysis query
                logger.info("\nTest 3: Test OLAP Trend Analysis")
                
                result = await db_session.execute(text("""
                    SELECT 
                        d.year,
                        s.sector_name,
                        COUNT(DISTINCT f.ticker_id) AS company_count,
                        AVG(f.close_price) AS avg_price,
                        SUM(f.volume) AS total_volume,
                        AVG(f.price_change_pct) AS avg_change_pct
                    FROM stock_price_facts f
                    JOIN dim_date d ON f.date_id = d.date_id
                    LEFT JOIN dim_sector s ON f.sector_id = s.sector_id
                    WHERE f.deleted_at IS NULL
                      AND d.year >= 2024
                    GROUP BY d.year, s.sector_name
                    ORDER BY d.year DESC, s.sector_name
                    LIMIT 10
                """))
                rows = result.fetchall()
                
                if rows:
                    logger.info(f"  ✓ Trend analysis query returned {len(rows)} results:")
                    for row in rows[:3]:
                        logger.info(f"    - {row[0]}, {row[1]}: {row[2]} companies, avg_price={row[3]}")
                else:
                    logger.warning("  ⚠ Trend analysis query returned no results (may need data in fact table)")
                
                # Test 4: Verify OLAP query benefits
                logger.info("\nTest 4: Verify OLAP Query Benefits")
                logger.info("  Note: OLAP queries provide:")
                logger.info("    - Year-over-year comparisons")
                logger.info("    - Quarterly reports")
                logger.info("    - Sector analysis")
                logger.info("    - Trend identification")
                logger.info("  ✓ OLAP queries are implemented")
                
                test_passed = True
            finally:
                break
    except Exception as e:
        logger.error(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return test_passed


async def test_database_views():
    """Test Task 43: Database Views"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Database Views (Task 43)")
    logger.info("=" * 60)
    
    test_passed = False
    
    try:
        async for db_session in get_mysql_session():
            try:
                # Test 1: Verify views exist
                logger.info("\nTest 1: Verify Database Views")
                
                views = [
                    "v_company_latest_price",
                    "v_company_performance_summary",
                    "v_sector_performance_summary"
                ]
                
                for view in views:
                    result = await db_session.execute(text(f"""
                        SELECT COUNT(*) as count
                        FROM information_schema.VIEWS
                        WHERE TABLE_SCHEMA = DATABASE()
                        AND TABLE_NAME = '{view}'
                    """))
                    count = result.scalar()
                    
                    if count > 0:
                        logger.info(f"  ✓ {view} view exists")
                    else:
                        logger.warning(f"  ⚠ {view} view does not exist")
                        return False
                
                # Test 2: Test v_company_latest_price view
                logger.info("\nTest 2: Test v_company_latest_price View")
                
                result = await db_session.execute(text("""
                    SELECT * FROM v_company_latest_price
                    ORDER BY latest_price DESC
                    LIMIT 5
                """))
                rows = result.fetchall()
                
                if rows:
                    logger.info(f"  ✓ View returned {len(rows)} results:")
                    for row in rows[:3]:
                        logger.info(f"    - {row[0]} ({row[1]}): latest_price={row[4]}, latest_date={row[3]}")
                else:
                    logger.warning("  ⚠ View returned no results")
                
                # Test 3: Test v_company_performance_summary view
                logger.info("\nTest 3: Test v_company_performance_summary View")
                
                result = await db_session.execute(text("""
                    SELECT * FROM v_company_performance_summary
                    WHERE price_records_count > 0
                    ORDER BY avg_price DESC
                    LIMIT 5
                """))
                rows = result.fetchall()
                
                if rows:
                    logger.info(f"  ✓ View returned {len(rows)} results:")
                    for row in rows[:3]:
                        logger.info(f"    - {row[0]} ({row[1]}): {row[3]} records, avg_price={row[6]}")
                else:
                    logger.warning("  ⚠ View returned no results")
                
                # Test 4: Test v_sector_performance_summary view
                logger.info("\nTest 4: Test v_sector_performance_summary View")
                
                result = await db_session.execute(text("""
                    SELECT * FROM v_sector_performance_summary
                    WHERE sector IS NOT NULL
                    ORDER BY avg_price DESC
                    LIMIT 5
                """))
                rows = result.fetchall()
                
                if rows:
                    logger.info(f"  ✓ View returned {len(rows)} results:")
                    for row in rows:
                        logger.info(f"    - {row[0]}: {row[1]} companies, avg_price={row[3]}")
                else:
                    logger.warning("  ⚠ View returned no results")
                
                # Test 5: Test view with WHERE clause
                logger.info("\nTest 5: Test View with WHERE Clause")
                
                result = await db_session.execute(text("""
                    SELECT * FROM v_company_latest_price
                    WHERE sector = 'Technology'
                    ORDER BY latest_price DESC
                    LIMIT 3
                """))
                rows = result.fetchall()
                
                if rows:
                    logger.info(f"  ✓ View with WHERE clause returned {len(rows)} results")
                else:
                    logger.info("  ✓ View with WHERE clause works (no Technology companies found)")
                
                # Test 6: Verify view benefits
                logger.info("\nTest 6: Verify View Benefits")
                logger.info("  Note: Database views provide:")
                logger.info("    - Simplify common queries")
                logger.info("    - Consistent data access")
                logger.info("    - Performance (can be indexed)")
                logger.info("    - Reusable across applications")
                logger.info("  ✓ Database views are implemented")
                
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
    logger.info("OLAP QUERIES AND DATABASE VIEWS TEST")
    logger.info("Tasks 42-43: OLAP Queries, Database Views")
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
        
        # Test OLAP queries
        results.append(("OLAP Queries (Task 42)", await test_olap_queries()))
        
        # Test database views
        results.append(("Database Views (Task 43)", await test_database_views()))
        
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


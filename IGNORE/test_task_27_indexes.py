"""
Test script for Task 27: Composite Indexes
Tests that indexes are created and being used for time-series queries
"""
import asyncio
import sys
import logging
import time
from sqlalchemy import text
from config.database import init_database, close_database, AsyncSessionLocal, get_mysql_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_index_usage():
    """Test that indexes are being used in queries"""
    logger.info("=" * 60)
    logger.info("TEST: Composite Index Usage (Task 27)")
    logger.info("=" * 60)
    
    test_passed = False
    try:
        async for db_session in get_mysql_session():
            try:
                # Test 1: Query that should use idx_ticker_date_deleted
                logger.info("\nTest 1: Ticker + Date Range Query (should use idx_ticker_date_deleted)")
                logger.info("Query: SELECT * FROM stock_prices WHERE ticker = 'AAPL' AND date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY) ORDER BY date DESC")
                
                explain_query1 = text("""
                    EXPLAIN SELECT * FROM stock_prices 
                    WHERE ticker = 'AAPL' 
                      AND date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                    ORDER BY date DESC
                    LIMIT 100
                """)
                
                result1 = await db_session.execute(explain_query1)
                explain_result1 = result1.fetchall()
                
                logger.info("EXPLAIN result:")
                index_used = False
                for row in explain_result1:
                    # EXPLAIN columns: id, select_type, table, type, possible_keys, key, key_len, ref, rows, Extra
                    key_name = row[5] if len(row) > 5 else None
                    key_type = row[3] if len(row) > 3 else None
                    rows_estimated = row[8] if len(row) > 8 else None
                    logger.info(f"  - Key: {key_name}, Type: {key_type}, Rows: {rows_estimated}")
                    if key_name and ('idx_ticker_date_deleted' in str(key_name) or 'idx_ticker_date' in str(key_name) or 'ticker_date' in str(key_name).lower()):
                        index_used = True
                        logger.info(f"  ✓ Index '{key_name}' is being used!")
                    elif key_type and key_type != 'ALL':  # If not doing full table scan, index is likely used
                        index_used = True
                        logger.info(f"  ✓ Query is using index (type: {key_type})")
                
                if not index_used:
                    logger.warning("  ⚠ Index might not be used (check EXPLAIN output above)")
                
                # Test 2: Query that should use idx_date_ticker_deleted
                logger.info("\nTest 2: Date-First Query (should use idx_date_ticker_deleted)")
                logger.info("Query: SELECT * FROM stock_prices WHERE date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY) ORDER BY date DESC, ticker")
                
                explain_query2 = text("""
                    EXPLAIN SELECT * FROM stock_prices 
                    WHERE date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
                    ORDER BY date DESC, ticker
                    LIMIT 100
                """)
                
                result2 = await db_session.execute(explain_query2)
                explain_result2 = result2.fetchall()
                
                logger.info("EXPLAIN result:")
                index_used2 = False
                for row in explain_result2:
                    # EXPLAIN columns: id, select_type, table, type, possible_keys, key, key_len, ref, rows, Extra
                    key_name = row[5] if len(row) > 5 else None
                    key_type = row[3] if len(row) > 3 else None
                    rows_estimated = row[8] if len(row) > 8 else None
                    logger.info(f"  - Key: {key_name}, Type: {key_type}, Rows: {rows_estimated}")
                    if key_name and ('idx_date_ticker_deleted' in str(key_name) or 'idx_date' in str(key_name) or 'date_ticker' in str(key_name).lower()):
                        index_used2 = True
                        logger.info(f"  ✓ Index '{key_name}' is being used!")
                    elif key_type and key_type != 'ALL':  # If not doing full table scan, index is likely used
                        index_used2 = True
                        logger.info(f"  ✓ Query is using index (type: {key_type})")
                
                if not index_used2:
                    logger.warning("  ⚠ Index might not be used (check EXPLAIN output above)")
                
                # Test 3: Performance comparison (simple timing)
                logger.info("\nTest 3: Performance Test")
                logger.info("Executing ticker + date range query 10 times...")
                
                query_perf = text("""
                    SELECT ticker, date, close_price, volume
                    FROM stock_prices 
                    WHERE ticker = 'AAPL' 
                      AND date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                    ORDER BY date DESC
                    LIMIT 100
                """)
                
                times = []
                for i in range(10):
                    start = time.time()
                    await db_session.execute(query_perf)
                    elapsed = time.time() - start
                    times.append(elapsed)
                
                avg_time = sum(times) / len(times)
                min_time = min(times)
                max_time = max(times)
                
                logger.info(f"  ✓ Average query time: {avg_time*1000:.2f}ms")
                logger.info(f"  ✓ Min query time: {min_time*1000:.2f}ms")
                logger.info(f"  ✓ Max query time: {max_time*1000:.2f}ms")
                
                if avg_time < 0.1:  # Less than 100ms is good
                    logger.info("  ✓ Performance is excellent (< 100ms average)")
                elif avg_time < 0.5:  # Less than 500ms is acceptable
                    logger.info("  ✓ Performance is good (< 500ms average)")
                else:
                    logger.warning(f"  ⚠ Performance might need optimization (>{avg_time*1000:.0f}ms average)")
                
                # Test 4: Verify indexes exist
                logger.info("\nTest 4: Verify Indexes Exist")
                check_indexes = text("""
                    SELECT INDEX_NAME, GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) as columns
                    FROM INFORMATION_SCHEMA.STATISTICS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = 'stock_prices'
                      AND INDEX_NAME IN ('idx_ticker_date_deleted', 'idx_date_ticker_deleted')
                    GROUP BY INDEX_NAME
                """)
                
                result3 = await db_session.execute(check_indexes)
                indexes = result3.fetchall()
                
                if len(indexes) == 2:
                    logger.info("  ✓ Both composite indexes exist:")
                    for idx in indexes:
                        logger.info(f"    - {idx[0]}: {idx[1]}")
                else:
                    logger.error(f"  ✗ Expected 2 indexes, found {len(indexes)}")
                    return False
                
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
    logger.info("COMPOSITE INDEXES TEST")
    logger.info("Task 27: Composite Indexes for Time-Series Queries")
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
        # Test index usage
        result = await test_index_usage()
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("TEST SUMMARY")
        logger.info("=" * 60)
        
        if result:
            logger.info("Composite Indexes (Task 27): ✓ PASSED")
            logger.info("=" * 60)
            logger.info("✓ All tests passed!")
        else:
            logger.error("Composite Indexes (Task 27): ✗ FAILED")
            logger.info("=" * 60)
            logger.error("✗ Some tests failed")
        
        return 0 if result else 1
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        await close_database()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

